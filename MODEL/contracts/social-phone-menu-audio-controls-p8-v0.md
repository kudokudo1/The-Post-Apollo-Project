# Social PHONE P8 // In-menu iPhone audio routing and guarded calls switch

> **STATE //** GitHub repository review candidate; no live audio activation or desktop testing by this worker.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation / P8
> **STAFF //** External Hospital-compatible DOC; live Hospital registration not verified.
> **OPERATOR DIRECTION //** 2026-11-04: Stop sending terminal commands to end users for stream routing. Put the controls inside Social PHONE. Do not make the developer's own paired iPhone and BlueFerry installation the default connection for every Post-Apollo download.

## IMPLEMENTATION

Add two compact controls inside the **existing Social → PHONE → DEVICE** menu, beneath BlueFerry's saved-configuration state:

1. **iPhone media destination:** IPHONE / COMPUTER / AUTO. These request BlueFerry's existing, per-selected-iPhone `audio phone`, `audio pc`, `audio auto` preferences. No extra Post-Apollo routing database or global default.
2. **CALLS ON PC: ON/OFF.** The user can explicitly request BlueFerry's saved `calls enable` or `calls disable` preference. Enabling is blocked when the oFono service is not running, and the UI distinguishes *saved call preference* from actual HFP status. Missing oFono, D-Bus permissions, a suitable WirePlumber HFP backend, or a conflicting BlueZ plugin can still prevent working calls; this setting does **not** install/configure those services.

For a practical **calls only** setup, the user selects **IPHONE** for ordinary media and **CALLS ON PC: ON** for hands-free calls if supported. This is profile-based routing, not sampling, classifying, filtering or retaining audio content. iPhone notifications may still choose other Bluetooth routes or be affected by OS settings; do not promise a perfect per-notification filter.

`services/phone/PhoneAudioControls.py` provides an exact, allowlisted opt-in host boundary:
- `--status` reads only the already-active BlueFerry D-Bus service, addressed through its **unique owner**, and returns a strict sanitized projection of only media preference/route and calls enabled/state. No phone address, number, contact, message or private error is returned; the service is never D-Bus activated.
- `--set media phone|pc|auto` and `--set calls enable|disable` execute only an absolute installed `blueferry` CLI using fixed argv, no shell, after verified local config, already-running service, and read-only status. Enabling calls also requires active oFono. All execution is caused by the explicit menu click, never by opening the PHONE menu or checking status.
- The helper rereads the provider's saved preference after the command. It reports **PREFERENCE_SAVED** only if that preference matches the requested value, not merely because a command returned zero. This status still does NOT imply call-audio readiness, authenticated Social phone connection or message access. All errors are redacted and fail closed.
- BlueFerry owns persistent per-phone audio routing in its own settings store; callers are disabled by default unless explicitly configured by this user/provider. No Post-Apollo-wide, organization-wide, or install-time phone/audio defaults.
- The audio section is hidden while the Stage Director's foot terminal occupies the PHONE feed bay so the existing embedded setup workflow retains its space and geometry.

The Social contacts/chat UI, provider chooser, Stage Director, Identity Center, Account Broker, existing message access and saved pairing mechanism remain unchanged. No extra permissions dashboard or terminal-specific user instructions are introduced.

## HOW TO USE

After authorized merge and deployment:

**Social → PHONE → CONNECT PHONE** loads the current configured BlueFerry status. In the PHONE DEVICE panel:

- Select **IPHONE**, **COMPUTER**, or **AUTO** under **IPHONE AUDIO** to change ordinary media routing.
- Use **CALLS ON PC: ON/OFF** to request the hands-free call preference, when BlueFerry/oFono readiness permits.
- For calls only on the PC, select IPHONE media and enable CALLS ON PC when supported.
- If the background service or prerequisite is missing, the control is disabled with an explanation. The existing device must not be forgotten/re-paired to make audio modes appear.

This is not a generic Android audio feature. Future providers should expose their own proven capabilities through a common menu, not silently borrow BlueFerry's iPhone-specific functionality.

## VERIFY

