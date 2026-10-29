#!/bin/bash
# check_dcl.sh - cheap local sanity check for DCL procedures (no VMS needed).
# Usage: ./check_dcl.sh [file.COM ...]      (default: CREATE_GUEST.COM next to this script)
#
# Checks, per file: plain ASCII, no tab, one line-ending style (all LF or all
# CRLF), every line starts with $, no line over 254 characters, an even
# number of double quotes and no stray apostrophe on every non-comment line,
# every GOTO has a label and no label is defined twice, every CALL has a
# SUBROUTINE, SUBROUTINE/ENDSUBROUTINE balance, and an ODS-2 style file name.
# It cannot tell you that the DCL is right, only that it is not obviously broken.

here=$(cd "$(dirname "$0")" && pwd)
[ $# -gt 0 ] || set -- "$here/CREATE_GUEST.COM"
export LC_ALL=C
bad=0

for f in "$@"; do
  [ -f "$f" ] || { echo "$f: no such file"; bad=1; continue; }
  err() { echo "$f: $*"; bad=1; }

  base=$(basename "$f")
  name=${base%.*}
  echo "$name" | grep -Eq '^[A-Z0-9_$-]{1,39}$' || err "name '$name' is not an ODS-2 file name"
  ext=${base##*.}
  echo "$ext" | grep -Eq '^[A-Z0-9_$-]{0,39}$' || err "type '$ext' is not an ODS-2 file type"

  # line endings: all LF or all CRLF
  total=$(wc -l < "$f")
  crlf=$(tr -cd '\r' < "$f" | wc -c)
  if [ "$crlf" -ne 0 ] && [ "$crlf" -ne "$total" ]; then
    err "mixed line endings ($crlf of $total lines end in CR)"
  fi
  [ -n "$(tail -c1 "$f")" ] && err "last line has no newline"

  # work on a CR-stripped copy
  tmp=$(mktemp) || exit 2
  tr -d '\r' < "$f" > "$tmp"

  grep -n $'\t' "$tmp" | sed "s|^|$f: tab on line |" | head -5 | grep . && bad=1
  grep -n '[^ -~]' "$tmp" | grep -v $'\t' | sed "s|^|$f: non-ASCII or control char on line |" | head -5 | grep . && bad=1

  awk -v F="$f" '
    { n = NR; line = $0 }
    length(line) == 0 { next }
    substr(line,1,1) != "$" { printf "%s: line %d does not start with $\n", F, n; bad = 1 }
    length(line) > 254 { printf "%s: line %d is %d characters (limit 254)\n", F, n, length(line); bad = 1 }
    {
      iscomment = (line ~ /^\$ *!/)
      if (!iscomment) {
        q = gsub(/"/, "&", line)
        rest = line
        gsub(/\047\047[A-Za-z0-9_$]+\047/, "", rest)
        gsub(/\047[A-Za-z0-9_$]+\047/, "", rest)
        a = gsub(/\047/, "&", rest)
        if (q % 2) { printf "%s: line %d has an odd number of double quotes\n", F, n; bad = 1 }
        if (a) { printf "%s: line %d has an apostrophe that is not part of a symbol substitution\n", F, n; bad = 1 }
      }
    }
    { line = $0 }
    line ~ /^\$[A-Za-z0-9_$]+:/ {
      lab = line; sub(/^\$/, "", lab); sub(/:.*/, "", lab); lab = toupper(lab)
      if (lab in seen) { printf "%s: label %s on line %d already defined on line %d\n", F, lab, n, seen[lab]; bad = 1 }
      seen[lab] = n
      if (line ~ /SUBROUTINE/) subs[lab] = 1
    }
    line ~ /^\$ *(IF .* THEN )?GOTO / || line ~ / THEN GOTO / || line ~ /^\$ *GOTO / || line ~ /THEN +GOTO/ {
      t = line; sub(/.*GOTO +/, "", t); sub(/[^A-Za-z0-9_$].*/, "", t); gotos[++ng] = toupper(t); gline[ng] = n
    }
    line ~ /ON CONTROL_Y THEN GOTO/ { }
    line ~ /^\$ *CALL / {
      t = line; sub(/^\$ *CALL +/, "", t); sub(/[^A-Za-z0-9_$].*/, "", t); calls[++nc] = toupper(t); cline[nc] = n
    }
    line ~ /^\$[A-Za-z0-9_$]*: *SUBROUTINE/ { nsub++ }
    line ~ /^\$ *ENDSUBROUTINE/ { nend++ }
    /(ERROR|END_OF_FILE)=[A-Za-z0-9_$]+/ {
      t = line; sub(/.*(ERROR|END_OF_FILE)=/, "", t); sub(/[^A-Za-z0-9_$].*/, "", t); gotos[++ng] = toupper(t); gline[ng] = n
    }
    END {
      for (i = 1; i <= ng; i++) if (!(gotos[i] in seen)) { printf "%s: line %d: no label %s\n", F, gline[i], gotos[i]; bad = 1 }
      for (i = 1; i <= nc; i++) if (!(calls[i] in subs)) { printf "%s: line %d: CALL %s but no such SUBROUTINE\n", F, cline[i], calls[i]; bad = 1 }
      if (nsub != nend) { printf "%s: %d SUBROUTINE but %d ENDSUBROUTINE\n", F, nsub, nend; bad = 1 }
      exit bad
    }
  ' "$tmp" || bad=1
  rm -f "$tmp"
done

if [ "$bad" -eq 0 ]; then echo "check_dcl: OK ($# file(s))"; else echo "check_dcl: PROBLEMS FOUND"; fi
exit $bad
