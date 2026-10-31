/* HTTPD.C - a small web server for OpenVMS, with CGI.
 *
 * Written for DEC C V6.4 on OpenVMS VAX V7.3 (ANSI C89, TCPware or UCX sockets);
 * also builds with "gcc -ansi -pedantic" on a POSIX box for testing, where it
 * serves a Unix directory and runs CGIs through /bin/sh.
 *
 * What it does:  one request at a time, HTTP/1.0 style (the connection is
 * closed after every reply), GET and HEAD for files, GET HEAD and POST for
 * CGIs.  A directory gets its index.cgi, index.html or index.htm, or else a
 * listing.  /~name/ is the directory [name.WEB] on the web root's disk.
 *
 * CGI:  a file ending in .CGI or .PL is run with Perl, one ending in .COM with
 * DCL.  The request is passed the standard CGI way: environment variables
 * (DCL symbols on VMS), the POST body on SYS$INPUT, the reply on SYS$OUTPUT.
 * The reply is the usual "Header: value" lines, a blank line, the body.  A
 * "Status: 404 Not Found" line sets the status, "Location:" makes a redirect.
 * An NPH script may start with its own "HTTP/1.0 200 OK" line.  The text
 * output is read back as text, so a CGI is for text (HTML, plain, XML...).
 *
 * Settings come from logical names (environment variables on POSIX):
 *    HTTPD_PORT      port to listen on                       [80]
 *    HTTPD_ROOT      web root, "dev:[dir.www]"               [CPVAX$DUA1:[LIGHTTPD.WWW]]
 *    HTTPD_USERDIR   sub-directory of [name] for /~name/     [WEB]
 *    HTTPD_CGI       HTTPD_CGI.COM, the procedure that runs a CGI  (VMS only)
 *    HTTPD_PERL      the Perl image (read by HTTPD_CGI.COM; on POSIX the perl command)
 *    HTTPD_PERL_SETUP  a procedure HTTPD_CGI.COM runs before Perl (PERL_SETUP.COM)  (VMS only)
 *    HTTPD_TMP       where the request/reply scratch files go [SYS$SCRATCH:]
 *    HTTPD_KEEP      (any value) do not delete the scratch files, to see what a CGI was given
 *
 * Not here (on purpose): keep-alive, timeouts for CGIs, authentication,
 * PATH_INFO, ranges, caching headers.  A CGI that never ends stops the server.
 */
#ifndef __VMS
#define _POSIX_C_SOURCE 200112L
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#ifdef __VMS
#include <types.h>
#include <stat.h>
#include <socket.h>
#include <in.h>
#include <inet.h>
#include <unistd.h>
#include <unixio.h>
#include <descrip.h>
#include <lib$routines.h>
#include <str$routines.h>
#include <rmsdef.h>
#define DEF_ROOT     "CPVAX$DUA1:[LIGHTTPD.WWW]"
#define DEF_TMP      "SYS$SCRATCH:"
#define ROOT_END     "]"
#define DEF_CGI      "CPVAX$DUA1:[LIGHTTPD.BIN]HTTPD_CGI.COM"
#define NULL_DEV     "NL:"
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <dirent.h>
#define DEF_ROOT     "./www"
#define DEF_TMP      "/tmp/"
#define ROOT_END     ""
#define DEF_PERL     "perl"
#define DEF_CGI      ""
#define NULL_DEV     "/dev/null"
#endif

#ifdef __VMS
#define ALEN int
#else
#define ALEN socklen_t
#endif

#ifndef SOCK_CLOSE
#define SOCK_CLOSE(s) close(s)      /* /DEFINE=SOCK_CLOSE=socket_close if close() will not do */
#endif

#define SERVER      "HTTPD/1.0 (OpenVMS)"
#define REQ_MAX     16384           /* request line and headers */
#define BODY_MAX    (4L * 1024L * 1024L)
#define URL_MAX     2000
#define MAXHDR      48
#define MAXSEG      16
#define SEG_MAX     39
#define SPEC_MAX    512
#define RCV_SECS    20

static char g_root[256];            /* VMS: "dev:[dir.www" (no "]");  POSIX: "/dir" */
#ifdef __VMS
static char g_dev[64];              /* "dev:" */
static char g_cgi[256];
#endif
static char g_userdir[64] = "WEB";
#ifndef __VMS
static char g_perl[256];
#endif
static char g_tmp[128];
static char g_host[64] = "localhost";
static int  g_port = 80;
static long g_seq = 0;
static int  g_keep = 0;             /* HTTPD_KEEP defined: leave the scratch files, to debug a CGI */

/* ---------- small helpers ---------- */

static int ieq(const char *a, const char *b)
{
    while (*a && *b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        a++; b++;
    }
    return *a == *b;
}

static int ieqn(const char *a, const char *b, size_t n)
{
    for (; n > 0; n--, a++, b++) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
        if (*a == 0) return 1;
    }
    return 1;
}

static int bcat(char *dst, size_t cap, const char *src)     /* append if it fits */
{
    size_t n = strlen(dst), m = strlen(src);
    if (n + m + 1 > cap) return 0;
    memcpy(dst + n, src, m + 1);
    return 1;
}

static const char *conf(const char *name, const char *dflt)
{
    const char *v = getenv(name);
    return (v && *v) ? v : dflt;
}

