#!/usr/bin/env python3
"""talktest.py A|B
A = a cpbee user calls the VAX; the VAX answers with PHONE.
B = the VAX calls cpbee with TALK; cpbee answers with the command the ring shows."""
import pexpect, sys, re, time
from netrc import netrc

mode = sys.argv[1]
login, _, pw = netrc().authenticators("cpvax")

vax = pexpect.spawn("telnet cpvax", timeout=150, encoding="latin-1")
vax.logfile_read = open("vax.log", "w", buffering=1)
vax.expect(["Username:", "login:"]); vax.send(login + "\r")
vax.expect("assword:"); vax.send(pw + "\r")
vax.expect("Ready!", timeout=90); time.sleep(1)


def vsend(c):
    vax.send(c + "\r")


vsend("SET TERMINAL/DEVICE=VT100/BROADCAST"); time.sleep(2)
vsend("SHOW SYMBOL TALK"); vax.expect(r"TALK\]TALK", timeout=30)
print("hook ok: TALK symbol is the wrapper")
vsend("SHOW SYMBOL PHONE"); vax.expect(r"TALK\]PHONE", timeout=30)
print("hook ok: PHONE symbol is the wrapper")

bee = pexpect.spawn("ssh -tt cpbee", timeout=60, encoding="latin-1", dimensions=(24, 80))
bee.logfile_read = open("bee.log", "w", buffering=1)
bee.expect(r"\$ ", timeout=30)
bee.send("echo TTY=$(tty); mesg y\r"); bee.expect(r"TTY=/dev/pts/\d+")
print("cpbee side:", bee.after)

ESC = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-B]|\x1b[=>]|\x08|\r|\n")


def collect(p, secs):
    t = time.time() + secs
    buf = ""
    while time.time() < t:
        try:
            buf += p.read_nonblocking(4096, timeout=1)
        except pexpect.TIMEOUT:
            pass
    return ESC.sub("", buf)


def said(sender, receiver, text, label):
    sender.send(text + "\r")
    got = collect(receiver, 40)
    ok = text in got
    print(label, ok)
    if not ok:
        print("   receiver screen text:", repr(got[-400:]))
    return ok


if mode == "A":
    bee.send("talk system@cpvax.cmnet\r")
    i = vax.expect([r"connection requested by [^\r\n]*", pexpect.TIMEOUT], timeout=90)
    print("VAX ring:", "yes: " + vax.after.strip() if i == 0 else "NO RING (see vax.log)")
    if i != 0:
        sys.exit(1)
    time.sleep(1)
    vsend("PHONE chris@cpbee")
else:
    vsend("TALK chris@cpbee")
    i = bee.expect([r"connection requested by [^\r\n]*", pexpect.TIMEOUT], timeout=90)
    print("cpbee ring:", "yes: " + bee.after.strip() if i == 0 else "NO RING (see bee.log)")
    if i != 0:
        sys.exit(1)
    bee.expect(r"respond with:\s+(talk [^\r\n]+)", timeout=20)
    got = bee.match.group(1)
    time.sleep(1)
    print("cpbee answers with:", got)
    bee.send(got.strip() + "\r")

for who, p in (("VAX", vax), ("cpbee", bee)):
    j = p.expect(["Connection established", pexpect.TIMEOUT], timeout=90)
    print(who, "connected" if j == 0 else "NOT connected (see log)")
    if j != 0:
        sys.exit(1)
time.sleep(2)
a = said(vax, bee, "hello from the vax", "cpbee saw VAX text:")
b = said(bee, vax, "hello from cpbee", "VAX saw cpbee text:")
for p in (vax, bee):
    p.send("\x03")
time.sleep(3)
bee.send("exit\r")
vsend("LOGOUT")
print("RESULT:", "both directions work" if a and b else "FAILED")
