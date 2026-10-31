# Post-Apollo Identity Center // Account Manager Upgrade Plan v0

> **STATUS:** PROPOSED ARCHITECTURE + WORKER HANDOFF; operator approval required for implementation, merge, migration and production activation.
>
> **DATE:** 2026-10-31.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **SCOPE:** Social account-management upgrade plus future nationwide service-distribution-company workforce identity, branch authorization and application access.
>
> **PROPOSED OWNER:** Shared Post-Apollo Identity/Account Manager subsystem. Social remains a consumer; no worker, Team, Staff Role, Hospital Room or live Session has been assigned by this document.
>
> **SOURCE:** Operator direction in Social Hub discussion: one-stop in-product sign-in, no user-managed browser cookies or browser-settings setup, and future centralized branch/worker login management.
>
> **RELATION:** Extends [Social Account Manager handoff v0](./social-account-manager-handoff-v0.md). It does **not** silently replace its catalog contract, the approved [Social adapter contract](../../services/messaging/ADAPTER-CONTRACT.md), Syntagma policy, or provider authentication rules.
>
> **VERIFY LEVEL:** Current GitHub source read on 2026-10-31; no new identity service or live desktop/company environment was provisioned, tested or certified.

## 1 // Executive direction

Turn **Account Manager** from a Social-only inventory/planner into a **Post-Apollo Identity Center** shared by Social, future dispatch, scheduling, inventory, branch administration, worker tools and mobile/web clients.

**User-facing goal:** One Post-Apollo entry point to sign in, see the account and branch context, link approved external services, restore valid sessions, manage access, and reconnect on expiration. Users should never have to browse cookie folders, move session databases, run manual token commands, or use browser settings as the account-management UI.

**Security boundary:** "One-stop" means one control surface and coordinated workflow, **not** a promise that every third-party provider can authenticate entirely inside a Post-Apollo-owned form. Providers may require protected system-browser authorization, native app/device prompts, passkeys, QR or MFA. Post-Apollo initiates the action, returns the result to the same Account Manager view, and avoids cookie extraction, credential replay or prohibited embedded webviews.

**Architecture choice to review:** Use a mature, standards-based identity provider (IdP) for primary worker authentication and federation rather than building authentication cryptography or a new general-purpose password manager. Post-Apollo owns its business authorization model and Account Broker; the IdP provides authentication. Choice of IdP, deployment mode, and hosted/on-prem options are **not decided** here.

## 2 // Source-of-truth snapshot / protect what exists

These are implementation observations, not proof of running-desktop behavior:

| Current source | Observed capability | Boundary / remaining work |
| --- | --- | --- |
| `services/social/SocialIdentityStore.qml` and `SocialIdentityPolicy.js` | Local saved Social identity/organization metadata, families, visibility and selection | A local Social identity is **not** a proven employee login, central principal, or authorization grant. Preserve existing IDs and layout behavior. |
| `services/social/SocialAccountDetailsStore.qml` | Private local account notes and profile hints | Nicknames/phone/email fields are **not** authentication or credential proof. Do not turn them into secrets storage. |
| `services/messaging/SocialAccountCatalog.py` | Read-only service catalog and `PLAN_ONLY` Connect All planning | No credential storage, session checks, actual batch login or universal provider authentication. |
| `services/messaging/bridges/telegram/` and `adapters/TelegramAdapter.qml` | Native Telegram QR/phone pairing and optional identity-specific local session paths | Default shared session must stay intact; private account routing still needs live acceptance and optional persistence. |
| `widgets/messanger/XBrowser.py` and `MessagingW.qml` | Provider Chromium profiles and opt-in scoped browser windows | Browser windows/cookies do not prove identity or valid authentication. User must not manage cookie files. |
| `widgets/messanger/AppSelector.qml` | Existing Social Settings and Linked Accounts interface | Must remain the Social entry point, but not become the enterprise identity database. |
| `services/messaging/PROVIDER-ACCESS.md` | Provider desktop/web fallback contracts | Launch/dock does not grant native inbox or verified login APIs. |
| `MODEL/contracts/social-account-manager-handoff-v0.md` | Existing authority boundary and batch planner proposal | Read it before changing catalog schema or provider status semantics; parts describe the historical 2026-10-24 baseline and may lag merged code. |

