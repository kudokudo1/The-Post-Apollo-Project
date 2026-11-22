# 🏥💜 Connections C3e/C4b/C5 ↔ Forest B4c // Two distinct signed roles (NO AUTHORITY)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Connections C3e/C4b/C5 Forest-specific authorization seam  
**STAFF ROLE //** external Hospital-compatible DOC, live registration unverified  
**STATE //** source-only, uninstalled, **verify-only**, no real C5 signer or human consent, production Forest HOLD  
**OWNER DECISION //** [Forest #2161](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7084063192): C3e/C4b/C5 Forest interface owned by this Connections DOC per operator's explicit correction; no protected Identity-owner unpause and no Forest backend/ForestW takeover

## IMPLEMENTATION

The existing B4b host callback checks Python policy twice. This does not authenticate the caller or coordinate revocation through a protected C5 issuer. The already merged B4c [two-store ordering reference #2168](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2168) demonstrates that revocation must serialize with a one-operation commit fence and retain UNKNOWN_HOLD for an unreconciled outcome, but the fixture uses forgeable values and cannot be shipped.

**New source-only check:** services/connections/forest/ForestC5SignedEvidencePreflight.py validates **two independently signed Ed25519 role records** against an exact canonical Forest COMMIT intent. There is no private signing key, listener, local file opener, database writer, installed host policy, local seat, C5 grant or native command. The only exposed entry point is verify_unenrolled_role_consistency; **every positive trust / consent / commit / tool / production output is permanently False**.

- An exact **COMMIT_GENERATE** intent names audience postapollo.forest.conversation.v1, independently verified principal (in future), Tree, B3 actual user turn, B3 reserved attempt, request and grant IDs, selected model, expected revision, consent epoch, issue/expiry, freshness challenge, requester/commit-host release SHA256, original requester PID/start/UID and seat epoch.
- Signed **requester** role postapollo.forest.requester.v1 and distinct **reviewer** role postapollo.forest.consent-reviewer.v1 bind that same intent hash, challenge, epoch, role and public key fingerprint.
- Strict canonical JSON, exact fields, size, numeric ranges and all identifier grammar, two distinct 32-byte Ed25519 public keys, bounded 64-byte signatures, role/decision separation and actual Ed25519 verification prevent signature aliasing, switched domains, duplicate fields, partial records and cross-audience substitution in the disposable fixture.
- The API deliberately receives public keys as **caller-provided fixture input**. This can prove *signature byte consistency* only. No root is independently operator-enrolled; no key custodian, revocation authority, real kernel process observation or human approval exists. Never use the function result to perform a native action.

**Two-phase contract:** B4a must first authenticate and approve PREPARE_GENERATE before inference. B3 generates the durable reserved attempt ID *after* this initial check. The protected C5 COMMIT_GENERATE fence is a **separate later operation** binding the actual reserved ID and the unchanged original intent. A Boolean pre-commit hook alone cannot hold a protected permit across the final SQLite COMMIT/ROLLBACK. Only a future approved issuer can provide the real permit and signed durable terminal acknowledgment. No release of a stalled fence merely because a TTL expired.

**Scope:** GENERATE commit only. READ_SESSION, Leaves memory, model tools and private history are distinct permission scopes; this contract never permits any of them.

## VERIFY

Dedicated Github CI installs **pinned cryptography==46.0.4** in a disposable Ubuntu job and runs the new signature/role suite, the existing Forest B4c two-store ref and B4b synthetic callback regression. Tests create two temporary in-process Ed25519 private keys solely to produce fixture signatures and check wrong role, changed grant/principal/Tree/model/turn/attempt/revision/release/process/seat/epoch/nonce, wrong audience, noncanonical/duplicate JSON, expired/future lease, false key identity and explicit deny-only output.

All source fields are exact and test-only. A green CI indicates canonical signed fixtures and denial composition, not real user authorization or native host trust. No host-installed test run has been performed.

## WATCH OUT FOR

1. Anyone can generate a key pair and valid signatures in the CI/test harness. Both signatures could be signed by an attacker outside a protected service. The reviewer role signature is not proof that a **human** saw and approved a specific review prompt.
2. The signed PID/seat/release values in this fixture are client-supplied claims. The real C3e/C4b owner must independently measure connected kernel peer lifetime, exact installed requester and commit-host process/release, active unlocked seat, and externally enrolled issuer key/floor/history before comparing any signed bytes.
3. Signatures alone have no replay database or durable revocation fence. Existing two-store reference is only an ordering demonstration; future C5 implementation must own native protected storage, one-use transaction, revocation acknowledgment and authenticated terminal receipt.
4. Private conversation storage remains plaintext only in B1/B3 synthetic tests. Do not connect QML/ForestW, Ollama, a live chat, or personal prompts to these fixtures.
5. Existing C5 TASKS, Hospital, Identity and TimeW grant domains remain separate and unchanged. The separately paused protected C3e/Identity owner #2018 and production key/host deployment are not automatically resumed.

## NEXT / DECISIONS

**Connections owner (this DOC):** accepts v0 role separation and commit intent fields as a **preflight source contract** only; production acceptance stays HOLD. Continue with a separate native issuer/host identity, human-seat C5 approval and durable fence implementation only under independently reviewed operator-approved key/service custody.  
**Forest backend DOC:** adopt the agreed two-stage semantic contract in its own lane after source and security review. Do not treat test-only record status as an authorization; B4b callback remains synthetic.  
**Nurse 2:** independent exact-head pre-merge source/security review of canonical encoding, role domains, signature substitution, no-authority outputs and future unsafe import paths.  
**Operator:** explicit approval still required for production signer enrollment, real personal data storage, host service installation, live Forest/B4c enablement.

**STATE //** CI/SOURCE ONLY, NO KEYS ENROLLED, FOREST / TIMEW / SIGN-IN PRODUCTION HOLD.
