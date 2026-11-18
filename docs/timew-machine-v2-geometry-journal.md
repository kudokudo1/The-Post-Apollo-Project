# TimeW MACHINE // Durable V2 geometry-operation journal

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // TimeW MACHINE · Desktop & Brave Recovery
STAFF ROLE // External Hospital-compatible DOC, not verified live Hospital registration
ASSIGNMENT // Separate durable journal for V2 floating resize+position operations, CI-only
UPSTREAM // Draft PR #2058 (disposable V2 floating placement), stacked dependency
PRODUCTION // HOLD

## IMPLEMENTATION

`services/time/MachineV2GeometryJournal.py` is a dedicated SQLite WAL ledger for two-step floating placement, *separate* from legacy `MachineMoveJournal.py`. It uses an explicitly constructed path ending in `post-apollo/machine/v2-geometry-operations.db`, restricts directory/file access to the owning UID, rejects symlinks and hardlinks, and maintains `PRAGMA synchronous=FULL` and a durable before-state transaction. The journal API accepts the existing disposable pilot's `begin`, `dispatching`, and `finish` calls without adding any production CLI.

- `begin` records only canonical checkpoint and selected-window UUID, application ID, transient current Sway container ID, original rectangle and target rectangle. Private titles, PIDs, URLs, browser data, commands, tokens, and arbitrary fields are rejected.
- `dispatching` persists the phase **before** any Sway command. It does not approve, move or restore a window.
- `finish` records `verified_fixture_placement` only when the *caller* reports exact postflight, or `uncertain_requires_review` after a partial/unverified attempt. The journal does not itself authenticate compositor evidence.
- `pending` and `get` reopen read-only after process death without creating directories/databases, running commands or replaying anything. `prepared`, `dispatching`, and `uncertain_requires_review` all block future operations until a separately approved recovery protocol exists.
- A completed checkpoint/window key is not silently reusable. Changing the live container ID does not bypass this duplicate guard.
- Error responses from the journal are fixed refusals; stored summaries have a strict allowlist and size cap.

The disposable `MachineV2FloatingPilot.py` continues to require explicitly injected Sway readers and command runners, a distinct manually selected transient container ID, and CI guard flags. Those flags are **not** cryptographic authorization. The fixture pairing proves no historical Brave identity.

## HOW TO USE

No new TimeW control or workstation operation is exposed. CI source tests only:

```bash
python3 -B -I tests/timew/test_machine_v2_geometry_journal.py
python3 -B -I tests/timew/test_machine_v2_floating_pilot.py
```

The separate private native Sway workflow invokes the existing `tests/timew/test_machine_geometry_headless_sway.py`, which now uses a **real durable temporary SQLite geometry journal**, not an in-memory mock, when moving back a disposable floating test window. All files, subprocesses and compositor sockets stay under the GitHub runner's private throwaway root.

## VERIFY

Test coverage includes:

- Initial missing-journal read without creating anything; restrictive SQLite and directory modes; WAL/FULL synchronization
- Stored before-state and three transitions with restart from a completely separate Python process
- Crash at prepared/dispatching, uncertain partial result, duplicate old key, and global pending-operation block
- Concurrency with six first-write attempts: only one begins
- Invalid UUIDs/rectangles, extra title/PID/URL/token fields, symlink and hardlink refusal, unsafe file/directory permissions, unsupported SQLite schema, tampered private metadata
- Pilot successful selected-window fixture, replay denial, incomplete second command and pending crash hold
- Existing V1 Restore and V2 saved-geometry regressions

CI-native stock Sway proves *behavior with an isolated compositor*, not the operator's real Fedora/SwayPX environment. Exact-head results and NRS-2 review must be recorded separately.

## WATCH OUT FOR

1. **This is durable logging, not trustworthy operator approval.** The underlying manual-window selection and `execution_approved: true` in the disposable test are not protected C3e/C5 grants. Neither the journal nor PR #2058 is authorized for live workstation use.
2. **A journal commit cannot make Sway's two commands atomic.** Between resize and move, a process can die or the window can change. Even an IPC `success=true` is not proof without a fresh real compositor observation. A crash at `dispatching` stays uncertain and is never auto-retried or automatically undone.
3. **SQLite file and its WAL are owner-private, but full user-session protection is not established.** A hostile process already running as the same Unix UID could alter local files. The journal is not a signed authorization source, independent antirollback ledger, tamper-resistant archive or multiuser trust root.
4. **A checkpoint UUID and live Sway con_id do not authenticate a Brave window.** The same app ID can refer to different windows. A future trusted browser-to-compositor identity and operator consent channel remain necessary. No stable pairing proof is claimed here.
5. **This does not reconstruct tiling trees, migrate across monitors, open missing apps or tabs, or retrieve a protected Brave archive.** It only rehearses a pre-existing, manually chosen, same-workspace floating window's geometry.

## CHECKLIST

- [x] Main and PR #2058's latest 6/6 exact-head results verified
- [x] Create stacked additive V2 journal branch
- [x] Private v1 SQLite schema and non-replay state machine
- [x] Crash/reopen/concurrency/privacy regression tests
- [x] Integrate real ledger into fake two-window pilot and isolated Sway native test
- [x] Dedicated GitHub workflow and durable runbook
- [ ] Exact-head CI and raw native Sway step verification
- [ ] Independent Nurse 2 review
- [ ] Operator disposition of upstream #2058 then stacked PR
- [ ] Trusted signed one-use operator authorization and independent per-window identity
- [ ] Recovery UI for uncertain geometry operations and operator-controlled resolution
- [ ] Native Fedora/SwayPX acceptance, protected Brave tab restore and final production consent

## NEXT / DECISIONS

Keep this as a **stacked DRAFT PR** based on #2058's branch, not `main`, until the upstream PR is reviewed and disposed. After exact-head CI, ask NRS-2 to audit concurrent journal writes, SQLite/symlink security, crash-phase holds and lack of real authorization; *do not merge merely because CI is green*. No real workstation writes, live Sway actions, native host installation, C3e/C5 ownership transfer, production enablement or permanent automatic recovery.