**Do not erase or reinterpret:** old Telegram shared `personal.session`, browser profiles, family layout files, service IDs, ongoing provider authorization, unsupported-adapter statuses, operator UI layout decisions or any other worker's active code.

**Git baseline for this document's inspection:** `main` near `2e4d121b8cdc237a9819be6a9c03581f6a18e9de` on 2026-10-31. Workers MUST check latest HEAD, open PRs, branch ownership and current files again before coding.

## 3 // Target ownership and trust boundaries

```text
[[ Post-Apollo Identity Center UI ]]
  - My account / passkey / MFA / devices / sessions
  - Organization / region / branch / team selector
  - Linked services / Connect All / reconnect / status
  - Authorized admin / worker access management
                       |
                       v
[ Identity Center service / API gateway ]
  |          |                |               |
  v          v                v               v
[IdP/SSO] [Authorization] [Account Broker] [Audit / policy]
             |                |
    [Org/role/grants DB]  [Protected vault refs]
             |                |
             v                v
      [Post-Apollo apps]  [Provider adapters]
         Social, Dispatch,     Telegram, sanctioned
         Jobs, Scheduling,     OAuth/API, provider-
         Inventory, etc.       owned browser/native flows
```

**Identity Center owns:** authenticated people and workforce identity references; organization membership; branch/region/team scopes; role/permission grants; user consent; session and device policy; account-link records; provider connection orchestration; revocation workflows; audit semantics; stable versioned APIs.

**Identity provider owns:** secure primary authentication, account recovery and federation primitives, authenticator lifecycle, passkeys/MFA, and issuance/validation of signed identity assertions or tokens.

**Account Broker owns:** connection attempts, reauthorization coordination, per-provider status evidence, request correlation, refresh/revoke where permitted, and secret references. A single "Connect All" request is a **batch of independently authorized provider operations**, not one universal password login.

**Credential Vault owns:** protected application secrets, refresh tokens and other sensitive credentials only as needed, scoped by owning organization/person/provider. Use a reviewed key management solution with encryption at rest, key rotation and scoped access; do not put reusable secrets in Social QML, identity JSON, PRs, logs or process arguments. Local native provider session files may remain with their provider and must not be copied into a central credential database by default.

**Social owns:** existing UI, service selection, chat/provider adapters, app-specific capability truth, and display of Account Broker statuses. Its local `identity-N` IDs are organization/layout handles until an explicit, reviewed migration maps them to authenticated principals.

**Business apps own:** their domain records and action authorization checks. A Social login should never authorize dispatch, payroll or inventory actions merely because the account name matches.

**Authorization lives on the server/API**, not just in UI show/hide rules. Every request must verify tenant, principal, active session and resource scope.

## 4 // Proposed domain model (names and schema are review candidates)

| Record | Key fields / meaning | Invariant |
| --- | --- | --- |
| Person / Principal | immutable `principalId`, IdP subject/issuer, status | Each human has an individual account; display names/emails can change. |
| Organization | `orgId`, policy/ownership | Separate organization data and authorization boundaries. |
| Region / Branch / Team | opaque IDs, parent org, explicit memberships | A region's manager sees only granted branches, not every tenant. |
| Membership | `principalId`, `orgId`, optional branch/team, lifecycle | Invite, active, suspended, terminated, transferred are distinct. |
| Role / Permission | role definition and granular action/resource permissions | Deny by default. Enforce scope and least privilege. |
| Assignment / Grant | who, permission/role, branch scope, approver, expiry | Temporary and cross-branch access expires and is auditable. |
| Device / App Session | sessionId, subject, device, assurance, expiry/revoke state | Server validation and revocation; secure local cache is not authoritative. |
| Linked Provider Account | `accountLinkId`, subject/org/service, provider account reference | Do not identify provider account by nickname alone. |
| Credential Reference | vault pointer, owner, provider, scope, rotation metadata | Never store plaintext passwords or refresh tokens in catalog/notes. |
| Connection Attempt | requestId, subject, service, scope, nonce/state, status | Idempotent, correlatable; stale completion cannot switch identity. |
| Audit Event | eventId, actor, action, object, scope, time, decision, requestId | Tamper-evident retention/access policy; avoid secret payloads. |

