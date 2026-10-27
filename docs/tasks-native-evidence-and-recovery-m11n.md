# 🏥💜 TASKS M11n // Native JSON copy and durable journal observations

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS storage continuity, Proxy 1 → Proxy 2 successor work  
**Source:** [M11m isolated native handshake](./tasks-json-gate-host-transport-m11m.md), [M11l disposable owner](./tasks-json-gate-owner-m11l.md)  
**Evidence date:** October 26, 2026 (operator terminal, America/New_York)  
**Status:** **PARTIAL NATIVE OBSERVATION**, not full native-failure acceptance, production activation or live Hospital registration

## IMPLEMENTATION

M11m merged as [PR #849](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/849). The operator subsequently used the **standalone** `TaskJsonGateHarnessM11m.qml` from a newly cloned GitHub checkout and an explicitly created private **synthetic** `m11l-tasks-copy/todo-copy.json`. No personal task file was used.

This record captures only the evidence **actually posted** by the operator. It does not change the Python host, native QML bridge, production TASKS singleton, `shell.qml`, tests on the operator's system or the synthetic file.

### Native and durable observations

| Evidence | Exact observation | Supported interpretation |
| --- | --- | --- |
| Quickshell standalone start | `Configuration Loaded` | Test QML configuration initialized |
| Synthetic seed | `Synthetic disposable test created` | A new explicitly named test file was seeded; original path withheld |
| Read-only file inspection after closing the standalone shell | `Saved test title: M11M_TEST_2` | The source JSON contained the synthetic revision-2 title |
| Test shell exit | `^C` | The terminal Quickshell invocation was interrupted; this alone does not indicate a configuration error |
| Journal phase | `RECOVERY_REVIEW` | The durable owner remained fenced at inspection |
| Journal epoch | `3` | A legitimate epoch value, not evidence of an error |
| Journal pending stage | `NONE` | No outstanding reservation in the inspected durable row |
| Independent file hash comparison | `HOST HASH MATCHES FILE: True` | Journal `source_hash` matched SHA-256 of the inspected synthetic JSON at that moment |
| Journal reason | `FRESH_OWNER_MUST_REVIEW` | A fresh process attached and persisted recovery review |

The host's source code increments `epoch` when it freezes and again whenever an existing journal is opened by a new owner. The expected `2` from one illustrative test sequence is **not a required value**. `3` can result from an additional open or transition, but the supplied journal output does not prove which events occurred. Do not infer a particular click sequence from the final row alone.

The terminal result is strong **durability and restart-fencing evidence**. It is not proof of every native FileView callback. The QML trace was not included in the supplied terminal excerpts.

## HOW TO USE

There is **nothing to run or alter** to preserve this checkpoint. GitHub's `tests/tasks/fixtures/task_m11n_native_evidence_20261026.json` is a path-redacted, machine-readable version of these observations.

The operator's synthetic test directory should remain unchanged while its history is potentially needed. Do not rebootstrap, delete, reset or re-use an ambiguous authority. The previous run's `test_file` shell variable is session-local and not an assumption for future sessions.

## VERIFY

Static GitHub checks validate the source-of-truth invariants and that this evidence manifest clearly separates observations from unobserved acceptance gates. These checks do not themselves run the native test and do not replace the original operator terminal observations.

**Observed now:** native test configuration loaded; synthetic file reached revision 2; durable journal hash matched source; journal recorded no pending stage and `RECOVERY_REVIEW`.  
**Not independently observed:** exact QML native event chain for each save; FREEZE/STOP/EXISTING button order; fault injections; operator's backup independent comparison; rollback; a production gated JSON stage.

## WATCH OUT FOR

- The SQLite file in the test folder is only an **admission journal**. It is not a production TASKS SQLite store or an approved migration.
- The QML bridge and Python host remain **disposable-copy-only**; `ApolloHubTodoStore.qml` still uses its original JSON FileView with `guardedWriterEnabled: false`.
- A matching journal hash at inspection is evidence for a stable file at that moment. It is not a general guarantee that future writes, disk faults, or power loss cannot corrupt data.
- Do not publish private paths, actual task JSON, screenshots of unrelated windows, or journal database bytes to GitHub.
- The user has unrelated local Quickshell changes; no local pull, reset, process restart, cleanup or activation is authorized by this report.

## CHECKLIST

- [x] Independent GitHub source/status and current TASKS ownership checked
- [x] Operator-observed standalone Quickshell startup recorded
- [x] Synthetic file revision 2 recorded
- [x] Durable recovery phase, epoch, pending stage, source hash match and reason recorded
- [x] Explain why epoch 3 is not automatically a failure or proof of a specific sequence
- [x] Machine-readable sanitized evidence and source-only CI
- [ ] Obtain native UI event/state history for complete two-save chain and freeze/reattach order, if needed
- [ ] Independently verify fresh synthetic backup/rollback and native failure cases
- [ ] Review full Python-vs-JavaScript JSON schema parity
- [ ] Create/approve separate production OS-host + QML wiring only after gates above
- [ ] Authorize local production activation/SQLite migration separately

## NEXT

Treat M11n as **partial native acceptance** of synthetic source persistence and durable recovery fencing. If further operator-native acceptance is required, gather concise **UI statuses** (not private data) from a new, independently isolated test run. Otherwise proceed with **GitHub-only, unactivated** parity/failure review. Do **not** construe this observation or its documentation PR as authority to switch on guarded production writes.

## DECISIONS

The original JSON singleton stays the only live TASKS writer; guarded mode remains compile-disabled; task SQLite and remote project writes remain inactive. This report records observed evidence without promoting it to full native acceptance or final operator `DONE`. Merge of this documentation, local writes, production actuation and migration have distinct approval boundaries.