static void copy_to(char *dst, size_t cap, const char *src)
{
    size_t n = strlen(src);
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n);
    dst[n] = 0;
}

typedef struct { char *p; long n, cap; int err; } Buf;

static void buf_add(Buf *b, const char *s)
{
    long m = (long)strlen(s), c;
    char *np;
    if (b->err) return;
    if (b->n + m + 1 > b->cap) {
        c = b->cap ? b->cap : 1024;
        while (c < b->n + m + 1) c *= 2;
        np = (char *)realloc(b->p, (size_t)c);
        if (!np) { b->err = 1; return; }
        b->p = np;
        b->cap = c;
    }
    memcpy(b->p + b->n, s, (size_t)m + 1);
    b->n += m;
}

/* ---------- input from the socket, with a time limit ---------- */

/* recv() that gives up (returns -1) if nothing arrives for RCV_SECS: a browser that opens a
   connection and says nothing must not hold up the one-at-a-time server.  (TCPware has
   SO_RCVTIMEO in its header but setsockopt refuses it, so this uses select().) */
static int recv_wait(int s, char *buf, int n)
{
    fd_set rd;
    struct { long sec, usec; } tv;      /* the layout of a struct timeval */
    FD_ZERO(&rd);
    FD_SET(s, &rd);
    tv.sec = RCV_SECS; tv.usec = 0;
    if (select(s + 1, &rd, NULL, NULL, (void *)&tv) <= 0) return -1;
    return recv(s, buf, n, 0);
}

/* ---------- output to the socket, buffered ---------- */

typedef struct { int s; int n; int err; char buf[4096]; } Out;

static void o_flush(Out *o)
{
    int off = 0, r;
    while (off < o->n && !o->err) {
        r = send(o->s, o->buf + off, o->n - off, 0);
        if (r <= 0) o->err = 1; else off += r;
    }
    o->n = 0;
}

static void o_write(Out *o, const char *d, long n)
{
    long room, k;
    while (n > 0 && !o->err) {
        room = (long)sizeof o->buf - o->n;
        k = n < room ? n : room;
        memcpy(o->buf + o->n, d, (size_t)k);
        o->n += (int)k; d += k; n -= k;
        if (o->n == (int)sizeof o->buf) o_flush(o);
    }
}

static void o_str(Out *o, const char *s) { o_write(o, s, (long)strlen(s)); }

/* ---------- requests ---------- */

typedef struct {
    char *method, *target, *proto, *query;
    char  path[URL_MAX + 1];            /* the URL path, %-decoded */
    int   nhdr;
    char *hname[MAXHDR], *hval[MAXHDR];
    long  clen;                         /* Content-Length, or -1 */
    const char *body;                   /* body bytes that came with the headers */
    long  have;
    char  remote[32];
} Req;

static const char *hdr(const Req *r, const char *name)
{
    int i;
    for (i = 0; i < r->nhdr; i++)
        if (ieq(r->hname[i], name)) return r->hval[i];
    return NULL;
}

static const char *reason(int code)
{
    switch (code) {
    case 200: return "OK";
    case 301: return "Moved Permanently";
    case 302: return "Found";
    case 400: return "Bad Request";
    case 403: return "Forbidden";
    case 404: return "Not Found";
    case 405: return "Method Not Allowed";
    case 411: return "Length Required";
    case 413: return "Request Entity Too Large";
    case 414: return "Request-URI Too Long";
    case 500: return "Internal Server Error";
    case 501: return "Not Implemented";
    default:  return "Status";
    }
}

static void send_head(Out *o, int code, const char *why, const char *ctype,
                      const char *extra, long clen)
{
    char line[300];
    time_t t = time(NULL);
    struct tm *tm = gmtime(&t);
    sprintf(line, "HTTP/1.0 %d %s\r\nServer: %s\r\n", code, why ? why : reason(code), SERVER);
    o_str(o, line);
    if (tm && strftime(line, sizeof line, "Date: %a, %d %b %Y %H:%M:%S GMT\r\n", tm))
        o_str(o, line);
    if (ctype) { o_str(o, "Content-Type: "); o_str(o, ctype); o_str(o, "\r\n"); }
    if (clen >= 0) { sprintf(line, "Content-Length: %ld\r\n", clen); o_str(o, line); }
    if (extra) o_str(o, extra);
    o_str(o, "Connection: close\r\n\r\n");
}

static int send_error(Out *o, int code, const char *extra, int head)
{
    char body[200];
    sprintf(body, "<html><head><title>%d %s</title></head>\n"
                  "<body><h1>%d %s</h1></body></html>\n", code, reason(code), code, reason(code));
    send_head(o, code, NULL, "text/html", extra, (long)strlen(body));
    if (!head) o_str(o, body);
    return code;
}

static int send_redirect(Out *o, const char *where, int head)
{
    char extra[URL_MAX + 40];
    if (strlen(where) > URL_MAX) return send_error(o, 400, NULL, head);
    sprintf(extra, "Location: %s\r\n", where);
    return send_error(o, 301, extra, head);
}

/* ---------- URL and file names ---------- */