Separate **human login**, **organization/branch role**, **connected external account**, **device session**, and **Social layout identity**. One person may belong to several branches, have time-bounded grants, and link multiple provider accounts. Their effective authority must not be derived from account nicknames, geographic location or whatever window is currently focused.

## 5 // One-stop user experience

### Worker first sign-in (company-owned apps)

1. Worker opens Post-Apollo and chooses **Sign in** inside the Identity Center.
2. IdP authenticates with passkey or supported MFA, using its secure auth mechanism.
3. Identity Center fetches active organization/branch memberships and only authorized app choices.
4. Worker selects an allowed branch/context. Post-Apollo passes a scoped, short-lived authorization context to each company app.
5. Reopening Post-Apollo securely resumes a valid session where policy permits; expiration, revoked access, elevated action or new device asks for a fresh authentication or step-up.
6. Sign out / revoke device / leave organization invalidates backend sessions, not just local UI state.

### Social or external service connection

1. User selects **Identity Center → Linked Accounts → Connect** or **Connect All**.
2. Broker enumerates supported services and obtains user consent for each requested scope.
3. Telegram uses its existing in-widget QR/phone provider process. Compatible OAuth/OIDC services use official authorization-code + PKCE via **an OS-protected external user-agent** when required; after redirect/device-code completion the user returns to the same Post-Apollo screen.
4. Existing provider-owned apps/browser sessions may be opened through Post-Apollo, but are reported as **UNKNOWN** until supported provider evidence establishes authentication.
5. Broker stores only needed secret references, maps link to correct principal/org/identity, updates truthful status and can attempt supported silent refresh only where the provider authorizes it.
6. Expired/revoked/not-linked entries show **Reconnect**, **Sign-in required**, or **Unsupported**, never a fabricated success message.

No cookie-folder steps. No scripted credential filling into arbitrary provider websites. No MFA bypass or synthetic cookies. No universal "sign in to 32 services" guarantee.

### Manager/administrator

An authorized manager opens **Identity Center → Organization → Branches / People / Access**, invites a worker, grants a narrowly scoped role, sets expiry if temporary, and sees an auditable confirmation. Branch transfer or termination withdraws company access and initiates supported external-provider revocations without deleting personal accounts.

## 6 // Proposed API and process contracts (not yet implemented)

Define versioned typed interfaces before modifying QML or provider adapters. Below are *examples to review*, not active endpoints:

```json
{
  "contract": "post-apollo.identity-center.v0-proposal",
  "requestId": "opaque-request-id",
  "actorSessionRef": "opaque-authenticated-session-ref",
  "organizationId": "org-example",
  "selectedBranchId": "branch-example",
  "operation": "connectServices",
  "serviceIds": ["telegram", "x", "discord"]
}
```

The authenticated caller identity **must** come from a validated server session or signed assertion, not a client-supplied email, mutable QML label or bare `identityId`.

Response rows should include `serviceId`, `requestId`, `accountLinkId` (if known), `status`, `evidenceSource`, `lastCheckedAt`, `nextUserAction`, `requiresInteraction`, `providerCapability` and sanitized `errorCode`. Suggested statuses:

- `UNLINKED`, `CHECKING`, `CONNECTED_VERIFIED`, `REAUTH_REQUIRED`, `WAITING_FOR_USER`, `UNKNOWN`, `UNSUPPORTED`, `FAILED`, `CANCELLED`.
- `CONNECTED_VERIFIED` requires provider-specific evidence, not a nonempty cookie directory, open window, account note or local vault entry.
- Scope every event, cached result, refresh operation and send acknowledgment to the immutable subject, organization, account link, provider and request generation.
- Explicit consent is required for account linking and any privilege-increasing operation. No automatic credential/session migration.
- Separate authenticated workforce APIs from optional personal Social accounts. Keep personal account data inaccessible to branch admins unless specifically authorized by a legitimate enterprise integration.

