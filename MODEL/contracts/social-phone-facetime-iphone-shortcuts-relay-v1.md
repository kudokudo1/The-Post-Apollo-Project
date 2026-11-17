# Social PHONE // iPhone-only FaceTime Shortcuts relay V1

**Patient:** \`kudokudo1/The-Post-Apollo-Project\`  
**Staff:** Hospital-compatible external PHONE DOC; no live Room, Assignment, Session or ownership lock was technically verified.  
**Assignment:** First real *request transport* for the operator's iPhone-only FaceTime plan. No Mac. The target is start, receive, view, answer, end and use PC media; only a narrow outgoing **request + acknowledgment** can be built with supported iPhone Shortcuts today.  
**Base:** current main after merged [PR #2020](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2020); existing [issue #1999](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1999) tracks actual device/audio proof.

## IMPLEMENTATION

\`services/phone/PhoneFaceTimeShortcutRelay.py\` is a stand-alone, opt-in in-memory HTTP relay using only Python stdlib. It supports **actual local HTTP request → phone-role GET → phone-role acknowledgment**; tests execute this sequence over a real ephemeral loopback port. It does **not** contain a FaceTime dial implementation, iPhone app, iOS Shortcut, Apple authentication, video stream, BlueFerry Calls1 operation, or incoming call detection.

- **Manually started only.** Importing the module, running it without \`--serve\`, or using an invalid port starts **no** listener. With a valid explicit \`--serve --port PORT --admin-token-file FILE --iphone-token-file FILE\`, binds **only 127.0.0.1**, not WLAN, 0.0.0.0, IPv6, or any public network.
- **Two independent secrets**, random at least 43 base64url characters each, held in owner-only regular files (0600, no symlink; checked via O_NOFOLLOW and fstat). One for trusted local operator methods, one for the trusted iPhone Shortcuts workflow through a *separately configured TLS gateway*. Token never enters a URL, CLI argument, response body or log. All HTTP responses use \`Cache-Control: no-store\`; no CORS grants.
- Operator-only \`POST /v1/operator/request\`, exact JSON \`{"mode":"audio"|"video","target":"+E164 number"|"email@host"}\`, strictly allowlisted. At most one pending request. Uses a random request ID. Request exists only in memory for 90 seconds; no persistence or logs. Never automatically queues a call from a contact/section change.
- Authenticated iPhone-only \`GET /v1/iphone/next\` retrieves the pending request (\`requestId\`, \`faceTimeUri\`, mode and expiry) and marks it \`DELIVERED_TO_SHORTCUT\`. The URI is \`facetime-audio:+E164\` or \`facetime:+E164\` (or conservative email), **only for iPhone-side use**, never opened by Linux.
- The iPhone's *manually run* Shortcut must explicitly ask for user confirmation before using **Open URLs** to request FaceTime to open. Then it can send authenticated \`POST /v1/iphone/ack\` with exact JSON \`{"requestId":"...","event":"OPEN_URL_REQUESTED"}\` or \`DECLINED\`. The server accepts only the currently claimed ID once, before expiry. No replay or fabricated \`CONNECTED\`/ \`ANSWERED\` events.
- Operator-only \`GET /v1/operator/status\` reports only \`EMPTY\`, \`QUEUED\`, \`DELIVERED_TO_SHORTCUT\`, \`PHONE_REPORTED_OPEN_REQUEST\`, \`PHONE_DECLINED\`, \`CANCELLED\` or \`EXPIRED\`. It intentionally never returns phone number, contact, email, invitation token or request ID. \`POST /v1/operator/cancel\` is supported. All statuses always hardcode **FaceTime connected, incoming, answer, hangup, mic, audio, video, Personal and Apple FaceTime authentication to false**.
- All HTTP body sizes <=512 bytes, methods/paths fixed, no content echo, no request access logging, no client socket/internet on import or by default, no permissive scheme or redirect.

### Functional boundary

This is a **working loopback relay protocol**, but **not yet a working PC↔iPhone FaceTime integration**. It requires all of the following, each separately approved and verified:

1. Trusted DNS/TLS reverse proxy or equivalent under operator control. Expose **only** the phone endpoints \`/v1/iphone/next\` and \`/v1/iphone/ack\` over HTTPS, with a browser/Shortcuts-trusted certificate and restricted network access. **Never expose operator routes** or the local HTTP port directly to a network. The Python server is deliberately loopback-only and does not manage proxy/firewall/Cloudflare/Tailscale state.
2. Manually configured iPhone Shortcut under the operator's Apple identity with a **private** phone token. It must be launched explicitly by the user. iOS does not guarantee periodic background polling or remote automatic run for arbitrary Shortcuts. Do not share/export a Shortcut containing the secret.
3. Trustworthy, separately permissioned PC PHONE UI action selecting a **verified recipient**, obtaining a fresh operator-confirmed consent and submitting an exact request. **No QML button was wired in this PR** because an unprovisioned relay would look like fake dial capability. The existing FT AUDIO / FT VIDEO button, preflight and reviewed invite remain unchanged.
4. Physical test: operator intentionally starts a safe non-emergency FaceTime Audio/Video call with a consenting party from the iPhone Shortcut; verify FaceTime actually opens/rings independently. If testing audio, route speaker and microphone by the iPhone audio picker, check both directions. A Shortcut HTTP ACK is not proof FaceTime connected.

### Example iPhone Shortcut design (not installed)

Once HTTPS is genuinely reachable and token is privately provisioned:

1. In **Shortcuts on iPhone**, create \`Post-Apollo FaceTime Request\`. Add **Get Contents of URL** (GET) to the approved HTTPS \`/v1/iphone/next\` path, with \`Authorization: Bearer <private-phone-token>\` HTTP header.
2. Check that the JSON \`schema\` equals \`post-apollo.phone.facetime-shortcuts-relay.v1\` and \`state\` equals \`DELIVERED_TO_SHORTCUT\`. If not, stop. Never open a URL from unexpected JSON.
3. Display the intended FaceTime mode and recipient for a **specific per-request user choice** (Call / Decline). Do not auto-dial from a background trigger.
4. If Call chosen, construct/select the returned FaceTime URI only when its scheme and number/email match the expected shape. Use Shortcuts **Open URLs**. Then **Get Contents of URL** (POST JSON) to the approved HTTPS \`/v1/iphone/ack\`, same Authorization header, \`requestId\`, \`event=OPEN_URL_REQUESTED\`. If Decline, post \`event=DECLINED\`.
5. The PC records only the Shortcuts *report* of a requested open, never FaceTime call success. Shortcuts cannot independently attest Apple FaceTime remote call state.

**Apple evidence:** <https://support.apple.com/guide/shortcuts/apd58d46713f/ios> documents Get Contents of URL GET/POST; <https://support.apple.com/guide/shortcuts/apd621a1ad7a/ios> documents opening FaceTime URL schemes; <https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/FacetimeLinks/FacetimeLinks.html> documents FaceTime URL targets; <https://developer.apple.com/documentation/BackgroundTasks/choosing-background-strategies-for-your-app> illustrates why reliable background automation on iPhone needs an independently designed app/push channel.

## HOW TO USE

**Not live or deployed.** A reviewer can run the isolated CI tests without network exposure or Apple data. No instruction here constitutes approval to install secrets, open a firewall, expose a reverse proxy, start a daemon, or mutate the operator's desktop. The CLI is strictly disabled unless manually invoked with a port and two privately provisioned credential files. The user-facing action is not wired until PC↔iPhone authentication and an actual working, reviewable HTTPS path are established.

## VERIFY

New \`tests/phone/test_phone_facetime_shortcuts_relay_v1.py\` exercises **actual loopback HTTP** operator request → phone retrieval → phone ACK, separate token roles and rejection, exact FaceTime URI, strict target/mode allowlist, TTL expiry, one pending request, cancel, replay/fake call state rejection, malformed methods/bodies, no public bind, private file/symlink refusal, and unconditional negative FaceTime control/media claims. Dedicated workflow \`.github/workflows/social-phone-facetime-shortcuts-relay-v1.yml\` reruns existing iPhone pilot, FaceTime links, HFP route, PHONE audio and locked Personal editor tests. Exact-head GitHub checks must be verified.

## WATCH OUT FOR

This is **not a working iPhone remote FaceTime start/answer/end/video implementation**. It is only a narrowly scoped transport. Real iOS shortcut execution and Apple FaceTime result still need testing. A trusted phone-token holder can claim a request or forge its own OPEN_URL_REQUESTED acknowledgment; this authenticates bearer possession, *not* a physical call, a specific iPhone identity or a human's face/voice. The implementation makes that distinction explicit.

In particular, a browser-exposed, unauthenticated LAN endpoint, shared/reused token, plain HTTP to the iPhone, leaked phone-number URL, unrestricted operator gateway route, request logs or automatic call launch would be unsafe. The current module prevents opening a non-loopback HTTP listener. Any future HTTPS gateway needs explicit deployment/ownership/network security review. Do not ask iOS to automatically run a continuously polling Shortcut in background; iOS execution is not guaranteed.

Existing PHONE Favorites/Notes SAVE remains separate and hard-false without C3e/C5 permissions. BlueFerry \`calls_enabled:false\` relates to **cellular** Calls1, not FaceTime. Incoming FaceTime notifications, remote answer/end and live video are not implemented by this protocol.

## CHECKLIST

- [x] Confirm V1 iPhone pilot merged and owner scope clear.
- [x] Verify current Apple Shortcuts/FaceTime request behavior and background limits.
- [x] Implement real in-memory loopback request/phone-ack HTTP endpoints, no auto network.
- [x] Add real HTTP and adversarial security tests.
- [ ] Exact-head CI and review pass; no merge assumed.
- [ ] Operator-approved HTTPS gateway/credential provisioning, scoped to phone paths.
- [ ] Build and privately install iPhone Shortcut; run physical phone-to-PC acknowledgment test.
- [ ] Integrate a genuinely working request action into existing PHONE UI, with per-click confirmation and no fake connectivity.
- [ ] Independently test FaceTime Audio iPhone-to-PC route; incoming calls, remote answer/end, and video remain separate unsupported boundaries.

## NEXT

Confirm all exact-head checks and request external review. The next engineering slice, **only after operator approves relevant host/network changes**, is a secured HTTPS phone-facing endpoint and manual Shortcut that actually reaches it, then a PHONE button connected to a *verified* delivery/ack status. Real audio/video/answer/end claims stay blocked until independently demonstrated on the iPhone.

## DECISIONS

No Mac. External Hospital-compatible PHONE DOC, no claim of live Hospital registration. Direct-to-main review branch only. No local user machine writes, no iPhone automation installed, no backend pairing, no network listener started, no production TLS gateway, no QML fake dial button, no provider API/secret exposure, no FaceTime placed, no Apple login, no merge or operator acceptance. PR author cannot declare final done.
