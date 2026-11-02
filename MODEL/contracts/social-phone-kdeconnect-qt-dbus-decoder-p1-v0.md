# Social Phone Bridge // KDE Connect native Qt D-Bus SMS decoder P1 v0

> **STATUS //** Isolated repository implementation for review; Qt synthetic CI and live device behavior separately gated.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **BASE //** `main` at `a936da790e688f90e822a7ef585f431e674360d4` (PR #1028 merged on 2026-11-02). Reacquire HEAD and ownership before subsequent work.
>
> **HOSPITAL //** External browser Doctor, OPEN AI // CHATGPT, Hospital-compatible only. No live Room, Assignment, Staff Role, Session or checkpoint claimed.
>
> **SCOPE //** New `services/phone/qt/KdeConnectSmsDbusDecoder.h/.cpp`, standalone native C++ test, Qt6-only CI, this technical contract and its index entry. Existing `KdeConnectSmsNormalize.py`, routing policy, probe, Social/Identity Center files, audio/Bluetooth settings and live Quickshell remain unchanged.
>
> **DEPENDS ON //** [Network-first Phone Bridge ADR](./social-phone-bridge-network-first-adr-v0.md), [decoded SMS normalizer](./social-phone-kdeconnect-sms-normalize-p1-v0.md), [messaging adapter contract](../../services/messaging/ADAPTER-CONTRACT.md).

## 1 // Concrete mechanism

KDE Connect emits `conversationCreated` / `conversationUpdated` D-Bus signals carrying a `QDBusVariant` whose value can be a `QDBusArgument` of KDE's `ConversationMessage` structure. This decoder has a **native Qt6 + QtDBus** function:

- `decodeVariant(const QDBusVariant &)` checks the exact D-Bus structure signature, then reads fields in KDE's sequence: `event: i`, `body: s`, `addresses: a(s)`, `date: x`, `type: i`, `read: i`, `threadID: x`, `messageID: i`, `subID: x`, `attachments: a(xsss)`.
- `decodeFields(const SmsFields &)` accepts the same values already decoded into typed in-memory objects and validates the **text-only** subset. Unsupported events, wrong group address counts, invalid states/read flags/IDs/timestamps and unbounded content fail without producing a packet.
- Successful output is an in-memory `QJsonObject` shaped for the existing provider-local `KdeConnectSmsNormalize.normalize_message()` Python code. Its `date`, `thread_id` and `sub_id` are **decimal strings**, because JSON numeric values may lose precision for large 64-bit IDs. `_id` remains a native 32-bit integer. Address entries are carried only in memory for existing normalizer validation and must be authorized before use.
- Attachment thumbnails, MIME fields and identifiers are **discarded** here. The outbound packet contains only placeholder entries so the downstream normalizer may set `hasAttachments`. Attachment files, MMS-only content and rich reactions are out of scope.

