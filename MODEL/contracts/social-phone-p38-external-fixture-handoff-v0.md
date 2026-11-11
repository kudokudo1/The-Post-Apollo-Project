# 🏥💜 Social PHONE // P38 Upstream CI format handoff (DENY ONLY)

**Patient:** kudokudo1/The-Post-Apollo-Project. **Worker:** external Hospital-compatible DOC. **Room / Assignment / Session:** no verified live attachment or authorization; bounded PHONE-side adapter work only. **Checkpoint:** P37 PR #1884 merged. Existing dependency issue #1885 remains open. GitHub remains source of truth, and operator approval is separate from CI.

## IMPLEMENTATION

PHONE now has an independent, isolated read-only adapter at `services/phone/PhonePersonalUpstreamHandoffP38.py`. It compares **actual current repository source shapes** of upstream CI-only outputs against the P37 synthetic Ed25519-signed PHONE save request. It does **not** consume an independently issued challenge, verify a live Fedora host, accept real C5 consent, open the keyring, or write an encrypted vault.

- P37 must independently verify both domain-separated Ed25519 signatures for the exact synthetic PHONE request and fixed CI role/audience.
- C4b's existing `SilverblueReleaseCandidateV1` metadata fields are recognized only in their actual deny-only form. Release epoch, sequence and RPM/package digest must match the P37 signed host frame, while all C4b installed-host/production/login flags remain literally false. The C4b candidate is **caller-supplied**, even when its shape matches. Its `receipt_key_sha256` value is type-checked but is not treated as an installed signer.
- C3e-Z's existing `inspect_release_and_consume` result shape is recognized only when all three CI-only positive diagnostics appear and **every** listed real-host / independent-custody / human-consent / production flag is literally false. These result fields alone do not include the signed C3e full host witness bytes or issuer evidence, so they are **not independently authenticated by PHONE**. The adapter never executes C3e-Z's one-use challenge consumption itself.
- No genuine PHONE C5 receipt issuer or contract exists. Any purported external C5 approval is refused, regardless of its contents. The P37 synthetic consent signer is explicitly **not** real C5.
- Even when all CI formats line up, P38 returns only `CI_FORMATS_RECOGNIZED_NOT_AUTHENTICATED`, with `productionEnabled=false`, `vaultWriteEnabled=false`, `humanConsentVerified=false`, `installedHostVerified=false` and `keyReleaseEnabled=false`. Unsupported, malformed or promoted fields get the fixed refusal `EXTERNAL_TRUST_CONTRACT_UNAVAILABLE`.

**No change** to C3e, C4b, C5, Identity Center, P34/P35/P36 source, iPhone data, Live PHONE UI, installed packages or keyring credentials.

## HOW TO USE

There are **no new user-visible Favorites or Notes controls** in this stage. The dedicated GitHub Actions workflow runs purely synthetic tests against the actual imported C3e-Z / C4b Python source rosters and P37 cryptographically signed fixture messages. No actual contact data or OS keyring is accessed.

## VERIFY

- Import current C4b source to build its actual dataclass and current C3e-Z source to derive its actual allowlisted CI-only result fields; changing upstream fields causes PHONE CI to fail instead of silently accepting new flags.
- Confirm valid signatures and aligned current schemas still **never** unlock the vault.
- Reject missing, unexpected or inflated fields; false claims of production, installed host, rollback resistance and C5 consent; mismatched release epoch/sequence or package digest; bad signature/key; stale revision, profile, action, nonce, expired receipt or forged C5 input.
- Re-run P37 signature regressions, P36 synthetic host tests and P35 AES-GCM vault tests in disposable CI. The standard PHONE workflow also compiles P38 without invoking keyring code.

## WATCH OUT FOR

A well-formed C3e-Z diagnostic **is not** its authenticated full-record evidence. The mock SHA-256 digest in the P37 host frame is not bound to the C3e-Z signed record bytes by this adapter. The C4b release candidate likewise is not proof of actual signed running Silverblue RPM/systemd/SELinux/seat identity. A non-atomic, in-process test revision check cannot replace protected external challenge consumption or an explicit C5 human action.

The current P38 output is a **compatibility diagnostic only** and may be regenerated with forged caller-supplied CI data. It is forbidden to use it as authorization for `PhonePersonalContactVault.commit`, keyring unlock, actual Favorites or Notes persistence.

## CHECKLIST

- [x] Verify P37 merged, current C3e-Z/C4b CI source formats and C5's current non-authorizing reviewer.
- [x] Keep protected peer source and live desktop untouched.
- [x] Compose P37 cryptographic signed-fixture test with the exact upstream CI result rosters.
- [x] Refuse all real C5 claims and any unexpected promotion flags.
- [x] Maintain uniform deny-only key/host/consent/vault outputs.
- [x] Add adversarial integration tests, dedicated CI and PHONE compilation.
- [ ] Exact PR head CI and operator review/merge.
- [ ] C4b/Identity installed signed host evidence and separately enrolled root, actual PID/start/UID/GID, SELinux/cgroup/seat/rollback.
- [ ] C3e independent authenticated host-source + challenge issuer/one-use receipt and externally protected anti-rollback.
- [ ] C5 genuine PHONE-specific one-action human-consent signed receipt bound to exact saved change.
- [ ] Production Personal key namespace, unlock/rotation/recovery and atomic lease across P35 vault commit.
- [ ] Native installed-host verification and separate operator acceptance before Favorites/Notes write controls.

## NEXT

**P39:** Once owners provide actual signed evidence bytes and independent source-of-truth receipts, make a PHONE-side **source-authenticating** verifier binding C3e's full host record, C4b's installed gateway, C5's real per-action consent, and an externally issued one-use challenge **to one exact P37 request**. Carry protected session/consent state through the vault writer's critical section. Obtain local-host approval before any Fedora testing, and preserve existing owner roles. Only after verified trust and key custody may the contact star and note editor become writable.

## DECISIONS

No speculative production API, service, local write, merge, keyring interaction, consent substitution or iPhone-side contact edit. Treat recognized CI formats as untrusted compatibility data, never a permission grant. Operator retains acceptance authority.
