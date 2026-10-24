# Post-Apollo Social Hub // Shared Messaging Adapter Contract v1.0

> **STATUS //** OPERATOR-APPROVED (2026-10-24)  
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
> **DOMAIN //** Social Hub / native messaging adapters  
> **OWNER //** Post-Apollo messaging subsystem; operator controls assignment and acceptance  
> **SCOPE //** shared adapter behavior, normalization, worker isolation and integration gates  
> **SOURCE //** operator-approved three-chat adapter architecture decision (2026-10-24)  
> **IMPLEMENTATION //** contract only; does not certify an adapter, router or live account integration

This is the **one shared technical contract** for separately developed Post-Apollo
native messaging adapters. Each service bridge is independent; the existing
Social contact list and chat feed are reused. The shared router has **one
designated integration owner**. Individual service workers must not implement
their own parallel UI routers or change shared controls.

This contract is owned by the Post-Apollo technical source tree. Authority,
cross-worker coordination and reporting remain governed by the canonical
[Syntagma AGENTS](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md)
and [Hospital protocols](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/tree/main/OPERATE).
Approval of this specification is **not** permission to merge PRs, mutate a local
desktop, activate production or claim live Hospital registration.

## 1 // Architecture and responsibilities

```text
[provider / supported API, SDK, desktop service or verified bridge]
                            |
                 service-specific bridge
                            |
               <Service>Adapter.qml
                            |
             common adapter contract (this file)
                            |
        shared router (one integration owner; to be built)
                            |
        existing ContactList / ConversationFeed
```

- **Service bridge:** authenticated transport, provider semantics and capability
  discovery. It owns no shared UI components.
- **Service adapter:** normalizes service-native objects into the fields below.
  It owns the service's connection status, data, errors and sending lifecycle.
- **Shared router:** selects one active adapter and binds that adapter to the
  contact list and conversation feed. It owns app selection, switching and
  integration into `MessagingW.qml`.
- **Shared UI:** renders normalized conversation/message objects; does not
  implement provider-specific authentication or transport.

An independent platform needs its own adapter unless multiple services share an
actual interoperable client protocol (for example, Matrix homeservers through
one Matrix adapter). Website-backed Social modes do not automatically require
native chat adapters.

## 2 // Required QML-facing interface

Every new adapter exposes these **exact public names**. No worker may silently
rename or narrow the interface.

| Member | Type | Required behavior |
| --- | --- | --- |
| `serviceId` | string | Stable lower-case provider identifier, e.g. `telegram` |
| `active` | bool | Router-controlled permission to run active provider work |
| `backendMode` | string | Connection/authentication state |
| `backendDetail` | string | Human-readable status detail, no secrets |
| `capabilities` | object | Explicit supported/unsupported operation flags |
| `conversations` | array | Normalized conversation list |
| `loading`, `error` | bool, string | Conversation-list load/error state |
| `selectedConversationId` | string | Selected provider-native conversation ID |
| `messages` | array | Normalized history for the selected conversation |
| `messagesLoading`, `messagesError` | bool, string | Message load/error state |
| `sending`, `sendError` | bool, string | Pending send/error state |
| `sendSuccessSerial` | int | Increment **only after provider-confirmed success** |

Required functions (names and arguments are part of the contract):

- `refresh()`: refresh normalized conversations.
- `loadMessages(conversationId)`: select a conversation and fetch its history.
- `refreshMessages()`: fetch updates for the selected conversation.
- `sendMessage(conversationId, text)`: request a text send; its immediate return
  indicates **local acceptance only**, never provider confirmation or delivery.

A successful provider send increments `sendSuccessSerial`; a failed or
unsupported send must **not** increment it. This preserves the existing
`ConversationFeed.qml` behavior: unsent composer text is not cleared on
failed sends.

Existing `SessionAdapter.qml` provides much of this surface. Migration to
new members (including `serviceId`, `active` and `capabilities`) may use a
compatibility wrapper owned by the integration assignment, not a speculative
service-worker rewrite.

## 3 // Normalized conversation and message records

**Conversation** fields:

| Required | Optional |
| --- | --- |
| `id` (string, stable provider-native ID) | `nickname` |
| `serviceId` (string) | `active_at`, `avatarInProfile` |
| `type` | `members`, provider-specific metadata |
| `displayNameInProfile` | |
| `lastMessage` | |
| `unreadCount` | |

**Message** fields:

| Required | Optional |
| --- | --- |
| `id` (stable ID) | `type`, `senderId` |
| `conversationId` | `attachments`, delivery status |
| `body` (string) | provider-specific metadata |
| `direction` | |
| `sent_at` | |

Rules:

1. `direction` is precisely `incoming` or `outgoing`.
2. The adapter delivers messages **oldest to newest** to the shared feed.
3. IDs must remain stable across reloads, not be regenerated on each refresh.
4. Logical conversation identity is the pair `(serviceId, native conversation id)`.
   Never treat two different services' coincidentally equal native IDs as one
   conversation.
5. Normalize timestamps consistently across providers. **Timestamp unit is not
   yet frozen** in v1.0 and must be agreed in the shared integration contract
   before different provider histories are combined, sorted or compared.
   Workers should keep native units explicit and report them in their handoff,
   not guess at a universal unit.
6. Omit unavailable fields or report unavailable capabilities. Never fabricate
   message content, read status, contacts, delivery confirmation or identity.

## 4 // Lifecycle, authentication and data isolation

- The **router** controls which service adapter is `active`.
- An inactive adapter must not continuously poll, run unsolicited login flows,
  send messages or replace the selected adapter's displayed data.
