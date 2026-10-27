# 🏥💜 TASKS M11o // JSON policy parity and disposable-owner failure gates

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS storage continuity after M11n; GitHub-only development  
**Source of truth:** `services/hub/ApolloHubTodoPolicy.js` (real UI policy) and `services/projects/TaskJsonGateCandidateM11l.py` (test-only owner)  
**Status:** **isolated Python host hardening and source-parity verification**, not a production writer, activation, or live Hospital assignment  
**Predecessor:** [M11n observed source/journal evidence](./tasks-native-evidence-and-recovery-m11n.md)

## IMPLEMENTATION

Before admitting real JSON, the separate Python owner must not disagree unsafely with the TASKS JavaScript policy. This milestone adds the read-only `tests/tasks/fixtures/task_json_policy_oracle_m11o.cjs`, which directly loads the **actual** `ApolloHubTodoPolicy.js` via Node's VM, plus the cross-language `tests/tasks/test_task_json_policy_parity_m11o.py` fixture and temporary-file fault matrix.

M11o corrects **only** `TaskJsonGateCandidateM11l.py`, the already test-restricted OS owner:

- Refuse Python JSON decoder's nonstandard `NaN`, `Infinity` and `-Infinity` tokens. They are not valid JSON and the production `JSON.parse` rejects them, including in ignored extra fields.
- Count title, description and project-name size in UTF-16 units like JS `String.length`, rather than Python Unicode code points. Supplementary-plane characters use two units.
- Use ECMAScript `String.trim` whitespace behavior (including `U+FEFF`) for title/project-name boundary checks.
- Accept integer-valued JSON number forms such as `3.0` and `1000.0` where JavaScript uses one numeric Number type, while rejecting booleans, non-finite and fractional counters/timestamps.
- Refuse non-string `projectId` values without allowing unhashable arrays/objects to throw unexpected Python exceptions.

No changes to `ApolloHubTodoPolicy.js`, `ApolloHubTodoStore.qml`, `shell.qml`, task mutations or any production file paths.

### Explicit strict-only differences

The Python owner remains deliberately **stricter** than the reader for duplicate JSON keys: JavaScript `JSON.parse` takes the last key, whereas the durable host refuses an ambiguous source. This is the **single** intentional discrepancy in the M11o sample corpus and is asserted by name.

**No divergence for trailing line breaks:** direct execution of the production JS policy confirmed that its non-multiline end anchors reject newline-terminated task IDs, project IDs and due dates, just like the Python host. The M11o tests require matching rejection rather than claiming a host-only rule.

Any **Python-only acceptance** is a failure, not an acceptable discrepancy. A new or undocumented JS-accepted/Python-rejected case also fails parity until classified.

**Limits to the comparison:** The corpus covers canonical v1/v2/v3, nested references, invalid/extra fields, Unicode text, dates, counters, duplicate IDs/names, malformed JSON and the strict-only cases. This is a tested corpus, not a mathematical proof for every possible input. The OS host enforces an additional private file ownership/identity and 1 MiB **byte** ceiling, whereas the JS policy measures string code units; longer multibyte sources can also be intentionally refused under the host's data-safety policy and are not granted production eligibility.

## HOW TO USE

No UI changes and no local setup. GitHub CI runs:

```sh
python3 tests/tasks/test_task_json_policy_parity_m11o.py
python3 tests/tasks/test_task_json_gate_transport_m11m.py
python3 tests/tasks/test_task_json_gate_candidate_m11l.py
node tests/hub/test_apollo_hub_todo_policy.cjs
node tests/tasks/test_task_projects_policy.cjs
```

Tests create only new private temporary directories and synthetic task data. They do not inspect, upload, edit or restart the operator's real TASKS data or desktop.

## VERIFY

The cross-language oracle reports acceptance/rejection for each sample by invoking the **production JS parse()** function. Python checks the exact same raw string against the disposable OS-host validator. It rejects any unsafe host-only acceptance and demands explicit names for the deliberate host-only denials.

Additional disposable OS tests cover symlinks, hard links, permissive file modes, nonstandard JSON on initial bootstrap, oversized source, unknown journal schema, changed source across process reopening, pending stage mismatch and durable recovery review. Every test requires the fixture file to remain unchanged when a write is rejected.

CI success proves the listed static and temporary-file behaviors, **not** native Wayland callback timing, durable power-loss acceptance, all OS race windows or production authority.

## WATCH OUT FOR

- The `M11l` owner remains limited to a private folder literally named `m11l-tasks-copy` and a file `todo-copy.json`. It is not a production host.
- The M11m Process bridge is still unmounted from the real TASKS singleton. It cannot activate `guardedWriterEnabled: false`.
- A stage ID is durable only while pending in the current owner journal; a proven cross-stage lifetime replay blacklist has **not** been implemented. Do not claim full replay protection.
- The host's parse behavior may be conservatively stricter than the JS reader. An ambiguous or noncanonical real file must be reviewed, **never silently replaced with an empty document**.
- No synthetic fixture directory from earlier native tests should be rebootstrap/reset/overwritten to prove this milestone.
- The original user-local Quickshell tree may be dirty. This milestone uses GitHub only and does not install or run code on it.

## CHECKLIST

- [x] Verify merged M11n and absence of conflicting TASKS PR ownership
- [x] Implement direct JavaScript oracle against the real TASKS policy
- [x] Repair concrete false acceptance and string/number parity gaps in disposable host
- [x] Explicitly inventory known stricter policy differences
- [x] Exercise isolated OS-file and journal failure cases
- [ ] Verify GitHub M11o parity/fault workflows and independent review
- [ ] Complete broader native FileView crash/freeze/restart fault acceptance
- [ ] Implement lifetime stage replay fencing if guarded production mode is later approved
- [ ] Separately authorize production host and snapshot callback integration
- [ ] Separately authorize guarded-mode activation, rollback and later SQLite migration

## NEXT

Use the M11o results to decide whether remaining durability tests are sufficient for a **new, separately reviewed and disabled-by-default production integration**. Do not turn a passing unit/CI matrix into operator acceptance of actual personal TASKS writes.

## DECISIONS

No production writer modified; JSON remains the sole live TASKS writer. M11o is not SQLite migration, live host installation, desktop restart or Hospital ownership transfer. Final activation and operator acceptance remain separate.
