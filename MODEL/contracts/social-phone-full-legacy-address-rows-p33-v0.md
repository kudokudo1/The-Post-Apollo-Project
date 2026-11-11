# Social PHONE P33 // Full observed legacy phone/email rows and per-number call preparation

> STATE: GitHub-only draft for operator review; no local Quickshell deployment, installed-host test, phone call, production activation, or live Hospital registration claimed.
>
> PATIENT: \`kudokudo1/The-Post-Apollo-Project\`.
> ASSIGNMENT: Bounded extension of the existing PHONE → CONTACTS view and already approved \`contacts.read\` projection.
> WORKER: OPEN AI // CHATGPT external Hospital-compatible.
> ROOM / STAFF ROLE: no live Room, Session, role, or assignment ID verified; this document is a compatibility recovery pointer, not a Hospital ownership claim.

## IMPLEMENTATION

The installed operator BlueFerry 0.9.1 API (\`Messages1.ListContacts(uu)\`) provides every normalized phone number and email address in **the currently returned first-page record**. The P24 host was already reading both string arrays under the same one-shot \`contacts.read\` boundary but the P18a display mapper was dropping them, retaining only \`primary\`, \`phoneCount\` and \`emailCount\`. This work restores those arrays to the **current authorized in-memory card only**.

1. \`BlueFerrySocialProjection.py\` accepts legacy \`phone_numbers\` and \`email_addresses\` only as paired, bounded (64 each), count-matching lists of clean strings under the same profile and fresh per-read epoch. Reject mismatched, invalid, overlong, partial, or inconsistent primary values with content-free errors. Existing modern card pages that report counts only remain **unexpanded**, not artificially populated.
2. \`BlueFerryProjectionView.js\` revalidates array limits, counts, strings, primary match and a \`hasAddressDetails\` flag before passing the card to QML. Backward-compatible older snapshots with no detail keys are interpreted as **unavailable**, never falsely "zero numbers." Invalid replies fail the entire display validation. No new D-Bus method, provider API, storage, persistent identifiers or permissions are introduced.
3. \`PhoneContactDetail.qml\` displays each observed phone number in a read-only, selectable text field with adjacent **MAKE CALL**, followed by each observed email address in its own read-only field. All 0.9.1 phone and email labels are **UNLABELED** because the installed provider does not provide mobile/work/home/fax/Apple Watch labels.
4. \`PhonePane.qml\` rechecks that a row's number still exists in the **currently selected authorized contact card** (not a saved contact ID or an SMS conversation) and is dialable in the existing format, then fills the established PHONE → CALLS input. It clears prior confirmation and requires the existing **REVIEW OUTGOING CALL → CONFIRM CALL** actions and READY prerequisite before an actual call is attempted. This new function does **not** invoke \`requestCallAction\`, \`phoneCallsActionProcess\`, or a provider.
5. Existing four-line MESSAGES previews, fixed search, A–Z dividers, contact selection/revocation, calls setup, shared Social components and saved Personal preference all remain unchanged.

## WATCH OUT FOR

- 0.9.1 exposes the first **up to 100 contact cards** through this Post Apollo read port. A contact outside that first page is not fetched, and there is no claim that all iPhone contacts are loaded.
- \`hasAddressDetails: false\` is **counts-only** (modern card or older snapshot), not proof that the contact has no addresses.
- Ephemeral \`legacy-row-N\` IDs still change across reads and are only used to select currently loaded cards; no IDs, numbers or emails are persisted or used as contact identities, routing authorities or SMS recipients. The selected number itself is passed into the existing explicit human-reviewed CALLS dialer only.
- BlueFerry's phone audio and calling remain experimental and device-host readiness remains separate.
- The P21 remembered-consent path is same-user local preference, **not** cryptographic app-session grant authority. This change expands display of data already returned under \`contacts.read\` but does not claim stronger security properties.
- Future user-edited labels, iPhone contact writes, Favorites, Notes, FaceTime, automatic email composition, real SMS send and true backend phone blocking are not part of P33.

## VERIFY

- \`test_blueferry_legacy_contacts.py\` asserts complete per-read legacy arrays, fresh IDs and omitted provider labels.
- New \`test_blueferry_full_legacy_addresses.py\` exercises actual pure Python normalization + the exact QML JS validator through a Node VM with synthetic records, including malformed/forged/mismatched arrays, modern counts-only fallback and existing REVIEW/CONFIRM call gates.
- All original PHONE read-only menu, Personal revoke, identity, calling, integration, and search tests remain in CI.
- No live iPhone data should be printed into CI, logs, PR comments or screenshots. Current user runtime and actual calls are not yet verified.

## HOW TO USE

After separate operator-approved merge and local deployment, open Social → PHONE → CONTACTS with the previously granted \`contacts.read\` Personal preference. Select a card with multiple numbers. The currently observed numbers and email addresses appear in read-only rows. Click **MAKE CALL** beside a valid number to open PHONE → CALLS with that number already filled. The user must still select **REVIEW OUTGOING CALL** and then **CONFIRM CALL** after readiness checks.

A modern provider that only returns counts instead shows a clear "not available in this snapshot" message, rather than inventing numbers or labels.

## CHECKLIST

- [x] Recheck canonical AGENTS and Hospital protocol, GitHub HEAD and overlapping PRs.
- [x] Extend exact, bounded legacy contact read projection with no new provider operation.
- [x] Validate array details twice, preserving Personal consent and epoch.
- [x] Render number/email rows without editing data.
- [x] Route MAKE CALL to confirmation only, without automatic dialing.
- [x] Add explicit tests and existing CI routing.
- [ ] Verify the draft head's CI.
- [ ] Operator review/merge.
- [ ] Separately authorized installed Sway/Quickshell deployment.
- [ ] Actual visual, permission-revocation and non-emergency calling test.

## NEXT

Review the PR and exact-head CI. Once separately deployed, verify a synthetic or privacy-respecting multi-number contact locally, confirm that selecting each MAKE CALL fills exactly the chosen number, and verify that no call is placed before the two existing confirmations. The following independent assignment should handle stable contact identity/local labels and then Favorites/Notes storage; do **not** persist ephemeral BlueFerry IDs.

## DECISIONS

Only observed, already-consented legacy address arrays are displayed; no number type is guessed. PHONE keeps separate provider transport and CALLS approval boundaries, with no native phone configuration, connection, package, D-Bus, contact storage, or local host mutation.
