# 🏥💜 DOC 4 // Hospital C5-H5 all-entrypoint source inventory

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5  
**STAFF ROLE:** DOC 4 · external Hospital-compatible; live Hospital registration not verified  
**SOURCE BASE:** application main `1e13289cfdce713bf0ea004da7662d633a4c75b3`  
**PX EVIDENCE:** separately owned draft PX #133 at `7ea86895503f60a126824835401f75f97bf4aa02`, stacked on PX #130  
**PRODUCTION:** HOLD

## IMPLEMENTATION

C5-H4 (merged PR #2247) established a hard denial **inside the reviewed
native C5 issuer**. It does not establish that other installed Hospital/PX
writers cannot mutate the same SQLite source, especially older app/PX paths.

This milestone provides an additive, read-only source inventory rather than
changing any owner or allowing an alternate production route. The scanner
reads the **current application QML**, the fixed native request/read client
source, the merged C5 issuer, and the exact PX #133 source snapshot. It
never imports/runs those applications or accesses a database/socket/host.

At the inspected current application baseline, **21 Hospital QML services**
still reference desktop-local PX executables. These include Assignment,
Chart, Doctor/Room metadata writes, Session creation/attachment and
ordinary Room operations. **Three** QML services use fixed native Room
executables: `HospitalRoomLifecycleService.qml` uses the request and read
clients; `HospitalRoomBinService.qml` uses the read client; and
`HospitalDoctorService.qml` now uses native `doctor-directory` read.
The Doctor read migration is a change from the older PX-side inventory
that counted 22 desktop PX services and two native services. Doctor
**writes** remain held, not silently migrated.

PX still has four direct dispatch call sites for
`python3 "$ROOT/bin/px-hospital-store"`. The legacy source's
`legacy-store-cutover.v1` tombstone is checked before database open, but
its **absence allows pre-cutover desktop legacy operations**. That guard
cannot stop already-running processes or previously installed binaries.
The separately owned PX protected writer restricts generic
`store-command` to the distinct runtime UID and excludes lifecycle
mutators from the generic bridge; signed Trash/Restore uses the separate
root-issuer consent route. None of those source facts proves actual
installation or all-writer fencing.

The C5-H5 scanner rejects changed or newly observed desktop/native
source-entrypoint tokens, newly exposed generic privileged UI paths,
changed Room issuer hard-denial AST, changed PX runtime UID
and cutover guards, and disappearance of known legacy operation witnesses.
Its report ALWAYS includes:

`allWriterCompatibilityVerified: false`,
`allLegacyProcessesFenced: false`,
`installedHostObserved: false`,
`independentHumanConsentVerified: false`,
`protectedPxProductionWriterVerified: false`,
`productionAuthorized: false`,
`safeActions: []`.

## HOW TO USE

The dedicated GitHub workflow checks out the application at the PR head
and PX #133 at the explicit read-only pinned commit. It runs a hostile
source-mutation suite and prints the constrained inventory. It does not
open SQLite, invoke PX, execute QML, attach to native sockets or require
workstation privileges. No user-facing Hospital action is enabled.

## VERIFY

The adversarial suite checks the known baseline, new desktop PX paths,
unknown native requester paths, direct database/store-command and Room
lifecycle CLI bypass strings, lost native commit receipt checks, loss of
Doctor read-only status, changed cutover marker or protected runtime UID,
a generic bridge lifecycle bypass, replaced consent-root boundary,
and missing pin/source.

This is a **token- and AST-based source regression test**, not an
exhaustive dynamic call-graph analyzer or a complete live process inventory.
A renamed route, novel script launcher, alternate executable, or earlier
installed binary can evade its current patterns; the report refuses
release even on PASS.

## WATCH OUT FOR

PX #130/#133 are still **separately owned, draft, and uninstalled** at this
checkpoint. This PR does not update, merge or install them. A pinned
draft snapshot is development evidence, never native release authority.
The legacy PX data path, generic protected runtime bridge and native
consent writer all operate under different trust contracts; allowing
the desktop UID to call generic protected `store-command` would be a
permission escalation, not a compatibility fix.

A true all-writer release needs native process/installed binary inventory,
source owner agreement on each command and its caller UID, denied legacy
launches, WAL-consistent protected backup/rollback and migrations,
root-controlled source provenance, signed one-use consent and native
end-to-end success/negative cases. Hospital Burn remains unavailable.

## CHECKLIST

- [x] Recheck current app and PX #130/#133 branch/source ownership
- [x] Document current 21 legacy / 3 native application source routes
- [x] Add read-only cross-repo pinned PX source scanner
- [x] Add hostile route-mutation regression cases and isolated CI
- [ ] Exact-head GitHub CI and independent Nurse 2 review
- [ ] PX owner complete command-level runtime/native cutover and source release
- [ ] Installed old-writer fencing and protected backup acceptance
- [ ] Trust-enrolled exact-operation consent and one-use custodian
- [ ] Operator final production acceptance

## NEXT

Ask the PX owner to reconcile required ordinary Hospital operations
(Session, Doctor/Bed, Assignment, Chart, Room) with protected native
read/write APIs and caller permissions, without accepting a desktop
generic SQL/store-command RPC. DOC 4 preserves the issuer's unconditional
consent refusal until independently authenticated user approval can be
verified at the exact Room/nonce/graph/revision.

## DECISIONS

**C5-H5 is source/CI admission evidence only.** No PX branch edits,
system install, database write, secret/key, QML activation, service
restart, automatic merge, live Hospital registration or production
authorization. Any new source path requires fresh human review.
