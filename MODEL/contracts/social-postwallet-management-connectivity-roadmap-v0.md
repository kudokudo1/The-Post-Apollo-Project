# Social + PostWallet // unified management and connected accounts delivery map v0

> **STATUS:** OPERATOR GOAL CAPTURED / IMPLEMENTATION NOT AUTHORIZED BY THIS DOCUMENT ALONE. This is a concrete, incremental handoff for UI, identity, connections and organization-owner workers. It is not a newly accepted canonical UI layout or proof of production permissions.
>
> **PATIENT:** `The-Post-Apollo-Project`; relevant PostWallet owning repository must be independently located/verified before source reuse. The GitHub repository search in this task did not locate a separate `PostWallet` project or a `PostWallet` source match on main; this does **not** establish it does not exist elsewhere.
>
> **SOURCE:** Operator explicitly wants one fast, manageable Social / PostWallet interface covering full profile/identity/organization/branch controls, real account connections, login and switching rather than a growing set of disconnected preview panes. The user prioritizes secure authority before production-action buttons, but wants the UI work staged immediately after each security gate.

## What already exists (inspect and reuse, do not reimplement)

1. **Local Social ID layout:** `services/social/SocialIdentityStore.qml`, `SocialAccountDetailsStore.qml`; CPU++ `CpuPlusIdManagementPane.qml`, `CpuPlusIdDetailsEditor.qml`, `CpuPlusIdAccountEditor.qml`. Operator accepted create/rename/contact/account-name/remove persistence. These labels are not authenticated principals.
2. **Local organizations and branches:** `SocialOrganizationDirectoryStore.qml` plus `widgets/messanger/IdentityCenterLocalOrganizationEditor.qml` supports create, rename, archive/restore and permanent delete with guard. The existing Social menu already has the real local editor; CPU++ currently only links existing entities via `CpuPlusIdOrganizationLinksEditor.qml`.
3. **Structure, locations and relationships:** existing `IdentityCenterLocalStructureEditor.qml`, `IdentityCenterLocalBranchLocationsEditor.qml`, `IdentityCenterLocalUnitLocationsEditor.qml`, `IdentityCenterLocalFunctionalReportingEditor.qml`, `IdentityCenterLocalRelationshipModifiers.qml`.
4. **Portfolios:** `SocialLocalPortfoliosStore.qml`, `IdentityCenterLocalPortfolioEditor.qml` and locally editable links. A portfolio is not a verified authorization context.
5. **Existing Social screen:** `IdentityCenterSettingsSections.qml` already has sections PROFILE / ORGANIZATIONS / CONNECTED ACCOUNTS / SECURITY / SOCIAL LAYOUT. The LOCAL Organizations section hosts many long editors. The host-returned person/permissions, connected provider accounts and real switching sections are mostly preview/status and cannot impersonate a real host.
6. **Existing CPU++ Connections setting:** `CpuPlusSettingsConnectionsOverviewPane.qml`, `CpuPlusSettingsConnectionsListPane.qml`, `CpuPlusSettingsConnectionsDetailsPane.qml` inspect status, request review, host observation and local sources. Approval/login is explicitly unavailable. Reuse `ConnectionsRegistry`, `ConnectionsBroker`, `ConnectionsRequestStatus` and source policy, rather than relabeling the inspect buttons as real OAuth.
7. **Verified preview chain:** `DesktopHostLifecycle` (PRs #1460/#1471), pinned HTTPS read adapter (#1463), pinned OIDC code exchange (#1469) and token-free viewer (#1456). No selected real issuer, protected desktop host, real account vault or server-authorized mutation endpoint is deployed by those PRs.

## User-facing target within the existing CPU++ footprint

Maintain fixed 1000×834 chassis and three bays (390px left, 260px middle, remainder right). Do NOT turn each company into a massive scrolling full-page form.

**Mode rail:** evolve `ID MANAGEMENT` toward a broader operator-approved `SOCIAL / ACCOUNTS` destination without discarding its established edit behavior. A name change should be separately reviewed against mode labels, hotkeys and existing keyboard tests.

**Left overview / task switcher (390px):** compact rows `PROFILE`, `MY IDS`, `ORGANIZATIONS`, `BRANCHES & UNITS`, `PORTFOLIOS`, `CONNECTED ACCOUNTS`, `SECURITY`; connection/login status counts and a clear `ADD / CONNECT` action. A single summary / back row prevents deep nested menu overload.

**Middle selector (260px):** searchable active records for the chosen task. Show local/verified/connected states distinctly. Organization selector may target a local directory item for editing, but must never silently become a server tenant switch.

**Right action/editor bay:** one selected record, contextual quick actions (NEW, RENAME, SAVE, LINK/UNLINK, EDIT BRANCHES, ARCHIVE, RED DELETE) and a short expandable detail pane only when needed. Reuse Social stores and validation policies; do not clone organization writers.

**Visual behavior:** Preserve accepted color grammar: magenta for user inputs/add actions, orange text cursor where configured, red destructive X/Remove with confirmation, existing open/selected color behavior, and status distinctions for unverified vs authenticated. Avoid new floating windows; use existing bay/shelf controls and retractable details.

### Interaction examples

```text
SOCIAL / ACCOUNTS → ORGANIZATIONS → [existing LLC] → EDIT
                        + BRANCH / RENAME / PORTFOLIOS / ARCHIVE / REMOVE
SOCIAL / ACCOUNTS → PROFILE → [local ID] → EDIT CONTACT / ACCOUNTS
SOCIAL / ACCOUNTS → CONNECTED ACCOUNTS → [provider] → CONNECT / DISCONNECT
SOCIAL / ACCOUNTS → CONNECT ALL → show eligible providers + consent queue
SOCIAL / ACCOUNTS → SWITCH → choose authenticated principal / verified org
                        → host authorizes switch, then desktop changes context
```

The first two rows are achievable *locally* by reusing stores, preserving current user approvals. The last three require explicit provider and server security contracts. Button labels are **requirements, not implemented functionality** yet.

## Provider connection semantics: why Connect All is not a master password

**Connect Account** must choose a provider-specific approved flow. Existing QML must not collect or store a provider password. The trusted host launches provider authorization, validates PKCE/nonce/state and audience, saves only allowed connection capabilities in an OS-backed vault, and exposes token-free connected/reconnect/expired/revoked status to Social. A remote service may require MFA, user consent or a provider-specific launch. **One Post-Apollo login does not generally authenticate Discord, Reddit, Vesktop, browsers, mail and other unrelated applications.** Apps may refuse shared credential stores or account switching, and some have no integration API.

**Connect All** means *orchestrated onboarding*, not universal silent SSO: gather eligible providers; separate `CONNECTABLE`, `NEEDS CONSENT`, `IN PROGRESS`, `CONNECTED`, `EXPIRED`, `FAILED`, `NOT SUPPORTED`. Run safe per-provider authorization serially/with constrained concurrency, respect scopes/consent, allow cancellation and recover partial progress. Never auto-approve elevated scopes. Preserve different providers' token custody and logout boundaries. App OS process launching alone must not be displayed as an authenticated connection.

**Switch** is three separate actions and must be labeled accordingly:
- **Switch local Social ID/layout:** changes UI workspace selection only.
- **Switch connected provider account:** requires provider-specific session/identity support, clear destination and host-mediated account selection.
- **Switch verified organization:** server independently validates currently signed-in person, membership, scope, revocation, target tenant and downstream request authorization. Updating a local directory label cannot grant access. Server audit is mandatory for mutations.

## Security and source dependencies in build order

| Milestone | Owner and dependency | User-visible result |
| --- | --- | --- |
| S1 | Identity/desktop security: real PID-bound logind guard, Sway compositor lock source, protected native host process, service disconnect safety | Accurate host/session status, never stale company data after verified lock |
| S2 | Identity: choose/configure real IdP with approved issuer/client/API, OS secret custody, cryptographic validation, logout/revocation, audited session | Sign in / sign out / verified profile |
| S3 | Server authorization: verified organization list, explicit request-level org switch with scope checks and auditable context, no self-asserted roles | Switch Organization works for authorized members only |
| M1 | CPU++ + Social: reuse existing local organization/branch/unit/portfolio editors, navigable 3-bay menus | Direct quick-create/edit/archive/delete buttons, without authentication claims |
| C1 | Connections owner: provider registry and per-provider OAuth/OIDC contracts + OS vault, genuine connected/expired status | Connect Account, Disconnect, Reconnect |
| C2 | Connections + Identity + UI: managed Connect All queue with per-provider consent and recoverable failures | Batch onboarding and status dashboard |
| M2 | CPU++ + Social + PostWallet after source verification: verified profile, local labels, organization and connections displayed together with distinct badges, actions gated on actual scopes | Operator-facing complete Social/Account Center |

These tracks are **not one automatic megamerge**. M1 local management can be reviewed in parallel with S2 after non-authoritative writes are kept separate. S3 cannot be bypassed by adding a menu button. PostWallet profile source/owner remains an explicit recovery dependency.

## Handoff and verification

For each UI track, inspect the current Social editor/store and CPU++ bay sizing, test real create/rename/archive/delete persistence and no new duplicate storage. For each connection track, test same provider user consent, token leak prevention, failure recovery, revoked/expired state, switching without wrong-account leakage, and provider-specific unsupported status. For S3, verify server denies cross-org access even when a local user tampers with the UI.

**CURRENT STATE:** This document is an actionable scope/architecture map, **not implementation of provider integrations, company switching, OAuth host deployment, PostWallet profile support or the UI controls**. Operator approval of a prior local-ID milestone does not certify any security milestone automatically.

**Hospital:** Patient `The-Post-Apollo-Project`; Room, Assignment and staff ownership for S1/S2/S3/M1/C1/C2/M2 remain unregistered from this external browser session. GitHub technical sources and current PRs must be rechecked at every handoff; operator is final authority.
