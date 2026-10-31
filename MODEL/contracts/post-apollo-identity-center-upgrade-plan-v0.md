# Post-Apollo Identity Center // Multi-Organization & Portfolio Upgrade Plan v0.1

> **STATUS:** OPERATOR-DIRECTED REQUIREMENTS + PROPOSED TECHNICAL ARCHITECTURE + WORKER HANDOFF. Multi-organization/portfolio scope is operator direction; implementation, vendor, schema, access policy, merge and deployment still require separate approval.
>
> **DATE:** 2026-10-31.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **SCOPE:** One personal login across multiple distinct legal entities, nonprofit and for-profit organizations, family-linked and personally owned portfolios, partners and future external customer tenants; regional/national/global operations, workforce access and Social provider accounts.
>
> **PROPOSED OWNER:** Shared Post-Apollo Identity/Account Manager subsystem. Social remains a consumer; no worker, Team, Staff Role, Hospital Room or live Session has been assigned by this document.
>
> **SOURCE:** Operator direction in Social Hub discussion (2026-10-31): a one-stop in-product sign-in; several independent LLCs and a nonprofit grouped for management, additional independent family businesses, future partner/customer organizations, overlapping divisions and geography, and worker/branch/provider account delegation. No names, private legal details or actual account links are recorded here.
>
> **RELATION:** Extends [Social Account Manager handoff v0](./social-account-manager-handoff-v0.md). It does **not** silently replace its catalog contract, the approved [Social adapter contract](../../services/messaging/ADAPTER-CONTRACT.md), Syntagma policy, or provider authentication rules.
>
> **VERIFY LEVEL:** GitHub architecture and existing Social contract inspected on 2026-10-31. This revision documents requirements, not deployed tenants, real legal ownership records, working permissions, enterprise authorization or runtime acceptance.

## 1 // Executive direction

Upgrade **Account Manager** from a Social-only inventory/planner into a shared **Post-Apollo Identity Center** that authenticates a person once and lets that person select any organization and role for which they have independently verified access. Social and future business tools are consumers of the same cross-product service, not the owners of corporate authorization.

### Operator-confirmed product requirements (direction, not code acceptance)

- **Multiple legally separate organizations from day one:** initially two LLCs and one nonprofit in a linked management view, plus independent personal/family ventures and prospective software businesses, with capacity for unrelated clients to run their own organizations. The examples do not assert exact legal ownership, current registrations, employment or board powers.
- **Above-company management:** a **portfolio/workspace** can group authorized organizations for overview and administration without merging the entities, payroll, membership, secrets, audit logs, data or legal governance.
- **No artificial single-company ceiling:** a person may be a leader in one organization, an employee in another, own independent ventures, and later support or partner with other entities using the same personal login.
- **Separate functional and geographic structures:** divisions such as Education, Healthcare, Phones/Networks, Agriculture/Food, Sales and future lines of business coexist with countries, regions, branches, hubs, departments, teams and individual workers. Functional directors can span many locations, while a local manager may oversee several divisions in one branch.
- **Flexible workforce and external network:** employees, contractors, hiring staff, supervisors, marketing workers, partners and outside customers have separate identities and only the rights they are assigned. One person may hold different roles in multiple organizations or contexts.
- **Multi-owner external accounts:** personal Social accounts; company, division, region, branch or team accounts; and partner-delegated accounts must be distinguishable. When providers support it, allow separate rights to view, post, message, approve, administer and reconnect.
- **Expansion from local to national to international:** organizations are not locked to a US-only geography or one region layout. The nonprofit and LLCs may expand at different speeds; the backend needs explicit legal, timezone, localization, privacy and data-residency policy rather than treating all organizations as one.
- **All-in-one account experience:** all account linking, connection status, session restoration and reauthorization are initiated and managed from Post-Apollo; no manual browser-cookie/profile-file management.

### Keep the security boundary

"One-stop" means a unified workflow, not an unrestricted ability to impersonate every provider's login screen. External services may require a protected system-browser authorization, passkey, QR, MFA or device confirmation. Post-Apollo manages the request and returns to the same control center without extracting cookies, bypassing consent or replaying credentials.

**Implementation approach still to evaluate:** standards-based, mature identity provider (IdP) for human authentication; first-party authorization model for tenants, portfolios, scopes and grants; protected Account Broker and secret references. No IdP, database, hosting pattern or legal governance model is selected by this document.

**Critical invariant:** a portfolio, shared family relationship, software publisher or platform operator does **not** receive implicit access to another legal entity's confidential data. Access is explicit, scoped, revocable and auditable.

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

**Historical baseline:** This plan originally inspected main near `2e4d121b8cdc237a9819be6a9c03581f6a18e9de`. The multi-organization revision checked later main at `5e255fc6358803044fd8f19bec9c3bee83846461` on 2026-10-31. Treat all SHAs as provenance, **not** current HEAD. Workers MUST recheck GitHub and Hospital ownership before coding.

