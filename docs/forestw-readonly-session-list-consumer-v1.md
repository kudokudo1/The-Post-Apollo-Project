# 🏥💜 ForestW // Session-list consumer V1 (UI-owned staging)

**Patient:** The-Post-Apollo-Project  
**Room:** ForestW UI successor, existing contacts rail  
**Staff:** external Hospital-compatible DOC; live Hospital registration not verified  
**State:** SOURCE ONLY · **PRODUCTION READ/CHAT/VOICE HOLD**

## IMPLEMENTATION // What is staged

`services/forest/ForestSessionListConsumerPolicy.js` implements a **pure, non-authoritative** consumer for a *proposed* `LIST_SESSIONS` response. It accepts only a bounded, complete, request-correlated read-only snapshot, checks the currently selected Tree plus request generation, refuses unrecognized fields and malformed/private data, and returns only OPEN-session ID, title, revision and update time. It sorts open sessions newest-first. On any mismatch it returns no sessions and `UNAVAILABLE`.

**No IPC, filesystem, database, host process, provider enrollment, installed service, model inference, audio recorder or UI activation is added.** Existing `ForestW.qml` keeps `chatHostTrusted=false`, `voiceHostTrusted=false`, and `activeChatSessions=[]`. Even a structurally valid snapshot returns `sourceAuthenticated=false`, `permissionGranted=false`, `canReadSession=false`, and `safeActions=[]`. This parser cannot grant access.

The existing B1 `ForestSessionJournal.sessions(owner)` is synthetic, host-injected SQLite; the `owner_key` is a **filter, not authentication**. B4a `READ_SESSION` checks a *single known* session ID and publishes only ID, Tree, state and revision, **not a listing or titles**. C5's `authorize_read_session` currently refuses. Do not treat any of these as an installed authenticated `LIST_SESSIONS` provider.

## PROPOSED HOST CONTRACT // Requires Forest Core + Connections approval

The UI may eventually request **metadata only**, with:
- `action: "LIST_SESSIONS"` distinct from current B4a `READ_SESSION`;
- request-correlating `requestId` (16–96 allowed chars), visible presentation `treeKey` from one of the five configured Trees, and increasing local `generation` to discard stale replies;
- **no** user/owner key, database path, title, privileged permission flag, process ID, signer key, peer/seat proof or model permission supplied by QML.

The separately installed protected native host must **independently**:
1. Authenticate actual installed requester/peer process/lifetime, release and current unlocked seat through the C3e/C4b-approved boundary, not caller JSON, a Boolean, or same-UID socket credentials alone.
2. Enforce a distinct `LIST_SESSIONS` read entitlement and title/metadata disclosure policy through the approved C5 owner. `GENERATE`, `READ_SESSION`, `LIST_SESSIONS` and tools must not imply one another.
3. Choose the protected user's actual storage/database from **host-held custody**, verify owner isolation and storage integrity, apply the authorized Tree scope and bounded page **before serializing** any row.
4. Map UI Tree presentation keys to approved canonical Forest Core Tree keys. `BRISTLECONE_PINE` is currently only a UI presentation key; equality in untrusted input is not a grant.
5. Apply packet-byte limits (64 KiB proposed), reject duplicate JSON keys and malformed/noncanonical payloads on the host, supply host-owned request context, and stop disclosing upon revoke, seat change, process replacement, or host disconnect. The UI generation only prevents stale display, **not** privilege replay.
6. Return an exactly scoped, complete and bounded response **only after independent read admission**. Proposed view: `schema=postapollo.forest.list-sessions-ui.v1`, `action=LIST_SESSIONS`, matching requestId/treeKey/generation, `status=READ_ONLY`, `complete=true`, and at most 100 seven-field B1 session metadata rows. Titles are potentially private: their release requires explicit policy approval. If pagination is needed, define a separate approved version before partial results.
7. Keep transcript text, prompts, provider token streams, full author metadata, owner keys, recovery receipts and model thinking **out** of this response. Provide independent native tests for privilege isolation and future revocation ordering.

**Security warning:** Any client, test or fixture can fabricate this response. A structurally valid result alone MUST NOT set `hostConnected`, enable the ForestW session list, or activate SEND. Only an externally authenticated, separately approved host channel may deliver real data to the visible contacts panel. No trust field inside this JSON can substitute for that channel.

## HOW TO USE

For source inspection/testing only. No new desktop action until the upstream service exists. The recently merged prior ForestW rail still displays real B0 inventory results on an explicit user scan; chat list and SEND stay locked.

## VERIFY

```bash
python3 tests/forest/test_forest_session_list_consumer_v1.py
```

This uses Node.js for isolated pure-JS adversarial cases; no real personal data, Ollama, Connections issuer or filesystem mutation. GitHub CI adds it to the existing ForestW source-contract job.

## WATCH OUT FOR

- Do not import `services/connections/forest/ForestC5AuthorityBoundary.py` and reinterpret its deny-only reference mode as a real provider; `authorize_read_session` remains HOLD.
- Do not call B1 `sessions(owner)` directly from Quickshell or invent an `owner` key in QML.
- Do not reuse B4a's one-session read permission to enumerate session IDs or disclose title text. No automatic fallback to a different owner/Tree or synthetic fixtures when a provider is down.
- Do not label detected Ollama models as active agents, or call the currently five visible Tree choices five active conversations.
- The new consumer's schema and Tree mapping are a **UI proposal**, not a cross-owner signed contract. Real wire/schema/authorization choice belongs to Forest Core and Connections.

## CHECKLIST / NEXT

- [x] Implement pure fail-closed consumer and adversarial source test.
- [ ] Exact-head CI and Forest Nurse 2 scoped review.
- [ ] Forest Core + Connections agree on a distinct authentic `LIST_SESSIONS` operation and protected title disclosure.
- [ ] Independent installed native host, owner/seat/Tree scope and protected at-rest storage verified.
- [ ] Only then wire the approved host process to `ForestChatList` and test native live UI, with SEND/voice still disabled.
- [ ] Operator-controlled merge/deployment/final acceptance.

## DECISIONS

Source-only UI implementation is **not** permission to read real user sessions. Production remains HOLD; no ownership transfer to this UI worker, no automatic merge or host actions.