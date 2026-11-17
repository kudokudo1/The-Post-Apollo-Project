# Social PHONE // iPhone-only FaceTime pilot V1

**Patient:** kudokudo1/The-Post-Apollo-Project  
**Provider/role:** OPEN AI // CHATGPT, external Hospital-compatible DOC. No verified live Hospital Room, Assignment, Patient lock or Session.  
**User decision:** iPhone only. No Mac. The target is true PC-side **start / incoming / answer / hang up / two-way audio / video** for the existing FaceTime PHONE menu. A browser link alone is *not* the requested solution.  
**Work permission:** operator's "ok lets go" to pursue the first iPhone-only feasibility milestone, bounded review-branch code only. No local-machine writes, iPhone pairing/configuration, remote call action, installing apps, Apple login, merge or production activation.  
**Base:** current main at branch creation `13933e78e861dbe9c1af001c55bee4451054f185`; PRs #1998 (link handoff), #2003 (HFP probe), #2009 (partial call-state status) already merged. Issue #1999 is the open real-device acceptance thread.

## IMPLEMENTATION

Added `services/phone/PhoneFaceTimeIphonePilot.py`, a one-shot `--preflight` helper that *only* calls the existing read-only BlueFerry `PhoneAudioControls.inspect`, its already-running unique-owner GetStatus reader, and the existing read-only `PhoneFaceTimeAudioRouteProbe.inspect`. It is not a new FaceTime transport, browser tab, iPhone app or cloud API.

