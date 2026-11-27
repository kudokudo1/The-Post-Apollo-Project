# DOC 3 D10c — SYSTEM paired selectors and combined capture

Operator visual feedback: status text and selector overlap at compact and
intermediate sizes; preserve semantic vertical pairs at all sizes. SYSTEM
keeps two rows of five: Threads/Stall, Host CPU/Disk I/O, Memory/Storage,
CPU census/GPU, Network/Swap. Reserve a separate status rectangle with
minimum 16px readout height and clipping; stack the rail below it if there
is insufficient width. Memory and Swap DIAG add a top-right information
button in their observation header.

SYSTEM selection no longer replaces a previous instrument. Each selected
instrument displays its own calibration controls; host CPU and GPU have
separate sliders. A valid combined plan may contain two to ten distinct
instruments, using the existing single owner and bounded parallel runner.
The five newer collectors attach workflow-only monotonic baseline and
terminal timestamps; standalone receipt formats are unchanged. The runner
validates exact calibration and actual overlap; the independent receipt
policy revalidates each collector's semantic evidence. Existing process
identity pinning, cancellation, deadlines, PREPARE/START and per-child
limits remain in force. Aggregate report limit remains 300000 bytes; a
capture exceeding that limit is NOT VERIFIED, never silently truncated.

For all ten, a valid example is 10 seconds, 1-second thread/hardware
intervals, top count 4, 10-second memory/census intervals, storage
sample/report 1/10 seconds, stall threshold 350ms. Selection is not
permission to execute. A mixed capture can fail if a host device lacks
required measurements; workstation acceptance and observer overhead are
separate from disposable tests.

Added responsive header, paired selector, independent control and ten
selection fixture checks, ten disposable parallel child barrier test,
fixed argv and clock receipts, five-hardware semantic evidence tests.
No new resident polling, host configuration, or protected operations.
