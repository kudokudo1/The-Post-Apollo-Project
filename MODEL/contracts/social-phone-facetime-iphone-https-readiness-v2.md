# Social PHONE // FaceTime iPhone HTTPS gateway local readiness V2

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Role:** External Hospital-compatible PHONE DOC; live Room, Assignment, Session, locks, and host activation rights not verified.  
**Base:** Current `main` after [PR #2034](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2034) merged. This is a separate PHONE-owned security/readiness milestone, not a live integration.

## IMPLEMENTATION

The iPhone-only gateway now supports **read-only local material checking** with `PhoneFaceTimeShortcutHttps.py --check-configuration`. It inspects the exact IPv4/port declarations, owner-private TLS key, certificate/private-key compatibility and independent private operator/iPhone bearer credential files, and then exits without starting a server, attempting DNS resolution, contacting an iPhone, placing a FaceTime call, writing files, updating system services, or changing firewall configuration.

It emits one fixed JSON shape: `post-apollo.phone.facetime-https-local-check.v1`, `READ_ONLY_LOCAL_FILES_ONLY`, with state `LOCAL_MATERIAL_ACCEPTED` or `CONFIGURATION_REJECTED`. The success state means **only that local input material was accepted**. In both cases these claims remain false: `networkListenerStarted`, `iphoneReachableVerified`, `iphoneCertificateTrustVerified`, `iphoneShortcutConfigured`, `faceTimeConnected`, `faceTimeCallControl`, `videoAvailable`, `personalDataAuthorized`. The report contains no token, IP, path, recipient, contact, FaceTime link, private key, SAN or exception trace.

The gateway's original private-key check previously used `Path.lstat()` followed by a separate `SSLContext.load_cert_chain(keyfile=...)` pathname lookup. It now opens the key with `O_NOFOLLOW`, validates ownership and `0600`-equivalent permissions via **`os.fstat()` on that exact open file**, and uses Linux `/proc/self/fd/<fd>` to load the pinned inode into OpenSSL before closing the descriptor. A symlink swap between validating and loading the private key cannot redirect the key read. This is intentionally Linux-specific for the Fedora/Silverblue deployment target. The certificate itself is public data, but its issuer, expiration, full chain, subject-alt-name and trust are **not validated** by the local check: iOS must independently validate certificate hostname/IP identity and trust at handshake time. Local acceptance does not justify production activation.

No change is made to the existing HTTPS listener's explicit opt-in, private-IP-only binding, exact peer-IP restriction, TLS 1.3-only transport, independent operator-route isolation, or the FaceTime request/ack protocol. No UI FaceTime action is newly enabled.

## HOW TO USE

**Not deployed. Do not provision files or run a listener without separate host/network authorization.** After explicit operator approval of any necessary credential/certificate file creation, operators can inspect the local materials before authorizing a network listener. Use the **same argument values** intended for eventual deployment, but choose the dry-run flag `--check-configuration` instead of `--serve-iphone-https` and **do not** supply `--acknowledge-private-lan-exposure`:

```text
python3 services/phone/PhoneFaceTimeShortcutHttps.py \
  --check-configuration \
  --operator-port <APPROVED_PC_LOOPBACK_PORT> \
  --phone-bind <APPROVED_PC_RFC1918_IPV4> \
  --phone-port <APPROVED_HTTPS_PORT> \
  --iphone-client-ip <VERIFIED_IPHONE_PRIVATE_IPV4> \
  --certificate-file <EXISTING_TRUSTED_TLS_CERT_PATH> \
  --private-key-file <EXISTING_PRIVATE_KEY_0600_PATH> \
  --admin-token-file <EXISTING_ADMIN_TOKEN_0600_PATH> \
  --iphone-token-file <EXISTING_IPHONE_TOKEN_0600_PATH>
```

The actual mutation/activation, if later authorized, is the distinct `--serve-iphone-https --acknowledge-private-lan-exposure` invocation from the prior V1 contract. The check flag never activates it. A successful local check is followed by **separate** iPhone HTTPS trust and reachability tests, then no-call Shortcut claim/decline tests, then a consenting FaceTime call. The operator's full start/receive/answer/end/video goal remains open in [issue #2026](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2026), and the physical HFP route test remains in [#1999](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1999).

## VERIFY

Extended `tests/phone/test_phone_facetime_shortcuts_https_v1.py` with a valid temporary key/cert/token dry-run and a deliberately invalid permission case, intercepting `serve`, local and network server constructors, and even Python socket creation to prove **no listener or connection** occurs. Asserts exact data-minimized JSON and all false claims. Keeps real ephemeral TLS 1.3 + loopback dual-listener HTTP tests, bad peer/TLS/malformed paths and the previous inherited FaceTime, audio and protected Personal regressions. CI result at exact review branch HEAD must be verified separately.

## WATCH OUT FOR

This source-only check intentionally opens existing local private token/key files for validation; it should only be used after the operator approves creating or installing those materials. It does not prove Wi-Fi reachability, IP stability, firewall policy, Apple iOS trust, Shortcut configuration, FaceTime user or actual call control. A private-IP peer allowlist is not an iPhone identity proof. FaceTime URL scheme behavior inside an actual iPhone Shortcut needs a physical test. No full FaceTime incoming answer/end/video API is established.

## CHECKLIST

- [x] Observe merged #2034 and current main, check concurrent PHONE owners.
- [x] Eliminate TLS private-key validation/load path swap.
- [x] Add explicit read-only local configuration validation with fail-closed output and no listener.
- [x] Add source, denial and no-socket regression tests.
- [ ] Exact-head CI success and independent review.
- [ ] Operator-approved merge, separate host credential/cert/network authorization.
- [ ] Real iPhone TLS handshake, manual no-call Shortcut test, consented FaceTime trial.
- [ ] Native incoming answering, hangup, PC media/video remain unsupported or unverified.

## NEXT

Verify exact-head CI, resolve any regressions, submit for review. **Do not perform host deployment or issue a working FaceTime UI indicator.** After operator authorizes the physical boundary, verify local material acceptance before making any network listener change; test the actual iPhone certificate trust separately.

## DECISIONS

No Mac. No live Hospital attachment claimed. Direct-main-based review branch, no merge, no local machine write, no credential/certificate generation, no TCP listener, no Apple sign-in, no iPhone Shortcut, no FaceTime dialing or cellular call/Bluetooth change, no C3e/C5/Personal permissions expansion. Operator retains final acceptance.
