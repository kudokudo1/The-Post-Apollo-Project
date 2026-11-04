# 🏥 Company Network M11 // Owner-local, read-only hub map projection

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** Company Network vector map / data boundary  
**ROLE:** Nurse 2, external Hospital-compatible (no live registration)  
**ASSIGNMENT:** Establish a safe, bounded source for geographic hub markers  
**OWNER:** Company local hub directory owns storage; shared Identity Center remains future authority for genuine organization permissions  
**STATUS:** Isolated repository implementation; NOT mounted in the native renderer or Company widget

## IMPLEMENTATION

The existing \`CompanyHubDirectory.py\` is an owner-private, manually populated registry of reported hub claims. It is **not** a verified company/tenant membership, provider-contract database, customer profile or employee directory. The current Social identity and organization directories are local metadata systems, not authenticated grants.

Add \`services/company/CompanyHubMapReadOnly.py\` as a **one-shot, read-only projection** of that existing single source of truth. It requires **exactly** \`--owner-local-view\` to run and refuses setuid/root operation. It calls the existing \`CompanyHubDirectory.load()\`, which already checks owner-only directory/file permissions and validates document revision/schema. It then drops all but the four fields required for a visual point: \`id\`, \`longitude\`, \`latitude\` and \`reported: true\`. Archived hubs are removed. It emits a small \`post-apollo.company-map.owner-local-v1\` response on stdout. No paths can be supplied, no background service is started, and **no file is written**.

**Critical distinction:** \`--owner-local-view\` is an *explicit invocation/consent switch* for a same-OS-user session, **not** an organizational permission grant. No cross-organization data access, role verification, confidential workforce/client systems, authority elevation, or network access are provided. This script alone does not grant access to data that the local OS identity could not already read.

**No automatic map integration yet.** The native experimental Qt app still accepts only the synthetic M10 fixture. M11's projection is intentionally separate to allow inspection/verification before authorizing actual Company values in a renderer. It has no connection to \`shell.qml\`, live Company widgets or the internet.

## HOW TO USE

Only after operator approval and an installed/reviewed local checkout, an **explicit owner-local inspection** is possible:

\`\`\`bash
python3 services/company/CompanyHubMapReadOnly.py --owner-local-view
\`\`\`

This prints a JSON document to the **local terminal** that may contain real business coordinates. It should not be pasted into an external chat, committed to GitHub, uploaded, emailed, logged to third-party telemetry, or used as a provider authorization certificate. Ordinary launches of Company Network do **not** run it.

For isolated non-personal verification, no local files are required:

\`\`\`bash
python3 -m unittest discover -s tests/company -p 'test_company_hub_map_readonly_m11.py' -v
\`\`\`

The tests create disposable fake Company files under a temporary private directory, exercise both refusal and allowed read, then verify that the original file bytes, modification time and private permissions have not changed.

## VERIFY

CI enforces exact command gating, exclusion of organization/client/worker/service labels, archived-entry omission, file ownership, corrupt-file rejection, and retention of M3 directory tests. A source review confirms no Python network call, no arbitrary path argument, no writer call, and no Qt/Quickshell runtime hook.

**Unverified:** real users/roles, a real company identity/tenant grant, an actual IPC communication protocol, Qt import of the projection, encrypted transfer, and any live desktop interaction. These are future separate milestones, not implicit successes.

## WATCH OUT FOR

- Even coordinates can disclose sensitive operations. The projection is *not* anonymous or safe for public distribution. It is meant for **same-host owner-local display only**.
- A CLI switch is a human-intent gate, **not authentication**. For company-wide use, require a verified Identity Center principal, organization/resource scope, explicit grants, revocation and audit before exposing data across users/devices/processes.
- Never persist the projection unencrypted or make it accessible on TCP/HTTP. Do not use arbitrary path inputs or transmit the records to map tile providers.
- Any click on a map that recenters on a business site may disclose the viewed geographic region to the external tile provider. The native sidecar must not auto-pan to real hub coordinates; display should require a visible disclosure/consent step.
- Do not add worker names, client enrollments or protected personal data to \`CompanyHubDirectory.py\`.
- This step does **not** implement native desktop integration or the read-only map consumer; its source contract is the small safe producer needed before that consumer.

## CHECKLIST

- [x] Reuse the canonical CompanyHubDirectory validator and owner-only storage
- [x] Explicit opt-in read-only CLI path, no arbitrary file paths
- [x] Strip all names/service metadata and exclude archived entries
- [x] No writes, background monitors or network calls
- [x] Synthetic disposable tests and dedicated CI
- [ ] Confirm M10 benchmark repair PR #1269 native CI passes
- [ ] Add a native sidecar consumer gated by a visible operator action
- [ ] Permission-granted organization/tenant support
- [ ] Verify existing Company Hub button and vector map coexist on Fedora/SwayPX
- [ ] Operator final acceptance

## NEXT

Finish the M10 event-driven benchmark gate. Then, in a separate isolated Qt sidecar PR, implement fixed-path, one-shot consumption of the M11 projected data **only after an explicit operator action**; do not send any projected coordinates to the online map provider, and do not auto-center on private hubs. Add failure-closed tests for missing/malformed responses and no-coordinates-in-logs. Keep the existing Company widget as fallback until local visual acceptance.

## DECISIONS

The smallest data surface is four fields and owner-local reported claims. Memberships, roles and cross-company permissions cannot be inferred from this directory. The Company writer remains the only writer; this adapter is strictly a read-only, dormant addition.
