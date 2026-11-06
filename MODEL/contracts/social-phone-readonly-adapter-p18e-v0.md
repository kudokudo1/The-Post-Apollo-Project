# Social PHONE P18e // Dormant read-only BlueFerry display adapter

> **STATUS:** GitHub-only, independent provider-specific adapter, **not connected** to the Social router, PHONE UI, authenticated host, or production phone access.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
> **ROOM:** Social PHONE P18e, adapter-only continuation, external Hospital-compatible continuity; live Room/Assignment registration **not verified**
> **WORKER / PROVIDER:** DOC-compatible external worker / OPEN AI // CHATGPT, no independent Identity Center, Account Broker or shared Social router ownership
> **BASE:** `main` at `576a76bc14fa0765bfbbc2d27cde770da9f77c26`, after P18d PR #1381 merged, no colliding open PHONE/Identity/messaging-router PR at preflight on 2026-11-06.
> **SHARED CONTRACT:** `services/messaging/ADAPTER-CONTRACT.md` v1.0, approved 2026-10-24.

## IMPLEMENTATION

P18a now normalizes BlueFerry's actual data. P18c has host-only read methods, and P18d models one-instance revoke-versus-release ordering. This milestone implements the **service-owned display adapter** that a future protected host and router can use after real access is authorized, without editing the shared router or bypassing the host boundary.

- `services/messaging/adapters/BlueFerryAdapter.qml` uses the **exact shared adapter surface**: `serviceId`, `active`, `backendMode`, `backendDetail`, `capabilities`, `conversations`, `loading`, `error`, `selectedConversationId`, `messages`, `messagesLoading`, `messagesError`, `sending`, `sendError`, `sendSuccessSerial`, and `refresh/loadMessages/refreshMessages/sendMessage`. Its data source is deliberately *not* BlueFerry D-Bus or an untrusted QML subprocess.
- The adapter is **inactive by default**, with no Process, Timer, storage, network, service start or automatic pairing. Normal `refresh()` and `refreshMessages()` do not invent a backend call and return false. `sendMessage()` always returns false, `sendSuccessSerial` never increments, and sending capabilities remain false.
- A potential, *owner-controlled* future display ingress is modeled through `beginHostView(contextKey, profileId, epoch)`, `applyHostProjection(contextKey, epoch, sequence, operation, payload)`, and `dropHostView(contextKey, epoch)`. These are **public QML functions with forgeable arguments**, NOT authorization; a random token and increasing epoch cannot authenticate an application. The integration owner must NOT wire an untrusted caller directly to these functions.
- A host context cannot be silently replaced. An inactive adapter clears all of its local arrays and selected conversation, and `dropHostView` matches context key/epoch before clearing. An older context or duplicate/out-of-order per-capability delivery sequence is ignored instead of overwriting newer data. Malformed records *within* the current context fail closed and wipe the adapter's local state.
- `services/messaging/adapters/BlueFerryProjectionView.js` is a **pure**, bounded parser of already-delivered P18a projection objects, not a phone data reader. It checks the exact schema, profile, `execution=OFFLINE_PROJECTION_ONLY`, `authorization=NOT_EVALUATED`, and `routeEligible=false`. Conversation/message records are copied with the shared Social-required fields, excluding internal native keys and unsupported features; message dates stay explicitly `iso8601-offset` and must be ordered. Contact cards are copied to a *separate* `contactCards` collection and must match the profile and daemon epoch. Contacts are **not** fabricated into message conversations.
- `backendMode=DEGRADED` only when there is a local cached read-only projection; it **never** claims a production trusted host, live feed, content grant, historical completeness or send support. Once an approved bridge exists, the shared integration owner may choose appropriate `READY` semantics based on *actual* operation availability. The adapter's own context fields are not cryptographically protected.

**No shared edits**: `widgets/messanger/PhonePane.qml`, `services/messaging/SocialMessageRouter.qml`, `services/messaging/SessionAdapter.qml`, `components/ConversationFeed.qml`, Identity Center, Account Broker, P18c read port, P18d release model, oFono and host audio files remain unchanged. Current Social PHONE content continues to be empty and sending disabled.

## HOW TO USE

**Current operator:** no new UI control, login, installation or live desktop change. P18e is a service-owned integration component in GitHub, not a running iPhone inbox.

