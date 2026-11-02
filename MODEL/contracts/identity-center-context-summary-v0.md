# Identity Center // verified read-only membership context summary v0

> **STATUS:** SYNTHETIC OFFLINE RESPONSE CONTRACT. No live HTTP endpoint, production identity provider, durable company database, desktop integration or real employee access. Approval/merge and operator acceptance are separate.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator continuation after the existing Social USER // SETTINGS sections were merged in #981, following merged Identity Center prototype foundations and disposable real-Keycloak CI pilot.
>
> **SCOPE:** `services/identity/synthetic_policy_v0.py`, `services/identity/synthetic_request_boundary_v0.py`, `tests/identity/test_synthetic_context_summary_v0.py`, isolated CI workflow and this indexed contract. Existing Social QML/UI, provider-account flows, Hospital files and actual company data untouched.
>
> **HOSPITAL:** External Hospital-compatible repository contribution. No verified live Room, Staff Role, worker assignment or operator desktop attachment.
>
> **VERIFY:** Source-contract and offline test CI only; no live API or Quickshell behavior has been verified.

## Purpose and mechanism

USER // SETTINGS now contains a **read-only ORGANIZATIONS** page with a disabled switcher. The desktop correctly says it cannot verify company memberships yet. The next meaningful integration contract is **"who am I permitted to see?"**, not "trust whatever tenant the UI selected."

This slice adds a `readMyContexts` operation to the **existing test request boundary**:

```text
[ synthetic request: schema + operation + accessToken ]
                         |
                         v
[ existing SessionVerifier (fake or real CI test adapter) ]
        - signed-in person from verified session
        - trusted host time / issuer / audience / expiry
                         |
                         v
[ existing SyntheticPolicyStore SQLite :memory: ]
        - ACTIVE organization membership
        - exact per-person, per-org scoped grants not expired
        - portfolio membership JOIN independent active org membership
                         |
                         v
[ read-only versioned context summary ]
        organization IDs + kinds + scoped grant previews
        visible portfolio IDs + only independently joined organization IDs
                         |
                         v
[ future trusted HTTP API ] -> [ future Social settings adapter ]
     (NOT built)                 (NOT wired)
```

**Request fixture**

```json
{
  "schema": "post-apollo.identity.synthetic-request.v0",
  "operation": "readMyContexts",
  "accessToken": "DISPOSABLE-TEST-SESSION"
}
```

Only the exact three fields above are accepted. The caller cannot supply `principalId`, `organizationId`, `portfolioId`, `role`, `now`, or any other authority input. Any such field produces `{"status": "DENIED"}`. A production API would extract the access token from a protected HTTP authorization header and derive identity from a proper validated session, not trust this JSON shape as a ready-made public endpoint.

**Example synthetic response** (IDs are test fixtures, not real companies):

```json
{
  "status": "OK",
  "schema": "post-apollo.identity.context-summary.v0",
  "organizations": [
    {
      "organizationId": "llc_a",
      "kind": "llc",
      "scopeGrants": [
        {
          "action": "records.read",
          "divisionId": "health",
          "unitId": null,
          "expiresAt": null
        }
      ]
    },
    {
      "organizationId": "llc_b",
      "kind": "llc",
      "scopeGrants": [
        {
          "action": "records.read",
          "divisionId": null,
          "unitId": "maryland",
          "expiresAt": null
        }
      ]
    }
  ],
  "portfolios": [
    {
      "portfolioId": "family",
      "organizationIds": ["llc_a", "llc_b"]
    }
  ]
}
```

A recognized person with no authorized memberships gets `{"status":"OK","schema":"...","organizations":[],"portfolios":[]}`. An invalid/expired/revoked session gets **`{"status":"DENIED"}`**, never an empty-success response. Organization data and grant previews never leak for a different principal.

## Important boundaries

