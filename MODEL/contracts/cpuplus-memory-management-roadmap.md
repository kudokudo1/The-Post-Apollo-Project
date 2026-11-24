✦︎✦︎✦︎ Meta Apollo Logos //

# CPU++ // MEMORY MANAGEMENT MASTER ROADMAP

> STATE // operator-requested requirements record; proposed implementation plan
> UPDATED // 2026-11-24
> PATIENT // The-Post-Apollo-Project
> ROOM // CPU++ Resource Management & Stability
> SCOPE // CPU++ SYSTEM > MEM / SWAP
> AUTHORITY // External Hospital-compatible DOC; live Hospital registration not verified. Operator retains merge, deployment and acceptance authority.

## 00 // PURPOSE AND CONTINUITY

This is the durable inventory for all memory controls, menus, visualizations, deferred requests, notifications, authorization, diagnostics and future profiles discussed with the operator. Do not silently drop entries during implementation or worker succession. A proposal is not an implemented capability; a merged PR is not native acceptance. Update milestone evidence, blockers, decisions and recovery pointers here as work advances. Preserve separately owned services.

Primary goals: avoid desktop freezes while supporting many Brave windows and parallel workers; understand actual memory use before changing policy; provide safe, native, in-widget controls; never make a slider movement itself a privileged action. No forced workload closure, uncontrolled swap withdrawal or arbitrary root access.

## 01 // CURRENT CHECKPOINT

