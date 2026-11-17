# Social PHONE // FaceTime Audio and Video reviewed handoff V1

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** External Hospital-compatible PHONE DOC, live Room/Assignment/Session not verified  
**Assignment:** Operator-approved addition of FaceTime Audio and FaceTime Video **to the existing Social PHONE menu**, independent from P52/P53 signed status-host and from current Personal Favorites/Notes secure-save chain.  
**Base:** direct current main `65dd052c5385093a6005441fd6272736e08d7885` on November 17, 2026; P52 #1991 and P53 #1992 were verified merged on main before this separate branch.  
**Authority:** Github draft source work approved; no local machine modifications, implicit FaceTime service pairing, BlueFerry owner changes, service restart, automatic dial, real contact send, key read, or merge.

## IMPLEMENTATION

- `PhoneContactDetail.qml` replaces the single disabled placeholder FACETIME action with clearly separated **FT AUDIO** (cyan) and **FT VIDEO** (orange). Both open an in-menu handoff below existing CALL/MESSAGE/EMAIL; they do not switch providers or automatically place a call. This preserves the Favorites/Notes preview shell and hard-disabled SAVE. Contact change/hide closes and clears the handoff so an ephemeral cached contact cannot remain selected after permission/identity changes.
- `PhonePane.qml` adds **FT AUDIO** and **FT VIDEO** under the existing CALLS header, reusing the same handoff panel even without selected contacts. A Social identity change, CALLS exit or PHONE hide clears the handoff mode. The real cellular Calls1 control and explicit dial review remain unchanged.
- `PhoneFaceTimeLinks.js` is a pure QML JavaScript strict-allowlist parser. The only browser-eligible URL is a full exact-origin HTTPS `https://facetime.apple.com/join#v=1&p=...&k=...` invite (or documented slash variant), with bounded tokens. It rejects HTTP, subdomain tricks, userinfo, ports, query redirects, arbitrary fragments, unsafe schemes, oversized or malformed payloads. It never fetches, logs or retains link text.
- The same pure JS can derive **selectable Apple-device-only URI text** from an explicitly loaded read-only contact's real phone-number or email array, using Apple's `facetime-audio:` or `facetime:` schemes. That string is **not launched on Linux**, not routed via BlueFerry, not forwarded to the iPhone, not stored, and not proof that the target has FaceTime. Contact display `primary` or opaque IDs are not eligible unless present in the card's separately validated address arrays.
- `PhoneFaceTimeHandoff.qml` is the shared panel: explains native FaceTime is not connected; distinguishes Apple-device Audio/Video origin and optional, unverified iPhone Bluetooth audio routing from browser link participation; allows an invite to be pasted into magenta text with orange cursor; requires **REVIEW INVITE** followed by **OPEN INVITE** on an unchanged strict Apple URL; invokes `Qt.openUrlExternally` only from that second click and never declares a call connected. Chrome/Edge and remote host acceptance/permissions remain separate. No invite auto-open or web retrieval.
- No new service, proprietary FaceTime transport, Apple credential collection, Identity Center grant, C3e/C5 consent authority, encrypted vault write or audio-stack mutation is introduced.

## HOW TO USE

**After independently reviewed/approved merge and separately approved local Quickshell update:**

1. Social → PHONE → CONTACTS → select an approved read-only contact → **FT AUDIO** or **FT VIDEO**. The panel displays what is *not* connected and a selectable `facetime-audio:` or `facetime:` Apple-device URI if the current card has a valid phone/email. Copy it only for use on an actual Apple device. It does not make Linux dial or deliver anything automatically.
2. Social → PHONE → CALLS → **FT AUDIO** or **FT VIDEO** works without a selected contact. If someone has shared a FaceTime join invitation, paste it, choose **REVIEW INVITE**, then **OPEN INVITE**. Your desktop requests the default browser to open the exact Apple URL. Join there with browser microphone/camera permissions and host approval. The default browser may be incompatible; Apple's documented recommended Chromium-based browsers are Chrome and Edge.
3. For FaceTime Audio started on iPhone, separately select an available Bluetooth audio device using iPhone's own call/audio UI if supported. PHONE **does not verify or claim** that the current Linux HFP call service can carry FaceTime audio. Cellular CALL remains a different provider.
4. Switching Social identity, leaving CALLS, closing a contact or hiding PHONE clears panel input and review. A browser page already opened by an explicit user click has its own lifecycle.

