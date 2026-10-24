# Social Native Messaging // Schema v1.1 clarification proposal

> **STATUS //** PROPOSED FOR OPERATOR REVIEW, **NOT** AN ACCEPTED CONTRACT REPLACEMENT  
> **OWNER //** Post-Apollo Social shared integration  
> **PARENT //** [Shared Messaging Adapter Contract v1.0](../../services/messaging/ADAPTER-CONTRACT.md)  
> **SOURCE //** 2026-10-24 three-chat handoffs and shared integration review, issue #733  
> **SCOPE //** narrow compatibility clarifications; no new service permissions

This addendum proposes freezing the two intentionally open sections of contract
v1.0 before further native provider work. The integration branch uses the same
explicit Telegram capability names already present in its merged service adapter;
it does **not** claim that this document has been separately accepted or merged.

## 1. Capability object keys (proposal)

All new adapters should expose boolean keys under `capabilities`:

| Key | Meaning |
| --- | --- |
| `listConversations` | Can list the personal account's conversations |
| `readMessages` | Can read message history for a selected conversation |
| `sendText` | Can submit an outgoing text message with a provider-confirmed result |
| `liveUpdates` | Can deliver push updates (polling alone does not qualify) |
| `attachments` | Can handle native file/media messages in the shared UI |
| `calls` | Can make/receive calls in the shared UI |

Missing fields and non-`true` values are **false**. `backendMode:
"UNSUPPORTED"` has no usable capabilities, regardless of the presence of
adapter methods. `READY` must never be inferred from capability flags.
Existing `SessionAdapter.qml` predates the flags; the shared router is allowed
to use a **local Sessions-only compatibility exemption** for known text
functions until an explicit migration is approved. A provider's read-only
permission is not permission to send.

## 2. Timestamp representation (proposal)

New adapter data should provide `sent_at` and `active_at` as numeric UTC Unix
**seconds**. If the provider emits milliseconds, microseconds, or strings, the
provider bridge must convert using **documented native units**, not magnitude
guesswork. Null/unavailable timestamps must not become invented message times.

Telegram's Telethon bridge currently converts aware Python datetimes into Unix
seconds. The existing Session bridge passes through CLI/SQL data and has no
verified universal timestamp unit; its data must **remain untouched** in this
first two-service router change. Since the UI selects one provider at a time,
this does not cross-sort Session and Telegram records. Normalizing historical
Session values for a future combined timeline is a separate explicitly tested
compatibility job.

## 3. Composer lifecycle and routing

- Key a draft by **service ID + native conversation ID**, not native ID alone.
- A send acknowledgement belongs to the same service and conversation that
  originated the text; switching service/conversation cannot clear another
  draft.
- A provider's success serial must advance only for provider-confirmed success.
- Routing to an inactive or unsupported adapter must fail closed, with no fake
  contacts, messages or sends.
- Native selector index 0 remains Sessions; index 2 is Telegram. Browser and
  Discord selection contracts remain unchanged.

## 4. Acceptance boundary

This file is **reviewable proposed schema guidance**, not a unilateral rewrite
of the approved v1.0 document. Operator review and merge authorization remain
necessary. Offline source/mock checks are not proof of live login, successful
production sending or Sway compatibility.