| Milestone | Evidence / state |
| --- | --- |
| M1a live snapshot | [#2398](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2398), merged; operator reported UI loading |
| M1b native add | [#2399](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2399), [#2401](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2401); native operator readback 16 GiB disk swap, priority 10 |
| Native authorization | [#2406](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2406), [#2408](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2408); operator accepted graphical authentication |
| M1c.1 persistence | [#2411](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2411) merged; operator systemctl readback enabled; actual reboot proof pending |
| M1c.2a target vs actual | [#2422](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2422) merged, 3/3 CI PASS |
| M1c.2b expansion | [#2425](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2425) merged, 3/3 CI PASS; operator updated helper and observed available control, deliberately deferred actual expansion |
| M1c.2e composition | [#2429](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2429) merged, 3/3 CI PASS; native visual acceptance pending |
| M1c.2c/d reduction, extension persistence/recovery | Pending; superseded in scheduling by M1c.3a/3f below, not removed |
| Protected install and ARM/LOCK | [#2412](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2412), open dependency |
| Pending adjustment queue / Hub | [#2433](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2433), recorded requirements, implementation pending |

Last operator terminal evidence: 8 GiB ZRAM (priority 100, 16.8 MiB used), 16 GiB managed SSD swap (priority 10, 0 B used), persistent base unit enabled. Approximately 24 GiB combined logical swap. Do not treat this historical snapshot as current. Physical RAM installed 32 GiB; Linux usable total differs. Earlier global OOM and elevated Quickshell PSS are investigation evidence, not proof of current freeze cause or memory leak. Fedora Silverblue, Btrfs /var on NVMe. No extension activation, reduction, or reboot test claimed.

Recovery paths: widgets/CpuPlusW.qml; widgets/cpuplus/CpuPlusMemoryActuatorPane.qml; CpuPlusMemorySnapshot.js; CpuPlusSwapComposition.qml; CpuPlusMemoryAddControl.qml; services/memory/MemoryOperation.qml; scripts/post-apollo-memory-add-swap; installed root helper /usr/local/sbin/post-apollo-memory-add-swap; tests/cpuplus_memory_*; .github/workflows/cpuplus-memory-add.yml. Base /var/lib/post-apollo-memory-swap/swapfile; extension /var/lib/post-apollo-memory-extension/swapfile. Base systemd swap unit is enabled; extension presently temporary, retained file after boot requires explicit recovery.

## 02 // MENU AND VISUAL CONTRACT

Keep existing CPU++ SYSTEM three bays: left SYSTEM MONITOR, middle SYSTEM TARGET, right CPU++ ACTUATORS. No new independent window. MEM/SWAP select the right memory pane; retain left utilization, existing selection, other worker features and keyboard/focus behavior. Proposed compact subnavigation (icons, short labels where space allows): CAP / POL / PROC / AUTO / DIAG / PROF. Persistent bottom/visible authorization status and pending count/status; do not force a long scrolling menu. Exact dimensions and ordering subject to native UI review. Use existing components, Gohu typography, square outlines, cyan/magenta/yellow palette, native selector dials, existing scroll behavior. No costly extra effects/probes just for decoration.

Right composition: current live 24px outlined stacked track matching left SystemMonitorView. Width proportional to active capacity; bright fill represents occupied slots within each segment, dim fill unused capacity. ZRAM cyan, base NVMe yellow, extension magenta, other swap blue. Legend used/capacity/percentage, meaningful units (B/KiB/MiB/GiB), hide zero-capacity segments. All from same /proc/swaps observation; show mismatch/stale state instead of fabricating values. No extra poller. Preserve actual total, target and projected total independently. Moving slider never changes live bar. Proposed future clearly separate projected composition preview (optional second/dim outlined bar; not live utilization). Left compact mirror deferred until operator accepts right side. No physical RAM double counting: ZRAM logical occupancy vs compressed physical memory footprint are different. RAM can be shown separately with MemAvailable and pressure; do not label physical RAM as swap.

## 03 // CAPACITY (CAP)

Inventory (all future unless checkpoint says otherwise):
- Physical installed RAM and kernel usable RAM; DIMM cards by slot, capacity, vendor/model, speed/configured speed, channel where evidenced. No claim that an application's pages belong to a particular DIMM.
- ZRAM logical capacity and actual compressed RAM footprint; adjust size with separate safe device lifecycle, not blind reset. Show compressed/uncompressed data, metadata overhead, ratio and algorithm.
- Managed disk swap base and extension capacity, active used/free/priority, actual vs target slider, reset target, explicit prepare/confirm/cancel, expansion, reduction, zero target/remove. Initial target range 0–64 GiB step 4 (zero is not supported removal yet). Existing helper limit/reserve retained; user-adjustable bounds only after reviewed enforcement.
- Storage device selection: physical drive cards (model, capacity, free/used, mount, filesystem, supported target, reserved bytes, health when available). Choose approved storage location, maximum allocation and minimum reserved disk space. Never auto-select unrelated/unmounted Windows disk; no destructive disk format/mount or arbitrary path. Btrfs constraints/single-device validation; enforce reserve at root.
- Per-device priority; base 10, extension 9, ZRAM 100 as current evidence, not permanent mandated values. Priority changes may require deactivation and therefore safe gate.
- Boot persistence toggle, verify enablement, explicit reactivation of existing file, disable persistence separately from live removal, recover partial files/units; extension persistence and cleanup. No automatic deletion.
- INSTALL / UPDATE / REPAIR helper; installed identity/version and source/receipt, update required state, retry only on explicit action, protected release provenance. No arbitrary checkout-to-root install command in normal UI.

## 04 // MEMORY BEHAVIOR (POL)

Controls with current/target/default/readback, temporary vs persistent choice, explicit apply, cancel, restore supported default, explanatory tooltip and validation. No bulk application on opening menu.
- Swappiness (kernel 0–200): relative anonymous swap vs filesystem cache reclaim cost, not percent RAM threshold. Show actual kernel setting, contextual guidance; no arbitrary recommended setting chosen yet.
- ZRAM compression algorithm: available algorithms and current algorithm; compression speed vs savings. Safe reconfiguration/restart gate; no reset under pressure.
- Swap priority per device, consistent with CAP view; no duplicate independent writers.
- Filesystem metadata cache reclaim pressure (vfs_cache_pressure), advanced; distinguish from page cache and free RAM.
- Dirty memory/writeback limits: dirty ratio/bytes and background threshold, flush timing if supported; mutually exclusive modes and kernel constraints; disk stalls risk. Advanced, default unchanged.
- Preserve actual observed defaults and ownership. No global drop-caches button as a routine optimization; no unreviewed kernel tunables, BIOS speed changes or overclocking.

## 05 // PROCESS MANAGEMENT (PROC)

Group actual processes by stable application/cgroup identity; show RAM contribution (PSS/RSS/private, clarify shared pages), swap use when available, process count, growth trend and evidence. Correct omitted Quickshell and Brave contributors; identify relevant workers without killing tabs. Existing process menu and owner scopes remain intact.

Proposed controls: per-app monitoring, memory soft limit (cgroup memory.high where supported), hard limit (memory.max; may OOM-kill), swap limit (memory.swap.max where supported), OOM protection/selection policy (memory.low/min or appropriate oom_score_adj mechanisms, separate semantics), growth alert threshold/window, process priority (define CPU nice vs memory protection; not interchangeable). Explicit target group, scope, ownership, policy default, permissions, impact, readback and undo. Do not protect everything or impose hard limits on Brave/Quickshell by default. Distinguish systemd-oomd and kernel OOM; verify cgroup membership/controller availability. No blanket protection, forced kill, restart or unsolicited limit. Investigate Quickshell memory growth and autotiling process duplication before optimization; track evidence over time, do not call a leak proven from one sample.

## 06 // AUTOMATION AND SAFETY (AUTO)

Controls: auto expansion (default OFF), auto reduction (default OFF), maximum automatic allocation, minimum physical RAM headroom, remaining swap headroom, stability interval, check interval, pressure limits, pending requests, notification options, request expiry, manual recheck/apply/cancel/replace, history. Threshold values are proposed decisions to calibrate with native evidence, not silently selected production defaults. No forced reduction override.

### Queue / durable intent
Explicit QUEUE/REQUEST; slider alone stages a target. One pending target per managed allocation initially; explicit replacement/cancel. Store request ID, exact target, operation/source identity, observed capacity, requested time, last/next check, status, blocker code plus evidence, authorization mode (not secret), expiry, attempts/receipts/recovery pointer. Atomic local storage, validate schema and identity; corrupt/stale data fails closed. Intent persists through pane closure and ultimately Quickshell reset and reboot; never persist credentials or authority in user-writable state. On restart reconcile actual kernel/file/boot state, mark ambiguous running operation UNKNOWN, no auto replay or retry. Never mark done based on slider or process exit alone.

States: QUEUED -> WAITING -> READY -> AUTH REQUIRED -> ADJUSTING -> VERIFIED; alternatives FAILED, UNKNOWN/RECOVERY, CANCELLED, EXPIRED. Conditions can regress READY -> WAITING. Cancellation stops future work, not necessarily a running kernel command. Display current/target, delta, occupied bytes, RAM headroom, remaining swap, memory pressure, exact blocker/reason, last checked, next check time or disabled state, required action and request history. No guaranteed completion ETA. HOW TO RESOLVE should explain waiting, rechecking or explicitly freeing unneeded workloads if the operator chooses, never force closing workers or bypassing preflight. Show successful adjusted time and kernel-verified receipt.

### Safety / execution
Read live /proc/meminfo, /proc/swaps and /proc/pressure/memory; check file identity, priority, mount, ownership, space reserve, capacity, occupied pages, other operations, available RAM and remaining capacity, stable observation interval. Recheck immediately at privileged execution. A preflight is not an absolute guarantee against a subsequent spike. First bounded withdrawal: unused separate extension only, sufficient headroom/low pressure, preserve original base, protected operation serialization and recovery. Never truncate active swap or force withdrawal of occupied extension. Later occupied withdrawal/base replacement/zero target require separately reviewed migration and kernel behavior tests. Preserve files and recovery state on ambiguous result; no automatic cleanup or retry. Reclaim disk only after independently confirmed inactive and correct identity, explicit consent. Never assume a reboot removes files.

### Monitoring
Lightweight monitor only while request exists; independent of pane visibility; no constant spawning or heavy logging. Reuse current snapshot source where suitable, timestamp/validate observation, safe polling, event transition tracking. Initial notify-only mode requires fresh explicit authorization when ready. No monitoring while Quickshell stopped unless separate service implemented. Automatic execution later only with valid bounded protected grant, fresh preflight and explicit opt-in; expiry/revocation prevents new action, not necessarily abort of in-flight operation. No simulated READY used as permission.

### Notification Hub
Use existing notification owner/API and routing, not a second notification service. Notify on deferred (with blocker), ready (authorize/open CPU++), completed (actual capacity and time), failed/unknown/recovery, expired; cancel optional. Stable request/event identity and durable deduplication across restarts; no notification per poll. Respect source routing, DND and user notification preferences. Link/open exact CPU++ pending-operation view where supported; verify integration owner first. UI field remains readable even if notification suppressed. Example: "24 → 16 GiB requested; waiting for unused extension / safe headroom"; "Ready for fresh authorization"; "Verified 16 GiB at [time]". No promise of adjustment until kernel readback.

## 07 // DIAGNOSTICS (DIAG)

- Physical memory: DIMM specifications and installed/usable distinction, memory modules vs disk cards.
- RAM: total, available, anonymous/file cache, reclaimable, shared, slab, kernel and process breakdown where reliable. Avoid misleading sum of RSS or ZRAM capacity.
- Compressed memory: /sys/block/zram*/mm_stat and relevant sysfs, actual RAM footprint, logical occupied swap, compression ratio, overhead, algorithm; validate platform fields.
- Swap activity: pages in/out from kernel counters and rates, per-device occupancy, active state/priority; distinguish retained cold pages from ongoing thrashing. No attribution of pages to individual physical DIMMs.
- Memory pressure: PSI some/full and trend, headroom, historical peak and recent spikes; include source/time and missing-data state.
- Process growth: stable identity, PSS/private/RSS/swap trends, grouping Brave/Quickshell, bounded history, alert on sustained growth.
- OOM history: kernel and systemd-oomd events where accessible; timestamp/boot/process and evidence; no claim a single event caused every freeze.
- Memory leak suspects: evidence-based trend and lifecycle correlation; distinguish cache/shared memory. Investigate compositor/GPU/clocksource/autotiling warnings separately where relevant. No automated blame or restart.
- Physical storage: cards and capacity/reserve/health when evidenced; no unrelated disk writes.

## 08 // PROFILES (PROF)

Proposed named profiles: BALANCED, DEVELOPMENT, GAMING, LOCAL AI, STABILITY, CUSTOM. Saved combinations of capacity targets, memory policy, process protections, automation limits and notifications. Preview exact diffs with unsupported fields, per-operation permissions, partial application outcomes, rollback plan and actual readback. Save/edit/delete/rename custom profiles, restore defaults explicitly; no profile applied at selection or startup without authorization. Defaults/values are not decided. Do not silently change kernel policy or enable automation merely because a profile name suggests it.

## 09 // SYSTEM AUTHORIZATION / INSTALLATION (CROSS-CUTTING)

Follow #2412 and coordinate Connections and Clock owners. Existing graphical one-shot Polkit verified; no reusable grant installed. ARM/LOCK UI and adjustable authorization duration dial (up to 24h proposed, not approved default), expiry choices: duration, Quickshell process reset, logout, PC reboot, screen lock, manual LOCK; combined earliest expiry when selected. Exact operation scope/limits, process/session/boot identity, protected host enforcement, revocation, fresh preflight and readback. No QML boolean as authority, password caching, broad root cache or unrestricted sudoers. Store intent independent of grant. Root-owned trusted installer with fixed component ID, verified release/version/digest, atomic install, rollback, provenance; not privileged arbitrary source from mutable checkout. Coordinate before crossing owner boundaries. Existing helper update remains explicit manual bootstrap until trusted installer available.

## 10 // ROADMAP AND ACCEPTANCE GATES

Order can be adjusted by operator; preserve IDs and all requirements. Capacity and memory behavior first, diagnostics early for stability, process controls after evidence, automation and profiles on protected foundations. Queue work is already explicitly requested and should be retained regardless of ordering.

| ID | Deliverable | State |
| --- | --- | --- |
| M1a–M1c.2b | Snapshot, add, native auth, base boot enablement, target correction, expansion | Merged; native gates noted above |
| M1c.2e | Right live composition/usage | Merged; visual acceptance pending |
| M1c.3a (2c) | Bounded safe extension withdrawal/reduction backend | Pending |
| M1c.3b | Durable adjustment queue and status | Pending |
| M1c.3c | Condition monitor, recheck, remediation | Pending |
| M1c.3d | Notification Hub integration | Pending owner/API verification |
| M1c.3e | Explicit protected automatic execution | HOLD #2412 |
| M1c.3f (2d) | History, receipts, recovery, extension persistence/reactivation/cleanup | Pending; split as needed |
| M1d | CAP remaining controls, safe ZRAM lifecycle, storage target/reserve/priority, persistence disable/removal | Pending |
| M1e | POL readback and staged memory behavior controls | Pending |
| M2 | Hardware DIMM/storage cards, DIAG compressed usage, activity, PSI/OOM | Pending |
| M3 | PROC grouping/growth, Quickshell diagnostics/optimization, bounded process controls | Pending |
| M4 | Advanced AUTO policy, profiles, cross-menu integration, performance and recovery | Pending |
| X1 | Protected installation/update/repair and ARM/LOCK shared authority | HOLD #2412 |
| UX-L | Left composition mirror | Deferred until explicit operator visual approval |

Acceptance per milestone: source/unit tests (invalid, stale, absent, conflicting data); exact-head CI; independent review for privileged/security work; native visual/operator verification; disposable native Btrfs/SELinux/systemd tests before production withdrawal; reboot proof at normal operator restart; fault cases (occupied extension, memory spike, reserve failure, concurrent operations, interruption/crash, cancelled/expired authorization, stale source, ambiguous result, duplicate notification, reboot reconciliation). Distinguish mocks, native fixture and production evidence. Do not test live expansion/reduction while operator is running important work unless operator explicitly chooses. Avoid restart/reload as routine; normal deployment follows existing lifecycle rules. Keep runtime cost bounded and measure.

## 11 // REPORTING / RECOVERY

Use IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS at meaningful handoffs. Record exact PR/head, CI, merge, review, operator evidence, blockers, pending actions and recovery pointers. No silent feature removal. This document is a roadmap, not authorization to implement every control at once. No runtime changes, live Hospital registration, merge or acceptance implied by this record.

## 12 // OPEN DECISIONS

- Exact UI rail/icon order, right bar final styling and whether to mirror left.
- Whether projected composition gets its own bar or preview text; keep live usage independent.
- Calibrate safety thresholds, stability and poll intervals; protected reduction behavior under concurrent workloads.
- Queue expiry, history retention, cancellation and post-reboot scope; auto mode off until protected authorization.
- Notification owner/API and exact routing/action support.
- Supported storage targets, ZRAM compression algorithms and actual kernel/cgroup controls; profile presets and default values.
- Trusted installer and bounded authorization owner/contract, #2412.
- Native expansion, withdrawal, boot and visual acceptance deliberately pending; operator decides test timing.

