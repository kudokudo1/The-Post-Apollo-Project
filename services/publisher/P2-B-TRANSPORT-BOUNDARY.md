# Publisher P2.B // Host binding and transport rehearsal contract

**Patient:** The-Post-Apollo-Project  
**Room/role:** SocialW Publisher · external Hospital-compatible DOC (no verified
live Hospital registration)  
**State:** P2.B local source and test only. **No actual provider transmission.**

## What changes in real bytes and processes

P2.A already creates provider-specific JSON **previews**, not outbound
requests. P1 saves text drafts, media references, scheduled jobs, local access
request *labels* and operation history. None of those JSON/SQLite values can
authenticate a provider account.

P2.B adds a pure, bounded \`PublisherTransportBoundary.py\`. It takes a
P2.A preview and a **user-selected local binding candidate** containing:

| Field | Meaning |
|---|---|
| \`version\` | Contract version 1 |
| \`provider\`, \`scope\` | Selected provider and requested operation; text only |
| \`identityId\`, \`context\` | Local Social identity label and personal/organization context |
| \`accountAlias\`, \`destinationAlias\` | Unverified display labels, not account identity or channel ID |
| \`jobId\`, \`jobStatus\` | Caller-claimed P1 queue job ID and manually reviewed status |
| \`draftDigest\` | Caller-claimed 64-character digest for source comparison |
| \`previewFingerprint\` | Caller-claimed P2.A fingerprint for visual comparison |

These are **all untrusted input**. The contract refuses extra fields,
credentials, fake grants, invalid scope, mismatch between preview/provider,
stale fingerprint, a job not labeled reviewed, and malformed identity/alias
fields. Valid inputs produce a local candidate fingerprint to compare in
tests. They **never** produce authorization.

The \`authorize()\` and \`deliver()\` functions always answer
\`canDispatch:false\`, \`sent:false\`, \`providerReceipt:null\` and
\`TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED\`, regardless of caller-provided
"approved", "signed", "owner", "consented" or "not revoked" flags.

**Critically:** this code does not integrate with the Connections broker. The
current Connections source still advertises
\`credentialActionsEnabled:false\`; the existing C5d protected host source is
a disposable signed-reviewer fixture, not production human consent.
Do not treat those components as implemented publishing authorization.

## A real protected host must supply authority

A future Connections/Identity **owner-approved** service will need to
independently verify, at the moment of each send/refresh/retry:

1. The signed and still-running calling process, including its intended role.
2. Verified provider account and destination, not a user-typed alias.
3. Operator consent for exact scope, account, tenant and purpose.
4. Unexpired, unrevoked durable grant with a fresh trust check.
5. The exact stable queue job + current immutable source/media digest.
6. Provider-specific constraints, independent receipt reconciliation and
   duplicate-prevention state.

The protected service will own credentials and provider transport. It must not
trust a local QML flag, JSON record, caller-supplied fake signature, or an
unverified endpoint string. Its contract requires a separate approved
assignment with the Connections/Identity owners. P2.B adds **no** protected
host process, secret handling, localhost socket or public network dependency.

## Failure simulation (always marked mock)

The pure \`fixture_transition\` / \`fixture_observe\` methods model
\`fixture_prepared\` → \`fixture_pending\` → simulated confirmed or unknown
outcomes. They are internal **test-state values** and cannot send a post.

- If a simulated send times out, the item becomes \`fixture_unknown\`.
- A negative lookup does **not** prove no post exists. The item stays
  unknown and cannot automatically retry.
- A mock positive receipt can complete the simulation, but its returned
  \`providerReceipt\` is **always null**, \`realPosted\` is **always false**.
- A mismatched account or source content immediately blocks the fixture.
- A second "begin" when the first is pending/unknown/confirmed is refused.

This guards the most dangerous later failure mode: blindly repeating a post
after a timeout. These checks alone are **not real remote idempotency**.

## Provider receipt expectations, future only

Discord's webhook execution can return message information when using
\`wait=true\`; remote confirmation should be tied to the exact channel and
message ID. Bluesky/AT Protocol returns record URI and CID from a successful
record write. An owned website needs a separately reviewed publish endpoint
and response/reconciliation protocol. No P2.B result claims any of these
values. Current references:

- https://discord.com/developers/docs/resources/webhook#execute-webhook
- https://atproto.com/guides/writing-data
- https://atproto.com/specs/at-uri-scheme

Provider policies and APIs must be rechecked before a real transport is
enabled. The first live provider test must be explicitly operator initiated
on a disposable, genuinely authorized test destination.

## Verification and operator handoff

- Python unit tests cover provider/scope mismatch, tenant and destination
  binding, forged approvals, stale draft/preview identifiers, strict JSON
  fields, no network/credential import, mock timeout/unknown/duplicate paths,
  and zero real receipts.
- Existing P2.A adapters, P1 store/queue, and Social Settings tests run again.
- No P1 schema migration, QML UI redesign, background job installation or
  real posting occurs.

**Next:** P2.C must be coordinated with the owner of Connections/Identity
before attempting live authorization. P2.D should add actual transport
receipt persistence/reconciliation after the host has signed execution and
owner consent. Do not add a second unprotected credential or permit writer.

**Rollback:** Close P2.B's draft PR. The host, P1 data files and P2.A
mainline adapter remain unchanged.