static int hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int url_decode(char *dst, size_t cap, const char *src)      /* -1 if bad */
{
    size_t n = 0;
    int a, b;
    while (*src) {
        if (n + 1 >= cap) return -1;
        if (*src == '%') {
            a = hexval((unsigned char)src[1]);
            b = a < 0 ? -1 : hexval((unsigned char)src[2]);
            if (a < 0 || b < 0 || (a == 0 && b == 0)) return -1;
            dst[n++] = (char)(a * 16 + b);
            src += 3;
        } else {
            dst[n++] = *src++;
        }
    }
    dst[n] = 0;
    return 0;
}

typedef struct {
    char *dir[MAXSEG];
    int   ndir;
    char *user;             /* /~user/..., or NULL */
    int   bare_user;        /* the path was just /~user */
} Loc;

/* a directory is letters, digits and _ $ - ; a file may have one dot as well.
   Nothing else gets near the file system: no [ ] : ; * % ^ " and no "..". */
static int ok_seg(const char *s, int dot_ok)
{
    size_t n = strlen(s);
    int dots = 0;
    if (n == 0 || n > SEG_MAX * 2 || s[0] == '.' || s[0] == '-') return 0;
    for (; *s; s++) {
        if (isalnum((unsigned char)*s) || *s == '_' || *s == '$' || *s == '-') continue;
        if (*s == '.' && dot_ok && ++dots == 1) continue;
        return 0;
    }
    return 1;
}

/* split the (decoded, modifiable) path into directories and a last name;
   *file is NULL when the path ends in a slash.  Returns -1 if it is not allowed. */
static int split_path(char *p, Loc *l, char **file)
{
    char *seg;
    int last;
    l->ndir = 0; l->user = NULL; l->bare_user = 0; *file = NULL;
    if (*p != '/') return -1;
    p++;
    while (*p) {
        seg = p;
        while (*p && *p != '/') p++;
        last = (*p == 0);
        if (!last) *p++ = 0;
        if (*seg == 0) continue;
        if (seg[0] == '~' && l->ndir == 0 && l->user == NULL) {
            if (!ok_seg(seg + 1, 0)) return -1;
            l->user = seg + 1;
            if (last) l->bare_user = 1;
            continue;
        }
        if (last) {
            if (!ok_seg(seg, 1)) return -1;
            *file = seg;
        } else {
            if (!ok_seg(seg, 0) || l->ndir >= MAXSEG) return -1;
            l->dir[l->ndir++] = seg;
        }
    }
    return 0;
}

/* the file spec of NAME in directory L; NAME "" gives the directory itself */
static int fs_spec(char *out, size_t cap, const Loc *l, const char *name)
{
    int i, ok;
    out[0] = 0;
#ifdef __VMS
    if (l->user)
        ok = bcat(out, cap, g_dev) && bcat(out, cap, "[") && bcat(out, cap, l->user)
          && bcat(out, cap, ".") && bcat(out, cap, g_userdir);
    else
        ok = bcat(out, cap, g_root);
    for (i = 0; ok && i < l->ndir; i++)
        ok = bcat(out, cap, ".") && bcat(out, cap, l->dir[i]);
    return ok && bcat(out, cap, "]") && bcat(out, cap, name);
#else
    ok = bcat(out, cap, g_root);
    if (ok && l->user) ok = bcat(out, cap, "/~") && bcat(out, cap, l->user);
    for (i = 0; ok && i < l->ndir; i++)
        ok = bcat(out, cap, "/") && bcat(out, cap, l->dir[i]);
    return ok && bcat(out, cap, "/") && bcat(out, cap, name);
#endif
}

static int fs_isfile(const char *spec)
{
    struct stat st;
    if (stat(spec, &st) != 0) return 0;
#ifdef S_ISDIR
    if (S_ISDIR(st.st_mode)) return 0;
#endif
    return 1;
}

static int fs_isdir(const Loc *l, const char *name)       /* is NAME a sub-directory of L? */
{
    char spec[SPEC_MAX], n2[SEG_MAX * 2 + 8];
    struct stat st;
#ifdef __VMS
    copy_to(n2, sizeof n2, name);
    if (!bcat(n2, sizeof n2, ".DIR") || !fs_spec(spec, sizeof spec, l, n2)) return 0;
    return stat(spec, &st) == 0;
#else
    copy_to(n2, sizeof n2, name);
    if (!fs_spec(spec, sizeof spec, l, n2)) return 0;
    return stat(spec, &st) == 0 && S_ISDIR(st.st_mode);
#endif
}

static void list_add(Buf *b, const char *name, int isdir)
{
    buf_add(b, "<li><a href=\"");
    buf_add(b, name);
    if (isdir) buf_add(b, "/");
    buf_add(b, "\">");
    buf_add(b, name);
    if (isdir) buf_add(b, "/");
    buf_add(b, "</a></li>\n");
}

static int name_ok(const char *s)
{
    return ok_seg(s, 1);
}

