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

## HOSPITAL // Camera M4d Zoom Web App guest prototype · 2026-11-05

### IMPLEMENTATION
- [PR #1320](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1320) experiments with the same *mechanism* used by Social X/Instagram: a real managed Chromium XWayland app window, not a web view rendered by Quickshell. Here the provider URL is Zoom's official `https://app.zoom.us/wc`, which supplies its own sign-in/Join/New Meeting interface.
- New `scripts/camera/ZoomWebHost.py` reuses Social's read-only Chromium browser selection policy while keeping a separate Camera-owned, identity-labelled private profile. It checks Sway output bounds, unique WM_CLASS, same-UID process lineage with exact browser-profile argv, and post-move window geometry. Only after an exact dock match does Camera enable a transparent viewport and a nested input-region cutout.
- Entering Zoom starts the managed Web App instead of native Zoom. Leaving Zoom/closing Camera removes the input hole before requesting scratchpad hide. A manually selected native Zoom option remains a fallback when the experimental web host fails.
- The Camera header retains DOWNLOAD, size, and close controls while the hosted browser fills the page. Camera relinquishes layer-shell keyboard focus when the browser dock is verified so the browser can receive login/meeting input.

### HOW TO USE
**Source-only experimental draft. Do not merge or deploy until native acceptance.** After an approved isolated Quickshell/Sway trial, click Camera → Zoom. The Zoom Web App should appear inside Camera's page, offering its actual login or Join/New Meeting controls. Other Camera modes should hide but not log out the browser. Zoom's native Flatpak installation is no longer required for the web path.

### VERIFY
- Offline GitHub CI includes mock tests for untrusted/ambiguous browser classes, private profiles, output bounds, bounded geometry convergence, Sway scratchpad teardown, closed-by-default input mask, and no forced native Zoom launch.
- Native SwayPX/Quickshell validation is NOT complete: verify actual panel global coordinates, compositor stacking/alpha, cutout geometry, browser keyboard/focus/popup capture, browser device permissions, and resilience across move/resize/output changes before acceptance.

### WATCH OUT FOR
- This is compositor-adjacent code in a draft. A matching XWayland class and profile ancestry are not a substitute for Stage Director's future trusted actor-origin/session controls; do not treat the prototype as certified security containment.
- Zoom Web is a different session from Zoom's installed Flatpak. Browser-managed Zoom login cookies are not copied into Social and Social account aliases do not grant Zoom access.
- Starting or joining meetings needs provider permission and the operator's deliberate Zoom UI clicks; camera/mic and screen share prompts must not be silently accepted.
- Avoid browser/Quickshell/Sway installation, permissions or live restarts until separately approved. Existing user's local `main` has uncommitted work.

### CHECKLIST
- [x] Confirm Social X/Instagram hosting uses Chromium + Sway docking, not QtWebEngine
- [x] Official Zoom Web App URL and supported login/join/new-meeting path verified
- [x] Source-only independent browser actor and Camera host prototype
- [x] Fail-closed geometry and input mask contracts
- [ ] Exact-head GitHub CI / native preview verification
- [ ] Sway global position, keyboard focus, popup/resize/multi-monitor acceptance
- [ ] Central Social/Connections provider authorization and identity switching
- [ ] Operator acceptance

### NEXT
After CI, run an isolated native desktop test with temporary browser profile and no production activation; record exact Sway actor identity, rect and Camera bay. If the geometry is not verified, preserve the closed input hole and do not automatically loosen it. Hand off Stage Director's compositor trust boundary to its owning worker.

### DECISIONS
External Hospital-compatible Camera worker, source-only; no live Hospital registration, repository merge, package install, browser launch on user's actual desktop, Quickshell reload or Sway configuration change.
