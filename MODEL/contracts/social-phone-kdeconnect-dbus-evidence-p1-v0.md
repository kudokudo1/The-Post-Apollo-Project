# Social Phone Bridge // KDE Connect D-Bus plugin evidence P1 v0

> **STATUS //** P1 isolated executable synthetic evidence classifier; no real D-Bus call or phone integration.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **BASE //** `main` at `58f8ef7192eedb430729c53c2804a019c25b6d2b` on 2026-11-02 after merge of PR #1021. Recheck GitHub HEAD and active ownership before further action.
>
> **AUTHORITY //** Operator-selected [network-first Phone Bridge ADR](./social-phone-bridge-network-first-adr-v0.md), subsequent [P0 route planner](./social-phone-capability-policy-v0.md), and [P1 device-presence probe](./social-phone-kdeconnect-presence-p1-v0.md).
>
> **SCOPE / OWNERSHIP //** `services/phone/KdeConnectDbusEvidence.py`, `tests/phone/test_kdeconnect_dbus_evidence.py`, a targeted CI job, this contract, and the model index. No shared Social UI/router, Identity Center, Account Broker, existing P0/P1 APIs, Bluetooth settings, KDE Connect installation, phone pairing or local Quickshell change. No verified live Hospital role, room, assignment, session or checkpoint.

## 1 // Mechanism: what KDE Connect actually exposes

KDE Connect's desktop daemon registers objects with D-Bus. A paired device object exposes metadata and methods which an authorized local process may inspect, including:

- `org.kde.kdeconnect.device` at a per-device object path, with `isPaired`, `isReachable`, `supportedPlugins`, `activeProviderNames`, `type`, and `loadedPlugins()`;
- `loadedPlugins()` reports desktop plugin instances loaded for that device; supported plugins are computed from advertised packet capabilities, and enabled plugins are loaded only for paired, reachable devices;
- desktop plugin metadata names `kdeconnect_sms`, `kdeconnect_contacts`, and `kdeconnect_telephony`;
- `org.kde.kdeconnect.device.sms` has methods including `sendSms` and `requestAllConversations`, and `org.kde.kdeconnect.device.conversations` includes reply/query operations;
- `org.kde.kdeconnect.device.contacts` includes `synchronizeRemoteWithLocal()`, which can trigger remote contact transfer;
- the telephony plugin handles call **events/notifications**, not general PC audio bridging.