**Upstream evidence (inspected 2026-11-02):**
- [KDE ConversationMessage D-Bus field order and streaming operators](https://github.com/KDE/kdeconnect-kde/blob/master/models/conversationmessage.h).
- [KDE incoming Android message-map key names](https://github.com/KDE/kdeconnect-kde/blob/master/models/conversationmessage.cpp).
- [KDE SMS conversation D-Bus signals](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/conversationsdbusinterface.h).

This is real Qt typed decoding code, **not** a KDE Connect signal subscription or a live read. The independent native CI test constructs synthetic Qt structures only. It does not prove that an installed user's KDE Connect daemon exports the exact same runtime type/variant shape; that requires a separately authorized disposable-device test.

## 2 // Security and ownership boundaries

The decoder is a library with **no D-Bus connection, daemon start, subprocess, socket, polling, filesystem, UI output, pairing, SIM choice, message send or runtime activation**. It performs no authorization. Its returned packet can include sensitive body and participant addresses, so a trusted host must enforce person/device/line permission, memory boundaries and non-logging handling **before** invoking it. No raw phone content belongs in unit fixtures, PRs or diagnostics.

The historical `services/phone/KdeConnectDbusProbe.py` deliberately remains metadata-only. Do not repurpose it to request conversations. Any future event receiver needs explicit consent, a verified Android device, an independently verified LAN route, and a narrow user/line-scoped bridge that never turns plugin-presence evidence into authorization.

Never interpret native SMS `type=2` as provider delivery confirmation or increment `sendSuccessSerial` from decoding alone. This code has **no** send method and makes no claim about Android SMS permissions, personal iMessage, iPhone cellular calling, FaceTime, HFP call audio or Bluetooth fallback support.

The existing Social integration owner retains ownership of `MessagingW.qml`, `AppSelector.qml`, `ContactList.qml`, `ConversationFeed.qml`, shared message-router/timestamp policy and cross-provider acceptance. This PR does not change their schema or UI.

## 3 // Test / run instructions

Tests run only inside ephemeral GitHub Actions runner using `qt6-base-dev` and `pkg-config`. They compile with C++17, `-Wall -Wextra -Werror` and Qt6 Core/DBus, then execute the local in-process fixture:

```bash
g++ -std=c++17 -fPIC -Wall -Wextra -Werror \
  $(pkg-config --cflags Qt6Core Qt6DBus) \
  services/phone/qt/KdeConnectSmsDbusDecoder.cpp \
  tests/phone/qt/test_kdeconnect_sms_dbus_decoder.cpp \
  $(pkg-config --libs Qt6Core Qt6DBus) -o /tmp/post-apollo-kde-sms-decode-test

/tmp/post-apollo-kde-sms-decode-test
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

These commands are **developer-only** on a machine already provisioned with Qt6. Running tests doesn't activate KDE Connect, but do not install Qt packages or modify the operator's live desktop without explicit approval. The PR CI installs dependencies **only on its disposable GitHub runner**.

Tests verify timestamp/ID precision, native state values, group flags, read flags, content limits, attachment thumbnail suppression and the Qt D-Bus variant gate. All fixtures are invented.

## 4 // What remains unverified

1. Real D-Bus message delivery and the exact installed KDE Connect/Qt versions.
2. Authenticated principal/device/SIM line binding and revocation before exposing private messages.
3. Phone-side SMS permission and **network** transport verification rather than Bluetooth.
4. The Qt-to-Python handoff boundary: whether to keep the bridge native and emit a single IPC envelope, or use an approved native QML adapter. This is not chosen by the current implementation.
5. Acceptance of a read-only message event subscription with disposable Android test texts. No send path or auto-polling is authorized.

## 5 // HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Standalone Qt D-Bus SMS structure decoder and synthetic native test/CI; output compatible in shape with the already-merged Python normalizer. No caller integration.

### HOW TO USE
Review the new C++ source and isolated GitHub Action; no Post-Apollo button or resident service exists.

### VERIFY
Check PR exact-head CI results, confirm structural signature against installed KDE version during a later explicitly permitted hardware test, and distinguish local synthetic checks from genuine phone data.

### WATCH OUT FOR
The Qt output includes private decoded message content in memory; it must never be sent to GitHub Actions logs or developer traces. Header/source must compile with the selected Qt6 version. QDBusVariant marshalling may vary across runtime versions, so do not claim actual device support from fixture tests.

### CHECKLIST
- [x] Confirm #1028 merged, no active Phone Bridge PRs, Syntagma and source contracts.
- [x] Inspect KDE's Qt D-Bus ConversationMessage structure.
- [x] Implement native decoder with bounded text-only validation and error codes.
- [x] Add synthetic tests and isolated CI workflow.
- [ ] Exact PR-head native Qt CI successful.
- [ ] Operator review and merge, not implied by code/test status.
- [ ] Trusted event receiver, user permissions and real Android test device.

### NEXT
If CI and review pass, coordinate an **explicitly authorized and read-only** local message receiver using a disposable Android test conversation, after the identity/line and network trust boundaries are established. Never widen the old metadata probe silently.

### DECISIONS
Network-first continues as governing architecture. Bluetooth remains an optional per-capability fallback. iPhone and Android remain product targets with distinct platform constraints. No live Hospital registration, local machine mutation, new user interface, or production activation occurred.
