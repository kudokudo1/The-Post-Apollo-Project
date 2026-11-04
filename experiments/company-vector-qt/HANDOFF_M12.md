# 🏥 Company Network M12 // Optional owner-local map consumer

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** Company vector renderer / owner-local data boundary  
**ROLE:** External Hospital-compatible Nurse 2, unregistered  
**ASSIGNMENT:** Wire the M11 owner-local projection into the isolated native vector renderer, fail closed on invalid data, and verify with disposable fake company records  
**SCOPE:** Standalone Qt proof, tests and dedicated native CI; **no shell or live Company widget modifications**  
**DEPENDENCY:** M11 PR #1272 (merged) owner-local projection; M10 benchmark repair PR #1269 (merged but native acceptance must be separately verified)

## IMPLEMENTATION

The **existing local Company Hub Directory** is the only writer. Its records are owner-only, operator-reported location claims, **not verified tenant authorization**. M11 added a read-only projection of the four minimal location fields. M12 adds a **one-shot, opt-in native Qt reader** without widening that boundary:

1. The native binary only reads if launched with \`--owner-local-hubs\`. It starts a fixed \`/usr/bin/python3\` command with a compile-time-pinned script path and exact \`--owner-local-view\` parameter. It has a 4-second bounded read, no TCP/listening socket and no user-provided data paths.
2. The owner-local projection already enforces same-UID/non-root execution, private file ownership, schema and read-only load. Qt independently parses and validates the response shape, schema, revision, authority label, unique ID format, reported-only status, coordinate ranges and 150-record cap. Missing/unsafe/corrupted data is rejected **without** inventing a fallback or logging private values.
3. QML creates a \`MapQuickItem\` at each returned coordinate using a generic **REPORTED HUB** orange pin, with no name, organization, service detail, hub ID, or coordinate in the UI/log. The header explicitly says **OWNER-LOCAL REPORTED HUBS // NOT VERIFIED**.
4. No automatic camera recenter, no streaming, no history/log file, no external map API containing the projected records. The application still only fetches OSM vector tiles if \`--online\` or \`--styled-online\` is separately chosen. Selecting/zooming into a private location could disclose geographic tile requests to OpenFreeMap, so product UI must add explicit disclosure before any workflow that centers on private coordinates.
5. Existing M9 fake marker and M10 synthetic fixture remain separate; owner-local mode refuses combining with those test modes. Default invocation without any flags continues the **offline synthetic map**, with **no Company directory read**.

## HOW TO USE

After permissioned local installation and explicit operator acceptance (not part of this PR), an owner can run a one-time **offline** read-only map window:

\`\`\`bash
./company-vector-probe --owner-local-hubs --capture
\`\`\`

This reads only locally owned reported business coordinates. It does not create a new owner session, authenticate to an organization, or grant enterprise access. A separate \`--styled-online\` flag requests real vector tiles. **Do not run online with protected business geography until disclosure/authorization rules are accepted.**

The native smoke test uses a disposable fake private hub record and runs the offline Qt window in GitHub CI. It does **not** use real company records.

## VERIFY

CI validates:
- M11's exact read-only projection and owner-only private storage tests
- Explicit, fixed-command Qt consumer and response allowlist
- Marker registration without hub IDs/coordinates in logs
- Negative authorization and malformed projection handling
- One disposable fake-owner directory, owner-only file, and native \`--owner-local-hubs --capture\` run (no online tile requests)
- M10 benchmark completion patch preserved in this stacked implementation

Native Qt screenshot visibility of generic pins in the offline synthetic Flint viewport requires human review, since fixture coordinates should be selected to fall within that viewport. CI confirms registration via log, not pixel-perfect placement. No live desktop/native GPU testing has occurred.

## WATCH OUT FOR

- **This is not organization-wide permission control.** An owner-only local file and explicit command switch are not verified employee login, company tenant, role grant or partner authorization. The planned Identity Center must eventually supply scoped, revocable grants.
- Real business coordinates can be commercially sensitive even without names. Do not place the projected JSON into remote storage or debug logs.
- The Qt process runs as the same OS identity that already owns the file; it does not grant access to others or read Social credentials.
- Nothing in M12 is loaded by \`shell.qml\`, CompanyCoveragePane, or the live widget. Company status indicators must not say verified business coverage based on these pins.
- Native sidecar surface embedding, launch control, keyboard focus, actual input latency and Fedora/SwayPX compositor compatibility remain separately blocked pending explicit local test approval.
- Any future multi-user/company network needs audited authenticated authorization in addition to OS file ownership.

## CHECKLIST

- [x] Reuse M11 single read-only local projection
- [x] Explicit opt-in fixed command with bounded process
- [x] Strict schema verification, failure-closed behavior
- [x] Generic geographically anchored owner-local markers
- [x] Separate offline synthetic and real vector map modes
- [x] CI synthetic private-store integration test
- [ ] M12 native CI, visual evidence and operator review
- [ ] Fedora local compositor test with approved installation
- [ ] Verified Identity Center tenant/role authorization
- [ ] Widget launch/focus/close and sidecar coexistence
- [ ] User accepts replacement of the current Company map

## NEXT

Check GitHub CI for exact marker registration and audit logs for leakage. Then test the sidecar UI with the operator's chosen desktop setup under explicit local-change permission, measure actual GPU/software jitter on Fedora/SwayPX, and design an authenticated UI consent control before any multi-user rollout.

## DECISIONS

Owner-local mapping is read-only and opt-in, **not** organizational authorization. No server, no network listener, no interactive privileged mode, no default Company data import, and no production activation.
