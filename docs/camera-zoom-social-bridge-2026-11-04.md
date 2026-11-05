# CAMERA // Zoom mode and Social account handoff

**Patient:** `The-Post-Apollo-Project`  
**Room:** Camera Zoom meeting integration  
**Assignment:** Add a separate Camera Zoom mode and reuse Social identity/account-name metadata without inventing sign-in state.  
**Connection:** External Hospital-compatible source-only work; no live registration or local activation.

## IMPLEMENTATION

- `widgets/CameraW.qml` adds a fourth **ZOOM** mode to the existing Camera capture/gallery/cleanup tabs. It reads the canonical `SocialIdentityStore.snapshot.activeId` and `SocialAccountDetailsStore.accountNamesFor(identityId, "zoom")`. Zoom names update under the same Social account data file, rather than creating a Camera account database.
- `services/social/SocialAccountDetails.py` authorizes exactly one external metadata label provider, `zoom`, in the same existing owner-only, revision-controlled Social store. The existing 32 messaging selector IDs are unchanged.
- `widgets/messanger/AppSelector.qml` adds **ZOOM // MANAGE ACCOUNT NAMES** to the existing Social Account Names editor, after its existing messaging app picker. Add/rename/reorder/remove still use the existing private storage and confirmation controls.
- `scripts/camera/camera_cli.py` exposes `zoom-status` (read-only native/Flatpak client check) and `zoom-open` (explicit launch only). It does not use a browser fallback, spawn daemons, copy Social cookies or pass any credential/token to Zoom.
- Tests validate account label isolation, unknown service refusal, unchanged 32 Social rail apps, local client discovery, explicit no-shell launch and unknown authentication.

## HOW TO USE

After native validation and operator-approved deployment:

1. Social → USER // SETTINGS → ACCOUNT NAMES → ZOOM // MANAGE ACCOUNT NAMES. Save an alias under the desired Social identity.
2. Camera → ZOOM. The active Social identity and those Zoom aliases will be displayed. Selecting an alias changes only the Camera selection label, **not the signed-in Zoom account**.
3. Camera → CHECK ZOOM → OPEN ZOOM CLIENT. Sign in, start or join a meeting in Zoom's official native desktop client.

## VERIFY

Required before merging/activating: exact-head CI, native Quickshell/QML startup and tab layout, Social alias save/reload/isolation, actual Fedora native/Flatpak Zoom launch, webcam/mic permission flow and cross-widget coexistence.

## WATCH OUT FOR

**NOT IMPLEMENTED:** authenticated Zoom account connection, Zoom OAuth, session switching, meeting list, schedule, conference media inside the Camera panel, recording Zoom calls, Zoom phone, or host privileges. The currently installed Social Account Names feature is **metadata**, not an authentication broker. The wider ConnectionsBroker in CPU++ still forbids production credential grants in current source. Never infer authorization from selected Social identity or nickname.

The Zoom Linux Meeting SDK is a separate CLI-oriented provider integration and needs developer app credentials, SDK authorization, authorized Zoom account scopes, supported Linux version, licensed flows, host/provider consent and native tests before it can power a real in-widget meeting. Stage Director might eventually contain the meeting client window, but visible containment is not yet implemented by this PR. Zoom's official OAuth general-app flow supports desktop PKCE, but the login consent and token vault must be created by the centrally owned Account Broker/Identity Center, never by Camera or the Social alias store.

## CHECKLIST

- [x] Four Camera modes remain independent
- [x] Reuse Social identity and label storage, no Camera credential database
- [x] Preserve 32 Social messaging selector entries
- [x] Native/Flatpak Zoom client detection and explicit launch
- [x] No silent webcam/microphone capture, Zoom recording, browser navigation or OAuth login
- [ ] Exact-head CI and native UI verification
- [ ] Social Account Broker/Identity Center Zoom provider authorization contract
- [ ] SDK/Stage Director feasibility and provider-governed embedded call proof
- [ ] Operator acceptance

## NEXT

1. Integrate an approved Zoom OAuth PKCE provider into the centrally owned Accounts/Connections broker. Verify scoped grants and explicit identity/session switching with test credentials.
2. Add authorized status, start/join/schedule actions in Camera only after broker APIs and Zoom Marketplace permissions are verified.
3. Prototype actual in-panel video with the Zoom Linux SDK or a verified Stage Director-hosted surface; do not call an external window embedded.
4. Native microphone, camera and screen-sharing consent controls, recording permission and call lifecycle tests.

## DECISIONS

Account alias records do not carry token or login state. User must deliberately open native Zoom. The current source-only implementation does **not** claim Zoom is installed, authenticated, embedded or deployed on Fedora. No local machine writes, Quickshell restart, user login, PR merge or production activation were performed.
