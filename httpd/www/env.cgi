#!/usr/bin/perl
# Shows what the server handed to a CGI: the CGI variables, and the POST body.
# (Not "keys %ENV": on VMS that walks every logical name table and can run out of quota.)
print "Content-Type: text/plain\n\n";
for my $v (qw(GATEWAY_INTERFACE SERVER_SOFTWARE SERVER_NAME SERVER_PORT SERVER_PROTOCOL
              REQUEST_METHOD REQUEST_URI SCRIPT_NAME SCRIPT_FILENAME PATH_INFO QUERY_STRING
              REMOTE_ADDR DOCUMENT_ROOT CONTENT_TYPE CONTENT_LENGTH
              HTTP_HOST HTTP_USER_AGENT HTTP_ACCEPT HTTP_COOKIE HTTP_REFERER
              HTTP_X_FORWARDED_FOR HTTP_X_FOO)) {
  print "$v=$ENV{$v}\n" if defined $ENV{$v};
}
if (($ENV{REQUEST_METHOD} || '') eq 'POST') {
  my $n = $ENV{CONTENT_LENGTH} || 0;
  my $body = '';
  read(STDIN, $body, $n);
  print "\n--- body (", length($body), " of $n bytes) ---\n$body\n";
}
