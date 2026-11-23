# 🏥💜 DOC 5 // TimeW C5 storage-independent custody probe (test only)

**PATIENT //** The-Post-Apollo-Project. **ROOM //** Connections C5 ↔ TimeW Scope A. **ROLE //** DOC 5, external Hospital-compatible; no live registration verified. **STATE //** TEST REFERENCE / PRODUCTION RESTORE HOLD.

## IMPLEMENTATION // One read, zero permissions

`tests/connections/timew/TimeWC5CustodianBoundaryReference.py` is an isolated Python **probe** of C5 TimeW operation-recovery evidence supplied by an injected test callback. It imports the strict claim grammar from the existing merged `TimeWC5SpendFenceReference.py` fixture; it never imports DOC 1's C3e Identity development ledger, starts a server, touches SQLite, enrolls keys, signs a grant, verifies human consent, executes window commands, or calls a native source.

The fixture's query binds an operation ID and grant ID with TimeW-only audience/action. Its response must match the original request's source/selection/intent digest, session, seat and issuer epoch. A synthetic local journal can be `PREPARED`, `DISPATCHING`, `UNCERTAIN` or `FIXTURE_COMPLETE`. The provider may report an untrusted local development ledger or candidate external custodian state. **Both are untrusted.** A caller-supplied prior history head can detect some *visible* decreases/forks, but it is not independently authenticated or antirollback, and cannot itself establish what the latest head is.

The public result **always** sets:
- `production_authorized=false`
- `native_action_allowed=false`
- `human_consent_verified=false`
- `external_custody_verified=false`
- `revocation_acknowledged=false`
- `retry_allowed=false`, `undo_allowed=false`, `safe_actions=[]`

It reads a provider **at most once**, never falls back to another provider on outage, and never infers unspent permission from missing records. `SPENT` with local `PREPARED` stays `UNKNOWN/HOLD`; `FIXTURE_COMPLETE` with any synthetic terminal receipt still cannot prove native SwayPX final placement. A forged production flag is refused as a schema mismatch.

## WHY THIS IS NOT A NEW PRODUCTION WIRE

The probe schema `postapollo.connections.c5.timew.custodian-probe-fixture.v1` and the plain callback are solely for **negative CI tests**; they do not select an installed endpoint, transport, external custodian, signing key, TLS root, credential policy, or permanent production field list.

- DOC 1's [#2217 development→independent NAS/other-computer migration](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217) is the operator-accepted development **sequence**, not authority for TimeW to reuse C3e Identity challenge/keys. DOC 1's [#2224 local ledger](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2224) demonstrates atomic transactions **and** rollback; it remains C3e-owned.
- DOC 5's [#2196](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2196) and [#2204](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2204) are merged, retrospectively scoped-PASS TimeW consent reference/rollback evidence. This probe composes only their validated *test input structure*, not their backing database into a new trust root.
- TimeW's [#2207](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2207) separately models exact fractional binary64 logical geometry; SwayPX's [#174](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/174) has source-defined timeout-forced CURRENT semantics. **Neither establishes C5 grant authority or settled native placement.** The probe accepts hashes only and never defines native geometry bytes/phase.

## HOW TO USE

From disposable repository checkout (ordinary user only):
```sh
python3 -B -I tests/connections/timew/test_timew_c5_custodian_boundary_reference.py
```

No keys, production secrets, root privileges, network services or user workstation action needed. Dedicated GitHub Actions can run this CI-only test and inherited C5 reference regressions.

## VERIFY // Negative matrix

12 cases cover local vs external-candidate provenance, SPENT/local PREPARED crash gap, active-with-dispatch contradiction, untrusted fixture terminal receipt, revoked/unknown states, exact operation/seat/source/audience mismatch, injected forged authority flag, prior apparent rollback/fork/inconsistent advancement, provider outage with **no fallback or retries**, malformed or expired clock, wrong stage, head and sequence invalid shapes.

The test suite does **not** establish genuine external current-head freshness, independent administration, key custody, signer/provenance, active unlocked operator seat, human approval, source-signed canonical binary64 geometry, guarded SwayPX commands, or trustworthy native receipts. Even a syntactically valid independently named provider can be a fake.

## WATCH OUT FOR / NEXT

Protected C5 native readiness still needs an **operator-approved independent custodian** with separately verified current head, key/role enrollment, challenge/grant atomic SPENT, anti-fork/rollback and crash recovery. Any eventual shared physical service must keep TimeW-specific audience, keys/role and grant history separate from Identity, Hospital and Forest. Native TimeW must bind exact compositor-selected object, active seat, user-visible before/target coordinates, source phase/settlement and one-use spend-before-effect. An external service outage is UNKNOWN/HOLD, not permission to use an old local ledger.

Request Nurse 2 independent **pre-merge exact-head** review and operator merge disposition. No source outside three DOC 5-owned new files and dedicated workflow is edited; no production activation, local host changes, signing keys, services, UI controls or Sway actions. **PRODUCTION HOLD.**
