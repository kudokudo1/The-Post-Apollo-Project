# Social Phone Integration // Capability Policy P0 (offline contract)

> **STATE //** EXECUTABLE SYNTHETIC / REVIEW CANDIDATE; **not a connected phone bridge**.
>
> **DATE //** 2026-11-02.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **BASELINE //** `main` at `89496f890346b6afc5cad56658df98f4704d2349`, verified after PR #1016 merged; reacquire current HEAD before continuing.
>
> **SOURCE / DIRECTION //** Operator-selected [network-first Phone Bridge ADR](./social-phone-bridge-network-first-adr-v0.md); this slice implements the isolated **route choice policy**, not actual device support.
>
> **OWNER / SCOPE //** New `services/phone/CapabilityPolicy.py` and `tests/phone/test_capability_policy.py` plus this contract and targeted workflow. Shared Social selector/router, Identity Center and Hospital code untouched. No verified live Hospital Room, Staff Role, Assignment or connection.
>
> **RESTRICTIONS //** No pairing, Bluetooth/BlueZ, Wi-Fi socket, KDE Connect or carrier APIs, credentials, phone data, live user, authorization gateway, Quickshell runtime, local installation or production changes. No PR merge permission implied.

## 1 // Mechanism

A pure Python `plan(request)` function receives **synthetic observations** about available backends. It validates the requested phone operation, local request-context IDs, connection preference, per-capability Bluetooth consent, and each backend's declared permission, authorization, probe, health and capability. It returns **one route proposal or a non-routing reason**. It does **not** perform the call/text, read messages, authenticate the user, use the network, or check that a phone is physically present.

A `ROUTE_CANDIDATE` is a *hypothetical eligible backend in the input*, **not** proof of a working API, signed-in iPhone, or real Bluetooth profile. The `VERIFIED` field is solely fixture-provided data in this slice. The eventual trusted Phone Integration Manager must obtain trustworthy, independently validated status and device scope before using any result.

No new Social app-selector ID, account link, keyboard route, notification, or phone UI has been introduced.

## 2 // Route request v0

The caller supplies one dictionary with **exact keys**:

| Field | Meaning |
| --- | --- |
| `schema` | `post-apollo.phone.route-plan.v0` |
| `requestId` | Opaque, 1–64 character correlation identifier, no secrets |
| `principalId` | Test-only human reference from a *future verified* upstream principal |
| `deviceId` | Test-only phone reference |
| `lineId` | Test-only linked phone account/line reference; personal and business lines are distinct |
| `operation` | One of `messages.read`, `messages.send`, `messages.receive`, `contacts.read`, `notifications.receive`, `calls.dial`, `calls.answer`, `calls.audio`, `calls.hangup` |
| `inFlight` | `NONE`, `SEND_OUTCOME_UNKNOWN`, `CALL_ACTIVE` |
| `policy` | Exact object below |
| `candidates` | 0–16 backend snapshots, exact fields below |

`policy` requires:
- `mode`: `AUTO`, `NETWORK_ONLY`, `MANUAL`;
- `bluetoothFallback`: boolean, default safe value should be `false` at the future UI boundary;
- `bluetoothOperations`: explicit unique allowlist of operation strings, empty by default;
- `manualBackendId`: opaque backend ID in `MANUAL` mode, otherwise `null`.

Each candidate must contain:
- `backendId`, `principalId`, `deviceId`, `lineId`: opaque identifiers;
- `transport`: `NETWORK` or `BLUETOOTH`;
- `operations`: unique subset of recognized operations;
- `authorization`: `VERIFIED`, `UNKNOWN`, or `DENIED`;
- `permission`: `GRANTED`, `UNKNOWN`, or `DENIED`;
- `health`: `READY`, `DEGRADED`, `OFFLINE`, or `UNKNOWN`;
- `probe`: `VERIFIED` or `UNVERIFIED`.

All nested objects reject unknown/missing keys. No phone numbers, contacts, message bodies, cookies, pairing codes, tokens or business names belong in this planning contract. All IDs are opaque alphanumeric/dash/underscore only; no read or write from local storage. A future production ABI is **not frozen** here, and schema migration is required before integration.

## 3 // Output and safety

The output contains only:
`schema`, `execution: PLAN_ONLY`, `requestId`, `operation`, `state`, `reason`, `backendId` or null, and `transport` or null.

Possible states:
- `ROUTE_CANDIDATE`: exactly one hypothetical eligible route. No call/send was performed.
- `SELECTION_REQUIRED`: more than one eligible route of the selected transport; do not arbitrarily choose the phone number/provider.
- `UNAVAILABLE`: no eligible route consistent with mode, identity, capabilities and consent.
- `BLOCKED`: sending outcome is uncertain or a call is active; do not make a second attempt or swap live audio/control.

