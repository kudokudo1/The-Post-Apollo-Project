# Social PHONE // iPhone-only FaceTime HTTPS gateway V1

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** External Hospital-compatible PHONE DOC; no verified live Room, Assignment, Session, or host authority.  
**Checkpoint:** [PR #2023](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2023) merged into main. This is a NEW source-only next milestone against that merged repository state. [Issue #2026](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2026) tracks complete iPhone-only FaceTime goal.

## IMPLEMENTATION

`services/phone/PhoneFaceTimeShortcutHttps.py` is an **explicitly launched, phone-only TLS 1.3 ingress** for the existing in-memory FaceTime Shortcut request relay. It does not start on import, in a normal PHONE session, or without two deliberate CLI opt-in flags.

The gateway shares **one in-memory Relay object** across two separate listeners, only if an operator has separately approved device/network activation:

- **PC operator listener:** HTTP bound solely to `127.0.0.1:OPERATOR_PORT` using the existing `PhoneFaceTimeShortcutRelay._LoopbackOnly` route set. Only a local holder of the independently provisioned admin token can create/status/cancel requests.
- **iPhone listener:** TLS 1.3 HTTPS bound to **one exact RFC1918 private LAN IPv4 address and port**, not wildcard, public IPv4, IPv6, link-local or a DNS name. Allows **one explicit iPhone private IPv4 peer**; all other peers are rejected before the TLS handshake. Uses the existing, separate 43+ character iPhone bearer token. **Only** `GET /v1/iphone/next` and `POST /v1/iphone/ack` are reachable. Attempts to call `/v1/operator/*` on HTTPS get 404, even when a user knows the admin token. There is no HTTP fallback on the phone port.
- **TLS identity:** certificate and matching private key are required up front. TLS 1.3 only. The key must be an owner-owned regular file inaccessible to group/others (typically 0600); symlinks refused. The iPhone must validate the certificate trust chain **and DNS/IP subject alternative name**. Certificate generation, installation, CA trust, DNS, firewall, VPN, pairing, LAN listeners and app/Shortcut provisioning are **not** performed by this PR.
- **No FaceTime provider rights:** a Shortcut claim is one-use and expires under the relay's existing 90-second memory-only lifecycle; an iPhone acknowledgment confirms only the Shortcut **reported an attempt to open the FaceTime URL**. No incoming FaceTime, Answer, End, mic, speaker, Apple user account or video capability is implied. The gateway does not interact with the Bluetooth daemon, system audio or protected Personal data.

`tests/phone/test_phone_facetime_shortcuts_https_v1.py` starts real local **TLS 1.3** and loopback HTTP servers using temporary, CI-only, self-signed test certificates that are explicitly trusted by the test client. It proves the end-to-end operator POST → iPhone HTTPS GET → iPhone HTTPS POST ACK → operator status path. It also rejects untrusted certificates, plaintext HTTP to TLS, leaked operator methods, wrong phone/admin tokens, public/wildcard binds, symlink/shared private keys and opt-in-less startup. **These tests do not exercise an actual iPhone or its FaceTime app.**

## HOW TO USE // Future operator-approved sequence

**Currently not deployed. Do not execute these setup steps without distinct authorization for each host/network change.** The commands below are a review contract, not proof that the host has certificates, stable IPs, firewall rules, a connected iPhone or a working Shortcut.

1. Verify an approved, isolated local Wi-Fi network, assign/check the PC's chosen RFC1918 IPv4 and the iPhone's current private IPv4. No public port forwarding. Confirm permitted peer is *actually* the intended iPhone and update the allowlist if the address changes.
2. Provision separate, high-entropy admin and phone tokens **outside GitHub**, each in an owner-only `0600` private file on the PC. Never store a live token in source, issue, URL, shell arguments or logs. On iPhone, the private phone token would be embedded into an operator-owned Shortcut and must never be shared/exported.
3. Provision a TLS certificate/key for an approved hostname or exact IP SAN that the iPhone's system trust store accepts. Prefer a publicly trusted CA certificate for a hostname resolved to the approved local address; **do not disable certificate verification**. Do not install an unknown root certificate on the iPhone.
4. Only after operator authorizes local binding, run the *reviewed* executable with these flags (actual paths/IPs/ports must be chosen and independently verified; do not copy placeholder values into a live system):

```text
python3 services/phone/PhoneFaceTimeShortcutHttps.py \
  --serve-iphone-https \
  --acknowledge-private-lan-exposure \
  --operator-port <APPROVED_PC_LOOPBACK_PORT> \
  --phone-bind <APPROVED_PC_PRIVATE_IPV4> \
  --phone-port <APPROVED_HTTPS_PORT> \
  --iphone-client-ip <VERIFIED_IPHONE_PRIVATE_IPV4> \
  --certificate-file <APPROVED_CERT_FILE> \
  --private-key-file <PRIVATE_0600_TLS_KEY_FILE> \
  --admin-token-file <PRIVATE_0600_OPERATOR_TOKEN_FILE> \
  --iphone-token-file <PRIVATE_0600_IPHONE_TOKEN_FILE>
```

5. Only after a trusted HTTPS endpoint has been independently tested on the iPhone, manually create **Post-Apollo FaceTime Request** in the iPhone **Shortcuts** app. Apple's official Shortcuts guide supports *Get Contents of URL* with GET, POST and JSON request body; the Open URL action supports FaceTime URL schemes. Set up the following precise, **manual** flow and test it with no actual call first:
   - **Get Contents of URL**: exact `https://<APPROVED_HOST>:<PORT>/v1/iphone/next`, method GET; HTTP header `Authorization: Bearer <PRIVATE_PHONE_TOKEN>`. Header remains private; do not include token as URL query text.
   - Extract dictionary values `schema`, `state`, `mode`, `faceTimeUri`, `requestId`, `expiresAt`. **If schema is not exactly `post-apollo.phone.facetime-shortcuts-relay.v1`, or state is not `DELIVERED_TO_SHORTCUT`, STOP.** Do not call if the current time is past `expiresAt`. Require a nonempty requestId and `audio`/ `video` mode. Compare URL scheme to mode: exactly `facetime-audio:` for audio or `facetime:` for video, with a human-visible, expected phone/email recipient. Never open any other scheme or redirect.
   - **Choose from Menu**: show the full intended recipient/mode, with **Call on iPhone** and **Decline**. Do not auto-open on fetch, launch from a background trigger, or allow a web page to supply a target.
   - If **Decline**: **Get Contents of URL** POST to exact `/v1/iphone/ack`, Authorization same phone header, JSON body `{"requestId":"<RETURNED_ID>","event":"DECLINED"}`.
   - If **Call on iPhone**: **Open URLs** using only the individually reviewed `faceTimeUri` from this authenticated response, then **attempt** POST to `/v1/iphone/ack` with `{"requestId":"<RETURNED_ID>","event":"OPEN_URL_REQUESTED"}` if the Shortcut continues. **Opening FaceTime can switch foreground apps and prevent a later Shortcut action from running.** No receipt should be presumed. A request is never marked FaceTime-connected based on ACK.
   - Shortcut permissions and any URL/app-open prompts are respected. FaceTime may place a call immediately after opening a scheme; the explicit **Choose from Menu** decision must come first. Never run this with an emergency number, strangers or without a consenting test participant.
6. From the approved local PC, use `PhoneFaceTimeShortcutOperator.py --queue-audio` or `--queue-video`, `--port`, and `--admin-token-file`. It privately prompts for the recipient and a literal `PREPARE` confirmation. Manually run the iPhone Shortcut once during the next 90 seconds. The PC can inspect only `QUEUED`, `DELIVERED_TO_SHORTCUT`, `PHONE_REPORTED_OPEN_REQUEST`, `PHONE_DECLINED`, `CANCELLED` or `EXPIRED`; it cannot detect the actual FaceTime state.
7. Verify the **real** consenting destination rings and the iPhone media independently. For FaceTime Audio, use the iPhone audio picker to select an available PC hands-free endpoint and verify both microphone and speaker. Keep [issue #1999](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1999) open until physical evidence exists. No claim that Bluetooth HFP can carry FaceTime video.

**Apple references:** [iOS Shortcuts API requests](https://support.apple.com/guide/shortcuts/apd58d46713f/ios), [iOS 27 URL schemes](https://support.apple.com/en-ie/guide/shortcuts/apd621a1ad7a/10.0/ios/27), and [FaceTime URL schemes](https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/FacetimeLinks/FacetimeLinks.html).

## VERIFY

- [x] Existing V1 source relay and operator CLI merged via PR #2023.
- [x] New source-only isolated HTTPS endpoint with private IP + client allowlist and TLS 1.3.
- [x] New actual TLS/HTTP dual-listener test harness and denial regressions.
- [ ] Exact-head CI, independent review, authorized merge (no assumption).
- [ ] Operator approval for PC listener, certificate and token provisioning.
- [ ] Actual iPhone HTTPS certificate/allowlist and manual Shortcuts GET/POST validation.
- [ ] Actual FaceTime Audio and Video start from user-confirmed Shortcut with consenting person; distinguish URL opened from ring/answer/connection.
- [ ] UI integration only after real outbound delivery evidence, plus separate consent/identity authority.
- [ ] Native incoming FaceTime, Answer, End, video display and PC camera forwarding: **not implemented or available through this gateway**.

## WATCH OUT FOR

This is a network-facing component if **someone deliberately starts it**, despite strict LAN-only address, allowlisted peer, TLS and bearer token. A private IPv4 address is not proof of iPhone identity. A compromised device at that IP could read a FaceTime request if it also has the phone token. Exposing it through a public tunnel or forwarding the network port is **outside approval**. Prefer same trusted Wi-Fi, no router internet port forwarding, firewall allowlist, and no shared Wi-Fi hotspot. No connection to Apple's FaceTime service, no Apple login and no access to FaceTime internal call session APIs. None of the requirements for remote native incoming, answer/end or video are met.

## NEXT

After CI, independent review and operator-authorized merge, obtain **separate explicit authorization** before host/network activity. Perform an iPhone-only HTTPS handshake without queueing a call first. Confirm /v1/operator remains unreachable from iPhone, phone token cannot access operator port and the certificate is trusted. Then test the manual Shortcut claim/decline path, followed by a consenting outbound FaceTime request. Only then make an actual PHONE-menu dial integration proposal.

## DECISIONS

No Mac. GitHub review branch only, no merge without operator approval. No host file edits, local token generation, firewall/OS config, network/TLS daemon start, Apple shortcut installation, actual call, Bluetooth change, FaceTime sign-in, production activation, Personal SAVE authorization, or claim of live Hospital Room/Assignment/Session. Operator holds final acceptance.
