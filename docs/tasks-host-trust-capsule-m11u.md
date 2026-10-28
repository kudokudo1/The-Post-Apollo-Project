# 🏥💜 TASKS M11u // Sealed synthetic host script trust capsule

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS guarded JSON continuity; isolated trust-preflight successor to M11t  
**Provider:** OPEN AI // CHATGPT, external Hospital-compatible; not a live Hospital-registered session  
**Source baseline:** `main` at `1d1036df2d25223b77dd668106642fd228b2a8c8` on 2026-10-28; recheck at review time  
**State:** **SYNTHETIC HOST IDENTITY PROBE ONLY**, not a real production host, production integration, native Quickshell acceptance or activation.

## IMPLEMENTATION

M11t established nine open production gates. M11u makes **one narrow part of `TRUST_EXEC` testable on Linux**, using only new test-only files:

- `tests/tasks/fixtures/TaskHostTrustCapsuleM11u.py`: an importable, **no CLI** Linux preflight that accepts exactly an explicitly named private folder `m11u-host-copy` and file `synthetic-host.py`. It rejects relative and traversal paths, symlinked folder/leaf, hardlinks, loose owner permissions, missing/large/changing files and hash mismatches.
- The expected SHA-256 digest must be supplied **independently** by the caller. The probe never trusts a digest inside the inspected source folder. A synthetic-only header is mandatory in addition to the pinned digest.
- The probe reads the source through an `O_NOFOLLOW` directory FD and then a directory-relative `O_NOFOLLOW` regular-file FD. It matches initial/final file identity and metadata before returning a private in-memory snapshot.
- For a test-only launch, the snapshot bytes are copied into a Linux `memfd`, sealed against writes, growth and truncation, and passed as `/proc/self/fd/<fd>` to a fixed `/usr/bin/python3` interpreter, required to resolve within `/usr/bin`, be owned by root and not be group/other writable, with `-I -S -B`. This avoids **reopening the original script path at launch**, closing the tested pathname-replacement window. The subprocess has no stdin, bounded output, a bounded timeout, and a reduced environment; only exact `M11U_SYNTHETIC_OK` output is accepted.
- The tests use disposable `tempfile.TemporaryDirectory` files. The task JSON singleton, M11l SQLite journal, M11m subprocess bridge and shell imports are never involved. The module has no `__main__` invocation and no task-directory option.

### Exact security claim

**Verified when CI passes:** a synthetic file with a trusted externally supplied digest and strict private metadata can be captured, and the captured script bytes can be launched from a sealed snapshot after an adversarial pathname swap, rather than re-reading a changed script from the path.

**Not claimed:** authenticating the **interpreter** or OS process; an end-to-end authenticated production launcher; protection against a same-user process that can subvert this trusted caller or its Python interpreter; protection against mutable ancestor directories outside the private leaf; host reply authenticity; QML native callback provenance; production TASKS source ownership; source backup; rollback; power-loss durability. A Python-level API and trusted hash parameter are not themselves trust anchors.

### Explicit negative / replacement checks

| Synthetic test | Expected boundary |
| --- | --- |
| Valid private source and independent digest | Return sealed synthetic result |
| Script replaced after capture | Original captured bytes run; replacement cannot silently change launched content |
| Hash mismatch or untrusted marker | Refuse |
| Symlink directory/leaf, hardlink | Refuse |
| World-readable script or loose private directory | Refuse |
| Missing, wrong directory name or oversized script | Refuse |
| Fake `python3` earlier in `PATH`, poisoned `PYTHONPATH` and `PYTHONHOME` | Use fixed, root-owned `/usr/bin/python3` with isolated args and sanitized environment |
| Valid digest but unexpected subprocess output | Refuse; matching digest is content pinning, **not** host authority |
| Snapshot mutated after capture | Refuse |
| Existing TASKS writer or shell mount | Remain unchanged and unconnected |

## HOW TO USE

No operator local action required. This is GitHub CI or disposable checked-out source only:

```sh
python3 tests/tasks/test_task_host_trust_capsule_m11u.py
```

The test needs Linux `memfd_create` and sealing. If unavailable, or if the fixed system interpreter cannot pass owner/permission checks, the capsule refuses rather than launching with an untrusted fallback. It does **not** start a background service, create a real TASKS journal, read real tasks or open a Quickshell window.

The user-facing TASKS, TODAY, PLANNER and Hub continue using the existing JSON singleton. The `guardedWriterEnabled: false` source guard is unchanged.

## VERIFY

- Inspect the source diff: only this M11u synthetic capsule, its unit test, this handoff and its narrowly scoped CI workflow should change.
- CI runs isolated synthetic real-subprocess tests (not native QML), plus source-only M11t, M11q and M11d safety contracts.
- The original operator-observed M11s four-fault acceptance remains historical evidence. M11u does not repeat those native tests or claim a production win.
- M11t's other eight gates remain **OPEN**, and `TRUST_EXEC` remains **OPEN** because interpreter/process provenance is not verified by this first slice.

## WATCH OUT FOR

- **No production host exists in this patch.** The name “host trust capsule” must not be read as a deployment mechanism or a new authorized TASKS writer.
- File content attestation requires an **independently trusted** digest. Taking the digest from the same untrusted directory defeats the premise. The test fixture constructs its own known digest only for testing.
- The sealed memfd removes one source-path TOCTOU window. The test uses a fixed, root-owned `/usr/bin/python3` executable and refuses user-writable interpreters (including hosted CI toolcache installations). Owner/mode checks still do not prove the interpreter's content, entire path ancestry, process identity, or supply chain.
- Same-user processes that already control the calling Python process, runtime, or deployment directory can defeat user-space checks. No mechanism here establishes hard isolation against them.
- A normal advisory `flock` and M11r session nonce likewise do not authenticate independent executable provenance.
- There is no new `TaskJsonGateCandidateM11l` import, production `ApolloHubTodoStore.qml` patch, `shell.qml` mount, SQLite task-data migration, actual task-file read or write, GitHub Projects operation, operator-local file change, Quickshell restart, or live Hospital registration.
- No merge permission or production activation follows from a green test.

## CHECKLIST

- [x] Confirm M11t present on `main`, production guard remains disabled and no active TASKS PR collision
- [x] Isolate source preflight under synthetic-only test path
- [x] Reject untrusted script metadata, external path and hash mismatch
- [x] Exercise Linux sealed-memfd pathname-replacement protection
- [x] Test stdout denial, environment poisoning and no live writer integration
- [ ] CI and independent review
- [ ] Separately scope interpreter/process-origin authentication
- [ ] Later production-source backup, stage/callback/UI, recovery and rollback acceptance
- [ ] Explicit authorization before production integration, merge/deployment/activation

## NEXT

Once reviewed, the next **separate** prototype should prove a trustworthy interpreter/deployment identity and bind the actually launched child process to the M11r session protocol and a durable owner epoch, still against synthetic data. Do not widen M11l's disposable source filter. Recheck current main and worker ownership before authorizing that cross-component work.

## DECISIONS

**Operative:** M11u is a bounded, GitHub-only synthetic executable-content pinning experiment. All production acceptance gates stay open, including `TRUST_EXEC`.

**Not authorized:** Actual production host, TASKS singleton patch, merge, real data inspection, local changes, startup, SQLite migration, backup restoration, production guarded writer or remote task write.
