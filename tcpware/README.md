# cpvax TCPware name configuration (domain cmnet)

On 2026-10-31 the local domain of the LAN changed from `lan` to `cmnet`. TCPware keeps the **full host name** in
`TCPWARE_DOMAINNAME`, so the VAX is now `cpvax.cmnet` (it was `cpvax.lan`, which its own resolver could not look up, so
`talk` said "Can't figure out network address" and Perl's `hostname()` returned an unresolvable name).

| File | Where on cpvax | Change |
|---|---|---|
| `TCPWARE_CONFIGURE.COM` (`.before` = previous) | `SYS$SPECIFIC:[TCPWARE]` (new version ;8) | `NETCU_DOMAIN == "cpvax.cmnet"`, `NAMED_SERVERS == "192.168.20.1"` (cpbee's dnsmasq on vaxtap, the resolver's name server list), `DOMAIN_LIST == "cmnet"` (search domain) |
| `HOSTS` (`.before` = previous) | `SYS$COMMON:[TCPWARE]` (new version ;4) | only `cpvax.cmnet cpvax` and `cpbee.cmnet cpbee`; every other name comes from cpbee's DNS (`TCPWARE_SVCORDER` is `local,bind`) |

Applied live with `NETCU SET DOMAIN cpvax.cmnet` and `DEFINE/SYSTEM` of `TCPIP_DOMAINNAME`, `TCPIP_NAMESERVERS`,
`TCPWARE_NAMESERVERS`, `TCPWARE_DOMAINLIST`, `TCPIP$INET_DOMAIN`, `UCX$INET_DOMAIN`; at boot `STARTNET.COM` and
`STARTUP_RESOLVER.COM` derive the same from `TCPWARE_CONFIGURE.COM`.

Undo: on cpvax `COPY SYS$SPECIFIC:[TCPWARE]TCPWARE_CONFIGURE.COM;7 SYS$SPECIFIC:[TCPWARE]TCPWARE_CONFIGURE.COM` and
`COPY SYS$COMMON:[TCPWARE]HOSTS.;3 SYS$COMMON:[TCPWARE]HOSTS.`, then reboot (or `NETCU SET DOMAIN cpvax.lan`).
