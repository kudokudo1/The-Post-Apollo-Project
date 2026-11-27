# D10a-a — Network interface observation

Bounded explicit read-only observer, not yet mounted in CPU++.
Reads /proc/net/dev and /sys/class/net identity and optional operational
state. No sockets, remote endpoints, DNS, ping, speed tests, packet payloads,
addresses, wireless credentials, configuration changes or resident polling.

1–30 seconds, 1–5 second integer cadence, maximum 12 intervals,
32 interfaces and 64 KiB ASCII JSONL. Includes loopback and virtual devices
independently: never aggregate stacked interfaces into a host total.
Pins visible name/index/link/type and resolved sysfs directory identity;
checks proc/sysfs coverage and counter continuity. This is not strong
interface identity attestation; snapshots are non-atomic. Topology changes,
counter reset, missing required sources or budget overflow refuse completion.
Unsupported/missing operational state is null. Idle zero is valid.

Schema post-apollo-network-io-v1. Each netio sample includes sequence,
elapsedMs, intervalMs and interfaces. Each interface tuple:

    [name, ifindex, iflink, ARPHRD type, operstate-or-null,
     RX bytes, packets, errors, drops, TX bytes, packets, errors, drops]

All counters are interval deltas. /proc/net/dev combines some drop/error
fields; these are kernel interface counters, not end-to-end packet loss.
Throughput uses actual elapsed time and decimal Mb/s (bytes * 8 / seconds
/ 1,000,000). No inference of internet latency, available link capacity,
application traffic or root cause. Complete record binds exact calibration.

Next: strict receipt, shared NETWORK workspace, semantic cyan selector,
reports/archive/notifications and sequential sets; preserve existing network
health functionality and no background pollers. Native and desktop acceptance
remain separate.
