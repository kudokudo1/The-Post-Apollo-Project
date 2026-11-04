# 🏥💜 TASKS M13n // Native Host Exit After Held-Open stdin

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS encrypted draft recovery / single writer continuity  
**ASSIGNMENT //** Resolve M13l native Quickshell IPC parsed-reply-before-timeout defect, synthetic only  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor, no live registration verified  
**BASE //** GitHub `main` at `f2edef08e2addcdb7d913ed16fb0c1d78eb18374` (Nov 4, 2026)  
**AUTHORITY //** Repository-only, test host/fixtures/CI/docs. No local Fedora writes, real keyring access, production TASKS activation, PR merge or service restart.

## IMPLEMENTATION

Operator's third M13l native isolated test confirmed source hashes, loaded QML, fired 100ms startup, accepted the private environment gate, attempted/accepted the QML Process start, and parsed a JSON reply from the Node host. At +5s it showed `M13L_REPLY_WAITING_HOST_EXIT`. At 45s the QML watchdog fired, Quickshell exited 0, and the test refused acceptance. Private Secret Service owner and test-key/file cleanup did not report an error. Portal accessibility and GVfs messages are not causally established.

**Reproduced mechanism in a separate Node v22 subprocess test:** a child started with writable stdin kept open can receive one newline-delimited request, print a response, call `readline.close()` and still remain alive because the underlying stdin pipe is referenced. Calling `process.stdin.unref()` after closing readline allows Node to exit normally, without forcing termination or dropping the response. Node's official readline documentation states that a readline interface on stdin can retain the process until EOF and recommends unref to exit without waiting for more input.

The M13n patch updates only the **synthetic-only** `tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs`: after writing the one allowed fixed status reply or after its timeout, `finishInput()` closes readline and unreferences stdin (with a destroy fallback if `unref` does not exist). The line reader still handles at most one request and returns only a bounded JSON status. No production key-release, decrypt, persist or TASKS source mutation flags change. No QML Process API, singleton, UI or keyring program changes.

New `tests/tasks/fixtures/TaskEncryptedDraftHeldStdinM13n.cjs` deliberately launches the actual host with `stdin` kept OPEN. It tests one malformed input and one real AES-256-GCM/GNOME Keyring synthetic encrypted roundtrip on a newly created disposable Secret Service bus and verifies that the child **exits**, returns a strict no-authority status envelope and does not output raw credentials/drafts. The existing M13k private-bus shell fixture now runs those two regressions, validates exact synthetic key/file cleanup and prints `M13N_HELD_STDIN_AND_PRIVATE_CLEANUP_PASS` only after success.

The M13l runner pins the new reviewed host blob hash, allowing a fresh isolated Fedora source preflight to verify the fix. M13k source tests now check stdin release and the parent held-open fixture's lifecycle behavior. CI path filters include the new fixture. Existing production TASKS one-FileView/one-writer and disabled flags remain unchanged.

## HOW TO USE

No workstation command is required to review this PR. After CI and operator review/merge, clone `main` into a **new** isolated `/tmp/postapollo-m13n-...` checkout (not a pull/reset of dirty `~/.config/quickshell`), run `bash tests/tasks/tools/task_m13l_native_ipc.sh --preflight .`, then operator-initiate the disposable `--run` test. The latter creates only a private bus/keyring and synthetic ciphertext; it never intentionally touches real TASKS data or real login keyring entries. `--run` is a local actuation decision, not part of repository-only implementation.

## VERIFY

- In CI, the isolated real Secret Service fixture must print `M13N_HELD_STDIN_AND_PRIVATE_CLEANUP_PASS` and the original `M13K_PRIVATE_HOST_IPC_AND_CLEANUP_PASS`.
- The held-open parent keeps the Node child's stdin writable until the child closes, unlike the older pipeline tests that closed input automatically and missed the bug.
- The malformed request must return `REFUSED_REQUEST_SHAPE` with all production authority flags false and exit normally.
- The valid request must recover only a fixed synthetic draft with the disposable private key and exit normally; the exact fake key/ciphertext must be absent after it exits.
- The M13l native Fedora test is still independently required; CI does **not** run the actual Quickshell Process callback.

## WATCH OUT FOR

- This corrects the Node host's process lifetime, not QML's actual `onExited` event. The latter must be reverified on Fedora.
- If child stdout error or cleanup verification fails, CI must refuse rather than print raw host data or accept a leaked test key.
- The `CI_ONLY` literal/private bus flags are test environment restrictions, not authenticated user consent. Production encrypted draft capture and restore remain disabled.
- The `dbus-run-session` portal/a11y/GVfs warnings may recur during native testing; do not infer they caused this hang unless new evidence supports it.
- Earlier native failure is recorded; M13l is **not** accepted merely because a fix was merged.

## CHECKLIST

- [x] Recheck main, Syntagma and active TASKS ownership; M13l-S #1196 merged
- [x] Reproduce held-open Node stdin hang outside the workstation
- [x] Release only synthetic host stdin on one-reply / timeout
- [x] Add genuine held-open parent regression with real private GNOME Keyring
- [x] Re-pin reviewed host in the isolated M13l runner and wire CI
- [ ] GitHub CI green / independent review / operator merge
- [ ] Single operator-initiated isolated native Fedora M13l test
- [ ] Confirm native QML Process callback/exit and cleanup PASS
- [ ] Only then scope production opt-in transaction design under separate authority

## NEXT

After CI green and review, rerun M13l native once from a fresh isolated checkout; expected acceptance marker `M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS`. If only reply/exit still blocks, investigate QML Process lifecycle with actual Fedora evidence, not further keyring setup or portal speculation.

## DECISIONS

**Verified:** real native Quickshell parsed a host reply but could not finish before the watchdog; held-open pipe hang reproduced on Node 22 and stdin unref allowed exit.  
**Implemented:** test-host subprocess lifetime and synthetic regressions only.  
**Not performed:** local workstation modifications, live keyring mutation, QML production activation, a second TASKS source writer, PR merge, or live Hospital registration.