## 3 // Target ownership and trust boundaries

```text
[[ Post-Apollo Identity Center UI ]]
   [Personal Sign-In]  [Portfolio Switcher]  [Org/Role Context]
                           |
                           v
[ Identity Center API / authorization gateway ]
      |                 |                  |
      v                 v                  v
 [IdP / SSO]    [Tenant + Scope Graph]   [Audit / Security]
                 |              |
                 v              v
         [Portfolio Views]   [Organization/Tenant Boundaries]
                                  |
                     +------------+-------------+
                     |            |             |
                  [LLC]       [Nonprofit]   [External client]
                     |            |             |
                [Divisions]  [Divisions]    [Own policies]
                [Locations]  [Locations]    [Own workforce]
                     +------------+
                                  |
                   [Grants scoped to org, function,
                      location, team, action]
                                  |
           +----------------------+-------------------+
           |                                          |
     [Post-Apollo apps]                          [Account Broker]
    Social / Operations /                     [Credential vault refs]
    Dispatch / Inventory                        [Provider adapters]
```

**Person/Principal:** one individual authenticates independently from any particular company. Effective access is resolved from their active, explicitly granted memberships and roles. A person may switch between several companies without signing up for multiple Post-Apollo identities.

**Portfolio:** a **management lens**, optionally grouping multiple legal entities and a person's own organizations. It has an owner/admin role for the portfolio *workspace*, but membership in a portfolio creates **no automatic tenant, board, financial, worker, payroll or provider-account permissions**. A consolidated dashboard only includes data independently permitted by each participating tenant. Portfolios and organizations may relate many-to-many by explicit agreement.

**Organization/Tenant:** the isolated security and data boundary for each legal or independently operating entity, including LLCs, nonprofits, partner organizations and unrelated paying customers. An organization may join a portfolio without relinquishing its separate identity, data controls, application subscriptions or administrators. Platform support staff, family relationships and another tenant's executives have no general data access.

**Governance:** represent ownership, presidency, company executive roles, nonprofit board authority and delegated administration as distinct **verified organization-specific governance records/assignments**. Do not infer legal ownership or grant nonprofit governance powers from family connection or a portfolio label. Nonprofit board rules and restricted mission/healthcare work must be separately enforceable.

**Functional structure:** programs/divisions (Education, Healthcare, Networks, Agriculture/Food, Sales, etc.), departments, projects and business lines belong to an organization and can span multiple branches or countries.

**Geographic structure:** locations/countries/regions/branches/hubs have their own hierarchy. A geographic manager may oversee multiple functional divisions; a national division director may oversee one function across many regions. **These are intersecting scopes, not one rigid folder tree.** A worker can belong to multiple locations or functions with explicit grants and effective dates.

**Workforce and partners:** employees, contractors, branch operators, recruiters, sales reps, external business partners and service customers have distinct memberships and cross-tenant collaboration agreements. An invitation or partnership does not grant authority in an unrelated organization.

**Identity Center owns:** authenticated principal links; portfolios and tenant membership; organization functional/geographic scope graphs; conditional roles and explicit grants; identity context switching; consent; account link inventory; device/session policy; revocation; audit contracts; stable versioned APIs.

**Identity provider owns:** secure primary login, MFA/passkeys, recovery, federation and signed authentication assertions.

**Account Broker owns:** provider-verified connection attempts, provider status evidence, permissions/scopes, reauthorization, approved refresh/revoke operations, request correlation and credential references. "Connect All" is a collection of provider-authorized independent operations, not a universal password login.

**Credential Vault owns:** securely protected tokens/credentials where legitimately needed, tenant/person/provider scope, key rotation and recovery. Existing native provider sessions stay provider-owned by default. Never place secrets in QML, Social identity JSON, logs, command-line arguments or GitHub.

**Social owns:** its own application selectors, messaging/browser adapters, personal and business provider account UX, transport capabilities and truthful status display. Local `identity-N` remains a layout/provider-scoping handle, **not** an enterprise principal or a global tenant key.

**Business apps own:** dispatch, inventory, scheduling, hiring, payroll and other business resources, with backend enforcement of tenant and requested action. Social account connectivity alone never grants business API rights.

**Authorization is always enforced by the trusted API/service** against authenticated principal, tenant, requested resource, branch/function scope, action, session assurance and grant expiry. UI visibility, portfolio membership or account naming is never sufficient.

### Company-wide and branch-wide directories

A future employee/worker directory, branch roster and connected-account catalog may be separate application surfaces. The **identity and access service owns the underlying principal, tenant, membership and account-link contracts**; it should not absorb hiring workflow, customer records, healthcare records, payroll or media scheduling simply because they share people and organizations.

