# 🏥💜 Universal Connections // C3a pinned private-bus status origin

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS · parallel protected-host hardening  
STAFF ROLE // Nurse 2 (NRS-2), external Hospital-compatible; not live registered  
ASSIGNMENT // Bound C2m read-only private D-Bus observations to the daemon-reported unique owner  
SCOPE // GitHub-only experiment, regression tests, and handoff documentation  
PRODUCTION ACTIVATION // NOT AUTHORIZED

## IMPLEMENTATION

C2m already used a disposable private D-Bus daemon to obtain the current owner of the well-known `org.postapollo.ConnectionsStatusPilot` name, queried its Unix UID, and returned only `OBSERVED_UNVERIFIED`. The earlier client then introspected and invoked `GetStatus` **through the replaceable well-known name**. A different connection could acquire that name between owner lookup and the read. Its output would still be marked unverified, but the status observation would be ambiguously attributed.

C3a fixes that preparatory trust weakness in `services/connections/experiments/C2mPrivateBusStatusPilot.py`:

1. Read the current name owner's **unique bus connection name** from the D-Bus daemon and validate its syntax.
2. Query the daemon's Unix UID for precisely that unique connection.
3. Introspect and call `GetStatus` through the unique owner, never the replaceable well-known name.
4. Query the well-known owner again after the reply; reject owner changes or disappearance with `HOST_OWNER_CHANGED`.
5. Keep every credential, API, approval and host-authentication flag **false**, even when the observation succeeds.

This is **not** a cryptographic host attestation, production system-bus identity, or an authorization primitive. Unique-name binding prevents substituting a different bus connection during one observation, not a compromised daemon, unprotected service, or malicious same-UID process.

The existing `C2m` isolated status test suite now includes deterministic owner-stability and adversarial owner-swap/disappearance/forged-name tests alongside its real private-D-Bus process tests. C2y Silverblue scripts, CPU++ QML, C2n protected unit templates, credentials and TASKS remain untouched.

## HOW TO USE

No operator desktop action. The C2m private-bus tests run only under the existing GitHub Actions `connections-c2m-private-dbus-pilot.yml` workflow. Production CPU++ → SETTINGS → CONNECTIONS stays read-only and unverified.

## VERIFY

Required exact-HEAD checks:

- [ ] Real C2m disposable D-Bus status and refusal tests pass.
- [ ] Stable unique owner calls `GetStatus` through the unique name.
- [ ] A different owner after the response is rejected.
- [ ] Owner disappearance after the response is rejected.
- [ ] Nonunique or malformed owner names fail closed.
- [ ] C2l/C2k/C2i/C2j and CPU++ broker regressions pass.
- [ ] Independent review and operator acceptance remain pending.

The race tests use a deterministic injected D-Bus mock to force exact time-of-check/time-of-use changes. The same workflow also exercises the actual isolated D-Bus daemon and service to check real transport compatibility. Neither proves production trust.

## WATCH OUT FOR

A bus unique name and a daemon-reported UID bind transport observations only; they do not establish trusted executable origin, operator identity, policy consent, or secure key handling. Same-UID session bus traffic remains untrusted by design. C2n–C2r protected-service experiments and C2y real Silverblue rollback remain independent gates. Do not promote this status to `hostAuthenticated=true` or enable `credentialActionsEnabled`.

## CHECKLIST

- [x] Recheck Syntagma AGENTS and relevant Hospital protocols.
- [x] Inspect current main, existing C2m/C2n experiments, and parallel C2y scope.
- [x] Create isolated GitHub branch and harden the C2m observation.
- [x] Add adversarial owner-switch tests.
- [ ] Verify exact branch HEAD CI.
- [ ] Independent review and operator decision on merge.
- [ ] Later establish protected service origin from OS-managed files, policy and authenticated caller.

## NEXT

After CI and independent review, coordinate a separate protected service-origin verification milestone using the already isolated systemd/D-Bus/SELinux status host. Do **not** implement real credential approvals in this branch. Coordinate with the C2y successor instead of changing its test harness.

## DECISIONS

Implementation is scoped to defensive private-bus observation hardening in GitHub. No production imports, local workstation writes, actual host authentication, real keyring access, service activation, or merge.
