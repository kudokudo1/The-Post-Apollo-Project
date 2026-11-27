# D9a-a — Host swap traffic and pressure observer

Explicit diagnostic reader, not yet a mounted menu or admitted report kind.
Reads /proc/vmstat pswpin/pswpout, /proc/meminfo, /proc/swaps and optional
/proc/pressure/memory and active /dev/zramN mm_stat. No writes, device
commands, swapoff, reclamation, privileged actions, file-content reads or
background polling. Existing DOC 1 capacity/policy ownership unchanged.

Bounds: 1–30 seconds, 1–5 second integer cadence, maximum 12 intervals,
32 active swap entries, 16 active zram names, 64 KiB ASCII JSONL. Swap
topology (names/types/capacity/priority) and host capacity checked; swap
paths retained only in local process memory, not output. This is not
strong device identity attestation. Non-atomic kernel snapshots are not
an exact cross-source accounting reconciliation.

Each swapio sample records memoryKiB [RAM total, available, swap total,
used], swapBytes [in, out] from actual page-size-scaled VM event counter
deltas (not physical disk traffic), optional pressure [some avg10, full
avg10, some stalled microseconds delta, full delta], and active zram rows
[name, original bytes, compressed bytes, total allocated bytes].
PSI rolling averages and interval stall counters are distinct. Missing
optional data is null; zero swap traffic is valid. zram total allocation
includes allocator overhead and is not additional usable RAM. A zram
row is a point measurement, not a swap throughput measurement.
No swap-path disclosure or per-process attribution. If topology or
required counters are invalid/reset, or output exceeds budget, refuse
the terminal receipt. Complete record includes actual page size,
duration, sample count and exact calibration.

Next: validate receipts and mount the observer in existing Memory/SWAP
DIAG without replacing CAP/POL/PROC/AUTO/PROF or duplicating the layout.
Preserve existing shared session, archive, notifications and workflow
sets. Dedicated native and desktop verification required.
