# Identity Center // Social USER // SETTINGS navigation seam v0

> **STATE:** UI foundation only, no enterprise authentication/organizations backend connected. Review branch; no desktop installation or runtime acceptance.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator requested reuse of the *existing* Social USER // SETTINGS workspace, not another permanent menu/window. Implementation direction confirmed before this bounded repo slice.
>
> **SCOPE:** `widgets/messanger/IdentityCenterSettingsSections.qml` (new), small anchor/state changes to `widgets/messanger/AppSelector.qml`, isolated contract test and workflow. `MessagingW.qml` and all Social backends remain untouched.
>
> **HOSPITAL:** External browser ChatGPT, Hospital-compatible; no verified live Room, Staff Role, Session attachment or ownership lease.
>
> **VERIFICATION:** GitHub source-contract CI required on exact head; Wayland/Quickshell interactive appearance and UX require separate operator acceptance.

## UI structure

**Existing entry path:** Social selector rail → **USER // SETTINGS**. This remains the only persistent entry. There is still exactly one Social FloatingWindow and the same workspace parent/geometry.

Inside the already-existing right-hand settings workspace:

- The fixed **USER // SETTINGS** header and footer button are preserved.
- Below that header is a horizontally scrollable navigation strip, styled with the existing `ActionButton` component, with sections **PROFILE**, **ORGANIZATIONS**, **CONNECTED ACCOUNTS**, **SECURITY**, **SOCIAL LAYOUT**.
- **SOCIAL LAYOUT** remains the default on every settings open. Its unchanged original three editing columns (identities/account names, button families, app organization) appear below the strip. Existing session/browser/Telegram actions and layout store continue their original behavior; the new navigation does not invoke them.
- Other sections display read-only, clearly disconnected information. The **ORGANIZATIONS** section shows *ACTIVE ORGANIZATION // NONE VERIFIED* and a **disabled** *SWITCH ORGANIZATION // UNAVAILABLE* action. No fabricated portfolio/company list, current role, manager status, session or credentials.
- **PROFILE** explains that local `identity-N` Social labels are not authenticated persons; **CONNECTED ACCOUNTS** points users back to existing Social controls without pretending the broker exists; **SECURITY** accurately reports that enterprise session/passkey/MFA management is not connected.
- Navigation is local, ephemeral QML state only and is reset to Social Layout upon opening. It does not write to disk or issue requests.

## Why the organization switcher is disabled

The merged identity foundation currently contains offline prototype functions and a real **disposable Keycloak CI pilot**. There is **no** production service exposing verified tenant memberships and grants, no real user signing session, no stable employer principal mapping and no approved authority for real company data.

Therefore an interactive company switcher could otherwise falsely imply tenant access just because a button changes a label. The current UI deliberately does not allow that. This is a safe **wiring slot**, not an implemented authorization control.

When the backend has been designed and separately accepted, the future consumer should:

1. Verify the signed-in principal using a protected backend, never local Social `identity-N`.
2. Fetch the authorized portfolio/organization and role/scope **summary** for that principal, with no secrets or unauthorized company data.
3. Populate the switcher only from verified grants and show an explicit *unavailable/expired* state when a membership is revoked or the server cannot authenticate it.
4. Send active context selections to the trusted API on every privileged request. UI selection alone cannot confer authority.
5. Preserve Social's local profile and account-label editing. Provider account connections belong to the separately reviewed Account Broker and never inherit enterprise rights from a portfolio display.

## Offline verification

The new [CI workflow](../../.github/workflows/social-identity-center-settings-navigation.yml) runs:

```bash
python3 -m unittest discover -s tests/messaging -p 'test_social_user_settings_rail.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_social_settings_workspace.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_identity_center_settings_sections.py' -v
```

These source contracts ensure one existing window/footer/header, the five tabs, default Social Layout, original editor IDs and actions, disabled unavailable switcher, no new auth/credential storage code and preserved host keyboard navigation. They are **not** QML engine compilation, click testing, geometry screenshot verification or real sign-in.

## Rollback

Do not merge the review PR or revert the isolated new component + AppSelector anchors/state + tests/workflow/index/docs if needed. No migrations, local data edits, company account creation, logout or token revocation exist in this UI slice. Revert of the UI leaves the previously merged identity backend prototypes and real Keycloak CI pilot untouched.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Embedded in-place Identity Center section navigation and read-only truthful placeholders within Social USER // SETTINGS. Preserved original Social Layout editing UI.

### HOW TO USE
When deployed in a separately accepted desktop build: open Social → USER // SETTINGS → choose a section. SOCIAL LAYOUT continues existing identity/account/family editing. ORGANIZATIONS shows no connected tenants until a trusted API exists.

### VERIFY
Confirm exact-commit GitHub CI, then separately inspect live Quickshell rendering, mouse/keyboard focus, horizontal nav scrolling at narrow widths, Settings close/reopen reset and existing Social provider behavior.

### WATCH OUT FOR
No backend, IdP session or actual business-org data is connected. **Do not** populate fake family LLC/nonprofit names as actual memberships or store enterprise permission in SocialIdentityStore. No second floating window or live modification.

### CHECKLIST
- [x] Current main, active PRs and Syntagma/Hospital entry protocols inspected
- [x] New UI sections built within original Settings workspace
- [x] Original Social editors retained and default selection preserved
- [x] Disabled org switcher and truthful not-connected states
- [x] Targeted static regression tests and CI workflow authored
- [ ] Exact PR-head CI success and independent review
- [ ] Live desktop/keyboard/geometry testing by authorized operator
- [ ] Trusted backend membership contract and security review
- [ ] Operator final acceptance / merge authorization

### NEXT
Verify CI; get UI review/acceptance; design minimum read-only, authenticated `GET /me/context`-style tenant summary contract with the Identity Center backend owner; wire only after trusted API and operator approval.

### DECISIONS
The existing Social USER // SETTINGS screen is the intended first desktop entry, with a portable section concept for other Post-Apollo apps. The enterprise organization switcher is **not live**. No chosen production IdP, stored company user, backend service, deployment or desktop installation.
