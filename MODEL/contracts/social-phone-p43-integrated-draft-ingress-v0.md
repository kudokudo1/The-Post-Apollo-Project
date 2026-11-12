# Social PHONE // P43 integrated draft UI and protected host ingress boundary

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff:** External Hospital-compatible DOC, original PHONE scope. Live Hospital Room/Assignment/Session not verified.  
**Starting checkpoint:** P41b PR #1944 and P42 PR #1946 merged; issue #1885 open; C4b/Identity C3e/C5 owners have not supplied authenticated production trust.

## IMPLEMENTATION
This is a **single multi-part PHONE feature slice**, not another cryptographic fixture:
1. **Existing Social menu wiring:** The existing CONTACTS `PhoneContactDetail.qml` header EDIT button opens P42's real in-memory `PhonePersonalDraftEditor`. The action is called EDIT but its screen labels **PREVIEW ONLY / NOTHING IS SAVED OR SENT TO IPHONE**. It provides favorite ON/OFF, text note draft, clear/cancel and a visibly disabled SAVE with its current legitimate host blocker. The original P40 FAVORITE, EDIT NOTE, DELETE NOTE and EMAIL remain locked; CALL and MESSAGE continue using existing controlled flows.
2. **Lifecycle:** Editor opening requires a current selected card with a bounded ephemeral row ID, not a persisted person identity. Closing/cancel, contact replacement, snapshot revocation/identity switch, section switch or hiding PHONE removes the draft. There is no attempt to cache private notes locally.
3. **Future native ingress boundary:** `services/phone/PhonePersonalEditIngressP43.py` validates a compact untrusted UI intent with **exact fields only**, for LINK/FAVORITE/NOTE/UNLINK; it rejects caller-supplied consent, host identity, profile, nonce, revision or authorization fields. The result is an ephemeral, immutable untrusted object with privacy-safe `repr`; it cannot save. A genuine installed PHONE host must re-derive profile, contact, revision, challenge, P41b `editHmac`, C5 approval and process trust from its own independently authenticated sources.
4. **Checks:** New P43 adversarial backend/UI source tests, reruns of existing P40/P42 contact UI tests and P42 JS behaviors with dedicated GitHub CI.

**Known limitation:** The user can now explore a local draft (after this code is deployed by a separately authorized operator), but it is **not** a saved Favorite/Note. SAVE is hard false, not just visually disabled or dependent on a QML-forgeable permission. The P35 vault, P41a in-lock callback and P41b HMAC are not linked to QML. No QML export of a raw protected key or guessed device/contact trust.

## HOW TO USE
After eventual authorized code deployment: Social → PHONE → CONTACTS → select a contact → EDIT → preview a local Favorite or Note draft; CLEAR DRAFT and CANCEL discard it. **Do not use this as a private note store.** There is no real SAVE action yet and draft state is lost when leaving the selected contact.

## VERIFY
P43 tests must verify strict rejection of unknown client auth fields, invalid note/selector, cross-action extra values and private error leaks. UI checks must prove exact selection and visibility gates, P42 edit component mount, cancellation and discard behavior, preserved original CALL/MESSAGE and hard-false save. GitHub CI is source and behavior testing only, not a native Quickshell runtime or installed Fedora security proof.

## WATCH OUT FOR
C4b/Identity installed Gateway and C3e genuine independent challenge and rollback evidence remain unverified; C5 has not delivered a genuine PHONE per-action signed human approval. The current PhonePersonalEditIngressP43 parser is only **untrusted input normalization**: anyone could create such an object. Do not expose an IPC server that treats it as authorization. A future native save must bind to the current live user seat, installed process/SELinux/cgroup and hold one-use C5+C3e authorization through P35 encrypted commit/readback, including uncertain-fsync handling (P40R). Never expose P35 master keys, trust pins, plain text files or forged `SAVED` statuses in QML.

## CHECKLIST
- [x] Recheck owner work and both P41b/P42 merges.
- [x] Mount previously finished draft editor into actual Social PHONE CONTACTS detail.
- [x] Discard on context loss/revoke/selection switch.
- [x] Build strict, privacy-safe untrusted intent parser for future host boundary.
- [x] Update locked P40/P42 tests and add combined regression workflow.
- [ ] Verify exact PR-head CI and independent operator PR acceptance.
- [ ] Implement installed host service, protected keys, genuinely enrolled source+C5 receipt, external one-use ledger and P35 lease.
- [ ] Wire authenticated SAVE and sealed readback to UI, truthful final status.
- [ ] Native Fedora/Quickshell layout/security test with separate local-machine authorization.

## NEXT
Complete **one integrated protected save work package** after upstream owner evidence is real: host-side selected card/proof resolution, verified C3e/Identity challenge, genuine one-use C5 approval, protected key lookup, locked CAS commit with permission held to fsync/readback, correct failure and stale/revocation states. Bind that host's authenticated saved-state response into existing P43 UI. Maintain a separate owner review/merge gate and production activation decision.

## DECISIONS
Do not modify C3e/C4b/C5/Identity owned files. No live machine edits, Quickshell reload, installed service or production keyring use, PR merge or production metadata write. Operator is final authority. This source-level UI preview change is independently reversible through its PR.
