# MACHINE // V2 floating geometry placement, disposable rehearsal

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Desktop & Brave Recovery
STAFF ROLE // External Hospital-compatible DOC; live registration unverified
ASSIGNMENT // Real command-path rehearsal for explicitly selected floating windows, including two same-app Brave windows
STATE // DRAFT, CI-ONLY, NOT PRODUCTION AUTHORIZATION

## IMPLEMENTATION

`services/time/MachineV2FloatingPilot.py` provides two distinct steps:

1. `prepare(request, read_runner=...)`: read a preexisting V1/V2 pair, strictly validate it, double-observe Sway with the existing fixed `get_outputs/get_workspaces/get_tree` queries, and check an **operator-manually selected current Sway container ID** against one saved V2 window key. This does not create or verify persistent identity and does not issue an action grant.
2. `execute_disposable(request, read_runner, command_runner, journal, ...)`: only usable through injected runners, an explicit fixture journal and a CI/GitHub Actions guard. Performs one bounded, same-output, same-workspace, floating-only **resize** then **absolute position** operation using the selected current container ID. Reobserves before each command and after the last command, never trusts IPC success by itself, and never automatically retries or undoes. The journal must report BEGIN and DISPATCHING before any possible compositor command; a bad receipt stops execution.

The fixed Sway command forms follow the standard compositor grammar: `[con_id=N] resize set W px H px` and `[con_id=N] move absolute position X px Y px` (see upstream sway(5)). No shell, focus, kill, app launch, output configuration, tiling manipulation or browser/tab API.

A saved window that is not floating, is fullscreen, is outside the saved output, has changed output topology, belongs to the wrong app, or is already in another workspace/output is **refused**. The saved window's UUID is a checkpoint record key, not a live window identity. Two Brave windows with the same app ID require an explicit independently chosen Sway container ID **for each attempt**; the operator could choose the wrong instance, and no cryptographic browser identity is asserted.

## HOW TO USE

There is **no TimeW button, CLI or production service** for this rehearsal. Do not call the execution helper on an operator machine. The only supported usage for this PR is a GitHub Actions disposable test runner, exercising synthetic Sway state and a private temporary SQLite checkpoint:

```bash
python3 -B -I tests/timew/test_machine_v2_floating_pilot.py
```

The test demonstrates two selected Brave-like floating windows on two virtual displays independently returning to their saved rectangles, including a second attempt that reports ALREADY without dispatch. The two window positions and commands are simulated in memory; a stock/native Sway execution is **not yet verified**.

## VERIFY

New tests cover real V1/V2 SQLite save/read from temporary `XDG_DATA_HOME`, two duplicate-app windows on separate outputs, correct per-container targeting, no-op, missing/fake IDs, changed monitor topology, torn two-read capture, fake successful IPC without postflight, second-command failure, missing journal and journal write failure. No source title, PID, browser URL, passphrase or native window ID is included in the public receipt.

The dedicated workflow also runs the existing V2 read-only planner, atomic geometry checkpoint, one-click V1 RESTORE and original single-window journaled-move regression. These are synthetic integration tests, not native desktop visual acceptance.

## WATCH OUT FOR

- **Not a trusted multi-window matching solution.** An operator-selected transient Sway container is only a manual same-session target. Historical Brave-to-Sway identity remains unverified.
- **Not an authorized production executor.** `CI` / `GITHUB_ACTIONS` flags are safeguards against accidental invocation, not authentication. The fixture journal is an injected test interface, not a validated durable user ledger.
- Two-step resize+move is **non-atomic**. If resize succeeds and positioning fails, report UNCERTAIN and retain the manual recovery hold. No automatic retry/undo. Actual persistent journaling and fresh signed operator approval must be designed and reviewed before exposing runtime execution.
- Only **floating windows already on their saved output/workspace** are supported. Tiling-tree reconstruction, changed monitor layouts, cross-monitor migration, missing application launch, Brave tab restoration and normal-browser profiles are explicitly outside this milestone.
- SwayPX-specific native behavior, output scaling, compositor constraints and permissions remain to be tested on a disposable native compositor.

## CHECKLIST

- [x] Recheck current Syntagma and merged #2054
- [x] Add isolated geometry command-path pilot with strict V2 preflight
- [x] Injected manual same-app window pairing, untrusted by design
- [x] Disposable two-display synthetic test and regression workflow
- [ ] Exact-head GitHub workflows and raw logs
- [ ] Independent Nurse 2 security review
- [ ] Disposable stock Sway live placement before any workstation execution
- [ ] Signed operator approval and durable geometry-operation journal
- [ ] Authorized TimeW integration, multi-window identity and Brave sessions
- [ ] Operator merge and production acceptance separately

## NEXT / DECISIONS

Keep as a **draft** until exact-head CI and independent review. The next serious implementation is a stock Sway disposable geometry test with a crash-safe **geometry-specific** journal, then independently authenticated manual multi-window pairing. Do not wire this helper to TimeW or the production compositor from this PR. No local machine writes, C3e/C5 changes, archive migration, protected Brave access or production activation.