**Core operations to define:** `getMySession`, `listMemberships`, `selectAuthorizedContext`, `listLinkedAccounts`, `connectService`, `connectServices`, `getConnectionStatus`, `disconnectService`, `listDevices`, `revokeSession`, `listAuthorizedWorkers`, `grantScopedRole`, `revokeGrant`, `offboardWorker`.

Define a service-owner contract and threat model for each operation before implementing the transport or storage. Preserve current `SocialAccountCatalog.py` `PLAN_ONLY` semantics until a versioned broker is explicitly accepted.

## 7 // Security and production invariants

- **Default deny** across organizations, branches, devices and provider account links; test against IDOR/cross-tenant access and privilege escalation.
- **Passkeys or phishing-resistant MFA** preferred for workforce login; require stronger step-up authentication for privileged actions, payroll/payments and account recovery.
- **No shared worker credentials**; use named service accounts with constrained permissions only when required. Never make a branch's generic password the master identity.
- **Session security:** secure issuance, bounded TTLs, refresh/rotation strategy, server-side revocation, lost-device response, replay protection, idle limits per risk and authoritative context checks.
- **Secrets:** provider-specific least-privilege scopes, encryption at rest/in transit, key ownership/rotation, restricted logs, no secret values in repo/CLI arguments/QML/config metadata/telemetry. Do not assume 0600 file permission equals encryption at rest.
- **Audit:** actor, action, target, grant/revoke decision and correlation IDs; protect against tampering; retention and privacy/access policy require operator/legal decisions.
- **Account recovery/offboarding:** verified recovery and emergency access paths, dual control for critical admin operations, no irreversible removal of provider personal accounts, tested organization and branch deprovisioning.
- **Offline:** if a branch device has no network, allow only explicitly designed bounded offline functions; no local cache may mint new privileges or make expired/revoked credentials appear valid. Document how revocation propagates after connectivity returns.
- **Third-party flows:** conform to the provider's terms and authorization mechanism; RFC 8252 requires native OAuth to use an external user-agent, not a credential-intercepting embedded webview. Prefer auth-code + PKCE, official device code or native approved flows. Do not claim all providers support APIs or silent refresh.
- **Operations:** per-tenant backups/recovery, high availability suitable for nationwide operations, observability without secrets, time synchronization, incident response and staged rollout. Security and compliance certification are future work, never inferred from passing unit tests.

