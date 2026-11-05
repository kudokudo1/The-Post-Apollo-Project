# 🏥💜 Universal Connections // C2l identity boundary review

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF // External Hospital-compatible Doctor; no live registration  
ASSIGNMENT // Synthetic topology checks for future protected host identity  
BASE // 94891ad77b4af703e2e90df7a8a54b3526909b81  
PERMISSIONS // Repository-only draft, tests, CI and docs; no desktop changes

## IMPLEMENTATION

C2k PR #1306 is merged. It explicitly launches a same-user Python process serving C2j's IDLE status. C2i uses path metadata and SO_PEERCRED for read-only inspection but correctly marks responses OBSERVED_UNVERIFIED. It does not authenticate a Post-Apollo host.

### Verified compatibility problem

- C2i expects a private per-user Unix socket, requires a same-user socket owner and same-UID peer.
- C2j creates a mode-0600 socket inside a private user-owned mode-0700 directory and rejects cross-UID client requests.
- A distinct protected service UID cannot simply replace the C2k process at this exact socket: directory permissions and same-UID peer requirements prevent it. Relaxing those checks without a separate review would be unsafe.
- The Python interpreter might be installed from a protected OS package but the user-editable source script and modules are not an independent trust root. Same-UID ownership, PID, cmdline, or self-stored checksum cannot elevate this link to authenticated status.

C2l creates only services/connections/experiments/C2lHostTrustBoundaryModel.py, an OFFLINE synthetic evaluator of the current socket and one possible future protected system bus. It never reads the host, launches a process, binds a socket, contacts a keyring, or changes permissions.

For the current socket, a matching UID is SAME_UID_SOCKET_NOT_IDENTITY and a differing UID is C2I_C2J_CROSS_UID_INCOMPATIBLE. For a proposed protected bus, the synthetic conditions include distinct service/client UIDs, matching service/peer UIDs, root-owned service unit, root-owned code, protected bus policy, and consent. Even a positive synthetic proposal yields PROPOSAL_ONLY_NO_DEPLOYED_TRUST_ROOT and still DENY.

All responses have hostAuthenticated=false, credentialPresent=false, grantActive=false, canApprove=false and canUseApi=false. The production QML and JS never import this model.

## HOW TO USE

No new desktop action. Existing CPU++ path: SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST. Observations stay unverified. C2l runs only in isolated GitHub CI.

## VERIFY

The standalone tests reject forged fields, wrong types, same-UID spoofing, cross-UID socket assumptions, unprotected proposed service configurations, mismatched service identities, missing consent, and a purportedly perfect synthetic plan. They also check that C2i/C2j/CPU++ remain deny-only. CI reruns the real-process C2k launcher and existing C2i/C2j tests.

These tests do NOT verify actual OS service provenance, system-bus ownership, SELinux, credential isolation, user consent, or local Fedora deployment.

## WATCH OUT FOR

This is architectural verification, NOT production host authentication. Caller-supplied service-ownership and consent booleans are never authoritative. reviewCandidate=true means only a topology deserves future review.

Potential protected service design: reviewed root-managed systemd service under a dedicated non-login UID, restrictive root-owned system-bus policy with verified owner, service-side secrets, and separate operator consent/revocation. This is only a proposal, not an adopted or implemented transport. It requires shared-seam review and separate desktop installation authorization.

## CHECKLIST

- [x] Verify C2k merged and no open competing Connections PR
- [x] Read Syntagma/Hospital protocols
- [x] Identify current transport/identity incompatibility
- [x] Add isolated fail-closed synthetic evaluator
- [x] Add adversarial tests and dedicated CI
- [ ] Complete exact-HEAD CI and independent review
- [ ] Operator selects protected deployment strategy
- [ ] Implement OS-verified host identity and authenticated communication
- [ ] Separately authorize local installation, consent, key operations and NASA requests

## NEXT

Review this gate and choose whether to develop a separately protected system-bus/service contract. Preserve C2i's current user socket strictly for unverified diagnostics until there is verified service-origin and consent enforcement.

## DECISIONS

Draft only. No current socket change, production integration, service launch, local machine writes, credentials, keyring modifications, merge, or real NASA traffic.