- An adapter explicitly reports sign-in, device pairing, permissions, degraded
  operation or unsupported capabilities.
- The approved states are:
  `PROBING`, `AUTH_REQUIRED`, `READY`, `DEGRADED`, `UNSUPPORTED`, `ERROR`.
- `READY` is permitted only when the declared functions actually work.
  A read-only client may still be available, but must declare sending unsupported.
- Prefer supported incoming events/streaming to unnecessary polling. Bounded
  polling is acceptable when the provider requires it.
- Associate async responses with the requested service and conversation.
  Stale callbacks must not overwrite another selected service/conversation.
- Do not print/store credentials, tokens, decrypted content or private data in
  test logs or UI error messages.

**Current compatibility note:** `SessionAdapter.qml` has an unconditional
5-second conversation polling timer and a 3-second selected-message timer. It
does **not** yet implement the common `active` lifecycle. This is known
migration work reserved for the integration owner, not proof of compliance.

## 5 // Capabilities and minimum functional slice

Adapters must truthfully indicate whether the platform supports:

- Conversation listing
- Message history reading
- Text sending
- Live incoming updates
- Attachments/media
- Calling or voice messages

The first shared UI target is **text messaging**. Attachments, rich embeds,
reactions, calls, voice messages and advanced group operations are later
capability extensions. A read-only adapter is acceptable if it transparently
reports that limit and the router disables unsupported controls.

**Open implementation detail:** the exact `capabilities` object keys and
timestamp representation require a single integration-owner freeze before
independent workers ship cross-adapter fixtures. A worker must not define
a conflicting global schema on its own.

## 6 // File boundaries and parallel ownership

Each service worker uses **one separate assignment, branch and draft PR**.
Proposed service-scoped files:

- `services/messaging/adapters/<Service>Adapter.qml`
- `services/messaging/bridges/<service>/`
- Distinct service-scoped contract tests under `tests/messaging/`

Paths above are **ownership envelopes**, not permission to create an
unnecessary bridge or to edit another service's files.

**Integration owner only:**

- `widgets/messanger/MessagingW.qml`
- `widgets/messanger/AppSelector.qml`
- `widgets/messanger/ContactList.qml`
- `components/ConversationFeed.qml`
- `services/messaging/SessionAdapter.qml`
- Shared router and shared adapter contract/fixtures

Service workers may **read** these shared files but must not independently
write them. When blocked by a shared change, report it to the integration
assignment instead of making an overlapping edit.

Before writing, inspect fresh `main`, open PRs, current task ownership and
the relevant Hospital compatibility protocols. Preserve other assignments.

## 7 // Development and Git process

- Branch from verified current `main`.
- Report the baseline SHA and contract version in the PR.
- Implement only the assigned service and its isolated tests.
- Never assume that another ChatGPT conversation is registered to live Hospital.
- Stop for scope expansion, security risk, unsupported service behavior or
  an ownership collision.
- Do not merge PRs, activate production, or change the operator's live machine
  without the required authorization.
- Any breaking change to this contract must be handled by the integration
  owner and reaccepted by the operator, rather than silently diverging.

## 8 // Minimum tests and acceptance

Use mock accounts/provider responses for all offline tests. Every adapter must
verify:

1. Conversation listing/normalization.
2. Message retrieval, chronological order and stable IDs.
3. A successful backend-confirmed send increments `sendSuccessSerial`.
4. Failed/unsupported sends do not increment success or clear unsent text.
5. Auth-required, degraded and unsupported-capability reporting.
6. Safe service/conversation changes while requests are in flight.
7. No unexpected network polling or login work while inactive.
8. No real personal credentials required by the offline suite.

Provider-specific integration tests and live login/runtime verification are
**separate gates**. Passing mock tests does not certify a working external
account, encryption bridge, call service or desktop interaction.

## 9 // Integration and handoff

An adapter is **integration-ready**, not automatically merged or live, when it:

- Passes its isolated contracts.
- Identifies the real supported provider interface and account/setup flow.
- Declares supported capabilities and limitations.
- Supplies setup, failure behavior, test evidence and rollback/handoff notes.

Only the shared integration owner wires verified adapters to `MessagingW.qml`
and chooses which one provides contacts, messages, loading and sending actions.

Workers hand off using the seven canonical Hospital report sections:
**IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT,
DECISIONS**. Include base/head SHA, branch, draft PR, test results, blockers
and shared seams requested. Hospital-compatible external chats must not claim
live Room, Assignment, Worker or Session registration without verification.

## 10 // Stop conditions and approval scope

Stop and report rather than inventing a workaround when:

- No supported personal-account integration method is verified.
- Account access requires unauthorized credentials, device behavior or
  prohibited service access.
- A necessary change touches another worker's owned files.
- Platform restrictions make a promised function unreliable.
- The adapter needs a breaking shared contract change.

**Operator-approved scope:** define this contract and isolate future worker
implementation. Acceptance of this document **does not allocate service
assignments** or authorize adapter construction, shared-router edits, merges,
local-machine modification or live service activation.

### Source and verification record

- Approved by operator in this project's conversation on 2026-10-24.
- Inspected against `services/messaging/SessionAdapter.qml`,
  `services/messaging/SessionBridge.py`,
  `widgets/messanger/MessagingW.qml`,
  `widgets/messanger/ContactList.qml` and
  `components/ConversationFeed.qml`.
- This is a **normative technical contract**, not a statement that the current
  runtime already implements it.
- Syntagma continues to own cross-project authority and Hospital semantics;
  this code-adjacent document owns only the Post-Apollo adapter contract.