## 4 // Proposed domain model (review candidate, not an adopted schema)

| Record | Identifiers / relationship | Invariant |
| --- | --- | --- |
| Person / Principal | immutable `principalId`; IdP issuer + subject; state | Human identity is independent of businesses and of Social `identity-N`. |
| Organization / Tenant | `orgId`, entity type, governance policy, data boundary | LLC, nonprofit, partner or customer data never shares a tenant merely because the people overlap. |
| Portfolio / Workspace | `portfolioId`, label, member-org references, workspace custodians | Above-company consolidated view, **not** automatic transitive access to tenant records. |
| Portfolio ↔ Organization participation | `portfolioId`, `orgId`, explicit approval and visibility conditions | Many-to-many membership is revocable; one org can appear in several authorized portfolios. |
| Organization governance | `orgId`, verified owner/board/executive/administrator role reference | Legal/business authority is separately verified; nonprofit board powers are not implied by family ties. |
| Individual organization membership | `principalId`, `orgId`, employment/contractor/partner type, start/end | Multi-organization careers and independent businesses are first-class. |
| Function / Division / Program | `functionId`, `orgId`, optional parent program | Healthcare, Education, Networks, Sales etc. can cut across geographic regions. |
| Geography / Operational Unit | `unitId`, `orgId`, country/region/branch/hub/team relationships | Country and branch scopes are distinct from business-function scopes. |
| Assignment / Scoped Grant | actor, `orgId`, function/unit selectors, actions, approver, expiry | A role may allow one division nationwide or several divisions at one branch. Deny by default. |
| Cross-organization Agreement | participating `orgId` values, authorized data resources/actions, approver, expiry | Explicit collaboration, no universal cross-tenant read or sharing all workers/accounts. |
| Role / Permission | organization or platform policy, bounded resource/action definitions | Portfolio admin, company executive, supervisor, employee, contractor and partner are context-specific, not global ranks. |
| Device / Session | `sessionId`, authenticated principal, device, assurance and expiry/revocation | Revoked/expired enterprise rights must never be recreated from local caches. |
| Linked Provider Account | `accountLinkId`, provider account subject, owner type/id, org context, capability | Personal, company, division, branch, team and partner-delegated accounts are distinguishable. |
| Account Access Grant | `accountLinkId`, grantee, provider-supported actions, scope and expiry | May permit viewing or posting without revealing the primary password or private messages. |
| Credential Reference | vault pointer, account owner/tenant/provider, key metadata | No plaintext secret in profile labels, organization membership records or audit output. |
| Connection Attempt | `requestId`, subject, owning entity, provider, requested actions, state | Idempotent; delayed callback cannot affect another tenant, personal account or active role. |
| Audit Event | actor, tenant, portfolio context, action, target, decision, correlation, time | Track grant/revoke and cross-tenant access, with separate tenant privacy and retention rules. |

### Example of independent authority

- A person's **one Post-Apollo login** might have: portfolio overview rights, executive rights for two participating LLCs, a different nonprofit role, and owner rights over their personal venture. These are **four or more independent grants** with separate audit trails, not one superuser status.
- Another family member can own a different LLC and choose to participate in a shared portfolio **without** granting that portfolio access to their payroll, passwords or private social inbox.
- A healthcare director may have permission for Healthcare across multiple authorized US regions, while a Maryland branch manager has permission for several divisions **only at their branch**. The backend computes the intersection of resource, action, tenant and assigned scope.
- An unrelated paying customer must not become visible to platform/family administrators just because both use the Post-Apollo software.

Avoid global account IDs based on name, email, company slug or hierarchy path. Use stable opaque IDs and explicit memberships. For revocation, a previously selected portfolio or branch never authorizes an otherwise denied operation.

## 5 // One-stop user experience

### Personal sign-in and portfolio selection

1. A person signs into Post-Apollo using **one personal identity**. This does not by itself select a company or grant corporate access.
2. Identity Center lists only portfolios and organizations to which the authenticated person has explicit invitations, memberships or governance grants.
3. Person opens a portfolio overview or chooses an organization and active role; the UI clearly displays **which legal entity, division/program and branch/hub context** is active.
4. Consolidated dashboards aggregate only fields that each participating organization separately authorizes. An executive view never silently combines restricted nonprofit, employee, health, client or financial records.
5. The same person can switch to their own venture, another employer, a partner context or a separate customer workspace without mixing tokens, drafts, account permissions or audit ownership.
6. Leaving the context, changing tenant/role, or revoking membership invalidates the corresponding authorization context and cached privileged data.

### Worker first sign-in (company-owned apps)