/* append an <li> for each name in the directory to B; -1 if there is no such directory */
static int fs_list(const Loc *l, Buf *b)
{
#ifdef __VMS
    char spec[SPEC_MAX], name[SEG_MAX * 4 + 8], prev[SEG_MAX * 4 + 8];
    struct dsc$descriptor_s sd, rd;
    unsigned long ctx = 0;
    unsigned int st;
    char *p, *q;
    int first = 1, isdir, i;
    size_t n;

    if (!fs_spec(spec, sizeof spec, l, "*.*;*")) return -1;
    sd.dsc$w_length = (unsigned short)strlen(spec);
    sd.dsc$b_dtype = DSC$K_DTYPE_T;
    sd.dsc$b_class = DSC$K_CLASS_S;
    sd.dsc$a_pointer = spec;
    rd.dsc$w_length = 0;
    rd.dsc$b_dtype = DSC$K_DTYPE_T;
    rd.dsc$b_class = DSC$K_CLASS_D;
    rd.dsc$a_pointer = NULL;
    prev[0] = 0;
    for (;;) {
        st = lib$find_file((void *)&sd, (void *)&rd, (void *)&ctx, 0, 0, 0, 0);
        if (!(st & 1)) {
            if (first && st == RMS$_DNF) { lib$find_file_end((void *)&ctx); return -1; }
            break;
        }
        first = 0;
        n = rd.dsc$w_length;
        p = rd.dsc$a_pointer;
        for (q = p + n; q > p && q[-1] != ']'; q--) ;       /* the name after the "]" */
        n = (size_t)((p + n) - q);
        if (n >= sizeof name) continue;
        memcpy(name, q, n);
        name[n] = 0;
        q = strchr(name, ';');
        if (q) *q = 0;
        if (strcmp(name, prev) == 0) continue;              /* older versions of the same file */
        copy_to(prev, sizeof prev, name);
        for (i = 0; name[i]; i++) name[i] = (char)tolower((unsigned char)name[i]);
        isdir = 0;
        n = strlen(name);
        if (n > 4 && strcmp(name + n - 4, ".dir") == 0) { name[n - 4] = 0; isdir = 1; }
        if (!name_ok(name) || (isdir && strchr(name, '.')) || strcmp(name, "000000") == 0) continue;
        list_add(b, name, isdir);
    }
    lib$find_file_end((void *)&ctx);
    str$free1_dx((void *)&rd);
    return 0;
#else
    char spec[SPEC_MAX];
    DIR *d;
    struct dirent *e;
    struct stat st;
    char full[SPEC_MAX];

    if (!fs_spec(spec, sizeof spec, l, "")) return -1;
    d = opendir(spec);
    if (!d) return -1;
    while ((e = readdir(d)) != NULL) {
        if (!name_ok(e->d_name)) continue;
        full[0] = 0;
        bcat(full, sizeof full, spec);
        bcat(full, sizeof full, e->d_name);
        list_add(b, e->d_name, stat(full, &st) == 0 && S_ISDIR(st.st_mode));
    }
    closedir(d);
    return 0;
#endif
}

/* ---------- file types ---------- */

static const struct { const char *ext, *type; int text; } mime[] = {
    { "html", "text/html", 1 },             { "htm", "text/html", 1 },
    { "txt", "text/plain", 1 },             { "css", "text/css", 1 },
    { "js", "text/javascript", 1 },         { "json", "application/json", 1 },
    { "xml", "text/xml", 1 },               { "csv", "text/csv", 1 },
    { "c", "text/plain", 1 },               { "com", "text/plain", 1 },
    { "gif", "image/gif", 0 },              { "jpg", "image/jpeg", 0 },
    { "jpeg", "image/jpeg", 0 },            { "png", "image/png", 0 },
    { "ico", "image/x-icon", 0 },           { "svg", "image/svg+xml", 1 },
    { "pdf", "application/pdf", 0 },        { "zip", "application/zip", 0 },
    { NULL, NULL, 0 }
};

static const char *ext_of(const char *name)
{
    const char *d = strrchr(name, '.');
    return d ? d + 1 : "";
}

static const char *mime_of(const char *name, int *text)
{
    const char *e = ext_of(name);
    int i;
    for (i = 0; mime[i].ext; i++)
        if (ieq(e, mime[i].ext)) { *text = mime[i].text; return mime[i].type; }
    *text = 0;
    return "application/octet-stream";
}

/* 0: not a CGI, 1: Perl, 2: DCL */
static int cgi_kind(const char *name)
{
    const char *e = ext_of(name);
    if (ieq(e, "cgi") || ieq(e, "pl")) return 1;
    if (ieq(e, "com")) return 2;
    return 0;
}

/* ---------- CGI ---------- */

#ifdef __VMS
static void desc(struct dsc$descriptor_s *d, const char *s)
{
    d->dsc$w_length = (unsigned short)strlen(s);
    d->dsc$b_dtype = DSC$K_DTYPE_T;
    d->dsc$b_class = DSC$K_CLASS_S;
    d->dsc$a_pointer = (char *)s;
}

static void env_set(const char *name, const char *value)    /* a local DCL symbol */
{
    struct dsc$descriptor_s nd, vd;
    unsigned int st;
    desc(&nd, name);
    desc(&vd, value);
    st = lib$set_symbol((void *)&nd, (void *)&vd, 0);
    if (!(st & 1) && vd.dsc$w_length > 255) {               /* older DCL: 255 characters at most */
        vd.dsc$w_length = 255;
        lib$set_symbol((void *)&nd, (void *)&vd, 0);
    }
}

static void env_del(const char *name)
{
    struct dsc$descriptor_s nd;
    desc(&nd, name);
    lib$delete_symbol((void *)&nd, 0);
}

/* run the script in a subprocess: SYS$INPUT is the file IN, SYS$OUTPUT the file OUT.
   LIB$SPAWN's input file is the subprocess's stream of *commands*, so the body is not given
   there (DCL would try to run it); HTTPD_CGI.COM points SYS$INPUT at it instead. */
