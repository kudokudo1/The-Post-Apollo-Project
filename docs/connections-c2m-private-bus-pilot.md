# 🏥💜 Universal Connections // C2m private D-Bus status pilot

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF ROLE // external Hospital-compatible Doctor (OPEN AI // CHATGPT)  
ASSIGNMENT // Noninstalled D-Bus one-method status service prototype  
BASE // main e408183cf3a56223e2f14f8d26eedf84b6aade8f  
PERMISSIONS // GitHub branch, tests, CI and docs only; no local machine actions

## IMPLEMENTATION

C2l PR #1308 is merged. Its architecture check showed that C2i/C2j's mode-0700 user runtime and mode-0600 same-UID socket cannot be reinterpreted as cross-UID trusted host transport. C2m takes a separate, additive path: an **actual message-bus method** on a disposable private test session bus. It is deliberately NOT the future root-protected production system bus.

- services/connections/experiments/C2mPrivateBusStatusPilot.py: two explicit CLI modes, --ci-private-serve and --ci-private-inspect. Both refuse execution unless POST_APOLLO_C2M_DISPOSABLE_TEST_ONLY=1 and an explicit unix: DBUS_SESSION_BUS_ADDRESS are provided. There is no auto-start, system-bus access, service installer, systemd unit, keyring action, NASA call or Quickshell binding.
- The single D-Bus method is GetStatus() on org.postapollo.ConnectionsStatusPilot1 at /org/postapollo/ConnectionsStatusPilot. It returns only the strict read-only IDLE JSON payload. The service claims its well-known name only when unowned; DO_NOT_QUEUE prevents latent takeover.
- An independent D-Bus client obtains name owner and Unix UID from the D-Bus daemon, calls the method and validates the response. All output remains OBSERVED_UNVERIFIED, hostAuthenticated=false, grantActive=false, credentialPresent=false, canApprove=false, canUseApi=false. A UID from the bus daemon does not prove installed-code integrity or consent.
- services/connections/experiments/C2mConnectionsStatusPilot.xml defines the exact one-method D-Bus contract, with no approval/cancel/key operations.
- tests/connections/test_connections_c2m_private_bus_pilot.py launches a real dbus-daemon, two separate Python processes, and a client in a disposable GitHub runner. It checks no implicit start, duplicate name refusal, status roundtrip, missing owner after exit, an unknown Approve call returning an actual D-Bus error, malformed modes, and contract shape.
- Dedicated CI installs only test-runner dependencies (dbus-next 0.2.3 and dbus-daemon if absent), reruns C2l/C2k/C2i/C2j, and checks production QML/broker files stay unchanged.

## HOW TO USE

No new desktop screen, menu command, daemon or credentials. The existing CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST remains a read-only same-user socket diagnostic.

C2m runs only within GitHub CI on a private, disposable test message bus. It does not install its interface on your Fedora desktop. The test-private D-Bus interface is not yet visible to CPU++.

## VERIFY

The private D-Bus roundtrip demonstrates a real independent service process, D-Bus name ownership, daemon-provided owner Unix UID, strict method replies, refusal of an unsupported method and shutdown disconnection. Exact-head CI is the acceptance gate. Native Quickshell regression is separate and must also remain green.

This is NOT a privileged service identity or trusted production connection. The real system-bus service, root-owned packaging, dedicated non-login service UID, SELinux interactions, restrictive bus policy, and authenticated user consent remain unimplemented.

## WATCH OUT FOR

A private session bus under the same UID can be impersonated by another same-user process. This pilot never elevates its outputs into authorization. The hard-coded CI-only flag and address are test gates, not security trust roots. D-Bus name ownership and UID reports are meaningful only when the bus daemon and policy are trusted independently.

Before a production integration, a separately approved architecture must protect code, service manager unit, bus policy, credentials, and name ownership; verify OS-enforced peer identity; handle operator consent/revocation; and separately install/test on Fedora. Do not modify the current C2i socket or turn credentialActionsEnabled true as a shortcut.

## CHECKLIST

- [x] C2l merge and ownership preflight
- [x] One-method D-Bus XML contract and isolated service/client
- [x] Real-process/disposable-bus CI test coverage
- [x] Preserve all deny-only authorization flags
- [ ] Exact-head CI and independent review
- [ ] Operator acceptance and separate merge decision
- [ ] Protected system-bus identity, UID and bus policy design
- [ ] Local deployment approval
- [ ] Credential authorization and real NASA service

## NEXT

After PR review, produce a noninstalled **OS policy and package prototype** with a dedicated service identity, restrict its system bus name and method access, and test denied clients and integrity assumptions on a disposable machine. Actual Fedora service installation and NASA credential use require separate approval.

## DECISIONS

No local writes, service activation, production user/account/session changes, keyring access, real NASA calls, shared Connections QML edits, or merge. Draft-only test milestone.
