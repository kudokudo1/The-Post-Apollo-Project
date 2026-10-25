# Social // Account Manager handoff v0 (review proposal)

> **STATUS //** PROPOSED INTEGRATION CONTRACT; no account-manager API was found in this repository at review time  
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
> **OWNER //** Social shared integration; independent Account Manager owns identities, linked accounts, secret storage, authorization and consent  
> **SOURCE //** Operator direction, 2026-10-24: use the planned account manager to coordinate Social connections and avoid repeated individual setup  
> **RELATION //** Does not replace [native messaging adapter contract v1.0](../../services/messaging/ADAPTER-CONTRACT.md) or the [proposed schema v1.1](./social-messaging-schema-v1.1-proposal.md).

## Actual assets inspected

The current Social selector has **32 entries**. The `XBrowser.py` launcher defines
**21** service-specific Chromium profiles and Sway classes. Sessions is an
existing native bridge, Telegram has its own native auth panel, and Discord
uses the Vesktop app. Signal, Messenger and Viber are inert `UNSUPPORTED`
native adapters; WhatsApp, WeChat, LINE, KakaoTalk and BeReal have no verified
supported personal-inbox integration in this wave. Thunderbird's read-only
email-account inventory is **not** installed or exposed as an Email Social
mode (see issue #603); it is not included as an active connection target.

Existing browser profiles are **service-specific, not identity-specific**.
`XBrowser.py` currently reuses the same per-service data directory and Sway
window class across all Post-Apollo identities. Do not infer an account switch
from a Social button highlight or a future identity switch.

## Boundaries

**Account Manager owns:** Post-Apollo identity creation and selection;
linked provider-account references; per-identity button families, visibility and
ordering; user consent; sensitive credential storage; real provider authorization
and account switching where supported.

**Social owns:** service IDs and selectors; browser/native/external transport
launchers; provider-specific capability truth; frontend connection state,
status/error display and handoff requests. Provider API restrictions continue to
apply, even when Account Manager holds an account link.

**One batch request is not a universal login.** A `Connect All` intent
should prepare/check each requested service with independent results, allow
parallel work where safe, show partial completion and route interactive
verification/2FA/QR to the service's supported flow. It cannot silently inject
passwords, bypass providers, scrape private inboxes or claim that an already
open browser profile is authenticated.

## Available read-only integration surface

`services/messaging/SocialAccountCatalog.py` is a **nonmutating bridge** for
the future Account Manager to inspect/plan the existing services. It has no
network, secret store, profile switch, browser launch or login side effect.

`python3 services/messaging/SocialAccountCatalog.py catalog`

prints `{"schema":"post-apollo.social-accounts.v0","authority":"catalog_only","services":[...]}`
with each entry's stable `serviceId`, visible label, selector index and
`channel`. All `supportsManagedBatchLogin` flags are currently `false`
because no integrated authorization provider has been verified.

`python3 services/messaging/SocialAccountCatalog.py plan`

reads **one newline-terminated JSON request on stdin**:

```json
{
  "schema": "post-apollo.social-accounts.v0",
  "identityId": "default",
  "services": ["telegram", "x", "discord", "signal"],
  "linkedServices": ["telegram", "x", "discord"]
}
```

`identityId` is a nonsecret opaque identifier, not a name or email.
`linkedServices` denotes **the manager's declared links**, not proof of a
valid login. The manager owns real account references and does not send them
through this planning channel. `services` preserves identity-local ordering
supplied by Account Manager. Inputs with extra keys, unknown/duplicate
services or credential fields fail closed.

A result has `execution: "PLAN_ONLY"` and per-service:
`serviceId`, `selectorIndex`, `channel`, `status`, `nextAction`,
`authenticated: null` and `batchLoginPerformed: false`.

- `PROFILE_OPEN_AVAILABLE`: `default` identity only; browser profile can
  be opened later by the established Social launcher. This **does not**
  prove cookies exist, authentication is valid, or the linked account matches.
- `INTERACTIVE_AUTH_AVAILABLE`: Telegram supports its existing explicit
  in-menu QR/phone login for the default identity. No prompt is triggered by
  the planner.
- `STATUS_CHECK_AVAILABLE`: the existing Sessions native status can be
  queried after an approved manager handoff.
- `EXTERNAL_APP_AVAILABLE`: the Vesktop window can be opened; its profile
  is not centrally switched or authenticated by this planner.
- `UNLINKED`: no link was declared; manager must link the provider first.
- `IDENTITY_ISOLATION_PENDING`: a different Post-Apollo identity must **not**
  inherit the current service-global Chromium/Vesktop/native account. This
  is a blocker until identity-safe profile routing is implemented.
- `UNSUPPORTED`: provider personal messaging/mobile access is not supported
  by this wave, even if the manager has an account reference.

## Required next integration protocol (not yet implemented)

Once Account Manager publishes its **real process, API, and owner-approved
transport**, agree on a versioned request:
`connectAll({identityId, selectedServiceIds, requestId})`. Account Manager
must return separate per-service states such as `QUEUED`,
`AUTH_REQUIRED`, `WAITING_FOR_USER`, `READY`, `UNSUPPORTED`, `FAILED`,
and `CANCELLED`. Each completion must be correlated with its identity and
request to stop stale responses affecting another identity.

For websites, add *real* identity-specific Chromium profiles and Sway
window identifiers before enabling identity switching. Do not reuse the
existing single per-service profile as though it belonged to a second
Post-Apollo identity. Provider login screens and multi-factor challenges
must remain in approved service/browser flows, not synthetic credential
injection. For Sessions/Telegram, preserve their own session semantics and
request explicit per-identity support rather than copying SQLite sessions.
Discord/Vesktop profile switching may not be supported and must report so.

The Account Manager can show a single **Connect All** action, but it should
only call actual service-specific authorization actions when the provider
and manager have established that capability. Otherwise it groups available
profile openings and offers truthful per-service user actions.

## Verification and acceptance

The offline contract suite checks the catalog against the live 32-button
selector and 21 browser-site IDs, tests per-identity isolation and unsupported
states, rejects unexpected secret-bearing input, and verifies the planner
never executes processes or connects to a provider.

**Not yet authorized or proved:** live cross-account sign-in; identity-specific
browser launch profiles; Account Manager IPC binding; UI Connect All button;
Telegram/Discord multi-account profile switching; production activation.
Those need the manager's published interface, scoped implementation approval,
offline integration fixtures and a separate operator desktop acceptance run.
