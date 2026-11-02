# Social Phone Bridge // KDE Connect Android SMS text normalization P1 v0

> **STATUS //** Isolated offline implementation candidate, **not a phone reader** or Social widget integration.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **DATE //** 2026-11-02.
>
> **BASE //** `main` at `083072c694013a154586eb71bb55be1a52986104`, verified after PR #1023 merged. Recheck current branch, PRs, source and Hospital ownership before continuation.
>
> **SCOPE //** New `services/phone/KdeConnectSmsNormalize.py`, `tests/phone/test_kdeconnect_sms_normalize.py`, targeted workflow, this contract and MODEL index. No edits to shared Social router, adapter contract, existing D-Bus diagnostics, account policy, phone pairing or live desktop.
>
> **CONNECTION //** External Hospital-compatible worker only. No live Hospital Room, Staff Role, Assignment, Session or checkpoint verified.

## 1 // What this implements

The upstream KDE Connect SMS plugin uses an Android-origin message representation with keys `event`, `body`, `addresses`, `date` (Unix milliseconds), `type`, `read`, `thread_id`, `_id` and optional `sub_id` or `attachments`. Those message maps are converted by KDE's `ConversationMessage` C++ type into its own structured D-Bus signal argument. **A real D-Bus client must decode that C++/Qt structure or access authenticated packet data before using this module; the module does not parse raw D-Bus wire bytes.**

This component takes already-decoded synthetic message maps and produces provider-local records aligned with required fields of [Shared Messaging Adapter Contract v1.0](../../services/messaging/ADAPTER-CONTRACT.md): stable message `id`, `conversationId`, `body`, `direction` and `sent_at`; it also supplies `serviceId=kdeconnect-sms`, `nativeStatus`, `timestampUnit=unix_ms`, read/group/attachment-presence flags.

The timestamp unit is **explicitly local** to this provider. The shared integration-owner's canonical cross-provider timestamp contract remains unfrozen and is **not** changed here. No global Social data shape is altered.

