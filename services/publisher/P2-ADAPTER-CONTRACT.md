# SocialW Publisher // P2.A adapter contract (OFFLINE preview)

**Patient:** The-Post-Apollo-Project  
**Scope:** Publisher-owned source files only, no change to shared messaging
adapters, Social Phone, Connections, Identity, or installed workstation.  
**State:** First P2 code slice. Pure payload shaping plus a stand-alone
preview CLI; **not an authorized publishing transport**.

## Fundamental mechanism

P1 contains local text drafts, media references, templates, a SQLite
schedule/review queue, account access *intent* labels and local event history.
None of those objects is a provider grant.

P2.A translates a user-reviewed **text-only** post into the actual *shape* a
provider would eventually accept. It does not choose the destination, access a
session, execute HTTP, upload a file, or create a provider receipt.

\`services/publisher/PublisherProviderAdapters.py\` is pure Python with:

- \`prepare(provider, title, body, createdAt, language, media)\` returning a
  bounded, provider-specific preview and explicit \`canDispatch:false\`,
  \`sent:false\`, \`providerReceipt:null\`.
- \`dispatch(...)\` unconditionally returning
  \`TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED\`. No forged QML flag, fake signed
  record, or crafted JSON can enable it.
- \`preview_from_json(raw, provider)\` allowing only exactly the five
  non-secret fields \`title\`, \`body\`, \`createdAt\`, \`language\`, \`media\`.
  Duplicate JSON keys, unknown fields and malformed input fail closed.
- An offline CLI reading a bounded JSON envelope **from stdin**, not
  credentials or account aliases from command-line arguments.

\`previewFingerprint\` is a local SHA-256 checksum for visually comparing
previews. It is **not** a transport idempotency key, cryptographic approval,
remote publication identifier, or immutable-media snapshot.

## Provider-specific mappings (P2.A)

| Adapter | Allowed P2.A content | Prepared operation | Why no transmission |
|---|---|---|---|
| Discord | Plain text up to 2,000 characters | \`discord.executeWebhook\`, \`content\`, \`allowed_mentions:{"parse":[]}\`, \`tts:false\` | Requires server/channel owner consent, securely held webhook, authorized invocation, and \`wait=true\` provider message confirmation |
| Bluesky | Plain text (conservative 300 Unicode code points) | AT Protocol \`com.atproto.repo.createRecord\` with \`app.bsky.feed.post\` record | Needs verified DID, owning PDS, authenticated grant, and returned \`uri\` + \`cid\`; no local layout alias may substitute for DID |
| Owned website | Title + text body | \`postapollo.owned_site.localDraft\` with \`publicationState:"draft"\` | There is **no universal website publishing endpoint**; requires separately approved site-specific contract, owner and route |

All providers refuse attached media in this slice. Future image/video adapters
must use a fresh asset validation and upload/reconciliation pipeline; existing
P1 file-reference existence is not sufficient proof of a safe media upload.
No automatic text splitting, long-form truncation, link rewriting, unsolicited
mention creation, fake analytics, or duplicate posting.

Language metadata is only attached to the Bluesky \`langs\` field when supplied;
it never translates the text.

## External provider specification evidence (recheck before enabling)

- Discord official webhook execution API:
  https://discord.com/developers/docs/resources/webhook#execute-webhook
- Discord official allowed mentions:
  https://discord.com/developers/docs/resources/message#allowed-mentions-object
- AT Protocol post-record writing:
  https://atproto.com/guides/writing-data
- Bluesky official post structure:
  https://bsky.network/docs/about-bluesky-content/posts/

Provider behavior, limits, access and review requirements change. The
transport owner must reverify documentation and current provider policies at
activation, and must not infer account/organization access from Social local
identity profiles.

## Permissions and operation ownership

The trusted publishing transport belongs behind a separately approved,
host-owned Connections/Identity grant. Before **each** attempt, refresh, and
retry, it needs evidence of:

1. Calling signed program / operating process identity and intended purpose.
2. Verified provider account + destination channel/record/site identity.
3. Explicit operator consent for that account and exact operation scope.
4. Personal/organization tenant binding, expiry and revocation status.
5. Current immutable source draft/media digest and scheduled-job status.
6. Provider-specific user restrictions and a retry/reconciliation policy.

The future transport cannot treat a local \`PublisherAccessIntentStore\` JSON
row as authorization. P1.4 review state remains deny-only until a separately
approved queue-to-transport integration. P1.6 local events must never be
relabeled as provider receipt evidence.

**Duplicate/post ambiguity:** A timeout after an HTTP request does not prove
that posting failed. Later transport must reconcile with the provider before
retrying. For Discord, opt for \`wait=true\` and require an observed message ID;
for Bluesky, require returned record URI and CID; neither receipt exists in P2.A.
No automatic repeat on ambiguous completion.

## How to exercise this slice (offline only)

Use the code/tests after branch installation. A fixture (not a real post)
might look like:

\`\`\`sh
printf '%s\n' '{"title":"Demo","body":"Hello from an offline fixture","createdAt":"2026-11-17T08:00:00Z","language":"en","media":[]}' \
  | python3 -I -B services/publisher/PublisherProviderAdapters.py --provider discord
\`\`\`

This prints a preview JSON object with \`canDispatch:false\`. It does not
open a connection, select a Discord channel, queue a post, or write a file.

## VERIFY / NEXT

- P2.A unit tests assert exact provider schemas, lengths, safe mention
  handling, malformed input refusals, media refusal, zero secrets, zero network
  imports, forged-grant denial and a subprocess CLI round trip.
- Existing P1 tests and Social Settings contracts continue to run.
- P2.B next: independent protected host-broker contract for account binding,
  approved execution scopes and dry-run transport receipts. This is an
  ownership/permission dependency, not permission to edit Connections or
  enable real posts.
- P2.C after broker acceptance: one provider at a time, with explicit
  user-initiated test posts on disposable authorized accounts, verified
  provider receipts and crash/timeout reconciliation. No rollout is implied.

**Rollback:** Close the draft PR. No P1 data schema migrations, local
workstation mutations, network connections or token storage were introduced.
