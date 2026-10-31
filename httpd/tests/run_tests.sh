#!/bin/bash
# Builds HTTPD.C for POSIX, serves a copy of www/ plus some test CGIs on a spare port, and
# checks the replies with curl.   Usage:  tests/run_tests.sh   (from anywhere)
set -u
here=$(cd "$(dirname "$0")" && pwd)
src=$here/..
tmp=$(mktemp -d)
port=${PORT:-18080}
fail=0
trap 'kill $pid 2>/dev/null; rm -rf "$tmp"' EXIT

gcc -x c -ansi -pedantic -Wall -Wextra -Wdeclaration-after-statement -o "$tmp/httpd" "$src/HTTPD.C" || exit 1

mkdir -p "$tmp/www/sub" "$tmp/www/empty" "$tmp/www/withidx" "$tmp/scratch"
cp "$src"/www/* "$tmp/www/"
echo "in sub" > "$tmp/www/sub/a.txt"
echo "<p>idx</p>" > "$tmp/www/withidx/index.html"
# raw-output CGIs are shell scripts here (.com is run with sh on POSIX, with DCL on VMS)
cat > "$tmp/www/redir.com" <<'EOF'
printf 'Location: /hello.html\n\n'
EOF
cat > "$tmp/www/status.com" <<'EOF'
printf 'Status: 404 Gone Fishing\nContent-Type: text/plain\n\nnot here\n'
EOF
cat > "$tmp/www/lazy.com" <<'EOF'
printf 'just some text\n'
EOF
cat > "$tmp/www/crlf.com" <<'EOF'
printf 'Content-Type: text/plain\r\nX-Made: crlf\r\n\r\ncrlf ok\r\n'
EOF
cat > "$tmp/www/nph.com" <<'EOF'
printf 'HTTP/1.0 202 Accepted\nContent-Type: text/plain\n\nnph ok\n'
EOF
printf 'print "Content-Type: text/plain\\n\\n"; print "start\\n"; print STDERR "oops\\n"; exit 3;\n' > "$tmp/www/exit3.cgi"

HTTPD_PORT=$port HTTPD_ROOT="$tmp/www" HTTPD_TMP="$tmp/scratch/" "$tmp/httpd" > "$tmp/log" 2>&1 &
pid=$!
for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -s -o /dev/null "http://127.0.0.1:$port/" && break
    sleep 0.3
done

u=http://127.0.0.1:$port
check() {      # check "name" "expected substring" actual...
    local name=$1 want=$2; shift 2
    local got=$*
    if [[ $got == *"$want"* ]]; then echo "ok    $name"; else echo "FAIL  $name: wanted [$want], got [${got:0:200}]"; fail=1; fi
}
nocheck() {    # nocheck "name" "unwanted substring" actual...
    local name=$1 bad=$2; shift 2
    local got=$*
    if [[ $got != *"$bad"* ]]; then echo "ok    $name"; else echo "FAIL  $name: found [$bad] in [${got:0:200}]"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

check "index.html at /"            "<h1>Hello</h1>"       "$(curl -s $u/)"
check "static html"                "alert"                "$(curl -s $u/hello.html)"
check "css type"                   "text/css"             "$(curl -sI $u/large.css)"
check "static 404"                 "404"                  "$(code $u/nope.html)"
check "dotdot"                     "404"                  "$(code --path-as-is $u/../etc/passwd)"
check "encoded dotdot"             "404"                  "$(code --path-as-is $u/%2e%2e/etc/passwd)"
check "encoded slash dotdot"       "404"                  "$(code --path-as-is "$u/sub/..%2f..%2fetc/passwd")"
check "bracket"                    "404"                  "$(code "$u/%5Bx%5D")"
check "colon"                      "404"                  "$(code "$u/a:b")"
check "NUL"                        "400"                  "$(code "$u/a%00b")"
check "dir without slash"          "301"                  "$(code $u/sub)"
check "dir redirect target"        "Location: /sub/"      "$(curl -sI $u/sub)"
check "listing"                    "a.txt"                "$(curl -s $u/sub/)"
check "listing title"              "Index of /sub/"       "$(curl -s $u/sub/)"
check "empty dir listing"          "Index of /empty/"     "$(curl -s $u/empty/)"
check "missing dir"                "404"                  "$(code $u/missing/)"
check "dir index.html"             "idx"                  "$(curl -s $u/withidx/)"
check "HEAD has no body"           "0"                    "$(curl -sI $u/hello.html | wc -c | grep -c '^0$')"
nocheck "HEAD body"                "<h1>"                 "$(curl -sI $u/hello.html)"
check "PUT is 405"                 "405"                  "$(code -X PUT $u/hello.html)"
check "POST to static is 405"      "405"                  "$(code -d x=1 $u/hello.html)"
check "garbage request"            "400"                  "$(exec 3<>/dev/tcp/127.0.0.1/$port; printf 'bogus\r\n\r\n' >&3; head -1 <&3)"

env=$(curl -s "$u/env.cgi?a=1&b=two%20words")
check "cgi QUERY_STRING"           "QUERY_STRING=a=1&b=two%20words" "$env"
check "cgi REQUEST_METHOD"         "REQUEST_METHOD=GET"   "$env"
check "cgi SCRIPT_NAME"            "SCRIPT_NAME=/env.cgi" "$env"
check "cgi SERVER_PORT"            "SERVER_PORT=$port"    "$env"
check "cgi REMOTE_ADDR"            "REMOTE_ADDR=127.0.0.1" "$env"
check "cgi GATEWAY_INTERFACE"      "GATEWAY_INTERFACE=CGI/1.1" "$env"
env=$(curl -s -H 'X-Foo: bar' -H 'Proxy: http://evil/' -A 'tester/1' "$u/env.cgi")
check "cgi HTTP_X_FOO"             "HTTP_X_FOO=bar"       "$env"
check "cgi HTTP_USER_AGENT"        "HTTP_USER_AGENT=tester/1" "$env"
nocheck "cgi no HTTP_PROXY"        "HTTP_PROXY"           "$env"
env=$(curl -s "$u/env.cgi")
nocheck "cgi env is cleared"       "HTTP_X_FOO"           "$env"
env=$(curl -s -d 'Mood=happy&x=%26' "$u/env.cgi")
check "cgi POST method"            "REQUEST_METHOD=POST"  "$env"
check "cgi POST length"            "CONTENT_LENGTH=16"    "$env"
check "cgi POST type"              "CONTENT_TYPE=application/x-www-form-urlencoded" "$env"
check "cgi POST body"              "Mood=happy&x=%26"     "$env"
head -c 300000 /dev/urandom | base64 -w0 | head -c 200000 > "$tmp/big"
bigfile=$(cygpath -m "$tmp/big" 2>/dev/null || echo "$tmp/big")     # a Windows curl needs its own path style
got=$(curl -s --data-binary @"$bigfile" -H'Content-Type: text/plain' "$u/env.cgi" | sed -n '/^--- body/,$p' | sed '1d' | head -c 200000)
if [[ $got == "$(cat "$tmp/big")" ]]; then echo "ok    cgi 200 KB POST"; else echo "FAIL  cgi 200 KB POST (${#got} bytes back)"; fail=1; fi
check "cgi redirect"               "302"                  "$(code $u/redir.com)"
check "cgi redirect Location"      "Location: /hello.html" "$(curl -sI $u/redir.com)"
check "cgi Status"                 "404 Gone Fishing"     "$(curl -sI $u/status.com)"
check "cgi lazy is html"           "text/html"            "$(curl -sI $u/lazy.com)"
check "cgi lazy body"              "just some text"       "$(curl -s $u/lazy.com)"
check "cgi CRLF header"            "X-Made: crlf"         "$(curl -sI $u/crlf.com)"
check "cgi NPH status"             "202"                  "$(code $u/nph.com)"
check "cgi non-zero exit"          "start"                "$(curl -s $u/exit3.cgi)"
check "cgi HEAD"                   "200"                  "$(code -I $u/env.cgi)"
check "ping.cgi (CGI.pm)"          "<h1>ping</h1>"        "$(curl -s $u/ping.cgi)"
check "status.html is served"      "cpvax status"         "$(curl -s $u/status.html)"
check "test.cgi form"              "Hello World!"         "$(curl -s $u/test.cgi)"
check "test.cgi answer"            "feeling glad"         "$(curl -s "$u/test.cgi?Mood=glad")"
check "post.cgi form"              "<textarea"            "$(curl -s $u/post.cgi)"
check "post.cgi answer"            "Feeling fine"         "$(curl -s -d 'Mood=Feeling+fine' $u/post.cgi)"
check "expect 100-continue"        "Mood=big"             "$(curl -s -H 'Expect: 100-continue' -d 'Mood=big' $u/env.cgi)"
check "server still alive"         "200"                  "$(code $u/hello.html)"

echo
if [ $fail = 0 ]; then echo "all passed"; else echo "FAILURES"; echo "--- server log ---"; cat "$tmp/log"; fi
exit $fail