static int run_script(int kind, const char *spec, const char *dir, const char *in, const char *out)
{
    char cmd[400];
    struct dsc$descriptor_s cd, id, od;
    unsigned int flags = 0, st, cst = 0;
    if (strlen(g_cgi) + strlen(spec) + strlen(dir) + strlen(in) + 32 >= sizeof cmd) return 0;
    sprintf(cmd, "@%s \"%s\" \"%s\" \"%s\" \"%s\"", g_cgi, kind == 1 ? "PERL" : "DCL",
            spec, dir, in);
    desc(&cd, cmd);
    desc(&id, NULL_DEV);
    desc(&od, out);
    st = lib$spawn((void *)&cd, (void *)&id, (void *)&od, (void *)&flags, 0, 0, (void *)&cst,
                   0, 0, 0, 0, 0);
    return (st & 1) != 0;
}
#define OPEN_BODY(n) fopen((n), "wb", "rfm=stmlf")
#else
static void env_set(const char *name, const char *value) { setenv(name, value, 1); }
static void env_del(const char *name) { unsetenv(name); }

static int run_script(int kind, const char *spec, const char *dir, const char *in, const char *out)
{
    char cmd[SPEC_MAX * 4];
    if (strlen(g_perl) + strlen(spec) + strlen(dir) + strlen(in) + strlen(out) + 40 >= sizeof cmd)
        return 0;
    sprintf(cmd, "cd '%s' && %s '%s' < '%s' > '%s'", dir, kind == 1 ? g_perl : "sh", spec, in, out);
    return system(cmd) != -1;
}
#define OPEN_BODY(n) fopen((n), "wb")
#endif

static const char *cgi_fixed[] = {
    "GATEWAY_INTERFACE", "SERVER_SOFTWARE", "SERVER_NAME", "SERVER_PORT", "SERVER_PROTOCOL",
    "REQUEST_METHOD", "REQUEST_URI", "SCRIPT_NAME", "SCRIPT_FILENAME", "PATH_INFO",
    "QUERY_STRING", "REMOTE_ADDR", "CONTENT_TYPE", "CONTENT_LENGTH", "DOCUMENT_ROOT", NULL
};

static int http_var(char *out, size_t cap, const char *hname)     /* "User-Agent" -> HTTP_USER_AGENT */
{
    size_t n;
    if (strlen(hname) + 6 > cap || strlen(hname) > 100) return 0;
    if (ieq(hname, "Content-Type") || ieq(hname, "Content-Length") || ieq(hname, "Proxy"))
        return 0;                                   /* CONTENT_*; and HTTP_PROXY is a known trap */
    strcpy(out, "HTTP_");
    n = 5;
    for (; *hname; hname++)
        out[n++] = isalnum((unsigned char)*hname) ? (char)toupper((unsigned char)*hname) : '_';
    out[n] = 0;
    return 1;
}

static void cgi_env(const Req *r, const char *script_spec)
{
    char tmp[64], var[128], uri[URL_MAX * 2];
    const char *h = hdr(r, "Host");
    int i;
    char *c;

    env_set("GATEWAY_INTERFACE", "CGI/1.1");
    env_set("SERVER_SOFTWARE", SERVER);
    if (h && *h) {
        copy_to(var, sizeof var, h);
        c = strchr(var, ':');
        if (c) *c = 0;
        env_set("SERVER_NAME", var);
    } else {
        env_set("SERVER_NAME", g_host);
    }
    sprintf(tmp, "%d", g_port);
    env_set("SERVER_PORT", tmp);
    env_set("SERVER_PROTOCOL", r->proto);
    env_set("REQUEST_METHOD", r->method);
    uri[0] = 0;
    bcat(uri, sizeof uri, r->target);
    if (r->query[0]) { bcat(uri, sizeof uri, "?"); bcat(uri, sizeof uri, r->query); }
    env_set("REQUEST_URI", uri);
    env_set("SCRIPT_NAME", r->path);
    env_set("SCRIPT_FILENAME", script_spec);
    env_set("PATH_INFO", "");
    env_set("QUERY_STRING", r->query);
    env_set("REMOTE_ADDR", r->remote);
    uri[0] = 0;
    bcat(uri, sizeof uri, g_root);
    bcat(uri, sizeof uri, ROOT_END);
    env_set("DOCUMENT_ROOT", uri);
    if (hdr(r, "Content-Type")) env_set("CONTENT_TYPE", hdr(r, "Content-Type"));
    if (r->clen >= 0) { sprintf(tmp, "%ld", r->clen); env_set("CONTENT_LENGTH", tmp); }
    for (i = 0; i < r->nhdr; i++)
        if (http_var(var, sizeof var, r->hname[i])) env_set(var, r->hval[i]);
}

static void cgi_env_clear(const Req *r)
{
    char var[128];
    int i;
    for (i = 0; cgi_fixed[i]; i++) env_del(cgi_fixed[i]);
    for (i = 0; i < r->nhdr; i++)
        if (http_var(var, sizeof var, r->hname[i])) env_del(var);
}

static void rm_all(const char *name)            /* every version of a scratch file */
{
    int i;
    if (g_keep) return;
    for (i = 0; i < 20 && remove(name) == 0; i++) ;
}

