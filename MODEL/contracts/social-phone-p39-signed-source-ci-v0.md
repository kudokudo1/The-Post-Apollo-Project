# Social PHONE P39 // Signed upstream source bytes, CI-only / DENY-ONLY

> Patient: kudokudo1/The-Post-Apollo-Project. Role: external Hospital-compatible ordinary DOC on PHONE source-consumer lane. No verified live Hospital Room, Assignment ID or Session. GitHub is the technical source of truth; operator retains approval.
>
> P38 PR #1889 was already merged by the repository owner at this checkpoint, 3/3 CI checks passed. P39 is a separate bounded branch and does not inherit authority to merge, deploy, activate or change another team's source.

## IMPLEMENTATION

P39 advances the PHONE contact metadata trust-consumer chain **beyond P38's caller-supplied C3e-Z/C4b summary booleans**:

- \`services/phone/PhonePersonalSignedSourceP39.py\` checks the actual, source-defined **C4b signed release envelope** bytes, verifying its Ed25519 signature with a supplied release-root public key and strict nine-path package/unit/file roster. It checks independently supplied test file/RPM pins, epoch/sequence floor, pinned receipt key digest and precise purpose/schema/domain. The signed package digest and exact release fields must bind to the existing P37 signed PHONE host frame.
- The same module checks the actual **C3e-Y signed full-host statement** bytes and Ed25519 witness signature under a *different* supplied witness public key. It enforces exact canonical structure and signed domain, release/challenge/hash binding, receipt-key fingerprint, SHA-256 of the supplied C3e-X evidence line and four supplied denial-frame bytes, and digest of a supplied complete snapshot. The C3e-X evidence line is parsed for exact enclosing schema, role, canonical framing and four records; P39 **does not independently validate its per-record kernel observations nor verify the four denial signatures**. These remain C3e-X/C3e-Z owner responsibilities.
- The signed witness frame's SHA-256 must equal \`hostEvidenceSha256\` inside P37's separately Ed25519-signed host receipt. The signed release's RPM digest must equal P37's \`releaseSha256\`. The P37 exact PHONE contact/operation/revision/challenge request and separate, synthetic signed reviewer receipt must still verify under P37's fixed CI-only contract.
- Five key roles (P37 host, P37 synthetic reviewer, C4b release root, C3e witness, Identity command receipt) must use **distinct** public keys. No trust-on-first-use, source-provided key acceptance, guesswork or promotion from an unsigned status flag is allowed. All keys, files, snapshot and P37 request remain **caller-supplied test inputs**, not independently enrolled installed-host authority.
- Every public result retains \`productionEnabled=false\`, \`installedHostVerified=false\`, \`humanConsentVerified=false\`, \`vaultWriteEnabled=false\`, \`keyReleaseEnabled=false\` and \`externalChallengeConsumed=false\`, including when all signatures and hashes match. Good synthetic bytes yield only \`SIGNED_CI_SOURCE_BYTES_BOUND_NOT_AUTHENTICATED\`. Missing, forged, stale or unsupported formats yield a content-free denial.

No new service registration, provider call, Linux process measurement, challenge consumption, network/IPC, Secret Service interaction, production key, iPhone contact edit, PHONE QML control or real note save. No modifications to C3e/C4b/C5/Identity-owned files.

## VERIFY

New synthetic \`tests/phone/test_phone_personal_signed_source_p39.py\` loads the **actual upstream C4b/C3e-Y Python schema definitions** to pin the consumer's strict formats. It generates separate disposable Ed25519 signers, source files and fake process metadata. Tests cover positive source-hash/signature consistency and numerous denials: wrong release/witness roles, altered RPM/file roster, duplicate JSON fields, noncanonical signed bytes, changed epoch, wrong receipt signer, forged C3e evidence/denial-frame digests, mismatched snapshot, stale PHONE action or revision, changed challenge/nonce/profile, expired reviewer and asserted genuine C5 consent.

Dedicated GitHub CI runs P39 tests plus existing P35-P38 protected PHONE regressions. Normal PHONE workflow compiles the new code but does not invoke real keyring/host functions. No private iPhone data appears in the tests.

## HOW TO USE

No operator PHONE control is connected yet. P39 is **synthetic cryptographic format checking only**. Review the P39 draft PR, exact-head CI, and owner handoff before considering any installed-host test. No local Fedora files or actual keyrings were modified by this worker.

## WATCH OUT FOR

These are real cryptographic verifications over **fabricated data**, not genuine independent trust. Caller-generated pins do not establish an enrolled release root. C3e-Y's witness signs digests of claimed C3e-X evidence/receipts, but this module does not verify the individual denial signatures, check actual kernel PID/start/executable/SELinux/seat, or consume a real independently custodied one-use challenge. A replayed matching fixture still matches without authorizing anything.

The installed-host/consent owner dependencies remain tracked in issue #1885:
- C4b/Identity must deliver independently enrolled and verified **actual installed host**, signed release, source digest/executable + process+seat evidence, rollback/revocation behavior.
- C3e must deliver independent signer/issuer custody, a source-authentic full host record, and rollback-resistant external one-use challenge issuance/consumption. C3e-AA #1896 remains independently owned.
- C5 must deliver a **genuine PHONE-specific one-action human-consent issuer**, not the synthetic reviewer used here.
- PHONE must choose a protected production Secret Service namespace, explicit key creation/unlock/rotation/backup/erase and a synchronized grant that persists through P35's revision-checked encrypted commit. P36 remains CI only.

It would be unsafe to activate favorite/notes saving on the strength of P39's matching result. Never treat signature validity over caller-supplied claims as proof of a real phone, trusted process or human.

## CHECKLIST

- [x] Verify owner merge of P38 and current C3e/C4b/C5 boundary.
- [x] Implement a PHONE-owned signed-source verifier without changing protected producer files.
- [x] Bind upstream release and witness bytes to the existing exact P37 signed contact-save request.
- [x] Keep every real authority/key/vault flag false and reject genuine C5 claims until verified.
- [x] Add synthetic cryptographic adversarial tests and regression workflows.
- [ ] Exact-head GitHub CI verification and independent operator review/merge.
- [ ] Actual independent installed-host provenance and true C5 human consent.
- [ ] External one-use challenge authority and protected contact-vault key lifecycle.
- [ ] Native installed Fedora disposable trust test with separate local-machine authorization.
- [ ] Real FAVORITE star and NOTES editor behind protected saved-state feedback and explicit delete.

## NEXT

The next **real implementation dependency** is the authoritative, independently enrolled production source from C3e/C4b/Identity plus C5's human-consent receipt and a one-use challenge consumed under a protected host. When those owners deliver, write a PHONE-side verifier using their **actual** signed source bytes and keys, then couple the decision with an encrypted vault commit under one synchronized protected authority. Do not invent the missing production service, use developer test keys in the live keyring, or falsely claim real local success. Once verified, implement the requested Favorites and Notes controls.

## DECISIONS

P39 is source-level read-only, denies all production effects and preserves all existing ownership, permissions and concurrent branches. Technical CI completion does not imply operator final acceptance or permission for local deployment.
