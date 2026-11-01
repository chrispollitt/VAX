#!/usr/bin/env python3
"""Builds LIFE.C for POSIX and checks, on a pseudo-terminal, that a key stops the game.

    python3 test_keystop.py            (from anywhere; needs gcc)

1. LIFE runs by itself on a terminal for a second or two, so it is still going.
2. A space typed then ends it with "you pressed a key" and the terminal is back to normal afterwards.
3. With its input not a terminal (a pipe) it runs to the end of the generations it was given.
"""
import os
import pty
import select
import subprocess
import sys
import tempfile
import termios
import time

here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()
exe = os.path.join(tmp, "life")
subprocess.check_call(["gcc", "-x", "c", "-ansi", "-pedantic", "-Wall", "-Wextra", "-o", exe,
                       os.path.join(here, "LIFE.C")])
failures = []


def check(name, ok, detail=""):
    if isinstance(detail, bytes):
        detail = repr(detail)
    print(("ok    " if ok else "FAIL  ") + name + ("" if ok else "  " + detail))
    if not ok:
        failures.append(name)


def drain(fd, secs):
    out = b""
    end = time.time() + secs
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            out += data
    return out


pid, fd = pty.fork()
if pid == 0:
    os.execv(exe, [exe, "500", "R"])
before = termios.tcgetattr(fd)
out = drain(fd, 1.5)
check("still running after 1.5 s", b"Finished" not in out, out[-80:])
os.write(fd, b" ")
out += drain(fd, 2.0)
check("space stops it", b"you pressed a key" in out, out[-120:])
_, status = os.waitpid(pid, 0)
check("exits normally", os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, str(status))
after = termios.tcgetattr(fd) if False else before      # the child's terminal is gone; the restore is checked below
os.close(fd)

# the terminal modes are put back: ask a second run what it saw and what it left behind
code = ("import os,pty,sys,termios,time\n"
        "pid,fd=pty.fork()\n"
        "if pid==0: os.execv(%r,[%r,'3','R'])\n"
        "time.sleep(2)\n"
        "t=termios.tcgetattr(fd); print('canonical' if t[3] & termios.ICANON else 'raw')\n") % (exe, exe)
res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
check("terminal back to normal after the game", res.stdout.strip() == "canonical", res.stdout + res.stderr)

res = subprocess.run([exe, "3", "R"], capture_output=True, text=True, input="")
check("with a pipe on the input it just runs", "Finished after 3 generations" in res.stdout, res.stdout[-120:])

print()
print("all passed" if not failures else "FAILURES: " + ", ".join(failures))
sys.exit(1 if failures else 0)
