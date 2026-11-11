# Social PHONE // P40R post-write encrypted vault observation (CI only)

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** external Hospital-compatible ordinary DOC. No verified live Hospital Room, Assignment or Session attachment.  
**Scope:** PHONE-only, independent, read-only diagnostic helper and synthetic tests. P41 production integration is still blocked on issue #1885.

## IMPLEMENTATION
P35 writes an encrypted file by atomic replace followed by directory fsync. A crash, I/O failure or missing acknowledgment in this window may leave a valid new sealed file despite an error. A blind retry is unsafe, particularly if a prior revision has been restored.

`services/phone/PhonePersonalVaultRecoveryP40R.py` inspects only an independently key-supplied encrypted vault and compares the authenticated current document to a caller-held, previously validated expected revision and pending document. It returns one of:
- `CURRENT_CIPHERTEXT_MATCHES_PENDING`: contents currently match; **not** proof of a durable commit.
- `CURRENT_CIPHERTEXT_HAS_PRIOR_REVISION`: previous revision currently observed; may be an old ciphertext rollback.
- `CURRENT_CIPHERTEXT_UNRESOLVED`: a different revision or conflicting document.
- `OBSERVATION_UNAVAILABLE`: malformed input, missing key/wrong profile, corrupt data or invalid filesystem evidence.

All results state `productionEnabled=false`, `writeAuthorized=false`, `retryAuthorized=false`, `durableCommitProven=false`. No public note, contact identity, master key or vault path is emitted. No retry, reconciliation write, key lookup, QML, D-Bus, CLI or provider operation exists.

## HOW TO USE
No new PHONE control. CI-only synthetic tests exercise the read-only observer using temporary encrypted fictional contact data. This is not a key provisioner or production recovery API.

## VERIFY
The tests simulate a directory-fsync error **after** atomic rename, rename failure **before** replacement, matching current content, prior content, same-revision conflict, tamper and bad profile/key. They assert no write authority is returned and no vault file is created by inspection. P35 regression tests run in the same separate CI workflow with a disposable runner dependency.

## WATCH OUT FOR
Observing an encrypted document after a failure does **not** prove the original write was durably acknowledged, prevent historical ciphertext rollback, or authenticate the caller. A trusted host must hold an independently enrolled signing root, live C3e/C4b/Identity process evidence, genuine C5 one-action consent, a protected Personal key and an atomic authorization/commit discipline. This helper cannot provide those authorities and must never be treated as a reason to unlock the P40 buttons.

## CHECKLIST
- [x] Scope recovery without affecting P40 UI, BlueFerry or generic Favorites++/Notes.
- [x] Define content-free post-error observation states without retry authority.
- [x] Add synthetic negative, uncertainty and no-mutation tests.
- [ ] Verify exact PR-head CI and operator review.
- [ ] Wait for cross-owner installed-host, challenge and C5 consent proof under issue #1885.
- [ ] Design genuine production key lifecycle and an atomic one-use commit host with separate approval.
- [ ] Perform separately approved native Fedora verification.
- [ ] Obtain final operator acceptance.

## NEXT
Keep P41 protected Personal save interface blocked until authentic upstream evidence is available. Within PHONE scope, use current owner-supplied trust grammar to plan an independently verified host/recovery ledger and native test, without treating P40R observations or P37–P39 synthetic matches as grants.

## DECISIONS
This diagnostic deliberately does not change the P35 commit API, P36–P39 trust checks, P40 disabled controls, global Favorites++, iPhone provider, runtime services or operator host. No merge or production activation is authorized by this PR. Source-only review is not final acceptance.