1. Worker opens Post-Apollo and chooses **Sign in** inside the Identity Center.
2. IdP authenticates with passkey or supported MFA, using its secure auth mechanism.
3. Identity Center fetches the person's authorized portfolios, organizations, roles, divisions/programs and branch/hub scopes, showing only permitted app choices.
4. Worker chooses an allowed **organization + action role + functional/geographic context**. Post-Apollo passes a scoped, short-lived authorization context to each company app.
5. Reopening Post-Apollo securely resumes a valid session where policy permits; expiration, revoked access, elevated action or new device asks for a fresh authentication or step-up.
6. Sign out / revoke device / leave organization invalidates backend sessions, not just local UI state.

### Social or external service connection

1. User selects **Identity Center → Linked Accounts → Connect** or **Connect All**.
2. Broker enumerates supported services and obtains user consent for each requested scope.
3. Telegram uses its existing in-widget QR/phone provider process. Compatible OAuth/OIDC services use official authorization-code + PKCE via **an OS-protected external user-agent** when required; after redirect/device-code completion the user returns to the same Post-Apollo screen.
4. Existing provider-owned apps/browser sessions may be opened through Post-Apollo, but are reported as **UNKNOWN** until supported provider evidence establishes authentication.
5. Broker stores only needed secret references and maps the connection to the **correct owner (person, organization, division, branch or team)** with explicit grants. It reports provider-evidenced status and attempts silent refresh only where authorized.
6. Expired/revoked/not-linked entries show **Reconnect**, **Sign-in required**, or **Unsupported**, never a fabricated success message.

No cookie-folder steps. No scripted credential filling into arbitrary provider websites. No MFA bypass or synthetic cookies. No universal "sign in to 32 services" guarantee.

### Manager/administrator

An authorized manager opens **Identity Center → Organization → People / Programs / Locations / Access**, invites a worker, grants a narrowly scoped role at one or more functions and branches, sets expiry if temporary, and receives an auditable result. An independent organization decides who may invite or approve staff. Branch transfers/offboarding revoke scoped company access without deleting the person's own account or their rights in unrelated organizations.

### Shared business/social account experience (provider-capability dependent)

A worker may have a personal social account and separately be allowed to **view**, **publish**, **reply/message**, **approve content**, or **administer** a company, branch, team or program account. The app must display the exact account owner and active permission before acting. Providers differ: unsupported fine-grained delegation must report as unsupported, not be simulated through a common shared password. Company account permissions and optional personal messages remain separate. Partner access uses explicit cross-organization grants and can be independently revoked.

### Portfolio overview experience

An authorized portfolio administrator may see high-level organization cards, authorized summaries, assigned branches/programs, connection issues and outstanding invitations. Drill-in requires a separate verified tenant grant. Portfolio administrators cannot silently browse every participating organization's employee directory, messages, nonprofit records or partner accounts.

## 6 // Proposed API and process contracts (not yet implemented)

Define versioned typed interfaces before modifying QML or provider adapters. Below are *examples to review*, not active endpoints:

```json
{
  "contract": "post-apollo.identity-center.v0-proposal",
  "requestId": "opaque-request-id",
  "actorSessionRef": "opaque-authenticated-session-ref",
  "organizationId": "org-example",
  "portfolioViewId": "portfolio-example-optional",
  "selectedDivisionId": "program-example-optional",
  "selectedBranchId": "branch-example-optional",
  "accountOwnerRef": "org-owned-account-example",
  "operation": "connectServices",
  "serviceIds": ["telegram", "x", "discord"]
}
```

The authenticated caller identity **must** come from a validated server session or signed assertion, not a client-supplied email, mutable QML label or bare `identityId`. Portfolio, organization, division/branch and account-owner IDs in requests are **untrusted selectors**; the server resolves and independently authorizes every relationship. A token for one tenant cannot be promoted to another through a client-selected organization value.

Response rows should include `serviceId`, `requestId`, `accountLinkId` (if known), `status`, `evidenceSource`, `lastCheckedAt`, `nextUserAction`, `requiresInteraction`, `providerCapability` and sanitized `errorCode`. Suggested statuses:

- `UNLINKED`, `CHECKING`, `CONNECTED_VERIFIED`, `REAUTH_REQUIRED`, `WAITING_FOR_USER`, `UNKNOWN`, `UNSUPPORTED`, `FAILED`, `CANCELLED`.
- `CONNECTED_VERIFIED` requires provider-specific evidence, not a nonempty cookie directory, open window, account note or local vault entry.
- Scope every event, cached result, refresh operation and send acknowledgment to the immutable subject, organization, account link, provider and request generation.
- Explicit consent is required for account linking and any privilege-increasing operation. No automatic credential/session migration.
- Separate authenticated workforce APIs from optional personal Social accounts. Keep personal account data inaccessible to branch admins unless specifically authorized by a legitimate enterprise integration.