static int save_body(int s, const Req *r, const char *name)
{
    static char chunk[2048];
    FILE *f = OPEN_BODY(name);
    long left = r->clen, n = r->have < left ? r->have : left;
    int got;
    if (!f) return -1;
    if (n > 0) { fwrite(r->body, 1, (size_t)n, f); left -= n; }
    while (left > 0) {
        got = recv_wait(s, chunk, left < (long)sizeof chunk ? (int)left : (int)sizeof chunk);
        if (got <= 0) break;
        fwrite(chunk, 1, (size_t)got, f);
        left -= got;
    }
    fclose(f);
    return left == 0 ? 0 : -1;
}

static int bad_name(const char *line)           /* not "Token: value" */
{
    const char *c = strchr(line, ':');
    const char *p;
    if (!c || c == line) return 1;
    for (p = line; p < c; p++)
        if (!(isalnum((unsigned char)*p) || *p == '-' || *p == '_')) return 1;
    return 0;
}

static int send_cgi_reply(Out *o, FILE *f, int head)
{
    static char line[1024], hdrs[4096], chunk[2048];
    char *c;
    size_t n;
    int status = 200, first = 1, have_ct = 0, have_loc = 0, bad = 0, lazy = 0;
    const char *why = NULL;
    char why_buf[80];

    hdrs[0] = 0;
    while (fgets(line, sizeof line, f)) {
        n = strlen(line);
        while (n > 0 && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = 0;
        if (n == 0) break;                                  /* the blank line: headers are done */
        if (first && strncmp(line, "HTTP/", 5) == 0) {      /* an NPH script's status line */
            c = strchr(line, ' ');
            if (c) {
                status = atoi(c + 1);
                c = strchr(c + 1, ' ');
                if (c) { copy_to(why_buf, sizeof why_buf, c + 1); why = why_buf; }
            }
            first = 0;
            continue;
        }
        if (bad_name(line)) {
            if (first) lazy = 1; else bad = 1;
            break;
        }
        first = 0;
        c = strchr(line, ':');
        *c++ = 0;
        while (*c == ' ' || *c == '\t') c++;
        if (ieq(line, "Status")) {
            status = atoi(c);
            while (isdigit((unsigned char)*c)) c++;
            while (*c == ' ') c++;
            if (*c) { copy_to(why_buf, sizeof why_buf, c); why = why_buf; }
            continue;
        }
        if (ieq(line, "Content-Type")) have_ct = 1;
        if (ieq(line, "Location")) have_loc = 1;
        if (ieq(line, "Connection") || ieq(line, "Content-Length")) continue;   /* ours to say */
        if (strlen(hdrs) + strlen(line) + strlen(c) + 8 < sizeof hdrs) {
            strcat(hdrs, line); strcat(hdrs, ": "); strcat(hdrs, c); strcat(hdrs, "\r\n");
        }
    }
    if (bad) return send_error(o, 500, NULL, head);
    if (lazy) {                                             /* no headers: take it all as HTML */
        rewind(f);
        hdrs[0] = 0;
        have_ct = 0;
        have_loc = 0;
    }
    if (status == 200 && have_loc) { status = 302; why = NULL; }
    send_head(o, status, why, have_ct || have_loc ? NULL : "text/html", hdrs, -1);
    if (!head) {
        while ((n = fread(chunk, 1, sizeof chunk, f)) > 0) o_write(o, chunk, (long)n);
    }
    return status;
}

static int do_cgi(Out *o, int s, Req *r, const Loc *l, const char *name, int kind)
{
    char spec[SPEC_MAX], dir[SPEC_MAX], in[160], out[160];
    int head = strcmp(r->method, "HEAD") == 0, post = strcmp(r->method, "POST") == 0, ok;
    FILE *f;

    if (!fs_spec(spec, sizeof spec, l, name) || !fs_spec(dir, sizeof dir, l, ""))
        return send_error(o, 500, NULL, head);
    if (post && r->clen < 0) return send_error(o, 411, NULL, head);
    sprintf(in, "%sHTTPD_%ld_IN.TMP", g_tmp, ++g_seq);
    sprintf(out, "%sHTTPD_%ld_OUT.TMP", g_tmp, g_seq);
    rm_all(in);
    rm_all(out);
    if (post && r->clen > 0) {
        if (save_body(s, r, in) != 0) { rm_all(in); return send_error(o, 400, NULL, head); }
    } else {
        copy_to(in, sizeof in, NULL_DEV);
    }
    cgi_env(r, spec);
    ok = run_script(kind, spec, dir, in, out);
    cgi_env_clear(r);
    if (strcmp(in, NULL_DEV) != 0) rm_all(in);
    f = ok ? fopen(out, "r") : NULL;
    if (!f) { rm_all(out); return send_error(o, 500, NULL, head); }
    ok = send_cgi_reply(o, f, head);
    fclose(f);
    rm_all(out);
    return ok;
}

/* ---------- static files, listings ---------- */

static int send_file(Out *o, const char *spec, const char *name, int head)
{
    static char chunk[2048];
    int text;
    const char *type = mime_of(name, &text);
    FILE *f = fopen(spec, text ? "r" : "rb");
    size_t n;
    if (!f) return send_error(o, 404, NULL, head);
    send_head(o, 200, NULL, type, NULL, -1);
    if (!head) {
        while ((n = fread(chunk, 1, sizeof chunk, f)) > 0) o_write(o, chunk, (long)n);
    }
    fclose(f);
    return 200;
}

#define LIST_END "</ul></body></html>\n"

static int send_listing(Out *o, const Loc *l, const char *urlpath, int head)
{
    Buf b;
    char title[URL_MAX + 40];
    long len;
    b.p = NULL; b.n = 0; b.cap = 0; b.err = 0;
    if (fs_list(l, &b) != 0) { free(b.p); return send_error(o, 404, NULL, head); }
    /* the path is only letters, digits, _ $ - . and / by now, so it is safe in HTML */
    sprintf(title, "<html><head><title>Index of %s</title></head>\n"
                   "<body><h1>Index of %s</h1>\n<ul>\n", urlpath, urlpath);
    if (strcmp(urlpath, "/") != 0) {
        sprintf(title + strlen(title), "<li><a href=\"../\">../</a></li>\n");
    }
    len = (long)strlen(title) + b.n + (long)strlen(LIST_END);
    send_head(o, 200, NULL, "text/html", NULL, len);
    if (!head) {
        o_str(o, title);
        if (b.p) o_write(o, b.p, b.n);
        o_str(o, LIST_END);
    }
    free(b.p);
    return 200;
}

/* ---------- one request ---------- */

static int serve(Out *o, int s, Req *r)
{
    Loc l;
    char work[URL_MAX + 1], spec[SPEC_MAX], name[SEG_MAX * 2 + 8], where[URL_MAX + 4];
    char *file;
    int head = strcmp(r->method, "HEAD") == 0, get = strcmp(r->method, "GET") == 0;
    int post = strcmp(r->method, "POST") == 0, kind, i;
    static const char *index_names[] = { "index.cgi", "index.html", "index.htm", NULL };

    if (!get && !head && !post)
        return send_error(o, 405, "Allow: GET, HEAD, POST\r\n", 0);
    copy_to(work, sizeof work, r->path);
    if (split_path(work, &l, &file) != 0) return send_error(o, 404, NULL, head);
    if (l.bare_user) {
        sprintf(where, "%s/", r->target);
        return send_redirect(o, where, head);
    }

    if (file == NULL) {                                     /* a directory: index file or listing */
        for (i = 0; index_names[i]; i++) {
            if (fs_spec(spec, sizeof spec, &l, index_names[i]) && fs_isfile(spec)) {
                file = (char *)index_names[i];
                break;
            }
        }
        if (file == NULL) {
            if (post) return send_error(o, 405, "Allow: GET, HEAD\r\n", 0);
            return send_listing(o, &l, r->path, head);
        }
        strcpy(name, file);
    } else {
        copy_to(name, sizeof name, file);
        if (!strchr(name, '.')) {                           /* no dot: a directory, or FILE. */
            if (fs_isdir(&l, name)) {
                sprintf(where, "%s/", r->target);
                return send_redirect(o, where, head);
            }
#ifdef __VMS
            bcat(name, sizeof name, ".");
#endif
        }
    }
    if (!fs_spec(spec, sizeof spec, &l, name) || !fs_isfile(spec) || ieq(ext_of(name), "dir"))
        return send_error(o, 404, NULL, head);
    kind = cgi_kind(name);
    if (kind) return do_cgi(o, s, r, &l, name, kind);
    if (post) return send_error(o, 405, "Allow: GET, HEAD\r\n", 0);
    return send_file(o, spec, name, head);
}

static int find_end(const char *b, int n)     /* index just past the blank line, or -1 */
{
    int i;
    for (i = 0; i < n; i++) {
        if (b[i] == '\n') {
            if (i + 1 < n && b[i + 1] == '\n') return i + 2;
            if (i + 2 < n && b[i + 1] == '\r' && b[i + 2] == '\n') return i + 3;
        }
    }
    return -1;
}

static char *next_line(char *p)               /* end the line at p, return the start of the next */
{
    char *e = strchr(p, '\n');
    if (!e) return NULL;
    *e = 0;
    if (e > p && e[-1] == '\r') e[-1] = 0;
    return e + 1;
}

static void trim_end(char *s)
{
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t')) s[--n] = 0;
}

static int parse_request(char *head, Req *r)         /* 0, or the status to answer with */
{
    char *p = head, *q, *line, *c;

    r->nhdr = 0; r->clen = -1; r->query = (char *)"";
    while (*p == '\r' || *p == '\n') p++;
    q = next_line(p);
    r->method = p;
    c = strchr(p, ' ');
    if (!c) return 400;
    *c++ = 0;
    while (*c == ' ') c++;
    r->target = c;
    c = strchr(c, ' ');
    if (!c) return 400;
    *c++ = 0;
    while (*c == ' ') c++;
    r->proto = c;
    trim_end(r->proto);
    if (strncmp(r->proto, "HTTP/", 5) != 0 || *r->target != '/') return 400;
    if (strlen(r->target) > URL_MAX) return 414;
    for (p = q; p && *p; ) {
        line = p;
        p = next_line(line);
        if (*line == ' ' || *line == '\t') continue;
        c = strchr(line, ':');
        if (!c || c == line || r->nhdr >= MAXHDR) continue;
        *c++ = 0;
        while (*c == ' ' || *c == '\t') c++;
        trim_end(c);
        r->hname[r->nhdr] = line;
        r->hval[r->nhdr] = c;
        r->nhdr++;
    }
    return 0;
}

static void log_line(const Req *r, int status)
{
    char when[40];
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    if (!tm || !strftime(when, sizeof when, "%d/%b/%Y:%H:%M:%S", tm)) sprintf(when, "%ld", (long)t);
    printf("%s [%s] \"%s %s\" %d\n", r->remote, when, r->method ? r->method : "-",
           r->target ? r->target : "-", status);
    fflush(stdout);
}

static void handle_client(int s, const char *remote)
{
    static char buf[REQ_MAX + 1];
    static Out o;
    static Req r;
    int n = 0, got, end = -1, status;
    char *q;
    const char *v;

    memset(&r, 0, sizeof r);
    copy_to(r.remote, sizeof r.remote, remote);
    o.s = s; o.n = 0; o.err = 0;
    while (end < 0) {
        if (n >= REQ_MAX) { send_error(&o, 400, NULL, 0); o_flush(&o); return; }
        got = recv_wait(s, buf + n, REQ_MAX - n);
        if (got <= 0) return;                               /* closed or timed out: nothing to say */
        n += got;
        end = find_end(buf, n);
    }
    buf[end - 1] = 0;                                       /* end of the headers (this was a "\n") */
    r.body = buf + end;
    r.have = n - end;
    status = parse_request(buf, &r);
    if (status) {
        send_error(&o, status, NULL, 0);
    } else {
        q = strchr(r.target, '?');
        if (q) { *q++ = 0; r.query = q; }
        v = hdr(&r, "Content-Length");
        if (v) r.clen = atol(v);
        v = hdr(&r, "Transfer-Encoding");
        if (url_decode(r.path, sizeof r.path, r.target) != 0) status = send_error(&o, 400, NULL, 0);
        else if (v && ieq(v, "chunked")) status = send_error(&o, 501, NULL, 0);
        else if (r.clen > BODY_MAX) status = send_error(&o, 413, NULL, 0);
        else {
            v = hdr(&r, "Expect");
            if (v && ieqn(v, "100-continue", 12) && r.clen > r.have) {
                o_str(&o, "HTTP/1.1 100 Continue\r\n\r\n");
                o_flush(&o);
            }
            status = serve(&o, s, &r);
        }
        log_line(&r, status);
    }
    o_flush(&o);
}

/* ---------- start-up ---------- */

static int setup(void)
{
    const char *v = conf("HTTPD_ROOT", DEF_ROOT);
    char *c;
    size_t n;

    copy_to(g_root, sizeof g_root, v);
    n = strlen(g_root);
#ifdef __VMS
    if (n > 0 && g_root[n - 1] == ']') g_root[--n] = 0;     /* "dev:[dir.www]" -> "dev:[dir.www" */
    if (n > 0 && g_root[n - 1] == '.') g_root[--n] = 0;
    c = strchr(g_root, ':');
    if (!c || !strchr(g_root, '[')) {
        printf("HTTPD_ROOT must look like dev:[dir.www], not \"%s\"\n", v);
        return -1;
    }
    copy_to(g_dev, sizeof g_dev, g_root);
    g_dev[c - g_root + 1] = 0;
    copy_to(g_cgi, sizeof g_cgi, conf("HTTPD_CGI", DEF_CGI));     /* HTTPD_CGI.COM reads HTTPD_PERL */
#else
    (void)c;
    while (n > 1 && g_root[n - 1] == '/') g_root[--n] = 0;
    copy_to(g_perl, sizeof g_perl, conf("HTTPD_PERL", DEF_PERL));
#endif
    copy_to(g_userdir, sizeof g_userdir, conf("HTTPD_USERDIR", g_userdir));
    copy_to(g_tmp, sizeof g_tmp, conf("HTTPD_TMP", DEF_TMP));
    g_keep = getenv("HTTPD_KEEP") != NULL;
    g_port = atoi(conf("HTTPD_PORT", "80"));
    if (g_port <= 0 || g_port > 65535) {
        printf("HTTPD_PORT is not a port number\n");
        return -1;
    }
    return 0;
}

int main(void)
{
    int ls, cs, one = 1;
    ALEN alen;
    struct sockaddr_in sin;

    if (setup() != 0) return 1;
    ls = socket(AF_INET, SOCK_STREAM, 0);
    if (ls < 0) { perror("socket"); return 1; }
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, (char *)&one, sizeof one);
    memset(&sin, 0, sizeof sin);
    sin.sin_family = AF_INET;
    sin.sin_addr.s_addr = htonl(INADDR_ANY);
    sin.sin_port = htons((unsigned short)g_port);
    if (bind(ls, (struct sockaddr *)&sin, sizeof sin) < 0) { perror("bind"); return 1; }
    if (listen(ls, 5) < 0) { perror("listen"); return 1; }
    printf("%s listening on port %d, root %s%s\n", SERVER, g_port, g_root, ROOT_END);
    fflush(stdout);
    for (;;) {
        alen = sizeof sin;
        cs = accept(ls, (struct sockaddr *)&sin, (ALEN *)&alen);
        if (cs < 0) { sleep(1); continue; }
        handle_client(cs, inet_ntoa(sin.sin_addr));
        SOCK_CLOSE(cs);
    }
}