**Future trusted-host / shared-router integration owner only:** after approving authenticated principal/session/device/line/consent and revocation, feed only **host-released** P18a projections to this adapter over an approved protected transport; initialize one opaque view context, deliver bounded separate `messages.read` and `contacts.read` snapshots with monotonic epochs and sequence numbers, and clear/wipe on sign-out, revoke, device switch, organization switch, permission loss, or broker restart. The host must own exact identity binding; a QML method accepting a caller-supplied token does not implement that.

## VERIFY

- `tests/messaging/test_social_phone_blueferry_adapter_p18e.py` composes the **real** P18a Python converter with synthetic native BlueFerry thread/contact fixtures and runs the **exact JavaScript validator** using a Node VM in CI. Positive checks validate conversation names, IDs, chronological messages, contact cards and no internal field exposure. Negative checks reject wrong profile/schema, fake authorization flags, reversed message order, invalid timezone, duplicate/cross-profile records, excessive lengths and malformed contact epochs.
- Static QML tests check the shared adapter field/function contract, inert default, separate contacts, old-epoch rejection, local state wipe, disabled send, no network/Process/Timer and **no** shared PHONE/router wiring.
- Existing PHONE CI workflow tracks the adapter, JS, tests and handoff and invokes the suite.
- **No Quickshell runtime, rendered PHONE UI, real protected IPC, BlueFerry call, local machine, iPhone or private message/contact access is exercised by the above tests.** Runtime acceptance is still required after a separately authorized host exists.

## WATCH OUT FOR

**Blocking cross-owner dependency:** `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` remains **PROPOSED**, with no verified assigned Identity Center/security grant authority or Account Broker permission/device-link implementation. The adapter cannot prove that an incoming QML object came from an authenticated host, and its `contextKey` is only an opaque correlation selector. The **full renderer/clipboard/cache purge** and a durable host-side revoke acknowledgment are **not** supplied by setting QML arrays to empty. Those guarantees require a reviewed actual IPC/process/UI lifecycle.

The standalone adapter intentionally reports a degraded cached view, not a live iPhone data session. BlueFerry's MAP/PBAP status, saved nickname, Bluetooth media connection or local organization/LLC label do not authorize reading private messages or contacts, and contacts remain separate from messages. The shared router contract's common timestamp unit/capability keys still require owner freeze. No additional auto refresh or sends are introduced.

## CHECKLIST

- [x] Recheck fresh `main`, merged P18d, Syntagma protocols, shared adapter owner, open PRs.
- [x] Reuse approved shared adapter contract and actual P18a projection shapes.
- [x] Add independent, dormant BlueFerry adapter with read-only methods and separate contact cards.
- [x] Add per-context epoch, per-operation sequence checks and fail-closed local wipe.
- [x] Add pure bounded JS projection validation, source and test/CI wiring.
- [ ] Exact-head CI.
- [ ] Operator review and merge.
- [ ] Verify QML runtime visuals under separately authorized deployment.
- [ ] Identity Center/security and Account Broker owners approve and implement actual grant/permission/transport.
- [ ] Shared router owner wires host-scoped PHONE content + reliable UI wipe.
- [ ] Live iPhone read-only Personal acceptance, then independently approved organizational separation.
- [ ] Separate multi-iPhone and oFono/HFP verification.

## NEXT

**P18f depends on an explicit cross-owner host decision.** Choose actual trusted process/IPC boundary, signed session verification, device/profile/line consent, durable grant generation, ability to force a reliable renderer wipe, and protected delivery semantics. The Phone Bridge owner can then connect P18c/P18d to that service and the shared router owner can attach this adapter to the existing Social PHONE conversations and contacts. Test manual revoke, sign-out, Personal-to-LLC/nonprofit selection, backend restart, partial history and stale callbacks with the actual iPhone before enabling.

Message sending, group reply, automatic background notifications, multiple simultaneous phones and oFono/HFP call routing remain independent capability assignments.

## DECISIONS

Stay within the independent BlueFerry service adapter file envelope. No unapproved Identity Center, Social router, shared UI, production auth, local machine write, Bluetooth/audio/oFono change or merge. The operator retains final authority. Recovery: close the draft PR, or revert its bounded commit if later authorized to merge.
