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

---

## Hospital Camera checkpoint // Zoom direct open + status stabilization (2026-11-05)

### IMPLEMENTATION
- PR #1302: Native Zoom may be registered as `FLATPAK RUNNING` without a Sway window. Keep automatic launch-on-entry but expose a prominent **OPEN / FOCUS ZOOM APP** action whenever installed, even when the process is present but window absent.
- Backend `zoom-activate` focuses an exact Sway Zoom window by observed positive numeric container ID, on explicit operator click only; otherwise it requests a native/system/user Flatpak launch. No automatic focus changes on mode entry and no meeting or login is fabricated.
- Previously the Internet and Zoom HTTPS status fields refreshed every 90 seconds and used `UNREACHABLE` after just one HEAD failure. They now reflect a single entry-time snapshot with neutral `UNVERIFIED` on a failed probe, not a supposed outage. No repeated background network probes.
- Zoom is still a provider-owned native window. Social aliases and Camera indicators are not Zoom login tokens; the operator must sign in inside Zoom and choose **New Meeting** or **Join**.

### HOW TO USE
After native deployment: Camera → ZOOM (attempt automatic start). Press **OPEN / FOCUS ZOOM APP** if there is no visible Zoom window, including when Camera says its Flatpak process is running. Complete sign-in and meeting controls in the Zoom client, not the Camera shell. The Internet and Zoom probe status is a one-time snapshot.

### VERIFY
- Exact-head GitHub CI passed for Camera, Grammar, Tasks on source commit `bf12e8b5b6a5f8cf4d39a380f2a7d8f40ed12042`; mock tests verify precise Sway focus, no title spoofing, explicit launch, missing package handling and neutral connectivity failures.
- No operator desktop Sway launch/window observation performed; a healthy process or successful `flatpak run` command is not proof of a visible conferencing surface.
- Historical operator screenshot showed `FLATPAK RUNNING // WINDOW NOT DETECTED` and network indicators oscillating. Public Fedora/Zoom Wayland reports document similar no-window symptoms; no local root cause has been proven.

### WATCH OUT FOR
- This PR does not embed Zoom, sign the operator in, or issue New Meeting/Join API calls. True in-widget conferencing is gated by Stage Director or supported SDK and central Connections broker authorization. Do not claim M4 complete.
- Manual focus targets a Sway class/app-ID matched window; compositor window metadata is not an authentication guarantee. Focus is a user-triggered convenience only.
- One HTTPS failure is classified UNVERIFIED, not offline. Network check is a point-in-time browser-like reachability sample, not a complete health or Zoom API status.

### CHECKLIST
- [x] Direct open/focus when installed even with background Flatpak but no window
- [x] Stop periodic internet indicator flicker
- [x] Preserve Social login-independent Zoom mode and download setup
- [x] Source CI regression tests
- [ ] Native window visibility and usability verification on Fedora
- [ ] Provider-authenticated login and new/join meeting controls
- [ ] Secure Stage Director / SDK embedded video meeting runtime
- [ ] Operator final acceptance

### NEXT
Use a native Fedora session to click OPEN / FOCUS, observe whether a Zoom window becomes visible, and read only targeted application start logs if it remains background-only. Coordinate full meeting and sign-in work with Connections/Identity Center and Stage Director owners.

### DECISIONS
Source-only draft PR, no merge, Quickshell reload, package change, portal restart, network permission change, Zoom login or live desktop modifications. External Hospital-compatible scope, not live registration.