**Core operations to define:** `getMySession`, `listMyPortfolios`, `listMemberships`, `listAuthorizedOrganizations`, `selectAuthorizedContext`, `getAuthorizedScopeGraph`, `listLinkedAccounts`, `connectService`, `connectServices`, `getConnectionStatus`, `disconnectService`, `grantAccountCapability`, `revokeAccountCapability`, `listDevices`, `revokeSession`, `listAuthorizedWorkers`, `grantScopedRole`, `revokeGrant`, `offboardWorker`, `requestPartnerAccess`, `revokePartnerAccess`.

Define a service-owner contract and threat model for each operation before implementing the transport or storage. Preserve current `SocialAccountCatalog.py` `PLAN_ONLY` semantics until a versioned broker is explicitly accepted.

## 7 // Security and production invariants

- **Default deny** across unrelated organizations, family/private ventures, nonprofit/for-profit tenants, portfolios, divisions, branches, devices and provider account links; test against IDOR/cross-tenant access and privilege escalation.
- **Passkeys or phishing-resistant MFA** preferred for workforce login; require stronger step-up authentication for privileged actions, payroll/payments and account recovery.
- **No shared worker credentials**; use named service accounts with constrained permissions only when required. Never make a branch's generic password the master identity.
- **Session security:** secure issuance, bounded TTLs, refresh/rotation strategy, server-side revocation, lost-device response, replay protection, idle limits per risk and authoritative context checks.
- **Secrets:** provider-specific least-privilege scopes, encryption at rest/in transit, key ownership/rotation, restricted logs, no secret values in repo/CLI arguments/QML/config metadata/telemetry. Do not assume 0600 file permission equals encryption at rest.
- **Audit:** actor, action, target, grant/revoke decision and correlation IDs; protect against tampering; retention and privacy/access policy require operator/legal decisions.
- **Account recovery/offboarding:** verified recovery and emergency access paths, dual control for critical admin operations, no irreversible removal of provider personal accounts, tested organization and branch deprovisioning.
- **Offline:** if a branch device has no network, allow only explicitly designed bounded offline functions; no local cache may mint new privileges or make expired/revoked credentials appear valid. Document how revocation propagates after connectivity returns.
- **Third-party flows:** conform to the provider's terms and authorization mechanism; RFC 8252 requires native OAuth to use an external user-agent, not a credential-intercepting embedded webview. Prefer auth-code + PKCE, official device code or native approved flows. Do not claim all providers support APIs or silent refresh.
- **Independent governance:** family relationship, portfolio administrator, platform operator, corporate title and nonprofit board membership are distinct authority sources. Verify and grant access inside each applicable organization; never infer all-company root privileges from owning Post-Apollo software.
- **Cross-organization collaboration:** explicit, revocable, auditable sharing agreements; protect unrelated paying customers. No hidden platform superadmin access to private customer content. Exceptional support access requires a designed, time-limited, approved and logged policy.
- **Business/social delegation:** provider-granted scopes bound to the correct personal/organization/program/branch account, with separate read/publish/message/admin rights where supported; no shared worker master passwords.
- **International readiness:** multi-country geography, locales, currency/timezones and jurisdiction-specific worker data and retention are design concerns. Review relevant nonprofit, health, labor, privacy and data residency obligations **when applicable**; no compliance claim is made by choosing a database.
- **Operations:** per-tenant backups/recovery, independent customer isolation, high availability suitable for national/international operations, observability without secrets, time synchronization, incident response and staged rollout. Security and compliance certification are future work, never inferred from passing unit tests.

