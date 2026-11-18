# 🏥💜 Connections C5-H1 // Hospital Room Trash/Restore Scoped Grant Admission

**PATIENT:** `The-Post-Apollo-Project`  
**COORDINATED PATIENT:** `The-Post-Apollo-Dev-Exp` · draft PX [#130](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/130) stacked on [#121](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/121)  
**ROOM:** Temporary Hospital authorization dependency coordinated with protected Connections C5, C3e/C4b, PX and Hospital owners  
**ROLE:** External Hospital-compatible DOC successor, explicitly operator-authorized to advance this bounded dependency; no verified live Hospital assignment  
**PERMISSIONS:** Additive Connections code, tests, workflow and documentation only; no cross-owner source edits, no operator workstation writes, no native installation, no production secrets or merging without operator acceptance  
**STATUS:** Source-level **CI-only** signed-grant admission; **NO native issuer, NO authenticated consent, NO protected PX writer, NO Room mutation authority**.

## IMPLEMENTATION

The Hospital owner has merged application [#2045](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2045), but `HospitalRoomLifecycleService.permissionReady` remains fail-closed. It expects `review.operatorAuthenticated===true` and `review.requiresOwnerReview===false` while the source-owned PX `review()` deliberately returns `false` and `true`. **Do not flip these booleans** or let QML invent a grant.

The PX owner, in unmerged #130, added the actual signed source transition gate. A Room mutation requires a root-pinned Ed25519-signed `post-apollo.hospital.room-lifecycle-grant.v1` envelope under the fixed `px-hospital-room-lifecycle-v12` audience. Its exact signed fields include Room, Patient, repository, graph digest, revision, action, operator, seat, host, retention, one-use nonce/approval ID and ≤60-second lifetime. PX consumes the grant inside the same `BEGIN IMMEDIATE` SQLite transaction as the state change. It rejects unsigned calls. A local caller may nevertheless bypass the command if it can directly modify the **same-user-writable database**; PX owns that missing protected writer boundary.

Current Connections C5a–C5d only tests TASKS-specific scopes and synthetic reviewer executables; none implements a Hospital issuer or independently proven human approval. This change **does not reuse TASKS authorization**.

### New bounded Connections source

`services/connections/hospital/HospitalRoomGrantAdmissionCI.py` defines **two explicit non-interchangeable scopes**:

| Action | Scope |
| --- | --- |
| TRASH | `postapollo.connections.hospital.room-trash.v1` |
| RESTORE | `postapollo.connections.hospital.room-restore.v1` |

It can independently inspect a **previously signed** PX v12 envelope against an exact canonical Hospital request and caller-provided CI pins, requiring the same Room, Patient, repository, graph SHA-256, revision, 256-bit nonce, operator, seat, host and action. It requires PX's **read-only source review** to be eligible for that action and never to claim human permission. It verifies Ed25519 under a separately passed CI public key and rejects TASKS scopes, wrong source state, forged signature, stale revision, wrong host, wrong seat, nonce mismatch, expired/long grants and omitted retention approval.

**It never signs, generates keys, writes grants, calls PX mutations, loads production root keys, offers a native CLI or changes UI.** All actual authority and operation flags are hard `False`. Because the key, review and identity pins still originate from a test caller, **even a successful result is not authorization**.

### PX contract verification

The dedicated CI checks out the exact immutable PX #130 source head `8c0f9c4e5788579efd9d34672ff308f4bca2937f`, **reads its actual `px_hospital_room_authority.py`**, and runs the same disposable synthetic signed envelope through BOTH the unmodified PX verifier and this bounded Connections reader. The workflow checks that PX still requires signed grants, atomically consumes one-use approvals and refuses unsigned transitions. No PX, C3e, C4b, Identity, C5a–d, Hospital QML or host file is modified.

## HOW TO USE

No user-facing controls are enabled. This is an interface contract for the native Connections/C5 owner and a deliberate security hold for PX/Hospital. Tests run on GitHub Actions using disposable Ed25519 test keys. There is no production command to mint or install a Hospital authorization.

Target UX *after separately approved installation*:

**Hospital → Surgery → SHOW WORKERS → Room → Trash++ Review**  
**Trash++ → TRASH → HOSP → Restore**

The review/confirmation controls never grant their own permission.

## VERIFY

- [ ] 40 new signed PX scope/grant refusal tests PASS on exact PR head
- [ ] Same test grant accepted by actual pinned PX #130 `_verify_bytes` in disposable CI, altered data refused
- [ ] Current Hospital UI remains locked
- [ ] Existing Connections credential authority remains disabled
- [ ] Independent Nurse 2 security review of new source, scope/domain, source review limitations
- [ ] Operator acceptance for **this CI contract** only, separate from production deployment

## WATCH OUT FOR // Unfinished native issuer and PX writer

The requested **real installed issuer and trusted operator consent do not exist yet**. This CI bridge must not be wired to a real Room state mutation or used to set `operatorAuthenticated:true`. A genuine issuer needs an operator-approved architecture with:

1. **Protected service identity and key custody:** a separately installed, verified native service with read-only operator-approved release identity and root-controlled signing private key; the PX public verifier key at `/etc/post-apollo/hospital/room-lifecycle-issuer.pub` must be installed from that independently approved key, never from CI, user-supplied QML, or a guest. Decide root key creation, enrollment, rotation, revocation, rollback recovery and service confinement.
2. **Per-operation human decision and Linux origin:** kernel-authenticated peer PID/start ticks/UID and signed program identity; verify an active local logind session and seat; use distinct per-action native policy such as approved Polkit authorization for `TRASH` and `RESTORE` with fresh explicit operator interaction, no reusable/general TASKS grant. Polkit supports `pkcheck --process PID,START_TIME,UID --allow-user-interaction`, but a correct policy + native agent + protected process identity and explicit Room-specific confirmation **must actually be implemented and reviewed**. Merely writing `confirmed:true` in JSON is not consent. This PR does not run `pkcheck` or implement a production service.
3. **Source-owner retention and data:** acquire Room/Patient/repository/revision/digest from the **protected PX writer**, recheck current state/blockers/legal hold and decision to retain data, bind exactly one one-use nonce/approval to the displayed action and current source graph, and sign only after that independent verification. A user JSON payload or a PX unprivileged read-only command cannot establish these facts.
4. **Protected PX storage and native installation:** PX owner must move the writable DB/WAL/backup/restore path behind an authorized service/user boundary and reconcile all old writers. Signed CLI enforcement alone does not defend against a same-UID direct SQLite write. The PX v11 #121 migration must precede v12 #130; require verified WAL-consistent backup + restore tests and both independent reviews before installation.

Security acceptance must reject wrong Room/action/revision/graph, wrong program/host/seat, untrusted/missing signer, invalid/expired/revoked consent, stale release policy, replay, direct SQLite mutations, stale backup and owner-disallowed retention. Burn is a separate future permission, not included here.

## CHECKLIST // Operator's five requested Connections tasks

- [x] Define `ROOM_TRASH` and `ROOM_RESTORE` as distinct source-enforced C5-H1 scope contracts, not TASKS permissions.
- [ ] Build and install a **real** protected native Hospital signing issuer (requires C3e/C5/Identity owner architecture, keys and operator approval).
- [ ] Verify **real human operator and seat decision** before any signature (requires installed native consent mechanism, not a synthetic CI reviewer).
- [x] Implement and test exact signed PX #130 grant conformance, no untrusted QML authority.
- [ ] Complete cross-owner independent security review and final native end-to-end tests.

## NEXT // Ownership handoff and decision

**Protected Connections/C5 owner:** decide and implement native per-action reviewer/issuer identity and real human consent with independently controlled keys; coordinate with C3e/C4b installed release provenance.  
**PX owner:** protect the DB writer/backup and approve v11→v12 migration.  
**Hospital owner:** keep UI deny-only; after PX+Connections native approvals, perform real Trash/Restore and recovery acceptance.  
**Operator:** explicitly approve the native signing-root custody, installation, key rotation and final production activation; source-only CI review is not enough.

## DECISIONS

One scoped PR, no fake production signer, no CI private keys exported, no localhost changes, no cross-owner source edits, no automatic merge, no Room trash, restore or burn. Passing tests does **not** make Hospital Trash/Restore production-ready.