These facts are grounded in KDE upstream desktop source (as inspected 2026-11-02):
- [Device properties and scriptable methods](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.h)
- [Device plugin lifecycle and registration](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.cpp)
- [Daemon D-Bus entry](https://github.com/KDE/kdeconnect-kde/blob/master/core/daemon.h)
- [SMS interface](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/smsplugin.h)
- [Conversation interface](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/conversationsdbusinterface.h)
- [Contacts interface](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/contacts/contactsplugin.h)
- [Telephony interface](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/telephony/telephonyplugin.h)

**CRITICAL DIFFERENCE:** Reading *metadata* (plugin loaded, paired, reachable) is not reading messages. Nor does a loaded desktop SMS plugin prove Android SMS permission, a valid SMS transport, correct phone user or line, recipient identity, or provider-confirmed send. D-Bus metadata does not prove network instead of Bluetooth. The device's `type=phone` does not identify its OS as Android. Telephony events do not give PC microphone/speaker access.

## 2 // What this slice implements

A pure offline `assess(observation)` function takes a caller-supplied synthetic representation of the D-Bus *device metadata* and returns a **redacted descriptive summary**. The function does **not** open session D-Bus, instantiate KDE Connect, run a CLI, inspect contacts, read messages, modify permissions, or launch a daemon. The inputs are untrusted: even reported `isPaired=true` cannot become an authenticated user's phone association.

Exact input keys:
- `schema: post-apollo.phone.kdeconnect-dbus-evidence.v0`
- `isPaired`, `isReachable`: real booleans (not int/string truthiness)
- `deviceType`: bounded opaque KDE device-type token (e.g., `phone`), **not platform verification**
- `supportedPlugins`, `loadedPlugins`: bounded unique opaque desktop plugin identifiers
- `activeProviderNames`: bounded unique identifiers, whose semantics are not treated as proof of network transport

Output:
- `execution: ASSESS_ONLY`, `provider: kdeconnect`, schema and `state`;
- `reportedPhoneType`, `reportedActiveLinkCount`, but **no raw plugin names, link provider names, device IDs, phone numbers or addresses**;
- `sms`, `contacts`, `telephonyEvents` plugin categories, each either `LOCAL_PLUGIN_LOADED`, `SUPPORTED_NOT_LOADED`, `NOT_ADVERTISED` or `NOT_EVALUATED`;
- `smsPermission`, `contactsPermission`, `callAudio`: all `NOT_CHECKED`;
- `transport` and `devicePlatform`: always `UNVERIFIED`;
- `routeEligible: false` **unconditionally**.

The snapshot is `INCONSISTENT_REPORT` if an allegedly loaded plugin was not advertised as supported, loaded plugins appear while not paired or reachable, or link providers are reported while unreachable. Such snapshots yield `NOT_EVALUATED`, never route eligibility. Other descriptive states: `NOT_PAIRED`, `NOT_REACHABLE`, `PAIRED_REACHABLE_REPORTED`. Input contracts fail closed with a raised `ValueError` for malformed/unexpected fields, duplicate plugin/provider names, bad types and excessive data.

**This is not an extension of P0's capability schema.** It intentionally cannot generate a verified `CapabilityPolicy.py` candidate. That requires a separate trusted broker, per-user device/line binding, authenticated event evidence and exact operation/permission checks.

## 3 // Tests and verification

From the repo root:

```bash
python3 -m py_compile services/phone/KdeConnectDbusEvidence.py tests/phone/test_kdeconnect_dbus_evidence.py
python3 -m unittest discover -s tests/phone -p 'test_kdeconnect_dbus_evidence.py' -v
```

CI: `.github/workflows/social-phone-kdeconnect-dbus-evidence.yml`.

The 20 synthetic tests cover local SMS/Contacts/Telephony plugin detection, supported-but-not-loaded, absent plugin, unpaired/offline and inconsistent snapshots, platform and transport non-inference, malformed or secret-bearing fields, type coercion, duplicate/bounded names, redaction and permanently disabled routing. No live D-Bus, KDE Connect daemon, SMS, contacts, call or network is accessed by the suite.

## 4 // Path to a real Android read-only probe (not yet authorized)

Before writing a live D-Bus reader, the next assignment must:
1. Reacquire main, shared Social ownership, live Hospital state if connected, and source code for the installed KDE Connect version rather than assuming `master` matches the host.
2. Decide who is authorized to read local KDE device metadata. A session-bus query might launch `kdeconnectd`, so treat local execution and its side effects separately from repository work.
3. Use only allowlisted **read-only** device metadata getters; avoid `requestAllConversations`, `sendSms`, `synchronizeRemoteWithLocal`, `setPluginEnabled`, and pairing/link-provider state changes during capability discovery.
4. Bind device identity and account/line scope to a trusted personal principal with revocation; do not map opaque device IDs into Social layout labels as proof of ownership.
5. Verify Android OS and active network transport using independent trustworthy evidence; `activeProviderNames` is only a report of link implementations and does not by itself prove path security or authorization.
6. Obtain the phone-side plugin permissions and **function-specific read behavior** from an explicitly approved device and disposable test content. A plugin loaded on Linux cannot certify SMS/contacts service.
7. Get Social messaging integration-owner review before any adapter, shared router, UI or message-send work. Provider send success must be distinguished from local D-Bus acceptance, delivered status, and unknown outcomes. Calling/audio has its own controller/verification gate.

No FaceTime, iMessage, personal carrier call bridge, new permanent Social window or cross-organization account authorization is implied.

## 5 // HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Pure offline, privacy-reduced KDE Connect D-Bus metadata classifier, tests, workflow and indexed contract.

### HOW TO USE
Run the synthetic unit test command above or inspect source. No actual local device diagnostic exposed by this slice.

### VERIFY
GitHub read-back and exact-head workflow outcomes must be checked separately; source-only verification cannot certify real device permission, transport, or call audio.

### WATCH OUT FOR
Desktop plugin presence is only local evidence. Don't translate `LOCAL_PLUGIN_LOADED` into `READY`, `VERIFIED`, `GRANTED` or a send authorization. No local machine changes or Bluetooth fallback were made.

### CHECKLIST
- [x] Verify PR #1021 merge and current main, Syntagma, shared scope.
- [x] Confirm upstream D-Bus metadata and plugin names.
- [x] Add isolated classifier and adversarial mocks.
- [ ] Exact-head GitHub CI result.
- [ ] Operator review and merge approval.
- [ ] Separately authorized trusted local D-Bus probing, phone-side permissions, identity and transport verification.

### NEXT
Review draft PR and scope next read-only live diagnostic separately, without pairing or extracting personal phone data. Restore ownership and exact-head proof before continuation.

### DECISIONS
Operator-selected product direction remains network-first, Bluetooth opt-in per capability, iPhone and Android target, existing Social Hub UI. No new production API or phone-connection vendor is selected.

**NEXT WORKER:** Use the current Patient/Room/Assignment and source as authority, not conversational status; do not merge or deploy without operator approval.