Automated tests:
- `tests/phone/test_phone_audio_controls.py`: strict content-free projection, no D-Bus autoactivation, preflight and oFono failure, fixed allowed commands, saved media/calls confirmation, malformed/fake actions, error redaction, no global store.
- `tests/messaging/test_social_phone_audio_controls.py`: existing PHONE menu and contact/feed reuse, single primary Connect Phone button, in-menu media and call controls, no automatic changes, selected/disabled states, preservation of Stage Director space and no false HFP promises.
- Existing BlueFerry, Phone and Stage Director suites via `.github/workflows/social-phone-one-action-setup.yml`.

No real iPhone, PipeWire, WirePlumber, oFono, Sway, or Fedora runtime was touched or tested by this worker. GitHub CI cannot verify actual Bluetooth audio profiles. A successful menu preference change is not proof a call route works until tested.

## WATCH OUT FOR

- Upstream BlueFerry documentation: the **first explicit media route choice** may install a per-phone WirePlumber rule and briefly **restart WirePlumber**, interrupting other Bluetooth audio. The menu warns about this. The worker does not make that choice on the operator's machine.
- BlueFerry HFP calling is experimental and requires oFono running, system D-Bus authority, appropriate WirePlumber HFP ownership and non-conflicting BlueZ plugin. This PR checks the active oFono service before offering ON, but cannot configure/validate every host prerequisite. A stored ON is **not** synonymous with READY.
- BlueFerry itself owns settings.json and per-selected-phone state. No universal iPhone MAC, default pairing, auto-installed audio mode, or user-specific developer settings ship to other people's installations. Users lacking BlueFerry see unavailable controls, not an implicit installation.
- This is an opt-in host audio action on a menu click. Under Hospital rules, developer/test worker has made **no local machine changes**. Real host prerequisite repairs, package installs, D-Bus policy or audio-service changes require separate explicit operator approval and the assigned audio/Phone Bridge owner.
- The actual authenticated Social SMS/iMessage/contact link remains separate Gate A work. Do not infer permission from audio state or turn a call preference into a content grant.
- Emergency calls remain on the iPhone.

Upstream verification: `erikwb/blueferry` `docs/en/user/phone-audio.md`, `docs/en/user/calls.md`, `src/blueferry/cli_audio.py`, `src/blueferry/cli_calls.py` as read 2026-11-04.

## CHECKLIST

- [x] Recheck current main, P7 merged state and open PR ownership.
- [x] Confirm upstream BlueFerry per-phone media preference, call preference and OS prerequisites.
- [x] Add content-free, unique-owner status/explicit fixed-argv audio action boundary.
- [x] Add compact media and call preferences in the existing PHONE menu without terminal instructions.
- [x] Keep call ON guarded and media route/call state separate.
- [x] Avoid per-installation default, new device store and Stage Director regression.
- [x] Add unit and QML tests with CI workflow.
- [ ] Exact-head CI and mergeability review.
- [ ] Shared Social/Phone and OS audio owner review, operator-authorized merge.
- [ ] Live Fedora first-change WirePlumber behavior, iPhone playback and HFP incoming-call verification.
- [ ] Actual Social protected-content bridge under separate Gate A ownership.
- [ ] Final operator acceptance.

## NEXT

Review CI; then, in an authorized Fedora session, verify the user's actual BlueFerry selected device, oFono, HFP backend and per-phone preference responses. Use one explicit UI action to test IPHONE media routing, then separately test supported calls with a non-emergency test call. Any missing system prerequisites must be handled as a scoped host change with operator consent, not an automatic install.

## DECISIONS

PHONE audio controls live inside Social and invoke provider-specific capabilities on a deliberate click. BlueFerry's pairing and audio settings remain its own, per selected device. Post-Apollo must not ship the developer's pairing, notification sharing, or calls/media preferences to other installs. Keep one primary Connect Phone action, small ordinary settings, no new security vault and no terminal requirement for end users. No local changes, merge, production activation or live Hospital registration by this worker. Roll back by closing the draft or reverting isolated changes after any later authorized merge; final DONE belongs to the operator.
