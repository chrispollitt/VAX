# httpd

A small web server for **OpenVMS VAX V7.3** in **DEC C V6.4**, with **CGI** (Perl, or DCL).
It replaces the Perl `HTTP::Daemon` script that used to run as `[LIGHTTPD.BIN]HTTPD_VAX.PL`.

* one request at a time, HTTP/1.0 style (one request per connection, no keep-alive)
* `GET` and `HEAD` for files, `GET` `HEAD` `POST` for CGIs
* a directory shows its `index.cgi`, `index.html` or `index.htm`, or else a listing
* `/~name/` is `[name.WEB]` on the web root's disk
* a client that connects and says nothing is dropped after 20 seconds
* about 1100 lines of C; builds on VMS and (for testing) with `gcc -ansi -pedantic` on a POSIX box

| file | what |
|------|------|
| `HTTPD.C` | the server |
| `BUILD_HTTPD.COM` | compile and link (`CC`, then `LINK`; it tries the likely socket libraries until one links) |
| `HTTPD_CGI.COM` | runs one CGI script; `HTTPD.EXE` calls it through `LIB$SPAWN` |
| `HTTPD_CONFIG.COM` | the settings (logical names): port, web root, Perl... |
| `HTTPD_RUN.COM` | what the detached process runs: `@HTTPD_CONFIG`, then `HTTPD.EXE` |
| `START_HTTPD.COM` | `@START_HTTPD` starts it detached as process `HTTPD`; `@START_HTTPD STOP` stops it |
| `www/` | the sample site: your old test pages, with the CGIs rewritten as ordinary CGIs |
| `tests/run_tests.sh` | builds the POSIX version and checks about 60 things with curl |

## Install (as done on cpvax)

Layout, as before: `[LIGHTTPD.BIN]` for the program, `[LIGHTTPD.WWW]` for the pages.
Copy the files over by FTP in **ASCII** mode (passive), build, copy the program, start it:

```
$ SET DEFAULT CPVAX$DUA1:[LIGHTTPD.SRC]        ! anywhere will do for the build
$ @BUILD_HTTPD
$ COPY HTTPD.EXE CPVAX$DUA1:[LIGHTTPD.BIN]
$ @CPVAX$DUA1:[LIGHTTPD.BIN]START_HTTPD
```

`HTTPD_RUN.COM`, `HTTPD_CGI.COM`, `HTTPD_CONFIG.COM` and `START_HTTPD.COM` go in `[LIGHTTPD.BIN]` next to
`HTTPD.EXE`. The log is `[LIGHTTPD.BIN]HTTPD.LOG` (one line per request).

To start it at boot, put `$ @CPVAX$DUA1:[LIGHTTPD.BIN]START_HTTPD` in `SYSTARTUP_VMS.COM`
(where the line that submitted the old `HTTPD_VAX` batch job was).

## Settings

Logical names, set in `HTTPD_CONFIG.COM`:

| name | meaning | default |
|------|---------|---------|
| `HTTPD_PORT` | port to listen on | 80 |
| `HTTPD_ROOT` | web root, written `dev:[dir.www]` | `CPVAX$DUA1:[LIGHTTPD.WWW]` |
| `HTTPD_USERDIR` | sub-directory shown for `/~name/` | `WEB` |
| `HTTPD_TMP` | where the request and reply scratch files go | `SYS$SCRATCH:` |
| `HTTPD_CGI` | the `HTTPD_CGI.COM` to use | `CPVAX$DUA1:[LIGHTTPD.BIN]HTTPD_CGI.COM` |
| `HTTPD_PERL` | the Perl image | `CPVAX$DUA1:[P]PERL.EXE` |
| `HTTPD_PERL_SETUP` | run before Perl if `PERLSHR` is not defined | `CPVAX$DUA1:[P]PERL_SETUP.COM` |
| `HTTPD_KEEP` | (any value) keep the scratch files, to see what a CGI was given | not set |

## CGI

Files ending in `.CGI` or `.PL` are run with Perl, `.COM` with DCL. They are **ordinary CGIs**:

* the request arrives in the usual CGI variables (`REQUEST_METHOD`, `QUERY_STRING`, `CONTENT_TYPE`,
  `CONTENT_LENGTH`, `SCRIPT_NAME`, `REMOTE_ADDR`, `HTTP_HOST`, `HTTP_USER_AGENT`, `HTTP_COOKIE`... for every request
  header; `HTTP_PROXY` is deliberately not passed). They are DCL symbols; `HTTPD_CGI.COM` tells Perl to read them
  (`PERL_ENV_TABLES`), so `$ENV{QUERY_STRING}` and `CGI.pm` just work
* the POST body is on `SYS$INPUT`
* the reply goes to `SYS$OUTPUT`: header lines, a blank line, the body. `Status: 404 Not Found` sets the status,
  `Location:` gives a 302, a script that prints no headers at all is sent as `text/html`, and an NPH script may start with
  its own `HTTP/1.0 200 OK`
* the reply is read back as **text**, so CGIs are for HTML, plain text, XML, JSON... not pictures

This is different from the old server, which ran the `.cgi` files with `eval` *inside* its own Perl process with `$q` and
`qprint` already defined. A script written for that needs `use CGI; my $q = CGI->new; print $q->header(...)` at the top and
`print` instead of `qprint`; `www/test.cgi`, `post.cgi`, `ping.cgi` and `wise.cgi` show the change. (`post.cgi` used to run
the text you posted as Perl; it now just shows it.)

Things that bit on the way, in case they bite again:

* Perl's `%ENV` ignores DCL symbols unless `PERL_ENV_TABLES` lists `CLISYM_LOCAL`
* `LIB$SPAWN`'s input file is the subprocess's stream of *commands*, so the body cannot go there; `HTTPD_CGI.COM`
  does `DEFINE/USER_MODE SYS$INPUT` instead (a plain `DEFINE` does not survive in a detached process)
* `RUN/DETACHED` needs `/AUTHORIZE`, otherwise the process gets the small system default quotas and Perl fails with
  `%SYSTEM-F-EXBYTLM` or silently (`glob` and `system` return nothing)
* TCPware refuses `SO_RCVTIMEO` (status 0x34C); the read timeout uses `select()`
* `keys %ENV` on VMS Perl walks every logical name table; do not use it to list the CGI variables

## Not here

Keep-alive, `PATH_INFO`, authentication, byte ranges, caching headers, binary CGI output, and a time limit for a CGI
(one that never ends stops the server; `STOP HTTPD` and start it again).

## Why the old server stopped working

The old script ends with `Can't call method "url" on an undefined value at httpd_vax.pl line 148` in every log from
October 2026. `HTTP::Daemon->new(LocalAddr => hostname(), ...)` returned nothing: `hostname()` now answers
`cpvax.lan` (the TCPware domain name, `TCPWARE_DOMAINNAME`), and the VAX's own resolver cannot look that name up
(`gethostbyname` fails, and the module says `Bad hostname 'cpvax.lan'`). In the 2023 log it was just `cpvax`. Leaving out
`LocalAddr` makes it bind fine. `SYSTARTUP_VMS.COM` submits the old job at every boot, so it crashed again each time.

## Testing

`tests/run_tests.sh` builds `HTTPD.C` for POSIX (CGIs run through `perl` and `sh`) and checks static files, directories,
URL tricks (`..`, `%00`, `[ ]`, `:`), the CGI environment, GET and POST (including a 200 KB body), `Status`, `Location`,
NPH, HEAD, and the CGI.pm samples. On cpvax the same things were checked with curl from cpbee, plus the idle-connection
timeout and `wise.cgi`.
