# 🏥💜 Connections ↔ Hospital // Staffing-native issuer cross-owner interface

**PATIENT (issuer):** `The-Post-Apollo-Project`  
**PATIENT (writer):** `The-Post-Apollo-Dev-Exp`  
**ROOM:** Universal Connections / Hospital Session + Doctor staffing  
**ROLE / AUTHORITY:** Connections-side **documentation-only coordination**. This is not a new live Hospital registration, not ownership transfer from C5-H2, and not permission to edit Hospital #133.  
**BASE:** Connections `main` at `f8c4f9d0c6d394b9746fba20f5ffa13d8442919b`  
**SOURCE REFERENCES:** Merged C5-H2 [#2056](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2056) (head `29f816fb008d93f3153e2f347df579e6bd69283b`); Hospital [draft #133](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/133) (head `ee1dc74056fbd2c849d3391e3148b003514b2932`).  
**STATUS:** PROPOSED / CROSS-OWNER AGREEMENT PENDING. **PRODUCTION:** HOLD.

## IMPLEMENTATION // Exact proposed interface

The Hospital draft implements a source-only signed staffing-grant verifier and disposable PREPARE/COMMIT coordinator. Merged C5-H2 implements real native credential/seat/Polkit checks for **Room TRASH and RESTORE only**. The signed grant formats, root signing key, Polkit actions, request shape and database-owner protocols are **different**. A staffing grant is **not** a Room lifecycle grant with its action name changed.

### Exclusive staffing action and permission set

| Operation | Exact Polkit action | What it may change through protected Hospital writer |
| --- | --- | --- |
| `SESSION_ATTACH` | `org.postapollo.hospital.session-attach` | Attach the reviewed Session to the exact Room, Patient, Assignment and Doctor/Provider |
| `DOCTOR_SUCCEED` | `org.postapollo.hospital.doctor-succeed` | Succeed the reviewed Doctor/Session, preserving the previous record and handoff |

For **both** candidate actions: `allow_any=no`, `allow_inactive=no`, `allow_active=auth_self`. **No** `auth_self_keep`, `auth_admin_keep`, wildcard action, or reuse of `org.postapollo.hospital.room-trash` / `org.postapollo.hospital.room-restore`. Neither action conveys Bed registration, Room Trash/Restore, Burn/Burn All, arbitrary SQLite, generic process control or session launch. The candidate Polkit XML in Hospital #133 is **not installed**. Native acceptance must audit **effective rules** and the actual authentication agent; `pkcheck` success alone cannot prove the person saw the exact operation details.

### Exact signed grant

Use the existing Hospital #133 `bin/px_hospital_staffing_grants.py` contract, **without inventing a competing schema**:

- `SCHEMA = post-apollo.hospital.staffing-grant.v1`; `AUDIENCE = px-hospital-native-staffing-v1`; Ed25519 domain `post-apollo.hospital.staffing-grant.v1\x00`.
- Canonical envelope `{"body": {...}, "signature": "<unpadded-base64url-Ed25519-signature>"}`, exact two envelope fields and exactly the existing `BODY_FIELDS`:
  `schema`, `audience`, `operation`, `scope`, `roomRevision`, `graphDigest`, `operatorId`, `approvalId`, `seatId`, `hostId`, `nonce`, `requestNonce`, `writerInstance`, `issuedAt`, `expiresAt`, `operatorUid`, `polkitActionId`, `policyGeneration`, `clientExecutableSha256`, `issuerReleaseSha256`, `reviewDigest`.
- `scope` contains exact `roomId`, `patientId`, `repository`, `branch`, `bedPath`, `assignmentId`, plus `sessionId`, `doctorId`, `providerId`, `mode` for `SESSION_ATTACH`; or prior/new Session/Doctor/Provider identities for `DOCTOR_SUCCEED`.
- Derive operator UID and seat only from Linux kernel peer + system `login1`, not request JSON, QML, desktop environment variables or a signature's own claims. `operatorId` is `uid:<operatorUid>`.
- The grant binds the **exact original PREPARE review** via the existing Hospital `px_hospital_staffing_operator_review.py` `reviewDigest`; a changed COMMIT frame cannot redefine what was reviewed. `nonce` and `requestNonce` are separate canonical 32-byte unpadded base64url values. The grant expires within **30 seconds**.
- Signed `policyGeneration`, client executable digest, issuer release digest, host, action and operator must be **exactly equal** to the currently root-owned writer verifier policy at transaction time, rather than accepting a stale signed grant after policy change.

### Real issuer / host / seat evidence

The staffing issuer can reuse the **mechanisms**, not the **TRASH/RESTORE privileges**, in `HospitalNativeIssuerService.py`: a privileged socket-activated service, `AF_UNIX/SOCK_SEQPACKET`, actual `SO_PEERCRED` and **per-packet** `SCM_CREDENTIALS`, PID + start ticks + full UID/GID, root-owned installed client ELF, root-controlled release allowlist, real system `login1` local active unlocked seat, and interactive per-operation Polkit with rechecks before signing.

An ELF hash of `/proc/PID/exe` for a Python service authenticates the **Python interpreter**, not necessarily the installed entrypoint, imported Python modules, systemd unit, SELinux label, or full approved release. **Root-owned config alone is insufficient installed-release provenance.** Require a separate protected C3e/C4b operator-approved signed release/origin binding and validate the native process+source before staffing authority is enabled. Verify active seat, lock state, relevant effective Polkit policy/agent and operator-visible exact review both before and after interactive authentication. If any evidence is unavailable, keep staffing denied.

### Signer separation / verifier enrollment / revocation

The Room issuer currently loads `/etc/post-apollo/hospital/issuer.key` and the Room verifier pins `/etc/post-apollo/hospital/room-lifecycle-issuer.pub`. **Do not reuse them for staffing.**

Hospital's staffing verifier independently pins the **public** key at `/etc/post-apollo/hospital/staffing-issuer.pub`. A proposed separate **private-key** location is `/etc/post-apollo/hospital/staffing-issuer.key` **only if approved by the future issuer owner**; a reviewed HSM/TPM-backed signer is another possibility. Neither is provisioned here. The operator/custodian must decide the actual signing-key holder, out-of-band public-key enrollment, release signing provenance, key rotation/revocation, policy generation floor, backup and recovery **before** a live signer is implemented or enabled. Never ship live signing private keys in GitHub, RPMs, UI fields or test artifacts.

Hospital's separate root-owned `/etc/post-apollo/hospital/staffing-verifier-policy.json` has canonical schema `postapollo.hospital.staffing-verifier-policy.v1` and only: `schema`, `operatorUid`, `clientExecutableSha256`, `issuerReleaseSha256`, `hostId`, `policyGeneration`, `allowedOperations`, `expiresAt`. The allowlist contains only `SESSION_ATTACH` and/or `DOCTOR_SUCCEED`. Its 31-day maximum expiry and exact generation equality are **necessary, not independently rollback-resistant custody**. Old policy files could be restored unless independently protected monotonic history is established.

### Protected writer-only transport

Hospital's `px_hospital_staffing_transport.py` specifies `postapollo.hospital.native-staffing-request.v1` with exact canonical `prepare` and `commit` frames.

- **PREPARE:** `schema`, `kind=prepare`, `action`, `roomId`, complete `intent` and `requestNonce`. Writer replies with `postapollo.hospital.native-staffing-prepared.v1`, exact Room revision + graph digest + writer process instance; `operatorAuthenticated=false` and `requiresExternalConsent=true`.
- **SIGN:** Native issuer validates prepared source, exact operator-visible review digest, enrolled release/host/seat and action-specific Polkit approval. Only then it signs the staffing domain envelope. Never hand a reusable signed grant to QML or an arbitrary client.
- **COMMIT:** Dedicated issuer sends the original request/intent with `kind=commit`, original `requestNonce`, `writerInstance` and `signedEnvelope` (base64url canonical envelope) **only to the protected Hospital writer**. The writer verifies the root-pinned public key, current host and root-owned revocation policy, signed exact source graph, original PREPARE, operator, seat, action and one-use approval nonce, all under the same `BEGIN IMMEDIATE` as the original Session/Doctor mutation. On refusal, no source write; new nonce and human review required.
- **RECEIPT:** Protected writer issues the source-verified response. Connections may return only a bounded operation result, not raw signed grant, private key or database handle. Hospital owns atomicity, consumption, source transaction tests, schema migrations, old-writer fencing, backup and recovery.

**Frame mismatch requiring explicit agreement:** merged C5-H2's `MAX_IPC=8192`; Hospital staffing requests allow `MAX_FRAME=16384`, canonical signed grants up to `8192` bytes. A new staffing service must agree on bounded request/response framing, strict truncation refusal, READY handshake and total decode limits. **Proposed:** separate staffing socket/service identity, rooted in `/run/post-apollo/hospital/`, and no extra actions on Room Trash/Restore's current `issuer.sock`. The exact socket basename, installed UID/GID, systemd service, SELinux and maximum packet/response bytes are **UNAPPROVED** until owners agree. Preserve the existing protected writer's exclusive database and its legacy Room Trash/Restore socket.

## VERIFY

**Source facts, not production evidence:**
- Hospital #133 exact head `ee1dc74056fbd2c849d3391e3148b003514b2932`: **3/3 GitHub workflows PASS**, still draft and unmerged. Staffing dispatcher `dispatch_native_staffing()`, native transport `dispatch_native_request()` and native peer `authorize_staffing_from_packet()` intentionally refuse.
- Connections merged C5-H2 #2056 has native process/login1/Polkit mechanisms for **TRASH/RESTORE**, not for these staffing actions; its grant domain is `post-apollo.hospital.room-lifecycle-grant.v1\x00`. Its service is not an approved staffing issuer.
- This Connections document is an **interface review only**. It contains no executable source, workflow, actual installer, key, database migration or production permissions.

## WATCH OUT FOR // Contract decisions pending agreement

1. **Issuer boundary:** Separate staffing service and socket, installed accounts, SELinux context, exact bounds and READY/SCM_CREDENTIALS framing. Prevent any Trash/Restore/Bed/Burn action crossover.
2. **Key / release custody:** Operator-designated enrollment custodian, independently pinned private/public key pair, signed installed Python + unit provenance, rotation/revocation, policy generation history and recovery.
3. **Human-consent evidence:** Which audited installed Polkit rules/agent and request-specific review mechanism prove the active person actually approved the correct PREPARE, rather than a generic/cached/overridden permission.
4. **Writer delivery:** Exact PREPARE/COMMIT/receipt and protected writer peer identities, expected 16 KiB/8 KiB envelope limits, grant TTL, replay/rollback semantics, approved v13 migration and old-writer fence.
5. **Authority separation:** No Hospital Trash/Restore permission or irreversible Burn; C5/PX/Hospital owners independently review their own source. The protected C3e/Identity work and previously paused worker must not be silently reassigned.

No staffing issuer implementation may rely on the proposed fields and untrusted caller fixtures as **live authority** until these decisions are accepted by both affected owners and the operator.

## CHECKLIST

- [x] Read current Syntagma AGENTS / Hospital operating rules and merged C5-H2 / exact draft Hospital #133.
- [x] Review both Polkit actions, signed grant and root-owned verifier policy.
- [x] Compare actual C5-H2 native process/seat checks, grant domain and IPC bounds with Hospital staffing draft.
- [x] Publish proposed Connections-side interface for cross-owner review without editing either established implementation.
- [ ] Hospital owner acknowledgement and any required interface corrections
- [ ] Connections C5-H2/staffing owner acceptance or explicit new bounded staffing implementation assignment
- [ ] Separate approved signer/host provenance/consent and protected writer/migration decisions
- [ ] Only then implement and independently test an isolated staffing native issuer
- [ ] Native test installation / production acceptance only after separate operator authorization

## NEXT

Receive and reconcile the two owners' decisions on the five unapproved boundaries. Any final API change should first update this source contract and Hospital #133's companion proposal, and only then proceed to an isolated source-only staffing issuer draft. C3e #2075/#2076 are separate protected signer/witness preflight assignments, not an implicit authorization to modify installed C5/H2 service or Hospital writer.

## DECISIONS

**COORDINATION ONLY.** No edits to Hospital #133, C5-H2, existing Room/Trash/Restore, PX migration, C3e source, native service, real keys, credentials, user workstation or sign-in. No merges or production permission activation. Live Hospital staffing/Room assignment registration unverified.
