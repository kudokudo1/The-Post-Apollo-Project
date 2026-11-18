# 🏥💜 Connections C5-H2 // Native Hospital Room Signer and Active-Seat Authorization

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections C5-H2 · protected Hospital-specific issuer with Identity logind mechanism  
**STAFF ROLE:** External Hospital-compatible DOC, operator-authorized implementation for Hospital/Connections; live Hospital registration not verified  
**OWNER BOUNDARIES:** Additive `services/connections/hospital` and own test, workflow, templates and docs. Existing C5a–d, C3e/C4b, Identity, PX and Hospital UI untouched.  
**PREREQUISITES:** Merged C5-H1 [#2051](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2051), PX signed grant draft [#130](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/130), PX protected-writer handoff, operator key custody/retention/production approval.  
**DEPLOYMENT:** **HOLD**. Source-only candidate, NOT an installed signer or approved production operation.

## IMPLEMENTATION // Actual mechanism

A desktop app must never be able to produce an authorization by presenting `Room ID + revision + confirmed:true`. The new bounded native service does not accept a public key or a grant from the caller. The **only** request from a desktop client is canonical JSON:

`{"schema":"postapollo.connections.hospital.native-request.v1","action":"TRASH","roomId":"hospital-room-01"}`

The root-only systemd socket-activated service, after separately approved installation, has the following actual OS-backed path:

1. **Kernel requester:** receives Linux SOCK_SEQPACKET on the passed socket and obtains `SO_PEERCRED` (PID/UID/GID). Reads the kernel process start ticks, current UID/GID and actual root-owned ELF inode via `/proc/PID/exe`; compares its SHA-256 to a **root-owned** exact client executable digest and configured operator UID. Checks again around authorization. Rejects any arbitrary QML flag, CLI process label, user-supplied PID or executable path. The executable digest still requires separate *signed installed-release provenance* before it is an independently approved identity.
2. **Real active logind seat:** connects to the **system** D-Bus `org.freedesktop.login1`, looks up the session by the kernel peer PID, validates matching UID, nonremote active user session, assigned seat, active state and `LockedHint=false`, and records a seat/session binding. Rechecks after authorization. A missing, switched, locked or detached session refuses. **LockedHint alone is not a reliable Sway/swaylock lock guarantee**; operator-approved independent compositor lock evidence is still required for production.
3. **Protected PX source review:** contacts a fixed `/run/post-apollo/hospital/px-writer.sock` over AF_UNIX SOCK_SEQPACKET, validates the socket's protected ancestry and the other end's kernel `SO_PEERCRED`, dedicated PX UID and root-enrolled executable SHA-256. This protected PX writer **does not exist yet**. It must return a canonical exact review snapshot for one fresh issuer nonce: Room, Patient, repository, current revision, graph SHA-256, action, eligibility, zero blockers, retention-approved, legal-hold false, policy generation (minimum floor), short expiry, and writer instance. A user-writable SQLite database or a QML snapshot is NEVER an acceptable substitute.
4. **Interactive per-action Polkit:** asks `/usr/bin/pkcheck` for either `org.postapollo.hospital.room-trash` or `org.postapollo.hospital.room-restore` against the kernel-bound PID/start/UID triple, with `--allow-user-interaction` and a `polkit.message` containing the protected Room, Patient, repository, revision, full graph SHA-256, retention choice and seat. Template action policy requires `auth_self` in an active session, not an `*_keep` cached authorization. The actual effective Polkit rules and active trusted authentication agent MUST be audited, because a rule can override the action or an agent can fail to show the request-specific message. **Polkit success cannot by itself prove that the human saw the exact Room, so native full consent acceptance remains HOLD.**
5. **Real Ed25519 signature creation:** only after the above checks, the root-only service opens the fixed root-owned 0600 private seed `/etc/post-apollo/hospital/issuer.key`, checks parent owner/mode, no symlinks, single-link regular file, exact 32 bytes and stable read; it refuses unless its derived public key matches the separately installed 32-byte public anchor `/etc/post-apollo/hospital/room-lifecycle-issuer.pub`. The program has **NO key-generation or CLI signing function** and no environment public-key override. The caller never sees either key. The exact v12 signed grant contains one TRASH or RESTORE action, Room/Patient/repo/revision/graph, operator UID, seat/session, host fingerprint consistent with PX's root-owned machine-ID binding, signed retention, nonce/approval ID and max 30-second expiry.
6. **Protected writer only:** sends the **signed grant** over a distinct authenticated PX writer socket with the same issuer nonce and writer instance. The writer MUST recheck the Room/graph/blockers/retention policy and consume one-use approval **inside its own BEGIN IMMEDIATE Room transaction**, return a precise committed receipt and reject replay. The issuer compares receipt digest, Room, action, revision, preserved-original and no-Burn fields. **Only then** does the desktop receive minimal `COMMITTED` metadata; it never receives the signed grant, private key or general database capabilities.

This is implementable native source for a protected execution path, not a mock signer. **Its current deployment cannot work safely:** the protected writer/issuer installation, release pins, operator-owned private key, active agent and independent lock/retention policies are not provisioned. Without them it necessarily refuses, rather than downgrading to a fake CI reviewer.

### Exact protected PX writer contract proposed to the PX owner

The issuer sends a canonical bounded `prepare` packet:
`{"schema":"postapollo.hospital.protected-writer-request.v1","kind":"prepare","roomId":"…","action":"TRASH","requestNonce":"<43-char base64url>"}`.

The protected PX owner replies with an exact canonical `postapollo.hospital.protected-writer-prepared.v1` object containing these exact fields: `schema`, `requestNonce`, `action`, `roomId`, `patientId`, `repository`, `expectedRevision`, `expectedDigest`, `state`, `blockers`, `canTrash`, `canRestore`, `retentionApproved`, `legalHold`, `policyGeneration`, `writerInstance`, `expiresAt`. The service refuses inconsistent source state, legal hold, expiry, missing protected policy generation and wrong writer instance.

After operator authorization, the issuer sends canonical `commit` with `schema`, `kind`, `roomId`, `action`, `requestNonce`, `writerInstance` and `signedGrant` (ASCII canonical PX envelope). PX must atomically refuse wrong source revision/digest, replay, legal hold, expired signer or revocation. PX returns a canonical `postapollo.hospital.protected-writer-receipt.v1` containing exact `schema`, `requestNonce`, `roomId`, `action`, `revisionAfter`, `grantDigest`, `state`, `originalPreserved:true`, `burnAllowed:false`. **This service is not the protected SQLite writer.**

### System integration templates (not deployed)

- `services/connections/hospital/native/post-apollo-hospital-issuer.socket`: systemd SOCK_SEQPACKET socket, root-managed path, restricted group, no installation target.
- `services/connections/hospital/native/post-apollo-hospital-issuer.service`: root service with systemd socket-only invocation and resource/file confinement; no installation target.
- `services/connections/hospital/native/org.postapollo.hospital.policy`: two separate Polkit `auth_self` actions, no inactive/noninteractive default and no KEEP caching.

No template is registered on the operator workstation by this PR. The native executable installation path, group, SELinux policy, immutable release hashes, root key provisioning and actual Polkit rules/agent must be independently reviewed by the native owners before these units could be installed.

## HOW TO USE

No new UI or terminal command is ready. The application [#2045](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2045) remains source-merged but `HospitalRoomLifecycleService.permissionReady` **must remain false** until the protected writer and issuer are independently verified and source owners approve the integration. Neither code generation nor a Polkit policy XML proves that the user accepted a particular Room action.

For developer review, the GitHub workflow `.github/workflows/connections-hospital-native-issuer-h2.yml` checks actual source and exercises synthetic operating-system boundary fixtures alongside the **real** PX #130 Ed25519 `_verify_bytes` implementation. Test injection never exists through a production IPC field.

## VERIFY

- [ ] Native signer source compiles under pinned Python 3.12 and `cryptography==46.0.4`
- [ ] 38 native signing/source/receipt/fail-closed security cases pass
- [ ] Same signed grant verifies in exact PX #130 owner implementation
- [ ] Existing 40 C5-H1 scope denial tests still pass
- [ ] Independent Nurse 2 review of native interface, identity, logind, Polkit/retention and private key handling
- [ ] Protected PX writer and actual Fedora/Silverblue native end-to-end test, **not yet available**
- [ ] Operator final root/key/install/permission acceptance, **not granted by this PR**

## WATCH OUT FOR // Mandatory remaining authority before production

- **Key custody:** private root signing key and pinned PX verifier public key must be independently created, audited, enrolled, rotated and revoked by the operator; no test key or guest-self pin is acceptable.
- **Program/release identity:** a root-owned hash pin checks bytes but is not a complete signed release/SELinux/kernel-library attestation. The C3e/C4b owner must pin the installed issuer and caller against an operator-approved release policy and independently authenticated host/seat evidence.
- **Human presence:** Polkit may return authorized through external rules, cached grants or an agent that does not display exact details. Test the actual active authentication agent, policy rules, compositor lock and that a *specific Room and retention decision* were genuinely reviewed before declaring real operator consent.
- **PX storage:** current PX SQLite remains desktop-UID-writable. The PX owner has proved this bypass in CI; the native issuer must never sign against that database. Its protected writer must own the DB/WAL/SHM/backup, reconcile old writers and support v11→v12 migration and recovery.
- **Transactional correctness:** same UID permissions and Polkit alone cannot enforce source-level Room integrity; PX must verify source identity and signature/nonce under the protected transaction.
- **Production hold:** even if a staging service signs a test grant, that does not authorize enabling Room Trash/Restore, changing permissionReady or adding Burn.

## CHECKLIST

- [x] Inspect merged #2051 and current PX #130, C5a–d, Identity logind source and Syntagma protocols.
- [x] Implement root-only native signer source with real process/seat/Polkit/PX writer flow.
- [x] Add root key/public anchor checks and precise PX v12 signed body.
- [x] Add noninstalled systemd socket/service and action definitions.
- [x] Add adversarial unit/integration CI and owner handoff.
- [ ] Complete exact-head GitHub tests and independent review.
- [ ] PX owner builds protected SQLite service / retention and backup.
- [ ] Operator approves root/seat/agent/custody/rotation/recovery.
- [ ] Real trusted native installed-host acceptance and operator activation.

## NEXT

Nurse 2 reviews this source PR for missing trust edges; protected Connections/C3e/Identity owners verify the real client and issuer program provenance and active-session lock evidence; PX owner implements the protected prepare/commit writer contract. After those components are installed, test real native operator approval → signed exact PX grant → Room Trash → Bin → Restore with data preserved and no direct SQLite bypass.

## DECISIONS

No GitHub merge, real private key generation/export, native installation, permission switch, QML modification, direct PX data change, production Room transition or Burn. The operator remains the final source of authority. This implementation makes the native integration explicit without claiming the unimplemented protections already exist.