References: [NIST SP 800-63-4](https://csrc.nist.gov/pubs/sp/800/63/4/final), [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html), [OAuth for Native Apps / RFC 8252](https://www.rfc-editor.org/info/rfc8252), [SCIM / RFC 7644](https://www.rfc-editor.org/info/rfc7644).

## 8 // Worker work packages and dependency plan

Proposed lanes are **not assignments**. Room/Team/owner must be confirmed in Hospital and GitHub before a worker begins. Do not take ownership of another service by editing its files from a Social ticket.

| Lane / scope | Deliverable | Prerequisites | Acceptance evidence |
| --- | --- | --- | --- |
| **A. Architecture & threat model** | IdP/build-vs-buy evaluation, domain boundaries, trust diagram, threat model, API ADRs | Operator decisions on organization/tenant model | Reviewed design, misuse-case test plan, no unresolved trust-owner collision |
| **B. Workforce authentication** | IdP-backed login, passkeys/MFA, recovery, device/session UI, token validation | A | Test IdP in disposable environment, expiry/revoke/step-up and recovery fixtures |
| **C. Branch authorization** | Organization → region → branch → team memberships, role/grant service, enforcement middleware | A + B | Multi-tenant cross-branch denial, manager delegation, temp expiry and offboarding tests |
| **D. Secrets & vault integration** | Key-management decision, secret-reference APIs, rotation/backup strategy, no-secret logging | A + B | Security review, encryption/key isolation, lost-key recovery and no plaintext-leak checks |
| **E. Account Broker** | Versioned provider capability registry, connect/refresh/revoke/interactive queue, truthful status, partial Connect All | A + D | Each provider reports distinct supported capability; no fabricated login, secrets or cross-account leakage |
| **F. Social integration** | Existing Settings uses new broker status/actions; Telegram identity and browser profile routing retained | E; coordinate with Social owner | Login/reconnect UX, safe identity switching, stale-result and window-focus tests |
| **G. Enterprise admin & provisioning** | People/Branches/Access UI, invite/transfer/offboard, SCIM evaluation, audit export | B + C + D | End-to-end manager and worker tests, severed access on revocation and privacy review |
| **H. Ops, verification & pilot** | Deployment topology, staged rollout, monitoring, backup/restore, desktop/mobile/web trust testing | B through G incrementally | Security review, controlled branch pilot, incident rehearsal, operator sign-off |

### Suggested release sequence

**Phase 0 — Decisions and contract freeze:** agree on primary identity authority, branch hierarchy, secret store approach, interface boundaries, provider capability matrix and no-browser-cookie promise. No code migration.

**Phase 1 — Workforce identity foundation:** implement a single *test* organization and two branches with one admin, one branch manager and a worker. Exercise IdP authentication and server-enforced access; avoid coupling to Social until stable.

**Phase 2 — Secure Account Broker:** versioned provider status, consent, connection attempts, explicit account-link ownership, vault references and reversible Connect All orchestration. Start with one supported provider and mock fixtures; never promise all 32.

**Phase 3 — Existing Social upgrade:** connect current Linked Accounts UI to broker; keep existing social layout and provider-specific adapters; fix browser/private-account mode persistence behind opt-in and verify on real Quickshell/Sway.

**Phase 4 — Workforce console and branch pilot:** invite/transfer/offboard, scoped admin controls, branch isolation, device loss, revocation and audit. Test offline/poor connectivity and privilege boundaries before expansion.

**Phase 5 — Nationwide rollout:** availability and disaster recovery plans, controlled region waves, training/support and documented acceptance for dispatch/scheduling/inventory integrations.

**Stop gates:** No transition merely because tests compile. Require live runtime evidence, security verification, operator approval, rollback path and owner acceptance per phase.

## 9 // Migration, compatibility and rollback

- Introduce a **separate mapping** from local Social `identity-N` to centrally authenticated principal/organization scope; do not mutate existing `social-identities-v1.json` or treat the first identity as an enterprise administrator.
- Keep legacy shared Telegram, existing per-identity private Telegram session paths, browser profile directories, and current Account Details notes intact during the pilot. No bulk cookie import, profile copy, password extraction or session reassignment.
- A broker rollout should be versioned and opt-in; the current Social behavior should remain available behind an explicit fallback until accepted.
- Migrate only with explicit consent, mapping preview, backup and reversible transformation. Where third-party session migration is unsafe, require provider-supported reauthorization.
- Reverse a failed rollout by disabling the new broker integration feature flag and restoring prior known-good code/config snapshots. **Never** roll back by deleting provider session files or user credentials.
- Preserve separate recovery paths for central IdP outage, lost authenticator, organization admin lockout, compromised device, expired external provider token and cross-branch permission error.

## 10 // Verification matrix

Mandatory scenarios before launch:

1. A worker for Branch A cannot read Branch B dispatch, inventories, payroll or linked accounts.
2. Regional manager sees only explicitly granted branches; corporate administrator performs privileged actions with step-up.
3. Worker transfers branches; old grant expires/revokes even if a device still caches the old layout.
4. Contractor's limited assignment expires without affecting their personal Social accounts.
5. Manager offboards a worker; Post-Apollo company sessions revoke; provider revocation is attempted/reported per supported capability and failures remain visible.
6. Device lost/stolen; server session revoked, private files and UI cannot recreate authority.
7. Two Telegram private identities display separate conversations, drafts and provider confirmations, including when delayed responses arrive after switching.
8. Website opens under correct identity-isolated browser profile; window existence or saved cookies never count as verified authentication.
9. Provider denies, expires or requires MFA; broker reports accurate state and stays in the Account Manager workflow.
10. Connect All produces partial success and independent consent, retries and cancel actions. Unsupported services remain unsupported.
11. IdP unavailable/branch offline: policy-defined fail-closed behavior without privilege escalation.
12. Vault restart/backup/rotation and audit log access work without disclosing secrets.
13. Quickshell, Sway, external provider and local/remote contexts are tested independently; synthetic tests do not count as live acceptance.

Document each result with exact commit, test environment, data scope, operator acceptance and rollback. Never test with real worker passwords, production tokens, or unauthorized personal accounts.

## 11 // Questions requiring explicit operator decisions

- **Identity provider:** self-hosted or managed, and which standards-compliant provider? Who administers its recovery keys?
- **Tenancy:** one nationwide company or multiple legal organizations/franchises? May one worker be employed by multiple organizations?
- **Control plane:** always-connected central backend, local-first with bounded offline rights, or hybrid? What locations/processes own secret storage?
- **Authentication:** required passkeys/MFA levels, device enrollment, emergency break-glass authority and recovery approvals?
- **Legacy account semantics:** what happens to Social identity-1 and existing shared Telegram/browser sessions?
- **Organization accounts:** which external accounts belong to the company versus workers personally? How are shared service accounts controlled and audited?
- **Provider UX exception:** acknowledge that official OAuth may require OS-protected browser/system-auth and redirect; the Post-Apollo dashboard remains the management surface.
- **Retention/compliance:** required audit retention, privacy boundaries, payroll-specific restrictions, data residency and operational recovery objectives.
- **Release authority:** who owns Identity Center code, its Hospital Room(s), security review, merges and production activation?

These are **open decisions**, not permission to select a vendor or deploy infrastructure.

## 12 // Hospital-compatible worker handoff

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
**ROOM:** Not verified / not registered by this external conversation.
**DOCTOR / PROVIDER:** External ChatGPT planning contribution / OPEN AI // CHATGPT.
**ASSIGNMENT:** Document the proposed Identity Center upgrade; no implementation assignment granted to other workers.
**PERMISSIONS:** Plan/document/review only; code changes, local writes, live account access, merge and deployment need their own authorization.
**CHECKPOINT:** Inspect this plan, the current Account Manager contract, latest GitHub HEAD/PRs and Syntagma's `AGENTS.md` and Hospital protocols before work.

### IMPLEMENTATION
Documentation-only proposal for a nationwide-ready Identity Center, preserving Social's current code boundaries. No backend, credential store, workforce tenant or provider login implementation is implied.

### HOW TO USE
Workers should read sections 1–7 for scope/ownership, select a bounded lane from section 8 **only after assignment**, and use sections 9–11 for migration and acceptance gates. Keep Social as consumer of the shared service.

### VERIFY
Current repository paths and source architecture were inspected. External authentication standards are linked above. **No source modifications beyond this proposed plan/index, no live Quickshell validation and no enterprise acceptance.**

### WATCH OUT FOR
Do not equate a Social local identity with a company worker, account nicknames with successful authentication, browser cookies with managed credentials, or a launchable desktop client with native provider access. Never place enterprise credentials in repo, chat, screenshots, logs or test fixtures.

### CHECKLIST
- [x] Operator goal translated into cross-product architectural work plan
- [x] Current Social account-manager boundary preserved
- [x] Proposed domain model, flows, security invariants, lanes and test gates documented
- [ ] Operator accepts architecture and resolves the decisions in section 11
- [ ] Hospital ownership/Rooms/Assignments confirmed
- [ ] APIs and threat model reviewed and frozen
- [ ] Implementation verified in synthetic and live controlled environments
- [ ] Explicit operator approval for rollout and final acceptance

### NEXT
Operator review → select IdP/tenancy/deployment/security boundaries → appoint worker owners and define first disposable two-branch pilot → create bounded implementation PRs with independent verification.

### DECISIONS
**Proposed:** one shared Identity Center; standards-based authentication; centrally enforced branch authorization; protected Account Broker and Vault; Social as a client; one in-product login-management UI with provider-compliant external authorization exceptions. **Not yet accepted as implementation authority.**