References: [NIST SP 800-63-4](https://csrc.nist.gov/pubs/sp/800/63/4/final), [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html), [OAuth for Native Apps / RFC 8252](https://www.rfc-editor.org/info/rfc8252), [SCIM / RFC 7644](https://www.rfc-editor.org/info/rfc7644).

## 8 // Worker work packages and dependency plan

These are **proposed lanes, not assignments**. Confirm actual Hospital Room, Staff Role, worker, file ownership, PRs and interfaces before implementation. Broad cross-component architecture is a coordination/mass-surgery concern; a Social-only worker must not rewrite enterprise authorization or account-vault ownership.

| Lane | Bounded deliverable | Dependencies | Acceptance evidence |
| --- | --- | --- | --- |
| **A. Architecture, governance and threat model** | Portfolio vs tenant boundary, independent legal/nonprofit governance, IdP choice evaluation, cross-org threat model, versioned APIs | Operator direction here; unresolved policy decisions in section 11 | Architecture review, authority graph, no accidental root rights |
| **B. Human authentication** | IdP-backed individual login, passkeys/MFA/recovery, devices and session lifecycle | A | Test IdP, signed-token validation, expired/revoked/step-up cases |
| **C. Multi-tenant portfolio and membership graph** | Independent LLC/nonprofit/customer tenants, portfolio aggregation, many-to-many participation, organization invitation, cross-org roles | A+B | Two+ unrelated tenant isolation, person with several roles, portfolio admin denied tenant-private records |
| **D. Functional/geographic authorization** | Division/program and location graphs, explicit scopes, time-bound grants, server enforcement | A+C | National division vs one branch intersect correctly, no implicit inherited access |
| **E. Vault and secrets boundary** | Reviewed key storage, scoped secret references, rotation/recovery, strict logs | A+B | No secret exposure, tenant separation, recovery/rotation fixtures |
| **F. Provider Account Broker** | Capability registry, owner classification, connect/refresh/revoke, batch orchestration, provider-evidenced statuses | A+C+E | Personal/company/branch/provider permissions separated; partial failures safe |
| **G. Social integration and account delegation** | Connect Social Settings to broker, correct identity/context switching, provider-supported viewing/posting/approvals | F and Social owner | Personal vs org-linked accounts, cross-account composer/window/permission tests |
| **H. Workforce, partner and portfolio admin UX** | Multi-org switcher, people/role/program/branch directory, invitations, staff and contractor lifecycle, partner agreements | C+D+E | Audited tenant switching, scoped view and cross-org revocation |
| **I. Production reliability and acceptance** | Tenant provisioning, backups, localization plan, security/ops monitoring, pilot and disaster recovery | All, staged | Security assessment, controlled multi-org pilot, operator sign-off |

### Release sequence with explicit multi-company gates

**Phase 0 — Contracts and ownership:** commit operator requirements (multiple companies, nonprofit, independent ventures, eventual external customers, two-dimensional access). Evaluate IdP/secret custody/tenancy, legal governance authority and portfolio-vs-tenant contracts. Confirm worker seams in GitHub/Hospital; no bulk migration.

**Phase 1 — Disposable multi-tenant proof:** create **at least three synthetic organizations** (two for-profit, one nonprofit), **two portfolios** (one shared and one independently managed), and an unrelated customer tenant. Include people with roles in several tenants and a separate program/region scope. Test denied access exhaustively before adding real workforce records.

**Phase 2 — Independent access engine:** enforce portfolio visibility separately from tenant permissions; function and geography grants; role lifecycle and organization invitations. Test executive, nonprofit governance, regional director, branch manager, worker, contractor and partner distinctions.

**Phase 3 — Secure provider broker:** vault references, account ownership, truthful provider status, reconnect, provider-supported action delegation and opt-in Connect All. Start with a small supported provider matrix; never promise automatic login to every Social button.

**Phase 4 — Social + admin UI:** integrate existing Linked Accounts and Identity Center organization/portfolio switcher while preserving local Social layouts and provider sessions. Add worker/org account catalog surfaces only at the owner-approved interface boundaries.

**Phase 5 — Controlled business pilot:** synthetic then operator-approved real isolated tenants, staff onboarding/offboarding, partner grants, nonprofit-sensitive boundaries, offline and lost-device drills, audit, recovery.

**Phase 6 — Multi-region/international growth:** localization, jurisdiction/retention and tenant-residency review, regional resilience, staged onboarding for partners and outside customers. No global activation before operator and security acceptance.

**Stop gates:** A passing schema/static test is not live authorization proof. Every phase needs reviewed security and tenant-boundary evidence, owner handoff, rollback and operator acceptance.

## 9 // Migration, compatibility and rollback

- Introduce a **separate mapping** from local Social `identity-N` to a person/provider scope and optional explicitly linked organization/account owner; do not mutate existing `social-identities-v1.json` or treat the first identity as an enterprise administrator or tenant.
- Keep legacy shared Telegram, existing per-identity private Telegram session paths, browser profile directories, and current Account Details notes intact during the pilot. No bulk cookie import, profile copy, password extraction or session reassignment.
- A broker rollout should be versioned and opt-in; the current Social behavior should remain available behind an explicit fallback until accepted.
- Migrate only with explicit consent, mapping preview, backup and reversible transformation. Where third-party session migration is unsafe, require provider-supported reauthorization.
- Reverse a failed rollout by disabling the new broker integration feature flag and restoring prior known-good code/config snapshots. **Never** roll back by deleting provider session files or user credentials.
- Preserve separate recovery paths for central IdP outage, lost authenticator, organization/portfolio admin lockout, nonprofit board governance, compromised device, expired external provider token, partner revocation and cross-branch/cross-tenant permission error.
- Keep existing or future business entities separate when importing: never silently merge two LLCs, a nonprofit, a person's private venture or an unrelated client's tenant. Preview and approve each org/portfolio association and each delegated permission separately.
- A former staff member's company access may be revoked while their personal Post-Apollo login, own independent organization and other valid employer memberships remain intact. Offboarding is **tenant-scoped** unless separately authorized.
- Portfolios are reversible views; removing an entity from a portfolio must not delete the legal organization's records, user identities, provider accounts or unrelated authorizations.

## 10 // Verification matrix

Mandatory synthetic and then controlled integration scenarios:

1. **Tenant isolation:** two LLC tenants, one nonprofit tenant and an unrelated customer tenant have separate principal grants, directories, payroll/worker records and provider account references.
2. **Portfolio is not privilege:** grouping three organizations in a family-management portfolio provides only independently authorized summaries; portfolio admin is denied any missing tenant grants.
3. **Multiple independent ventures:** one person manages their private business plus a second employer role through one login; switching contexts does not transfer organization secrets or powers.
4. **Independent family/partner business:** an additional organization joins a shared portfolio without granting its other members read access to sensitive data. Leaving the portfolio does not delete that organization.
5. **Nonprofit governance:** board/governance and operational program permissions remain distinct from LLC ownership/executive permissions, including records with additional privacy restrictions.
6. **Functional + geographic intersection:** national Healthcare Director sees only allowed healthcare programs across several regions; Branch Manager sees multiple authorized divisions at only their branch.
7. **Cross-border extensibility:** two countries use distinct region trees, local times and data handling policies; branch names are not global ID keys.
8. **Worker/contractor lifecycle:** a branch worker can sell/perform assigned work and access only permitted tools; a contractor's time-bound grant expires without affecting personal Social or another employer.
9. **Multi-org employment:** someone works for two organizations and a nonprofit with different roles. Revoking one membership preserves all other valid memberships.
10. **Partner collaboration:** branch partner receives exactly selected shared data/actions and can be revoked without exposing the entire employee directory.
11. **Regional/executive administration:** authorized organization officer performs step-up for privileged actions; manager delegation cannot exceed grant authority.
12. **Lost device:** server-revoked session cannot be reused from local QML state, cookie folders or stale signed context.
13. **Provider account owner:** personal, company-wide, division/branch/team and partner-delegated Social accounts remain clearly separate in UI and in broker/vault ownership.
14. **Social delegated permissions:** a worker with provider-supported posting rights cannot read private messages or administer account settings unless independently permitted; unsupported platform delegation is reported.
15. **Telegram identity separation:** two private accounts show separate conversations/drafts/acks; stale callback cannot deliver messages into another identity.
16. **Browser account isolation:** correct scoped browser opens; a window/cookie file is never evidence of authenticated account ownership.
17. **Provider refusal/reconnection:** expiry, MFA, consent denial and unsupported APIs return honest states; unified dashboard remains usable with provider-required external secure auth.
18. **Connect All:** partial success, cancel/retry and scope per provider/organization, without fabricating login or extracting secrets.
19. **Branch offline/IdP unavailable:** defined fail-closed handling, no new privileges minted by caches, recover after connection.
20. **Vault and audit:** key rotation, restore, tenant-isolated backups and cross-tenant audit access limits without leaking secrets.
21. **Customer data separation:** platform operator, portfolio administrator and unrelated customer cannot access each other's private data via support, exports or aggregate dashboards without separately approved audited grants.
22. **Desktop/runtime:** Quickshell, Sway, local provider subprocesses and remote API enforcement exercised independently; source tests alone are not live acceptance.

Log exact commit, synthetic dataset, test environment, result, owner, operator acceptance and rollback. Do **not** use production personal accounts, real worker credentials or non-consensual private data.

## 11 // Operator direction captured vs decisions still open

### Already established by the operator as product requirements

- **Multi-organization is required**, not optional or a later extension. Two distinct LLCs and one nonprofit may be grouped for cross-entity management; other personally controlled businesses and family-member ventures remain separate.
- **Above-company portfolio views are needed.** A person can oversee a set of organizations and see authorized summaries across them without merging legal entities.
- **Independent people and independent companies are first-class.** The same platform must support managers, workers, contractors, social account contributors, separate family businesses, service partners, and eventual unrelated paying organizations.
- **Functional divisions and geography overlap.** Healthcare, Education, Networks, Agriculture/Food, Sales and future business lines each need granular access across countries, regions, branches, hubs and teams.
- **National and eventual international operations**, with different growth patterns for each LLC/nonprofit; avoid US-only assumptions.
- **Social account connections can be personal, organization-wide, program-wide, branch/team-specific or delegated**, subject to each provider's supported permissions.
- **Post-Apollo is the one-stop management surface.** Users do not manually manage browser cookies or profile files.

These decisions **supersede the old plan's unanswered question** of one company versus multiple legal organizations. Do not ask the operator to redecide this without new evidence of a real conflict.

### Open governance and engineering decisions (do not silently assume)

- **Legal authorization and governance:** who, for each actual entity, may approve a portfolio link, grant a company role, change nonprofit board policies, administer company credentials or delegate cross-company access? Family connection or an officer title is not sufficient technical proof.
- **Portfolio model:** private personal workspaces vs shared management portfolios; who can create/approve memberships, what summaries are explicitly shareable, whether an org may appear in multiple portfolios.
- **Tenant provisioning/business model:** entity verification, handling for franchises/partners/customers, separation of subscriptions/billing, reseller support and customer admin ownership.
- **IdP and credential custody:** managed or self-hosted; primary/recovery administrator, passkeys/MFA, hardware-backed encryption, key recovery, approved external provider auth exceptions.
- **Central/offline architecture:** trusted server/control plane, local-only vs hybrid features, international data locations, lost-device and revoked-role behavior under disconnection.
- **Role catalog:** who invites/hires and approves workers in each LLC, nonprofit program, region or branch? What privacy limits apply to healthcare-related workflows, personnel and nonprofit records?
- **Social delegation:** which accounts are personally owned vs employer/branch owned? Which provider APIs legitimately support viewing, posting, messaging and approval by different workers?
- **Legacy Social migration:** explicit mapping choices for `identity-N`, shared Telegram login and provider-specific Chromium/Vesktop sessions; no silent reassignment or cookie migration.
- **Audit/compliance:** jurisdiction-dependent privacy, labor, nonprofit, health and payroll obligations, retention, availability, recovery and support access procedures.
- **Hospital ownership and release:** which owners/Rooms/Teams are accountable for Identity Center backend, authorization, vault, Social integration, security review, merges and production activation?

**No implementation decision is implied** by documenting these questions. Operators decide business authority; responsible engineering/security owners propose the concrete mechanisms and seek approval.

## 12 // Hospital-compatible worker handoff

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
**ROOM:** Not verified / not registered by this external conversation.
**DOCTOR / PROVIDER:** External ChatGPT planning contribution / OPEN AI // CHATGPT.
**ASSIGNMENT:** Update the Identity Center worker plan for the operator's explicitly multi-organization, portfolio/branch/division and delegated account requirements; no implementation assignment granted to other workers.
**PERMISSIONS:** Plan/document/review only; code changes, local writes, live account access, merge and deployment need their own authorization.
**CHECKPOINT:** Inspect this plan, the current Account Manager contract, latest GitHub HEAD/PRs and Syntagma's `AGENTS.md` and Hospital protocols before work.

### IMPLEMENTATION
Documentation-only revised proposal for a multi-legal-entity, portfolio-aware, international-ready Identity Center with separate nonprofit, family-venture, partner and customer tenants. Social's current ownership remains intact; no actual backend, workforce tenant, credential store or provider login is implemented by this document.

### HOW TO USE
Workers should read the operator-confirmed scope in sections 1 and 11 first, then review the portfolio/tenant/trust model in sections 3–4. Select a bounded lane in section 8 **only after formal assignment**. Treat personal authentication, legal-entity governance, portfolio aggregation, branch/functional rights and provider-account ownership as separate.

### VERIFY
GitHub source, current Model index, Account Manager handoff and Syntagma rules were inspected on 2026-10-31. External authentication standards are linked above. **Only documentation is changed in this scope; no live Quickshell, backend, enterprise authorization or legal-governance verification.**

### WATCH OUT FOR
Do not equate Social local identity with a person, a portfolio with legal ownership, family ties with tenant admin rights, company officers with nonprofit board powers, geography with function, account nicknames with authenticated providers, or provider windows with proof of login. No enterprise passwords, legal documents, employee lists or private session data in repository/chat/tests.

### CHECKLIST
- [x] Operator goal translated into cross-product architectural work plan
- [x] Current Social account-manager boundary preserved
- [x] Proposed multi-org/portfolio domain model, independent governance, functional/geographic grants, cross-provider ownership, worker lanes and expanded test gates documented
- [x] Operator confirmed the multiple-entity/portfolio/overlapping-division requirements in section 11
- [ ] Operator and authorized entity stakeholders resolve remaining governance/engineering decisions in section 11
- [ ] Hospital ownership/Rooms/Assignments confirmed
- [ ] APIs and threat model reviewed and frozen
- [ ] Implementation verified in synthetic and live controlled environments
- [ ] Explicit operator approval for rollout and final acceptance

### NEXT
Operator reviews this scope clarification → confirm governance and identity authority → assign workers to synthetic three-entity plus unrelated-customer tenant model → write threat model and approved API contracts → build bounded, separately reviewed implementation PRs.

### DECISIONS
**Operator-directed product requirements:** multiple distinct entities, portfolio overview, overlapping functional/geographic structures, several roles per person, delegated business/social account access and eventual outside customers. **Technical proposals pending review:** shared Identity Center, standards-based IdP, separately enforceable tenant grants, protected Account Broker/Vault and provider-compliant authorization. No implementation, assignment, merge or production acceptance is granted by this text.
