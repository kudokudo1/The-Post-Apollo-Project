# Social PHONE // FaceTime Audio V2 local HFP route observation

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff:** External Hospital-compatible PHONE DOC. Live Hospital Room/Assignment/Session, patient lock and accepted worker identity have **not** been technically verified.  
**Assignment:** Explicit continuation of operator-approved FaceTime Audio/Video addition to the existing PHONE menu; observe *whether a candidate Bluetooth hands-free audio path exists*, not initiate, receive or control Apple FaceTime.  
**Base:** current main `b837a9fcb6f1a6b7157b7551601dc1514f8dd437` on November 17, 2026. V1 [PR #1998](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1998) merged and seven PR checks passed before V2. [Issue #1999](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1999) owns the later real phone + audio-route acceptance. This code is new PHONE-owned helper, panel update, tests, docs and CI only.

## IMPLEMENTATION

- `services/phone/PhoneFaceTimeAudioRouteProbe.py`: a fixed, explicit `--status` **read-only** helper. It reads the already-existing `PhoneAudioControls.inspect()` BlueFerry status (GetStatus via already-running unique D-Bus owner, no pairing or provider activation), plus at most one bounded `pactl -f json list cards` observation of local PulseAudio-compatible/PipeWire Bluetooth card profiles. It sets `PULSE_NO_AUTOSPAWN=1` and 4-second subprocess timeout, uses no shell, exposes no device MAC/name, processes, source microphone/sink contents, contact numbers, FaceTime invite tokens or raw provider JSON.
- It recognizes **only profile labels** consistent with Bluetooth HFP/headset, including mSBC, on cards named `bluez_card.*` carrying BlueZ/Bluetooth properties. Distinguishes no profile, profile available-but-not-selected, and a profile actively selected *somewhere on this PC*. A2DP playback, a non-Bluetooth ALSA headset and a merely paired Bluetooth device do not count as an active hands-free profile.
- Separately reports whether **BlueFerry says its cellular hands-free path is ready** and **oFono is active**; it does not infer an iPhone's FaceTime session, Apple account or audio session ownership from any provider report. A system HFP profile might belong to a different Bluetooth device, and a working oFono link may not appear in PulseAudio card listings.
- The output is a fixed categorical schema `post-apollo.phone.facetime-audio-route.v1` with observed bools only. **Every response always sets `faceTimeAudioVerified=false`, `faceTimeConnected=false`, `faceTimeCallControl=false`, `microphoneVerified=false`, `speakerVerified=false`, `providerAuthenticated=false`, `personalDataAccess=false`, `canChangeRoute=false`.** It does not persist actual-connection badges or synthesize a source-signature/consent credential.
- `widgets/messanger/PhoneFaceTimeHandoff.qml` gets **CHECK AUDIO ROUTE** under FT AUDIO in both CONTACTS and CALLS. Only a click starts the fixed Python observation command; `StdioCollector` verifies the exact schema, execution role, every denial flag and categorical bounds before displaying non-authorizing status. It cannot switch profiles or invoke BlueFerry's mutating `audio`/`calls` actions. Contact, mode or view loss stops in-flight observation and clears stale state. **FT VIDEO**, invite REVIEW → OPEN behavior, Apple's exact host-only URL allowlist and copy-only Apple-device URI remain unchanged.
- Audio guidance instructs the user to start FaceTime Audio on the **actual iPhone**, choose the PC/Bluetooth endpoint from the **iPhone's own call audio picker**, and physically verify mic and speakers with a consenting participant. No true audio-route verification is claimed until that manual test and independent evidence exist.

## HOW TO USE

After review, operator-authorized merge and **separate approval for desktop deployment**, Social → PHONE → CALLS → FT AUDIO → CHECK AUDIO ROUTE, or PHONE → CONTACTS → selected contact → FT AUDIO → CHECK AUDIO ROUTE. The result is one of several cautious messages:

| UI state | What it proves | What it cannot prove |
|---|---|---|
| System HFP profile active | Some local BlueZ card has an HFP profile selected, and BlueFerry separately reports its cellular calls ready | That it is the iPhone's FaceTime Audio, or that mic and speaker work |
| HFP profile available | Local audio knows HFP but has not selected it for the observed card | That iPhone will offer this PC or FaceTime is routed |
| HFP not observed | `pactl` didn't expose an HFP profile | That the oFono HFP audio path is impossible |
| Cellular HFP not ready | BlueFerry doesn't report its cellular HFP path ready | That FaceTime is unavailable independently |
| Backend or audio inspection unavailable | A required read-only observation failed | Any device/app state |

No app permissions, phone calls, pairing, package installation, audio mixer setting, WirePlumber configuration, service restart, saved contact or note are changed.

## VERIFY

- `tests/phone/test_phone_facetime_audio_route_v2.py`: actual parser, list/map BlueZ profiles, active vs offered vs A2DP-only, non-BlueZ cards, malformed/oversized data, provider state spoof/timeout refusal, exact fixed `pactl` read-only command and environment, no raw identifiers, all authority flags always false. CLI is status-only.
- `tests/messaging/test_social_phone_facetime_audio_route_v2_ui.py`: explicit click, no automatic service launch, correct schema/false flags, output sanitization, stale request refusal, CONTACTS/CALLS handoff inheritance, and the existing FaceTime link review security preserved.
- `.github/workflows/social-phone-facetime-audio-route-v2.yml`: executable parser tests, UI contract checks and V1 URL security, BlueFerry audio/cellular and locked Favorites/Notes regressions. Exact-head checks needed; **not a substitute for live native Quickshell rendering, iPhone/PC audio route or a consenting caller**.

## WATCH OUT FOR

Apple officially allows FaceTime and cellular call audio routing to Bluetooth devices (https://support.apple.com/en-euro/guide/iphone/iph29145acf1/27/ios/27), and its Bluetooth HFP output/input are paired routes (https://developer.apple.com/documentation/avfaudio/avaudiosession/categoryoptions-swift.struct/allowbluetooth). That does not make BlueFerry Calls1 a FaceTime API, or show the iPhone selected the Linux desktop.

The local PipeWire/PulseAudio card may represent a completely different Bluetooth headset; the PHONE observer cannot correlate it with BlueFerry's iPhone or identify any FaceTime call. `pactl` may be absent or not expose an oFono-owned call transport, and desktop sound services can be unavailable in the current session. This is why the new UI uses **observed candidate**, never a green `FaceTime Connected` claim. Even an externally verified HFP path does not grant remote FaceTime answer/decline, contact dialing, mic capture or C5/Identity authority.

A read-only PulseAudio client query may connect to the existing user's audio socket; `PULSE_NO_AUTOSPAWN=1` inhibits legacy client autospawn, but the environment's socket-activated service behavior can differ. No explicit daemon start, restart, profile change or audio capture command is included.

The Personal P35 encrypted vault, P42 hard-disabled SAVE, C3e trust and C5 human consent are separate work; this scope cannot authorize them. No independent claim of live workstation testing or actual FaceTime connectivity.

## CHECKLIST

- [x] Verify Syntagma protocols, current owner state, #1998 merge into main, and issue #1999 still open.
- [x] Inspect actual BlueFerry read-only audio helper and the existing V1 handoff.
- [x] Add status-only HFP candidate probe, no phone identity/contact/FaceTime payload output.
- [x] Integrate user-initiated FT AUDIO route check into existing PHONE panel with no stale status.
- [x] Add hostile-provider/local-audio fixtures, CLI tests and QML/regression workflow.
- [ ] Exact-head CI green and independent review; no approval/merge assumed.
- [ ] Operator-authorized merge and separate live Quickshell deployment/visual test.
- [ ] Real iPhone FaceTime Audio call routed manually to PC and verified mic + speaker with a consenting person.
- [ ] Only if necessary, observe system BlueZ/oFono/WirePlumber route in a dedicated owner-approved environment; never modify another owner's audio service without explicit approval.

## NEXT

Verify P2 exact-head CI; fix real parser/renderer regression if any. Review and operator-authorized merge. After explicit desktop update approval, use the iPhone to place an ordinary **non-emergency FaceTime Audio** call with a consenting participant, select the existing PC/Bluetooth audio destination and confirm both directions. If the route cannot be selected or mic/speaker fail, perform read-only system observation and coordinate any actual HFP/profile/service fixes with the owner before changing the local machine.

## DECISIONS

Review branch only, direct main, no commit to another worker's PR, no merge, no local write, no live Hospital registration, no Quickshell reload, no Apple login, no Bluetooth/audio config change, no contacts or notes writes. V1 browser link review/copy-only Apple URI remains separately gated. Operator has final acceptance.
