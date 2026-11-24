# CPU++ DOC 3 // M3a.11 memory observation checkpoint

**State:** operator-reported observations and proposed source-only diagnostic.  
**Room:** CPU++ Resource Management & Stability / diagnostics.  
**Authority:** external Hospital-compatible DOC 3; Nurse 2 review pending; no live registration or deployment implied.

## Observations (2026-11-24, operator terminal)
- PID 1810955: 5.67 GiB PSS at 08:22; 5,973,380 KiB PSS at 08:27, including 5,895,452 KiB anonymous PSS.
- 08:34–08:36 mixed widget interaction: +184.8 MiB peak PSS, +65.8 MiB net; closed-widget comparison 08:38–08:40: +24.4 MiB peak, -19.2 MiB net. Different activities, not randomized trials.
- AppControl transitions: 6 CPU seconds / 6 wall seconds, then 9 / 7; closed-menu interval 9 / 30. Transition intervals do not establish steady-state cost or recursion.
- PID replaced by 4034678; at 08:58 RSS 8,403,784 KiB, PSS 8,325,919 KiB, anonymous PSS 8,243,844 KiB, SwapPss 21,784 KiB. At 09:07 same PID RSS 5,981,508 KiB, about 2.31 GiB less. No later PSS/SwapPss sample, so cannot distinguish reclaim from swapping. No matching kernel/OOMD/coredump/old-PID records; truncated journal; exit cause unknown.
- Operator identifies AppControl, Git, Hospital and Notification Hub as churn suspects, Music as retention suspect. These are leads, not attribution.

## Preserved prior decisions
- See [opening lifecycle pilot](../docs/window-opening-lifecycle-pilot.md): Git/Hospital unmap/remap crashed; preserve mapped surfaces and masks.
- See [existing lag evidence](syntagma-main-thread-freeze-evidence-20261013.md), [startup trace](syntagma-git-startup-trace.md) and [probe guide](../OPERATE/syntagma-ui-lag-probe.md). CAVA latest-frame coalescing and hidden Notifications history deferral are now default in inspected source; retain them. AppControl hidden histories reuse bounded arrays; visible histories copy on write. Do not infer which path caused private memory from mapping size.
- Previous source indicates multiple GitService instances and startup discovery; current ownership and behavior require reconciliation before edits.

## New observation tool
Run from a checkout containing this reviewed tool, without restarting or modifying Quickshell:
```sh
python3 -B scripts/cpuplus_quickshell_memory_observer.py --pid "$(pgrep -n -x quickshell)" --duration 120 --interval 10
```
The explicit PID should be checked if multiple instances exist. Default picks newest same-user Quickshell. Reads proc stat and smaps_rollup, reuses existing sampler identity parser, outputs only numeric JSONL, stops on unavailable/changed process identity or incomplete rollup. First CPU rate is null; subsequent rates are percent of one logical core, not a lifetime average. PSS + SwapPss approximates proportional resident and swapped footprint; neither proves object lifetime, allocator ownership or physical compressed swap cost. Reads may be nontrivial for large processes: manual bounded observations only, minimum ordinary interval five seconds, no daemon or QML polling. No logging of argv, notification text, file mapping names, or credentials. No additional packages or privilege.

## Next
Compare controlled states; use existing thread sampler and opt-in traces where available. No restart without operator approval. Do not change DOC 1 capacity, DOC 2 menu, DOC 4 queue, or other widget owners' files without coordination. Native test, exact-head CI and independent review required before adoption. No source-level performance fix claimed.