Routing invariants:
1. Reject malformed, unknown, duplicate, excessive or secret-bearing inputs.
2. Require **exact** principal, device, line and operation match to each candidate. Do not interpret Social `identity-N` as authenticated identity.
3. Candidate is eligible only when `authorization=VERIFIED`, `permission=GRANTED`, `health=READY`, `probe=VERIFIED` are all presented by the *fixture*.
4. In `AUTO`, try eligible **NETWORK** candidates before any **BLUETOOTH** candidates.
5. Use Bluetooth only if `bluetoothFallback=true` and the requested operation appears in `bluetoothOperations`. Even manual Bluetooth selection requires both.
6. In `NETWORK_ONLY`, never select Bluetooth. In `MANUAL`, select only the exact eligible `manualBackendId` and no implicit substitute.
7. Multiple equally eligible network backends or Bluetooth backends require explicit selection. The policy does not resolve carrier identity or message service equivalence.
8. Unknown message-send result blocks choosing a replacement backend. An active call blocks this planner's mid-call rerouting. Recovery and user-confirmed retries need separate evidence and contracts.
9. Do not equate backend selection with provider confirmation, successful send, delivery, or active call.

## 4 // Example (synthetic, not a live device)

```python
import sys
sys.path.insert(0, "services/phone")
from CapabilityPolicy import plan, SCHEMA

proposal = plan({
    "schema": SCHEMA, "requestId": "demo-1",
    "principalId": "test-person", "deviceId": "test-android",
    "lineId": "test-personal", "operation": "messages.send",
    "inFlight": "NONE",
    "policy": {"mode": "AUTO", "bluetoothFallback": False,
               "bluetoothOperations": [], "manualBackendId": None},
    "candidates": [{
        "backendId": "demo-network", "principalId": "test-person",
        "deviceId": "test-android", "lineId": "test-personal",
        "transport": "NETWORK", "operations": ["messages.send"],
        "authorization": "VERIFIED", "permission": "GRANTED",
        "health": "READY", "probe": "VERIFIED",
    }],
})
assert proposal["state"] == "ROUTE_CANDIDATE"
assert proposal["execution"] == "PLAN_ONLY"
```

## 5 // Run offline tests

```bash
python3 -m py_compile services/phone/CapabilityPolicy.py tests/phone/test_capability_policy.py
python3 -m unittest discover -s tests/phone -p 'test_capability_policy.py' -v
```

The isolated CI workflow `.github/workflows/social-phone-capability-policy.yml` runs those checks for relevant PRs. Tests exercise preference, fallback consent, manual routes, ambiguity, strict scopes, capability mismatch, denied/unknown permission or auth, offline/degraded/unverified backend, duplicate IDs, uncertainty, active calls, malformed/unexpected fields, bounds and synthetic iPhone unavailable states.

**This is a synthetic policy proof, not phone feature certification**. Do not feed it real customer or personal phone records.

## 6 // NEXT / feasible implementation boundary

**P0 follow-up:** coordinate a genuinely trusted capability-report source with the Identity Center/Account Broker and existing Social shared integration owner, then agree device link lifecycle, revocation and request correlation. That is a *separate assignment*.

**Android network pilot candidate:** investigate KDE Connect's actual messages/contacts and permissions through a narrow, read-only source adapter first; only permit sending after live provider-confirmed receipt, device auth and opt-in. It is not implemented here.

**iPhone network feasibility:** ordinary iOS third-party apps cannot be presumed to read personal iMessage inbox or relay cellular calls; pilot permitted contacts/LAN features separately. Bluetooth MAP/PBAP/HFP candidate research remains isolated and opt-in. Neither BlueFerry nor any other third-party project has been paired or installed by this change.

**Calls:** require a distinct call-state and PC audio contract with HFP/BlueZ/PipeWire ownership verification; the pure route policy must not claim that KDE Connect call notifications supply live call audio.

**UI:** if backend evidence becomes real, the Social integration owner may add a PHONE section to the existing single Social window, with truthful states and compatibility tests. No second permanent window.

## 7 // HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Isolated executable **PLAN_ONLY** route policy, synthetic tests and CI; not a service that runs.

### HOW TO USE
Inspect the Python policy and run the test command above. No visible Social control exists for this prototype.

### VERIFY
Read repo branch SHA, GitHub CI exact-head outcome, and test logs. No network or hardware verification from this slice.

### WATCH OUT FOR
All passed-in `VERIFIED` claims are untrusted without a future protected proof source. This planner is not an identity authorization gate. Existing Social shared files and schemas remain owned elsewhere.

### CHECKLIST
- [x] Read architecture ADR and Syntagma/Hospital entry rules
- [x] Inspect current shared Social adapter and account catalog
- [x] Implement pure, no-side-effects policy, with strict schema
- [x] Add synthetic isolation, Bluetooth and send/call safety fixtures
- [ ] Exact-head CI success; verify workflow outcome
- [ ] Integration owner handoff and policy review
- [ ] Real provider/device feasibility, trust source and API boundary
- [ ] Operator acceptance; no merge assumed

### NEXT
Review draft PR; do not expand into shared UI, credential binding, runtime or physical phone pairing without scoped authorization and collision check.

### DECISIONS
Operator direction preserved: **network first**, **Bluetooth only optional per-capability fallback**, **iPhone and Android product targets**, **existing Social Hub UI**. A specific implementation library, pairing mechanism, identity broker and production API remain undetermined.

**NEXT WORKER:** recheck current Patient/main, Room/Assignment and PR ownership, reread the ADR and this contract, then coordinate the first verified network-backed Android capability probe without silently extending the scope.