## VERIFY

- `tests/messaging/test_social_phone_facetime_handoff_js.js` executes actual QML JavaScript functions under Node, with valid Apple invite, trailing slash, malformed token, redirect/query, host spoofing, username, scheme, port, newline/injected URL, excessive length, no primary-only recipient, malicious email/number and audio/video URI tests.
- `tests/messaging/test_social_phone_facetime_handoff_ui.py` checks new buttons and modes, only second confirmed click may call `Qt.openUrlExternally`, no native Apple protocol execution, contact/identity clearing, read-only Apple-device text and unchanged false saving/cellular grant.
- `.github/workflows/social-phone-facetime-handoff.yml` executes both plus existing CALLS workspace, current contact details, P40 metadata lock, P42 editor shell, PHONE read-only menu, BlueFerry HFP call workspace and P44 encrypted synthetic save regressions. Exact-head CI required before accepting.
- Native live Quickshell rendering, actual FaceTime browser join, explicit Apple-device URL handoff and real Bluetooth FaceTime audio routing **have not been verified**. Any failure requires correction; neither source tests nor accepted `Qt.openUrlExternally` means call connection.

## WATCH OUT FOR

- Apple FaceTime is **not ordinary Bluetooth cellular HFP**. BlueFerry's `Calls1` covers cellular calls. Apple does not provide an authenticated native Linux FaceTime call-control provider in this project. FaceTime audio may be routed via Bluetooth device selection on the iPhone, but its compatibility with the user's Linux oFono/BlueZ/WirePlumber is unverified.
- The FaceTime browser capability is *join an already-created invitation*. It cannot create/host a new FaceTime call for arbitrary contacts, receive Apple's native calls or automatically establish an audio-only session. Browser support, camera/mic access, remote approval and resulting media are all externally governed. Apple's support guidance: https://support.apple.com/en-us/109364 ; URL scheme reference: https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/FacetimeLinks/FacetimeLinks.html .
- Invitation URLs contain join secrets. They are kept in editable QML memory only during the handoff, cleared on context loss, never logged/persisted or sent to a shell; the external browser necessarily receives the URL if the user explicitly opens it. The existing browser may track/history it independently. This is **not encrypted storage or complete secret erasure**.
- Apple-device URI text is display/copy only, never executed by Linux and never automatically transmitted to the phone. No fake FaceTime Audio capability flag and no new HFP auto-configuration.
- This is independent of the installed PHONE Personal STATUS-only host and owner C3e/C5 sign-off. Do not touch `PhonePersonalSave...` or enable Favorites/Notes SAVE based on FaceTime UI work.

## CHECKLIST

- [x] Read canonical Syntagma AGENTS/Hospital/permissions and verify PHONE mainline, no overlapping open PHONE PRs.
- [x] Confirm Apple FaceTime Link/Audio routes and existing inert CONTACTS placeholder and cellular CALLS architecture.
- [x] Add distinct contact/CALLS buttons and one guarded shared handoff panel.
- [x] Add literal Apple URL allowlist, no-autodial, contact-aware Apple-device text and context clearing.
- [x] Add executable JavaScript abuse tests, QML source guards and existing PHONE regressions.
- [ ] Pass exact-head GitHub CI and independent source/UX review.
- [ ] Operator-authorized merge; separate approval for local desktop deployment.
- [ ] Actual compatible-browser FaceTime invitation join with a consenting caller; manual iPhone audio-route test if desired.
- [ ] Future separately scoped native FaceTime provider only if a legitimate authenticated capability is discovered and reviewed.

## NEXT

Verify the new CI at exact branch SHA and correct any regressions. Then review/merge/deploy under operator authorization; after deployment, run a real invitation join in a compatible browser and independently test FaceTime Audio routing from the iPhone without assuming regular Calls1/HFP proves it. PHONE Favorites/Notes protected SAVE remains a separate in-progress assignment.

## DECISIONS

No live Hospital registration claimed, no local edits, no user-data/network probe, no uncontrolled URL opening, no merge or production activation. Neither this new UI nor ordinary phone-call readiness constitutes permission to place FaceTime calls or read/write Personal notes.
