# Sanitized firewall counters

Source and destination addresses are replaced before this file is written.

## IPv4 filter/EDGE_TS_INPUT

```text
Chain EDGE_TS_INPUT (1 references)
num   pkts bytes target     prot opt in     out     source               destination         
1 958 61310 ACCEPT all -- * * [source-redacted] [destination-redacted] ctstate RELATED,ESTABLISHED
2 10305 680K ACCEPT udp -- * * [source-redacted] [destination-redacted] udp dpt:53
3 22 1320 ACCEPT tcp -- * * [source-redacted] [destination-redacted] tcp dpt:53
4 0 0 ACCEPT tcp -- * * [source-redacted] [destination-redacted] tcp dpt:8443 ctstate NEW
5 106 160K LOG all -- * * [source-redacted] [destination-redacted] limit: avg 6/min burst 10 LOG flags 0 level 6 prefix "ASUS-EDGE-DROP "
6 111 160K DROP all -- * * [source-redacted] [destination-redacted]
```

## IPv4 filter/EDGE_TS_FORWARD

```text
Chain EDGE_TS_FORWARD (1 references)
num   pkts bytes target     prot opt in     out     source               destination         
1 89396 22M ACCEPT all -- * * [source-redacted] [destination-redacted] ctstate RELATED,ESTABLISHED
2 0 0 ACCEPT tcp -- tailscale0 br0 [source-redacted] [destination-redacted] tcp dpt:80 ctstate NEW
3 0 0 ACCEPT tcp -- tailscale0 br0 [source-redacted] [destination-redacted] tcp dpt:631 ctstate NEW
4 0 0 ACCEPT tcp -- tailscale0 br0 [source-redacted] [destination-redacted] tcp dpt:9100 ctstate NEW
5 0 0 ACCEPT udp -- tailscale0 br0 [source-redacted] [destination-redacted] udp dpt:161
6 3773 1443K ACCEPT all -- * ppp0 [source-redacted] [destination-redacted]
7 0 0 LOG all -- * * [source-redacted] [destination-redacted] limit: avg 6/min burst 10 LOG flags 0 level 6 prefix "ASUS-EDGE-DROP "
8 0 0 DROP all -- * * [source-redacted] [destination-redacted]
```

## IPv4 nat/EDGE_TS_PREROUTING

```text
Chain EDGE_TS_PREROUTING (1 references)
num   pkts bytes target     prot opt in     out     source               destination         
1 10305 680K REDIRECT udp -- * * [source-redacted] [destination-redacted] udp dpt:53 redir ports 53
2 22 1320 REDIRECT tcp -- * * [source-redacted] [destination-redacted] tcp dpt:53 redir ports 53
3 0 0 DNAT tcp -- * * [source-redacted] [destination-redacted] tcp dpt:8443 to:[translated-address-redacted]:8443
```

## IPv6 filter/EDGE_TS6_INPUT

```text
Chain EDGE_TS6_INPUT (1 references)
num   pkts bytes target     prot opt in     out     source               destination         
1 0 0 ACCEPT all * * ::/0 [source-redacted] [destination-redacted] RELATED,ESTABLISHED
2 0 0 LOG all * * ::/0 [source-redacted] [destination-redacted] avg 6/min burst 10 LOG flags 0 level 6 prefix "ASUS-EDGE-DROP "
3        0     0 DROP       all      *      *       ::/0                 ::/0                
```

## IPv6 filter/EDGE_TS6_FORWARD

```text
Chain EDGE_TS6_FORWARD (1 references)
num   pkts bytes target     prot opt in     out     source               destination         
1 0 0 ACCEPT all * * ::/0 [source-redacted] [destination-redacted] RELATED,ESTABLISHED
2 0 0 LOG all * * ::/0 [source-redacted] [destination-redacted] avg 6/min burst 10 LOG flags 0 level 6 prefix "ASUS-EDGE-DROP "
3        0     0 DROP       all      *      *       ::/0                 ::/0                
```