- An **organization membership** lets a user see their own membership *summary*. It does not imply permission to read or update any organization record. An organization can appear with `scopeGrants: []`.
- A **portfolio** is a management grouping, not software/legal ownership and not an authorization inheritance relationship. Only portfolio organizations with the person's **independently active** membership appear.
- `scopeGrants` is a **display preview only**. Every actual resource request must be independently re-authorized with server-side action, division, location, tenant and current grant checks. An old cached UI response is never a valid permission token.
- Expired grants disappear from the summary at the trusted test clock; revoking an organization membership removes that organization and its portfolio listing without removing another valid membership. Revoked *session* rejects the entire request.
- No personal employee details, secrets, social provider accounts, client cookies, raw token, grant ID, authentication session or unrelated user's data are exposed in the response.
- `kind` is only a synthetic fixture type (`llc`, `nonprofit`, `customer`); real organization names, identifiers, aliases and governance statuses require reviewed production schemas. Current model does **not** represent company ownership, board authority, policy inheritance, or actual role assignments.
- The `SyntheticPolicyStore` and request adapter are in the same test process; the injected fake verifier is not a security boundary. There is no TLS, durable DB, logged-in desktop session, audited grant administration, public endpoint or network access. **Do not expose this fixture to untrusted clients.**

## Offline verification

The [context-summary workflow](../../.github/workflows/identity-center-context-summary.yml) compiles existing identity modules and runs:

```bash
python3 -m pip install -r services/identity/requirements-jwks-verifier-v0.txt
python3 -m unittest discover -s tests/identity -p 'test_*.py' -v
```

Focused tests cover multiple independent memberships, function-vs-location grants, portfolio isolation, unrelated customer and nonprofit separation, revoked membership, expired grant, forged request identity/context/clock, revoked/expired session, unknown session, no secret leakage, unchanged legacy APIs and read-only behavior. Earlier signature verification and disposable Keycloak tests remain separate; the latter requires real CI Docker and is not run by the offline test discovery.

## Recovery and next implementation owner seam

All changes are additive to the existing offline models and narrowly extend the existing request handler. Rollback is refusing to merge the draft PR or reverting these specific files. No migrations, persisted real users, local system changes, or real sessions need cleanup.

**NEXT (separate scoped owner approval):** design a real trusted `GET /me/contexts`-style service endpoint and stable person/organization IDs, with IdP subject-to-internal-principal mapping, durable tenant data, revocation/audit and scoped API permissions. After a protected API is verified, implement a **read-only client adapter** for the existing Organizations page. The switcher remains disabled until actual server-authorized context selection is implemented and tested against forged IDs/revocation.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Read-only `readMyContexts` operation on verified-session synthetic request boundary plus SQL membership/grant/portfolio summary filtered for the verified principal.

### HOW TO USE
Review offline source and CI. No deployed UI action or real endpoint exists. JSON samples are test fixtures, not present-day company data.

### VERIFY
Check exact-head CI. Verify negative paths and preservation of old `authorizeRecord` / `listPortfolioOrganizations` operations. Desktop visual/runtime tests and real authorization are separately pending.

### WATCH OUT FOR
Do **not** interpret the summary's `scopeGrants` as authorization to perform an action. Do not derive enterprise principal IDs from Social `identity-N`. No public API or login mechanism is being delivered by this PR.

### CHECKLIST
- [x] Confirm #981 merge, existing backend and ownership before updates
- [x] Add read-only context projection with tenant-specific grant and portfolio filters
- [x] Enforce verifier-derived identity and exact closed request fields
- [x] Add synthetic negative tests and isolated CI
- [ ] Exact-head CI green
- [ ] Security/architecture and operator review
- [ ] Assign protected API, durable store and desktop adapter in separate bounded work

### NEXT
Verify tests → security review → trusted read-only API contract → read-only Social Organizations adapter → later approved organization switching.

### DECISIONS
Read-only context summary contract is prototype scope; no production tenant schema, API host, IdP vendor, desktop token handling, permissions management UI or company enrollment decided.
