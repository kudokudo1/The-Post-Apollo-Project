# CPU++ DIAG Workshop D1a — calibration preview

Operator direction: one universal instrument with subject-filtered views; reuse SelectorSlider (horizontal step presentation), SelectorDial, ActionButton and existing report infrastructure. No separate diagnostic daemon. Subject color controls border, ticks, handle and glow; fill conveys function.

## Operator-confirmed palette

Use Colors.qml constants, not duplicate hex. CPU orange, memory magenta, RSS blue (occupied resident capacity, not disk I/O), threads cyan (execution flow), PID purple (identity), time/uptime white, disk/storage blue, swap yellow, signals/network cyan, GPU and fans Omnitrix. Ordinary green denotes active processing. Duration and sampling: white/Omnitrix. TOP THREADS: cyan/magenta; stall threshold: white/yellow. The latest operator-approved palette supersedes the initial KILL convention. PR #2878 proposes the shared Colors.resourceColor mapping and purple #A879ED; independent review and merge pending. No runtime dependency on #2878 in D1a. Prepare white, calibrating yellow, ready/start orange, recording green, verified complete Omnitrix. Borrow full-face fill behavior from GitW saveWorkflowButton and Trash Burn, but real readiness/completion must be observed rather than inferred from animation. Do not edit shared control or other widget owners in this slice.

## D1a boundary

Pure, unmounted preview validates explicit known configuration fields against collector arguments and conservative current report budgets. Existing fixed buttons, QML owner, process execution, archive, timers, source probes, protected operations unchanged. No arbitrary PID/command/path, no automatic launch. Current 145s worker timeout, 155s owner deadline and 65536 report cap unchanged. Estimated interval/observation count is not a verified sample count or byte guarantee. Thread ranking retains top count plus main if outside ranking; the current Python CLI help is imprecise. AppControl v1 stays fixed until report validation and configuration provenance are upgraded. Memory interval 5–60 seconds, maximum 12 intervals plus baseline; census preview deliberately limited to 3 intervals (script supports 6); storage fixed 1s metadata observation, aggregated output each 10s/final. Inventory one-shot. These are initial conservative preview decisions, not universal hardware capabilities.

## Next

Independent Nurse 2 and DOC1 covering DOC2 review. D1b: exact launch configuration provenance, bounded output and report schema, guarded target identity, native qualification. D2: shared coordinated workflow, independent instrument intervals and common timestamps; avoid duplicated collectors. D3: UI and presets, shared fill behavior in coordination with relevant owners. Startup, GPU/network, exact core and QML function tracing remain unimplemented. No workstation changes or production resource actions.


## D1b — first configured collector

Thread sampling only: explicit configuration is copied and checked before the existing session owner starts the existing sampler. Fixed executable/path and newest same-user Quickshell scope; no caller PID, command, file path or authorization. The opt-in `--workshop` protocol bounds actual ASCII JSONL output to 65536 bytes, records duration/interval/top, process start ticks and observed monotonic duration, and refuses process identity changes. The owner checks the receipt against the submitted configuration before COMPLETE; comparisons refuse mixing a configured capture with legacy or different calibration. Same report archive and cancellation owner; no new background activity or UI mount. A successful report is observed data, not proof of root cause. Legacy fixed buttons remain available. Native fixture uses a disposable synthetic child, while synthetic procfs tests exercise the actual Python sampler. Real desktop performance and timing remain unqualified.

This draft is based on D1a head 31be2099. Merge D1a first; recheck final combined main, CI and independent review before merging D1b. Other collector configuration, process targeting, multi-instrument coordination, actual sliders and state button, stall threshold and shared KILL migration are not in this slice.
