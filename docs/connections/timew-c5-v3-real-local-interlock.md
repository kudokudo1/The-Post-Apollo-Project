# 🏥💜 DOC 5 // TimeW v3 local capture ↔ C5 local SPENT integration rehearsal

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · TimeW C5 Scope A  
**STAFF ROLE //** DOC 5, external Hospital-compatible · live Hospital registration unverified  
**ASSIGNMENT //** Real SQLite-backed local-first cross-store consistency/denial evidence, without borrowing TimeW runtime ownership  
**SOURCE //** C5 test, dedicated CI and this explanatory note only  
**STATE //** Disposable GitHub-runner integration test, never an installed service or native permission  
**PRODUCTION TIMEW RESTORE // HOLD**

## IMPLEMENTATION // Actual local files, not a new imagined receipt

This milestone **uses the existing merged implementations unchanged**:

- TimeW [merged #2284](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2284): `services/time/MachineV3LocalExactCaptureStore.py`. It saves one ordinary `PHASE_CURRENT` exact binary64 geometry record per checkpoint/window in an opt-in private v3 local SQLite file. Its local integrity checks prevent malformed files, missing uniqueness and duplicate capture, but ordinary same-UID SQLite values are **not protected native observations**.
- DOC 5 [merged #2196](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2196): `tests/connections/timew/TimeWC5SpendFenceReference.py`. It separately registers, locally spends, revokes and reopens an untrusted TimeW-only grant in a **different** disposable SQLite file. Its local `SPENT` is always nonauthorizing.
- TimeW [merged #2260](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2260): the original fractional observation reviewer, which remains HOLD even for matching in-memory before/target/post-resize/final values.

The new `tests/connections/timew/test_timew_c5_v3_real_local_interlock.py` exercises those three already-existing modules together using `tempfile.TemporaryDirectory`. It does not modify any existing TimeW/C5 module, SQLite schema, QML UI, SwayPX source, C3e/C4b gateway, TimeW V1/V2 journal or desktop host.

**What is genuinely tested (in real local SQLite, not just a mocked provider):**

1. Save an exact `CURRENT` rectangle with fractional y=92.5 to the TimeW v3 file; independently show that no C5 grant exists and neither store grants permissions.
2. Register and locally commit C5 `SPENT` on the original grant while the same TimeW capture stays readable; both source APIs still return `safe_actions=[]` and no native/production/custody flags.
3. Roll the entire **C5 local database** backward from SPENT to ACTIVE; local C5 can be re-spent, proving its real same-user rollback exposure. The TimeW v3 record does not fix it, and both outputs remain non-authorizing.
4. After a simulated lost C5 spend reply, reopen both actual stores; the C5 state stays SPENT/UNKNOWN, and a second spend is rejected. Restarted-process reads preserve only values and local state, not real permission.
5. Delete the local C5 database while keeping the TimeW capture. Missing C5 evidence refuses and cannot be replaced by a valid local layout or silently recreated by a read.
6. Mutate `y_bits` to a different **valid finite one-ULP value** in ordinary TimeW SQLite. The store preserves valid bits but has no anti-tamper authenticity; even with local C5 SPENT, it cannot verify a source, selection or receipt.
7. Bind fake unchanged window/checkpoint names, change the C5 seat/selection/intent, expire/revoke C5, request duplicate local captures or keep one store absent; no combination creates an action.
8. Compare a stored before CURRENT with untrusted matching target, post-resize CURRENT and final CURRENT, all READY-labelled: `MATCHED_VALUES_UNTRUSTED_HOLD`. A reported `TIMEOUT_FORCED` with CURRENT copied is `UNKNOWN_HOLD`; one-ULP target mismatch is `GEOMETRY_MISMATCH_HOLD`. **No follow-on MOVE or automatic retry.**
9. Confirm legacy `machine.db` and `v2-geometry-operations.db` were not created in the disposable working directory; no native window command or production resource is invoked.

This is stronger than merely comparing in-memory fixture dictionaries: it demonstrates actual local disk persistence, process boundary reload, full-file rollback, genuine SQLite constraints, valid-value mutation and cross-store independence.

## HOW TO USE

The GitHub Actions job executes from a disposable repository checkout:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_v3_real_local_interlock.py
```

The same workflow reruns the inherited TimeW v3 local store suite, C5 local spend fence and local-history cutover quarantine. No `XDG_DATA_HOME` or operator desktop storage is touched: all tested paths live beneath an auto-deleted temporary directory. No external network, root, key, native source or grant enrollment.

## WATCH OUT FOR // What this cannot claim

- Neither persisted SQLite row is a production-authorized consent record. Both are ordinary rollbackable local development data, even with private UNIX permissions and duplicate constraints.
- The TimeW v3 DB and C5 fixture **are not joined into a command service**. No source-authenticated SwayPX window, actual locked/unlocked active seat, physical operator review/gesture, approved signed binary64 wire, protected independently current SPENT keeper, settled R1/R2 or immutable terminal T0 is present.
- A local C5 SPENT and an exact matching geometry report cannot promote each other to authority. An ACK-less SwayPX resize timeout can still copy CURRENT/arrange scene. SwayPX [draft #182](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/182) corrected-head diagnostics now classify contradictory READY+TIMEOUT as ambiguous HOLD, not clean settlement.
- Even a valid current local TimeW capture never proves the compositor actually selected/captured the corresponding window. Saving this value before or after a local C5 fixture spend does not establish the required spend-before-native-effect ordering.
- No approved independent C5 hardware/custodian, operator-root, TimeW-specific signing role, enrollment API, canonical receipt parser, trusted renderer, native command endpoint, retry permission or recovery action exists.
- The operator's [local-first ordinary TimeW data now, separate hardware later](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7099013916) decision is settled; it does not grant live production consent. Future cutover must obey [C5 local-history quarantine #2288](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2288) and the still-[REVISE/HOLD C5 receipt RFC #2271](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2271).

## VERIFY / CHECKLIST

- [ ] Exact-head CI: new cross-store cases + inherited TimeW v3/C5 suites
- [ ] Nurse 2 independent exact-head **pre-merge** source/CI review
- [ ] Operator-controlled merge disposition
- [ ] Separately approved actual source/selection and protected one-use consent interface
- [ ] Native signed terminal receipts and recovery acceptance, including real crash/timeout/rollover

## NEXT / DECISIONS

**DOC 5 owns only this new C5-side cross-store test and its CI/docs.** TimeW owns actual v3 store and any future Save/preview UI; DOC 1/2 own independently enrolled producer/current trust; SwayPX owns true compositor source and instruction outcomes; DOC 5 owns separate protected TimeW C5 issuance/revocation/SPENT and recovery. This test intentionally consumes existing read-only/development APIs without expanding their authority.

This is a meaningful local-first integration checkpoint but is **not** the protected native integration itself. It adds no product feature, service, workstation modification, key or production permission. **TimeW Restore remains HOLD.**
