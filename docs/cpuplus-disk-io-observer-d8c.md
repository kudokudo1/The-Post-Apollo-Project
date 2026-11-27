# CPU++ DOC 3 D8c-a — Whole-device disk I/O observer

## Scope

Separate bounded Python reader, not yet mounted in CPU++ or admitted by the
diagnostic session/receipt/archive contract. It samples Linux /sys/block whole
device-backed block objects; excludes partitions and purely virtual devices
(loop, dm, zram). Virtual-machine devices may still appear device-backed;
this is not proof of physical media identity. No benchmarks, disk writes,
arbitrary paths supplied through CLI, filesystem content reads, privileges,
resident polling or new control authority.

Explicit workshop capture: 1–30 seconds, interval 1–5 seconds, maximum 12
intervals, 32 devices, 64 KiB ASCII JSONL. No default execution.
Device identity is pinned by name, resolved sysfs object, device number,
optional kernel disk sequence and directory inode; topology/counter reset
or report overflow refuses complete output. This is read-only observation,
not a protected hardware attestation.

## Receipt

Schema post-apollo-disk-io-v1. Each diskio sample has sequence, elapsedMs,
intervalMs and devices. Each compact device tuple is:

    [name, major, minor, diskseq-or-null,
     read-operations, read-bytes, read-ms,
     write-operations, write-bytes, write-ms,
     io-ms, weighted-io-ms, in-flight-at-sample]

Counters are deltas for this measured interval except the final point reading.
Linux stat sectors are always 512-byte units, independent of logical block
size. Read/write operations and bytes do not include discard/flush.
Read/write milliseconds and weighted I/O milliseconds can exceed elapsed
wall time with concurrent work; raw io-ms is a kernel accounting counter,
not a definitive saturation score. No cross-device sum of utilization.
No process attribution, filesystem cache attribution or latency guarantee.
Idle zero deltas are legitimate. Complete record binds requested calibration
and actual observed duration. No partial success receipt on errors.

## Next

Integrate through the existing STORAGE subject and single diagnostic owner:
add explicit diskio calibration, strict receipt validation, report summary,
archive/routing, PREPARE/START and native fixtures. Keep metadata capture
separate from device I/O. Use the D8b shared status/selector layout; do not
duplicate the workspace. Actual workstation acceptance and resource cost
measurements remain separate. No protected or live system changes.

## D8c-b integration

Storage now offers separate metadata and whole-device disk I/O selectors in the same status band. Disk I/O runs alone; sequential workflow sets can contain both capture kinds. Calibrate duration and interval, PREPARE then START. REPORT → DISK shows bounded per-device throughput/IOPS and kernel I/O time summaries; all raw records are retained. The existing archive, exact report notification route and single-flight owner are reused. No new timer, protected action or physical-device write. Native disposable fixture checks exact argv, receipt, archive and remount; exact-head CI and desktop acceptance remain pending. Dedicated disk comparison deferred.
