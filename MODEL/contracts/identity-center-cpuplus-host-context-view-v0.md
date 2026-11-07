# Identity Center → CPU++ ID Management // token-free host context viewer v0

> **STATUS //** Implemented *review-branch* UI consumer; operator acceptance, native runtime verification, production identity host and real permission administration remain **pending**.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **SCOPE //** CPU++ ID MANAGEMENT overview only: a collapsible, read-only view of an already running Identity Center host's validated context display. No new Identity Center authority, IdP setup, permission writers, company switcher or host startup.
>
> **OWNER //** CPU++ owns the presentation. Identity Center independently owns authentication, the scoped membership API, session validity, verified organization grants and the private snapshot channel. Local Social stores independently own editable layout IDs, notes and manual organization associations.
>
> **SOURCE //** Operator asked to proceed after accepting the local CPU++ ID/editor/organization-association milestones. Existing separate Identity Center host/IPC/display contracts and source were read at current main before implementation.

## Mechanism: processes, data and what changes

```text
[ separately operated Identity Center host (NOT deployed by this PR) ]
  authenticated IdP session + verified scoped API response
  privileged process owns bearer; never passes it to QML
                     |
    existing private read-only Unix socket, if available
                     |
 [ fixed identity_display_reader_cli_v0.py --json ]
  checks private XDG_RUNTIME_DIR socket and validated display payload
                     |
 [ reused IdentityCenterOrganizationDisplayReader.qml ]
  only when CPU++ ID MANAGEMENT / overview / CHECK HOST CONTEXT is active
  validates exact schema, finite bounded memberships + expiring grants
  clears on every new poll, close, host loss, malformed data, late results
                     |
 [ CpuPlusIdVerifiedContextPane.qml, left existing overview bay ]
  HOST STATUS / organization ID and kind / display scope previews
  portfolio IDs and their already-filtered member organization IDs
  no login, tenant switch, permissions request, local ID binding or write
```

The existing Social and CPU++ local IDs `identity-N`, account notes, organization-directory labels and manual organization links are NOT trusted people, employers or verified grants. They are not joined to host `organizationId` values by string equality or operator selection.

The Identity Center display contract is `post-apollo.identity.desktop-context-display.v0` with exact keys `schema`, `status`, `organizations`, `portfolios`, `canSwitchOrganization:false`. Each permitted organization has `organizationId`, `kind`, and preview-only `scopeGrants` with `action`, `divisionId`, `unitId`, `expiresAt`. Never add subject IDs, secrets, device tokens, bearer receipts, writable capabilities or self-asserted roles to that schema.

The user clicks **CHECK HOST CONTEXT** to begin the pre-existing fixed reader's five-second read-only polling. Clicking **HIDE HOST CONTEXT**, leaving CPU++ ID MANAGEMENT or closing the mode deactivates the reader and invalidates the display. Each poll clears the previous snapshot *before* a new response. If no host socket exists, the viewer shows **NOT CONNECTED** or **UNAVAILABLE**, never sample companies or implied access.

The right CPU++ bay's existing local rename/contact/account labels/organization link editor, and the middle bay's create/remove actions are not modified. The existing CPU++ 1000×834 chassis, 390px/260px/flexible three bays, and main rail remain identical.

## Trust, authority and limits

1. This is a **display**, not a permission gate or authorization receipt. A downstream server must independently validate current issuer/subject, tenant membership, scope, revocation and request intent before **every privileged operation**.
2. The current test-only socket checks same OS UID, not cryptographic host identity. A hostile same-UID process can forge the display, so neither the view nor its labels are proof of a real person's authority.
3. A signed-in *person identity* or production session status is **not supplied** by the display schema. CPU++ therefore does not claim to know one, even if organizations appear. No invented role selection or employee management UI is included.
4. The repo contains experimental real-Keycloak CI flows, an offline host state machine, private IPC and synthetic signed-claim tests. That does **not** establish a deployed, secure real IdP/API/host. This PR does not install any service or ask for user credentials.
5. The view intentionally has no action that can grant/revoke roles, switch companies, transfer ownership or update the Identity Center database. Existing local organization association edits remain non-authoritative.

## Verification

- New source-contract test: `python3 -m unittest discover -s tests/cpuplus -p 'test_cpuplus_identity_host_context_v0.py' -v`
- Existing real QML JS validator/lifecycle: `node tests/messaging/test_identity_center_ipc_viewer_v0.cjs`
- Existing isolated socket reader and tokenless projection: `python3 -m unittest discover -s tests/identity -p 'test_identity_display_reader_cli_v0.py' -v` and `test_desktop_context_projection_v0.py`.
- Existing CPU++ ID Management editor/geometry regression suites remain required, including Social organization links and data-store tests.
- GitHub CI on exact PR head is useful but **does not prove live desktop or real identity**. Operator desktop tests and a security-owned production-host acceptance gate remain open.

## Remaining work / next contract boundary

**Owner review needed before any actual authenticated account and role administration:**

- Approve the IdP, issuer/domain/redirect URI, HTTPS backend trust, native host supervision and OS credential custody.
- Deploy and independently security-review the privileged host and signed tenant-scope API, including sign-in/out, session revocation, suspend/lock and user-switch invalidation.
- Add a separately reviewed *server-authorized mutation API* for role changes: bound principal, independent organization+scope authorization, target subject, explicit operation, audit, confirmation and revocation. Local QML may submit an intent, never issue a grant.
- If an identity-to-organization relationship is ever needed in CPU++, map real verified host context to real identity records **in the server**, not to local `identity-N` aliases.
- Do not enable “Switch Organization”, “Grant Permission” or impersonation controls merely because this read-only viewer displays scope previews.

## Hospital-compatible checkpoint

**IMPLEMENTATION //** Bounded UI consumer on GitHub review branch, with no local-machine writes, new privileged service or permission actions.

**HOW TO USE //** After operator-authorized merge/deployment, CPU++ → ID MANAGEMENT → left overview → CHECK HOST CONTEXT; HIDE HOST CONTEXT to retract and invalidate it.

**VERIFY //** Exact-commit CI plus native desktop review required; no claimed live host.

**WATCH OUT FOR //** No production host is supplied. Same-UID display IPC is not a strong identity attestation.

**CHECKLIST //** Read-only consumer + tests; native runtime check pending; identity-host deployment and permission API blocked on separate owner approval.

**NEXT //** Review current-HEAD checks and UI layout; seek dedicated security/identity owner contract before any authenticated organization management.

**DECISIONS //** Keep local labels separate from verified memberships, preserve fixed CPU++ geometry, route all real auth to independently secured host and server; user retains final acceptance authority.

No Hospital Room, Assignment, Staff Role, session lease or local checkout registration was verified. The PR is the recovery pointer until one is established.