- Projects only **BlueFerry status observed**, its exact cellular call preference OFF/ON/UNKNOWN, **MAP/PBAP link self-report** (not authenticated phone identity), presence of the **notification-app inventory capability marker** `notification_muted_app_count` (not a FaceTime notification), and local **HFP profile offered/active** (not the iPhone's audio route).
- Never reads `ListNotifications`, `ListNotificationApps`, contacts, call lists, video or microphone; never outputs app IDs, phone numbers, MACs, raw D-Bus JSON, app histories or account details. It makes no network, Bluetooth or audio mutation.
- Every result forces **outboundIphoneShortcutVerified=false, outboundPcDispatchAvailable=false, incomingFaceTimeDetected=false, answerFaceTimeAvailable=false, endFaceTimeAvailable=false, liveFaceTimeVideoAvailable=false, twoWayFaceTimeAudioVerified=false, iphoneCompanionAuthenticated=false, faceTimeConnected=false, canChangeRoute=false, contentAccessEnabled=false, personalSaveAuthorized=false**.
- The shared existing `PhoneFaceTimeHandoff.qml` now offers **CHECK IPHONE SUPPORT** on both FT AUDIO and FT VIDEO. Only explicit click invokes the fixed `--preflight` command. It refuses unfamiliar status/schema/booleans and any non-false authority fields. It clears stale data and cancels the pending process on contact, mode or view loss. It never adds a fake "Dial", "Answer" or "End" control.
- Corrected the existing FT Audio HFP probe for the now verified live case: BlueFerry GetStatus `calls_enabled=false` intentionally does **not** include `calls_state` (official upstream `CallsController.snapshot()`). The UI now reports **CALLS ON PC IS OFF**, not "call state unreported." That setting is **cellular HFP only** and is not the FaceTime session status. This code does not enable calling.
- The original Apple HTTPS invite two-step review, copy-only Apple-device `facetime:` and `facetime-audio:` schemes, Bluetooth HFP probe, one-use Phone trust boundaries, and hard-disabled protected Favorites/Notes SAVE are unchanged.

## HOW TO USE

**After operator-authorized merge AND separately approved desktop deployment**, Social → PHONE → CALLS → FT AUDIO (or FT VIDEO), or CONTACTS → selected person → FT AUDIO/VIDEO. Click **CHECK IPHONE SUPPORT**. The output distinguishes a responding provider and optional Bluetooth/notification prerequisites. It never reports a connected FaceTime call.

**Real iPhone trials, with consenting non-emergency participants and no automated outbound call:**

1. **Outgoing by phone number:** On the iPhone, create a local Shortcut using Apple's FaceTime action for a known, consenting contact, or a user-reviewed FaceTime URL scheme. Test the Shortcut *on the iPhone first* and record whether it opens a genuine FaceTime Audio/Video call. Apple's documented Shortcuts URL schemes do not provide Linux with an authenticated remote-dispatch endpoint. A future iPhone companion must prove its own consent, receipt and call-start acknowledgment before any PC Dial control exists.
2. **Incoming detection:** Have that participant place a normal FaceTime call to the iPhone, while ordinary already-authorized BlueFerry notifications are enabled. Check *whether a FaceTime notification actually reaches* the existing Social PHONE notification surface. The optional BlueFerry notification-app inventory capability is **not** evidence that an incoming call is detected, identifies a caller, or has valid remote Answer/Decline actions. Do not start reading notification bodies or private app IDs in this pilot.
3. **Two-way FaceTime Audio:** During that user-initiated FaceTime Audio call, use the iPhone's own audio picker. If the PC/Bluetooth destination is offered, select it manually and confirm both microphone and speaker with the participant. The local `pactl` HFP-profile observation may belong to another device or oFono; an active profile never becomes FaceTime media proof.
4. **Live video / PC webcam:** No FaceTime video transport is exposed by BlueFerry or the read-only pilot. Investigating iOS streaming/capture APIs, system-protected video limitations and a user-consented companion is a **separate owner/permissions/implementation boundary**. No FaceTime video frames, camera, screen or audio are captured here.

### iPhone remote-control feasibility

Apple's official Shortcuts docs include a FaceTime action and FaceTime URL schemes, and iPhone can initiate by number (https://support.apple.com/guide/shortcuts/navigate-the-action-list-apdc33e4f4da/ios, https://support.apple.com/en-euro/guide/shortcuts/apd621a1ad7a/ios). These establish **local iPhone invocation**, not a PC-to-iPhone command channel, remote control, background dispatch, or successful call in this user's environment.

CallKit supports integrations for **the app's own VoIP service**, not an authenticated API to manage Apple's native FaceTime sessions from Linux (https://developer.apple.com/documentation/callkit). FaceTime links allow browser participants to join invited calls, not direct incoming ringing from an iPhone account (https://support.apple.com/en-bh/109364). Do not invent those capabilities or use automation to call without clear user confirmation.

## VERIFY

- `tests/phone/test_phone_facetime_iphone_only_pilot.py`: actual BlueFerry typed projection with the user's observed `calls_enabled=false` + intentionally absent `calls_state`, provider spoof/partial failure, notification inventory marker vs FaceTime-specific notification, trusted false booleans, invalid HFP/or false HFP authority, timeout/error payload suppression and strict `--preflight` CLI.
- `tests/messaging/test_social_phone_facetime_iphone_only_pilot_ui.py`: the new exact in-menu action, validation and denial flags, canceled stale process, existing FaceTime invite and PHONE provider lock behavior.
- Updated `tests/phone/test_phone_facetime_audio_route_v2.py` to distinguish upstream disabled-calls omission from unreported call state.
- New `.github/workflows/social-phone-facetime-iphone-only-pilot.yml` runs these tests plus V1 FaceTime link abuse, V2 HFP probe and protected PHONE regressions. Other inherited PR workflows may run separately.
- **CI passing only verifies static source/projection/test behavior. It does not verify the physical iPhone, remote launch, incoming calls, microphone, speakers, webcam or live QML rendering.**

## WATCH OUT FOR

"iPhone-only" does **not** imply we have a supported Apple FaceTime remote-answer/remote-hangup interface. A third-party iPhone companion may be able to request an on-device FaceTime action with confirmation, but must prove the platform permits it; it cannot assume CallKit authority over FaceTime. Remote iPhone-only PC video is not promised by this code.

No relay server, Apple Push/APNs account, Shortcuts automation, credentials, C5 consent, organization grant, background process, Bluetooth pairing, audio routing change, QML reload or host activation was configured. No customer phone data is included in tests. No two-way streaming or real call media was accessed.

## CHECKLIST

- [x] Re-read canonical Syntagma AGENTS + Hospital authority/continuity protocols; recheck main and FaceTime PRs.
- [x] Verify upstream BlueFerry's calls_enabled=false => calls_state absent contract.
- [x] Recheck current Apple Shortcuts, FaceTime and CallKit public documentation.
- [x] Add a sanitized, explicit-only preflight in PHONE with refusal of false FaceTime authority.
- [x] Correct intentional cellular calling OFF UI wording without enabling service.
- [x] Add adversarial tests and dedicated CI workflow.
- [ ] Verify exact-head CI and independent review; operator authorizes merge separately.
- [ ] Operator-authorized desktop update/visual verification.
- [ ] iPhone-only physical trials of native Shortcuts initiation, incoming notification behavior, two-way audio; record only outcomes without private contacts/call media.
- [ ] Decide whether a real authenticated iPhone companion or supported remote command path exists. If not, report an architectural blocker rather than faking full FaceTime.
- [ ] Separate owner/permission negotiation before implementing push/stream/control protocol and video.

## NEXT

Verify exact-head CI, review. After merge and separate desktop update approval, run the three iPhone trials. If native Shortcuts-by-number succeeds, design a consent-gated, authenticated transport with the **iPhone-side application** and a verified call acknowledgment; never mistake mere URL generation, request receipt or local HFP as successful dialing. Independently establish incoming-call observability before building Answer/End; video streaming requires separate source/permission feasibility.

## DECISIONS

External Hospital-compatible PHONE DOC in PHONE-owned files; no live Hospital registration or role escalation. Existing user desire for **full start/receive/answer/end/audio/video on Fedora with iPhone only** is preserved as target, not falsely reported as implemented. No Mac, no invitation-link-only substitution, no production activation, no local or iPhone changes. Final acceptance stays with operator.
