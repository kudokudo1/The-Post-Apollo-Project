# TimeW Scope A // Local-first v3 exact fractional capture lane

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Desktop & Brave Recovery · Scope A  
**STAFF ROLE //** TimeW owner DOC · external Hospital-compatible, no live Hospital registration verified  
**STATUS //** Additive, dormant source and disposable CI only; **PRODUCTION RESTORE HOLD**.

## Operator decision and scope

The operator accepted the local-first → independently administered NAS / separate hardware later sequence in [TimeW #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7099013916). Normal TimeW checkpoints, layouts and journals may remain local now. Local development/test data does **not** create protected C5 spending, independent source custody, trusted native window receipts or restored operator approval. An eventual NAS/custodian requires its own enrollment, migration, separate TimeW purpose/keys and explicit operator activation.

The existing TimeW V1 / V2 checkpoint schema and [V2 crash journal](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2059) already store *integer-only* values. Merged [TimeW #2207](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2207) introduced untrusted exact in-memory IEEE754 values; [#2260](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2260) and [#2272](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2272) strictly deny native authority. The next safe step is a **separate local capture store**, not changing the old schema.

## What this milestone implements

- New dormant module **`services/time/MachineV3LocalExactCaptureStore.py`**. A caller may explicitly choose a local absolute path ending `post-apollo/machine/v3-exact-local-captures.db`. `suggested_path()` returns an XDG path *without creating it*. The module has no CLI, startup hook, native runner, signed packet parser, SwayPX subscription, background worker, QML importer, install script or automatic migration.
- One explicit **`save(..., value=ExactLogicalRect(CURRENT))`** stores an ordinary *caller-supplied/untrusted* logical rectangle linked by UUID to an existing TimeW checkpoint/window **identifier** (not verified durable identity). Only one captured entry per checkpoint/window is allowed; duplicates are refused rather than replaced. A bounded 512-row SQLite database has private file/directory permissions, SQLite transactional writes, a separate `user_version=3`, and a 4-field local-only **fixed-width hexadecimal** encoding of exact binary64 bit-pattern integers. This is a **local storage representation**, NOT an approved cross-process wire or signature.
- `get(capture_id)` and `for_checkpoint(checkpoint_id)` are read-only: opening an absent database creates no file/directory. Returned captures are revalidated through the TimeW exact-value model and explicitly say local-only, no trusted source, selection, operator consent, native receipt, Restore, retry or undo. No command action is available.
- Strict type/version/phase/bit checks refuse booleans, incorrect UUIDs, malformed/nonfinite coordinates, negative-zero aliases, future schema and invalid fields. Opening either a new or existing local database verifies column names, types, nullability, the primary-key constraint on `id`, and the non-partial unique index on `(checkpoint_id, window_key)`; save also checks duplicates inside its transaction. A lookalike v3 table with matching columns but missing constraints is refused. Symlink/hardlink/world-readable DB or private directory are refused. This is normal same-user data hygiene, **not a protection against a fully compromised same-UID process or independent rollback**.
- **Exact storage does not mean tamper detection.** A one-ULP difference is preserved bit-for-bit during legitimate save/read, but changing one valid finite stored number into a different valid finite number is not detectable by this store. It retains no signed original, authenticated source, integrity commitment, protected history or external current-state witness. Malformed or nonfinite substitutions can be refused; valid-bit substitutions remain ordinary **untrusted** local data and cannot authorize Restore.
- Tests run only in temporary directories and a disposable child Python process; they do not touch the operator's desktop, home directory, XDG paths, existing TimeW checkpoint DB or V2 journal.

This v3 capture storage is **not** linked to TimeW's live Save UI. It is a staged data-layer component for later integration after a separate UI and consent decision. It does not assert that caller-supplied CURRENT was produced by a genuine native window or that CURRENT indicates settled state.

## Acceptance and forward compatibility

**Safe now:** Persist ordinary exact snapshot values in a separate developer-invoked local SQLite file; preserve historical integer V1/V2 checkpoints and journal on disk unchanged.

**Not accepted:** Native authoritative receipt serialization, source-enrolled SwayPX C3e/C4b producer, physical window selection, frame settlement, one-use C5 SPENT, native movement, consent, NAS cutover or production Restore.

**NAS later:** Treat the new local snapshots as *legacy user data*. Define opt-in bounded export/import, independent server current-history and antirollback authority, operator-visible provenance and retention rules in an additional reviewed migration plan. **No historic local consent/authorization may be promoted or grandfathered into the trusted external custodian.**

## VERIFY

On an isolated checkout:

```sh
python3 -B -I tests/timew/test_machine_v3_local_exact_capture_store.py
python3 -B -I tests/timew/test_machine_v2_exact_logical_geometry.py
python3 -B -I tests/timew/test_machine_v2_fractional_observation_review.py
python3 -B -I tests/timew/test_machine_geometry_store_v2.py
python3 -B -I tests/timew/test_machine_v2_geometry_journal.py
```

## NEXT / DECISIONS

TimeW owner should seek an independent Nurse 2 exact-head source/CI review prior to merge; user remains authority for merge and for any live UI/host installation. Further Stage A work should design a read-only local capture browser/preview before hooking Save, using native trust and consent only when the other owners have completed that separate path.

**DECISIONS // Local-first data is accepted direction. This particular v3 store is an unmerged source candidate, not a canonical runtime schema or production key/consent decision. TimeW Restore HOLD.**
