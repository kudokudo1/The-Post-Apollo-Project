# 🏥💜 TASKS M11y // Independent trust-anchor contract and signed synthetic release negative tests

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M11y signed-release trust-anchor mechanics, synthetic read-only verification  
**WORKER //** external Hospital-compatible ChatGPT doctor, not live Hospital-registered  
**INSPECTED BASE //** GitHub `main` `b50f1f67e6a209dae2307787f129102529958c9e` (October 30, 2026). Recheck before further changes.  
**STATE //** **SYNTHETIC-ONLY REVIEW**; not production-authorized, not a user trust store.

## IMPLEMENTATION

M11u tested pinned synthetic script bytes; M11v correlated a Linux child process to a system interpreter; M11w correlated the observed child/session to an actual **disposable** M11l SQLite journal owner; M11x identified the missing **independently trusted provenance** of the pinned interpreter and owner module. Those test pins came from the same CI checkout being tested. They cannot establish the origin of a production host.

M11y adds a separate, Node.js built-in crypto **Ed25519** signature verification slice to prove a real signature check and to exercise the *boundary* between a candidate release and independently controlled trust inputs.

- `tests/tasks/fixtures/TaskSignedReleaseVerifierM11y.cjs` is a read-only imported verifier with **no CLI, subprocess, install, or TASKS path**. It accepts only an absolute private `m11y-release-copy` fixture. The three files are explicitly synthetic: `synthetic-host.py`, `synthetic-owner.py`, `synthetic-interpreter.bin`; it **never executes** them.
- Caller must provide the trust anchor **outside** the release: Ed25519 public-key PEM, a separately pinned SHA-256 fingerprint of its DER SPKI, and a separately maintained **minimum accepted generation**. No fallback reads a key, fingerprint or generation floor from the candidate bundle.
- The `release.sig` Ed25519 signature covers exact bytes of a **canonical ASCII** `release.manifest`, requiring precisely version/header, positive generation, and three SHA-256 digests in a fixed order. Unrecognized/duplicate fields, malformed bytes, missing fields and extra lines are refused, including if a signer signs malformed content.
- Read-only capture enforces private owner-only folder and regular-file metadata, rejects a symlinked leaf, hardlink or loose file permissions, checks identity/size/timestamps before/after each file-descriptor read, compares signed hashes, and returns **only captured immutable-use byte buffers**, not executable paths or authorization.
- A signed older or equal generation is refused relative to the **caller-supplied** minimum generation. This function does not persist that floor. Without externally durable, rollback-resistant generation state, replay of an older-but-still-allowed release remains possible.
- The generated Ed25519 private keys exist **only inside disposable CI/test process memory**. There is **no production private/public key, no release artifact, no real interpreter file, and no deployment configuration** added to the repository.

### Exact verification vs. trust distinction

**What CI can establish:** the Node verifier correctly rejects modified manifests/signatures, a malicious substitute public key paired with the candidate release, malicious artifact changes, symlinks/hardlinks/permissive fixture files and a signed generation at/below the independently supplied floor. A passing release yields three captured matching synthetic byte buffers. The signature is a cryptographic integrity/authenticity check **relative to the caller-provided public key**.

**What CI does not establish:** who controls or distributes that public key, whether the caller's fingerprint or minimum generation are themselves authentic, whether the operator trusts a production signer, full trusted-path ancestry under same-user attack, a real process launching exactly these byte buffers, or OS/runtime control. A signature is not a guarantee of safe code, secure host process identity, durable task storage or production authorization.

**Trust-anchor operating decision, still OPEN:** choose an authoritative producer and a trust-root deployment mechanism independently controlled by the operator or OS administrator, for example an approved signed release and root-controlled verifier trust store. Publish the trusted key fingerprint, minimum generation and approved release source **outside any same-user-modifiable candidate release folder**. Specify who signs, how keys rotate/revoke, how a new generation is durably recorded without rollback, and who can approve a release. Verify key/provenance controls independently before a production gate can close. This milestone **does not choose or install** such a mechanism.

### Negative matrix

