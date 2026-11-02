# Social Phone Bridge // KDE Connect SMS signal fixture P1 v0

> **STATE //** Isolated test receiver, **not a production Android SMS event subscriber**.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **BASELINE //** `main` at `a272b3851ffcb06a73bcea716bc30506ec96ef67` after operator merged PR #1029 (2026-11-02).
>
> **PROVIDER //** OPEN AI / CHATGPT, external Hospital-compatible. No live Hospital Room/Assignment, staff role, ownership claim or session registered.
>
> **SCOPE //** New `services/phone/qt/KdeConnectSmsSignalFixture.h/.cpp`, `tests/phone/qt/test_kdeconnect_sms_signal_fixture.cpp`, dedicated CI, contract and MODEL index. No changes to shared Social UI/router, Identity Center, P0 routing policy, existing native SMS decoder, host KDE Connect, Bluetooth or user machine.
>
> **DEPENDS ON //** [Network-first Phone Bridge ADR](./social-phone-bridge-network-first-adr-v0.md), [Qt D-Bus SMS decoder](./social-phone-kdeconnect-qt-dbus-decoder-p1-v0.md), [messaging adapter contract](../../services/messaging/ADAPTER-CONTRACT.md).

## 1 // Upstream D-Bus signal seam

The KDE Connect desktop `ConversationsDbusInterface` is a `QDBusAbstractAdaptor` constructed with `Device *` as its parent. Its interface `org.kde.kdeconnect.device.conversations` emits `conversationCreated(QDBusVariant)` and `conversationUpdated(QDBusVariant)` on the **device object's path**, `/modules/kdeconnect/devices/<deviceId>`. The separate SMS plugin methods, including `requestAllConversations` and `sendSms`, have their own `/modules/kdeconnect/devices/<deviceId>/sms` path. Mixing these would silently miss the signals.

Evidence inspected from KDE upstream:
- [ConversationsDbusInterface header](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/conversationsdbusinterface.h)
- [ConversationsDbusInterface implementation](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/conversationsdbusinterface.cpp)
- [SMS plugin request path](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/smsplugin.cpp)
- [Device object and D-Bus registration](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.cpp)

## 2 // What is actually implemented

`KdeConnectSmsSignalFixture` is a native QObject that receives these two named signals, routes the `QDBusVariant` to the **existing** `decodeVariant()` native decoder, and emits either a decoded in-memory packet or a fixed-code rejection.

**Critical fixture-only restriction:** the receiver's sender is hardcoded to `org.postapollo.phone.fixture`, **NOT** `org.kde.kdeconnect`. It will start only if that synthetic service is already owned by the **same process** on the supplied bus. It does not start services, choose session bus automatically, inspect phone identities, call request methods, or subscribe to a real KDE Connect daemon. This deliberate restriction prevents accidental access to the operator's messages. There is **no production subscription path in this PR**.

It uses `start(bus, deviceId)` only with an explicitly injected bus and syntactically bounded device ID, then exact sender + path + interface + signal name D-Bus match filters; `stop()` disconnects both signals and disables the output. A restart with a different device ID is explicit. The fixture emits only the decoded packet in memory; it does not print, save, cache, send or forward data to Social.

Fixed decoder failure reasons can be emitted as `rejected(code)` without echoing personal content. Test assertions verify wrong device path, wrong interface, unrelated signals and messages after a stop are ignored. All data is fictional.

## 3 // Synthetic testing

GitHub Actions workflow: `.github/workflows/social-phone-kdeconnect-sms-signal-fixture.yml`.

The job installs Qt6 and D-Bus **only on its disposable runner**, generates Qt moc code, compiles the native fixture against the merged Qt SMS decoder, and runs it inside `dbus-run-session` with a test-owned service. It checks sender ownership, path and interface filters, exact 64-bit values, invalid-variant error reasons, lifecycle and device isolation. The job also reruns all Phone Bridge Python offline regressions.

No KDE Connect daemon, test phone, personal message, network permission, Qt UI or Bluetooth transport is involved.

## 4 // Required production authorization seam (NOT implemented)

An actual production `org.kde.kdeconnect` subscriber must **not** be enabled by changing the hardcoded fixture service name. That would bypass the missing trust and consent boundary. The next contract/assignment must specify:

1. A trusted **human principal and device ownership** grant, per line/SIM and organization, with revocation from Identity Center/Account Broker.
2. A separate assertion of network route security, Android-side SMS permission, and actual plugin availability. KDE Connect's loaded plugin or a device path is not user authorization.
3. A process-bound D-Bus sender-owner proof, connection loss handling and safe teardown when a device or identity changes.
4. Explicit user action granting **message content** access, with an inactive-by-default subscriber and no background read of history.
5. A typed, one-way, scoped Qt/Python or native Social adapter handoff with no logging or cross-organization message leakage. The shared Social router remains the integration owner's task.
6. Independent permission for requesting history or sending SMS, including provider acknowledgement and duplicate-send prevention. Those methods are not called here.

The operator currently has an iPhone and no Android test hardware has been established. Real Android and iPhone acceptance remains **unverified**. This PR cannot grant iMessage access, calls or FaceTime.

## 5 // HOSPITAL HANDOFF

### IMPLEMENTATION
Fixture-only Qt SMS event receiver using exact KDE signal metadata and current decoder, with stop/restart and safe output handling.

### HOW TO USE
Run GitHub CI or native isolated test on a separately provisioned disposable development runner. No Post-Apollo UI or host diagnostic is activated.

### VERIFY
Check PR exact-head CI for successful synthetic D-Bus test and full Phone Bridge offline regression. These checks do not certify permission, phone delivery, Wi-Fi transport, or Android SMS access.

### WATCH OUT FOR
Synthetic sender `org.postapollo.phone.fixture` is deliberately not the real KDE service. Test data contains message body in-memory, so future hosts must protect it. A code edit that targets `org.kde.kdeconnect` is a **new security scope requiring explicit operator review**.

### CHECKLIST
- [x] PR #1029 merged and canonical Syntagma/adapter contracts consulted.
- [x] Verified KDE conversation signal interface and object path.
- [x] Isolated test-only signal receiver and private bus fixture.
- [ ] Exact-head GitHub CI and operator review.
- [ ] Trusted device/line grant, phone permissions and real network test.
- [ ] Explicit authorization for future production subscriber and Social integration.

### NEXT
Design the trusted principal/device/line grant and cancellation lifecycle in coordination with Identity Center. Obtain separate operator approval before a real D-Bus phone-content subscription. Do not present a working phone integration in the current Social UI.

### DECISIONS
Network-first persists; Bluetooth remains optional per capability. User's iPhone and Android are independent platform tracks. No live Hospital registration, local machine write, PR merge, real pairing, phone-content access or production activation occurred.