**Source inspected:**
- [KDE ConversationMessage model and D-Bus structure](https://github.com/KDE/kdeconnect-kde/blob/master/models/conversationmessage.h)
- [KDE model's packet map decoding](https://github.com/KDE/kdeconnect-kde/blob/master/models/conversationmessage.cpp)
- [KDE SMS packet and request semantics](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/smsplugin.h)
- [KDE conversation event emitter](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sms/conversationsdbusinterface.cpp)

KDE's upstream types are `qint64` for dates/thread IDs, `qint32` for message IDs, and Android `type` values 1 (inbox), 2 (sent), 3 (draft), 4 (outbox), 5 (failed), 6 (queued). **An outgoing native type 2 is not a provider-confirmed delivery receipt and cannot increment Social's send-success counter.** Current scope deliberately supports nonempty text events only (`event=1`, or group text event `event=3`). Other event flags, attachment-only messages and complex MMS behavior are rejected as unsupported, rather than fabricating content.

## 2 // In-memory trust and data scope

The pure `normalize_message(packet, principal_ref, device_ref, line_ref)` function accepts only a fixed field subset, bounds sizes, validates signed numeric widths, and returns in-memory data. `normalize_conversation(packets, ...)` sorts oldest-first, collapses exact duplicate observations and raises on conflicting message IDs or mixed threads. It performs **no** subprocess, D-Bus, KDE Connect, file I/O, network, logging, contact lookup, SMS send or auto-polling.

The caller provides opaque `principal_ref`, `device_ref`, and `line_ref`; these are **not authenticated by the normalizer**. A trusted upstream broker must prove each association and distinguish personal phones from any independently authorized organization-managed line, including SIM `sub_id` binding and revocation. The module will not derive user ownership or a phone number from untrusted `addresses` or `sub_id` fields.

Conversation IDs are deterministic `<principal>:<device>:<line>:<thread_id>`; message IDs extend this with `:<_id>`. Because the delimiter is disallowed inside the opaque refs, scopes remain distinct. The native `_id` and thread ID are scoped to a phone; they are **not globally unique** by themselves. The caller must ensure opaque refs remain stable over authorized sessions and avoid leaking private identifying tokens into logs.

This is **UI-content code**, unlike the prior privacy-reduced device-diagnostic summaries: it intentionally returns the decoded `body` for a future authorized conversation feed. It does not return participant addresses, attachment thumbnails, raw SIM IDs or attachment blobs. Do **not** pass real personal text messages into synthetic tests, issue reports, GitHub logs or diagnostics. The future adapter/host must protect message content in memory, IPC and any optional encrypted cache.

## 3 // Unsupported or not-yet-proved behavior

- A loaded desktop `kdeconnect_sms` plugin is **not** proof of phone-side SMS permission, user ownership, actual network transport, conversation history access, delivery, RCS or MMS support.
- No real paired Android device, SMS conversation or permission is verified by this PR.
- KDE Connect SMS D-Bus emits structured `QDBusVariant` and `ConversationMessage` values; a vetted Qt/D-Bus decoding adapter and its permission boundary are **separate** work.
- The normalizer does not send messages. It cannot claim that queued/draft/failed/outbox state means successful sending, and it does not synthesize a delivery/read receipt. Group and attachment flags are descriptive only.
- The schema does not certify iPhone SMS/iMessage access, which uses different platform and Bluetooth constraints. Existing network-first and opt-in Bluetooth architecture remains unchanged.
- No changes to `MessagingW.qml`, `AppSelector.qml`, `ContactList.qml`, `ConversationFeed.qml`, shared adapter schemas, Identity Center, account broker or phone transport.

## 4 // Offline verification

From the repository root:

```bash
python3 -m py_compile services/phone/KdeConnectSmsNormalize.py tests/phone/test_kdeconnect_sms_normalize.py
python3 -m unittest discover -s tests/phone -p 'test_kdeconnect_sms_normalize.py' -v
```

Dedicated GitHub Actions workflow: `.github/workflows/social-phone-kdeconnect-sms-normalize.yml`. Synthetic fixtures cover incoming/sent/draft/outbox/failed/queued, decimal timestamp strings and exact milliseconds, signed integer bounds, stable IDs across refresh and across user/phone/line scopes, malformed inputs, address/group rules, attachment content redaction, strict fields, duplicate-safe ordering and mixed-thread rejection.

Passing mock tests demonstrates **local transformation invariants only**. It does not demonstrate real Android SMS read/send or desktop rendering.

## 5 // Next acceptance gates

1. Operator review and merge of this isolated PR, not automatic acceptance.
2. Separately approved local invocation of the merged read-only D-Bus diagnostic from PR #1023, or a disposable KDE Connect test environment. The diagnostic's `--probe` flag is **not** auto-run by this module.
3. A specifically approved paired Android test device, network transport proof, and phone-side SMS permissions. No personal content in diagnostics.
4. Trusted device/account/line binding and revocation; non-logging structured Qt/D-Bus `ConversationMessage` decoding.
5. Read-only message event delivery on approved disposable fixtures, then Social integration-owner review before connecting the shared conversation UI.
6. Actual sending, delivery semantics, contacts and call audio remain independent gated milestones.

## 6 // HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Isolated in-memory KDE SMS text message normalizer, deterministic scoped IDs, native state mapping, and chronological deduplication; tests and CI, indexed contract.

### HOW TO USE
Run the offline tests above or call `normalize_message` on **synthetic decoded packet maps only**. There is no user-facing phone integration in this slice.

### VERIFY
Check PR exact head, CI job steps, and source read-back. No real phone or local D-Bus interaction was performed.

### WATCH OUT FOR
Message `body` is sensitive and must only enter future trusted UI flows. Upstream D-Bus is a typed C++ structure, **not** a JSON reply; this module needs a vetted decoder. `sub_id` does not prove an authorized line. Native outgoing `sent` does not prove actual delivery.

### CHECKLIST
- [x] Prior P1 probe merge and Syntagma/shared adapter contract checked.
- [x] Actual upstream KDE SMS model/fields inspected.
- [x] Message normalization and 26 offline synthetic tests authored.
- [ ] Exact-head CI passed.
- [ ] Operator review, integration owner coordination and merge.
- [ ] Trusted decoded device data, user consent and live device acceptance.

### NEXT
Create a bounded Qt/D-Bus message decoding interface with explicit read-only and person/device/line authorization, then approved phone test data and integration-owner handoff. Do not wire or activate the Social widget yet.

### DECISIONS
Preserve network-first, optional Bluetooth fallback and dual iPhone/Android targets. This change implements an offline transform, not live SMS, phone calls or an authorization service. No registered Hospital worker/room or production deployment is claimed.