| Synthetic attack or edge case | Required result |
| --- | --- |
| Valid Ed25519 signature, external test trust key/fingerprint/floor, three synthetic files | Captured synthetic bytes; no execution or task authority |
| No external trust object, omitted fingerprint or floor | Refuse |
| Candidate release ships its own public key and new valid signature under attacker key | Refuse using independently supplied fingerprint/key |
| Replacement public key supplied with original trusted fingerprint | Refuse fingerprint mismatch |
| Modified manifest, bit-flipped signature, short signature | Refuse |
| Signed generation at or below independent floor | Refuse; no auto-downgrade |
| Externally advanced floor, old release presented again | Refuse |
| Changed host, owner or interpreter bytes without new signed manifest | Refuse digest mismatch |
| Replaced host pathname after verification | Captured bytes stay unchanged; future verification refuses |
| Symlinked file or folder, hardlink, loose artifact/folder permissions | Refuse |
| Signer signs duplicate, malformed, noncanonical or extra fields | Refuse canonical format |
| Wrong key type, malformed trust input or wrong fingerprint | Refuse |
| Production singleton and shell | Remain unmodified; one FileView and guarded flag false |

## HOW TO USE

No changes on the operator's Fedora machine. The test is self-contained using only Node.js built-in `crypto`, `node:test`, `fs` and temporary fixture folders. It never asks for a real signing key:

```sh
node --test tests/tasks/test_task_signed_release_verifier_m11y.cjs
```

Production TASKS, TODAY, PLANNER, Apollo Hub, existing M11l/M11m fixture restrictions, GitHub task data and SQLite task-data migration remain unchanged.

## VERIFY

- Inspect exact GitHub source and workflow output at the PR head; source-only tests check that `ApolloHubTodoStore.qml` has `guardedWriterEnabled: false`, one existing `FileView`, and no M11y mount in `shell.qml`.
- M11y CI runs the Ed25519 negative tests and previously implemented M11x/M11t/M11d source contracts. A green workflow verifies fixture behavior, **not** production trust provisioning or native Quickshell behavior.
- Inputs called “independent” are separate arguments by API **contract**, but in the test they are generated together in ephemeral test memory; this tests key separation mechanics, not a deployed independent administrator-controlled root.

## WATCH OUT FOR

- **No production host has been signed, built or launched.** M11y ships no production key, no real TASKS access and no source/backup integration.
- Ed25519 verification of a provided public key cannot tell whether the *caller* obtained that public key securely. A same-user attacker who controls both the caller and all trust inputs can fool the check; a production verifier must be protected separately.
- Signed generation alone cannot reject same-generation replays unless a durable externally trusted release digest or other monotonic identity is pinned. It cannot prevent rollback when the generation floor itself is attacker-controlled or reset.
- File-descriptor capture and pathname rechecks do not attest full path ancestry against all races or prevent an attacker from tampering with a later, independently reopened executable path. The intended output is verified captured bytes, not a reusable path.
- Existing `FileView.onSaved` callback ambiguity, UI success/failure semantics, backup/recovery and task-data preservation remain **unimplemented**.
- M11t's nine production gates remain **OPEN**, especially `TRUST_EXEC`, `PROCESS_BINDING`, `SOURCE_BACKUP` and `ACTIVATION_APPROVAL`.

## CHECKLIST

- [x] Verify M11x merged; inspect current repository, Hospital rules, ownership and original writer
- [x] Implement isolated Ed25519 canonical-manifest verifier without third-party dependencies
- [x] Require external key/fingerprint/generation and refuse candidate-supplied trust
- [x] Add signed downgrade, signature tamper, artifact replacement and metadata refusal cases
- [x] Preserve the original one-FileView, inactive-guard boundary
- [ ] Verify GitHub CI and independent review
- [ ] Operator review/merge
- [ ] Separately select real trust root, signing authority and key rotation policy
- [ ] Later disabled production-shaped backup, native callback and UI tests only after separate approval
- [ ] Separate permission for local installation, real data access, production activation or migration

## NEXT

Review M11y PR and actual CI. The next proposed **isolated** milestone is a synthetic source/backup/rollback preflight that independently reads back backups and refuses external changes. Before any real host implementation, settle who controls the trust root and monotonic release state. Never widen M11l/M11m's disposable task-file filters as a shortcut.

## DECISIONS

**Implemented:** test-only Ed25519 release verification contract using external-invocation trust inputs and disposable synthetic bytes.

**Proposed, not accepted:** root/admin-controlled or otherwise independently authenticated production signing/deployment trust root, release-generation persistence, key-rotation/revocation policy.

**Not authorized:** live TASKS writer change, real task-data access, local changes, production trust-store installation, signing with real keys, PR merge, native production test, SQLite migration, restoration, or activation.
