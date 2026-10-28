# 🏥💜 TASKS M11v // Synthetic interpreter and child-process correlation probe

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity; M11v synthetic trust-chain slice  
**PROVIDER //** OPEN AI // CHATGPT, external Hospital-compatible (not live registered)  
**BASE //** GitHub `main` `ea1db3a9c16f13ad9b206e57d9c207331bfb7497` on 2026-10-28; recheck before subsequent changes  
**STATE //** Synthetic-only, unmounted, not production-ready.

## IMPLEMENTATION

M11u established **script-content pinning** and sealed-memfd path-replacement protection. M11v tests two narrower relationships **without altering M11u or M11m**:

1. `pinned_interpreter(expected_sha256)` accepts an **independently provided** SHA-256 for the exact `/usr/bin/python3` resolved executable. It requires root-owned, non-group/other-writable `/`, `/usr`, `/usr/bin` ancestry, an ordinary root-owned executable in `/usr/bin`, a bounded read from an `O_NOFOLLOW` FD, matching before/after metadata and digest. A digest obtained from the same untrusted executable is **not** independent trust; tests intentionally calculate a local hash only to exercise the mechanism.
2. `run_bound_synthetic(snapshot, interpreterPin)` uses M11u's private `SyntheticSnapshot` and verifies the interpreter pin **again** before launch. It seals the script bytes in a Linux memfd, launches the fixed interpreter without a shell, opens `pidfd_open`, reads kernel-observed `/proc/PID/exe` device/inode and process start ticks while the child is alive, then supplies exactly one random challenge/epoch/request over a bounded synthetic protocol. The child must emit one strict `hello` session ID and exactly one matching reply. Invalid process identity, epoch, challenge, duplicate/extra output, stderr, exit, or timeout refuses the test.
3. Each test source is strictly `# M11U SYNTHETIC HOST ONLY` under a private disposable folder. The `TaskInterpreterProcessProbeM11v.py` module provides **no CLI and no production task path**, no journal writes and no Quickshell mount. The protocol epoch `7` is a fictional constant, not an M11p durable owner epoch. The test session is single-use and not attached to M11m's actual transport.

### Claim boundary

**What passing GitHub CI demonstrates:** a system-interpreter binary can be checked against a caller-provided pin; the launched synthetic child can be correlated to that binary's kernel-observed executable inode and a PIDFD; one challenge/session echo from the captured synthetic code is checked. An intentionally incorrect pin, process identity or reply is rejected.

**What it does not demonstrate:** independently trusted provision of that interpreter pin; an attested/immutable operating system; safe process identity in a compromised parent or same-user hostile runtime; a durable owner epoch/journal; authenticated M11m host responses; FileView callback attribution; real task-source backup; safe rollback; physical power-loss behavior; production activation. A random nonce echoed by code is **correlation, not authentication** if the parent or child can be impersonated. A PIDFD prevents PID reuse confusion but does not attest the contents of the running Python interpreter or its loaded libraries. The `TRUST_EXEC` and `PROCESS_BINDING` M11t production gates remain **OPEN**.

### Tests and refusal paths

| Synthetic case | Expected outcome |
| --- | --- |
| Pinned interpreter + sealed script + matching PID/executable + one session | `SYNTHETIC_PROCESS_BOUND` |
| Wrong or malformed independently supplied hash | Fail before launch |
| Non-system interpreter path | Refuse |
| Injected `/proc/PID/exe` inode mismatch | Refuse before sending request |
| Wrong fictional owner epoch | Refuse before spawn |
| Wrong challenge/session, bad status, extra output | Refuse |
| Child exits, malformed output, timeout | Refuse and close process/FDs |
| Poisoned PATH, PYTHONPATH, PYTHONHOME | Still invoke fixed isolated interpreter |
| Production TASKS singleton/shell source audit | No import, mount, second writer, task JSON input or active guarded writer |

## HOW TO USE

No action on the operator's Fedora workstation. The GitHub-only Linux test invocation is:

```sh
python3 tests/tasks/test_task_interpreter_process_probe_m11v.py
```

The test requires Linux `pidfd_open`, `/proc`, sealed `memfd`, and a root-controlled `/usr/bin/python3`; it refuses rather than using an insecure fallback. The actual TASKS, TODAY, PLANNER and Hub controls remain unchanged.

## VERIFY

- Current GitHub production `ApolloHubTodoStore.qml` was independently inspected before branching: exactly one FileView and `guardedWriterEnabled: false`.
- M11u and M11t are on GitHub `main` at the documented base; no open TASKS or M11v PR was found before starting.
- New test-only module, synthetic tests, this documentation, and scoped workflow are the only expected changes.
- GitHub CI is source/process **simulation** under disposable files; it does not run a native Quickshell callback or access user task data.

## WATCH OUT FOR

The test fixture obtains an interpreter digest from the same CI runner binary, therefore **does not satisfy a separately trusted production pin distribution requirement**. A root-owned path and a stable `/proc` inode do not by themselves authenticate the OS, interpreter, Python modules, process, or publisher. The actual durable journal owner remains M11l/M11p's disconnected **disposable** candidate. Do not loosen test-only path restrictions or wire this probe into production `stage(result)`. No live data, local checkout, process, Quickshell reload, SQLite task database, backup restoration, migration or activation.

## CHECKLIST

- [x] Inspect current main, M11u source, owner rules and writer authority
- [x] Create separate synthetic process-correlation probe, retaining M11u unchanged
- [x] Add wrong-pin, unexpected-executable, stale-epoch, forged-response and process-death regressions
- [x] Add non-activating documentation and isolated CI
- [ ] Verify CI and independent source review
- [ ] Separate M11w proposal for *durable disposable* owner session/process integration
- [ ] Operator review/merge and separate later production acceptance permissions

## NEXT

After CI, review the results and exact diff. A later **separately approved** milestone can connect this synthetic process correlation to the M11p durable disposable journal/session protocol **without broadening its private file restrictions**. Real source integration would require a new scoped proposal, and all M11t production gates remain open.

## DECISIONS

**Operative:** M11v is synthetic-only, on a review branch, with no activation ability.

**PROPOSED:** Independent interpreter pin distribution and actual durable OS host binding. No PR merge, production writer integration, user local change, task file read/write, Hospital registration, remote task mutation or SQLite migration is authorized by this milestone.
