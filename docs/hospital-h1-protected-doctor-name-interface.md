# 🏥💜 Hospital H1 // Protected Doctor Display-Name Writer Interface

**STATUS:** PROPOSAL / SOURCE-ONLY / NOT ENROLLED / NO NATIVE WRITER
**PATIENT:** `The-Post-Apollo-Project`; backend dependency `The-Post-Apollo-Dev-Exp`
**ROOM:** Hospital Trash++ ↔ Universal Connections
**AUTHOR ROLE:** External Hospital-compatible DOC, application-side candidate only
**PRODUCTION:** HOLD. Operator authorization, backend owner agreement and Nurse 2 review required.

## Existing source and why it is not an authorization path

Application `HospitalDoctorNameService.qml` currently invokes the desktop-local PX
`hospital doctor-name-set ID --name NAME --json` through `bash -lc`.
The PX store function `doctor_name_set` updates only `doctors.name`
and `updated_at`, preserving the concurrent `role`, `status` and other
Doctor fields. Its blank-name behavior resets the friendly name to `doctor_id`.

The protected PX backend at Hospital #133 has a generic `store-command`
interface that **already includes** `doctor-name-set`, but only a separately
authenticated runtime-service UID may invoke it. That endpoint is explicitly
**not** an operator desktop UID API. The installed fixed
`hospital-room-read` route accepts `doctor-directory` as a READ ONLY
operation and must **never** be repurposed for mutation.

No protected Doctor-name issuer, allowed desktop requester profile, signed
commit command, root-owned executable identity or accepted receipt contract
currently exists in the reviewed sources. A UI source change cannot invent
the missing permission.

## Candidate isolated app-side increment

This PR only adds `HospitalDoctorNameIntentPolicy.js` and
`HospitalProtectedDoctorNameService.qml` as **unused parallel candidate
components**, alongside executable source-level tests. They are NOT wired
into `HospitalW.qml` or used to replace the existing editor.

`prepareNameIntent` accepts exactly two plain JavaScript strings:
an existing technical Doctor ID shaped like the protected reader's
`[A-Za-z0-9._:/-]{1,160}`, and a display name of up to 96 Unicode
codepoints, excluding ASCII controls or malformed surrogate halves. It
trims input. Empty display names request the existing reset-to-technical-ID
semantics. Returned candidate shape:

```json
{
  "schema": "postapollo.hospital.doctor-name-intent.v1",
  "action": "DOCTOR_NAME_SET",
  "doctorId": "fixture-doctor-1",
  "name": "Display Name"
}
```

The payload cannot specify role, staffing status, room, assignment, provider,
privileges, SQLite, process commands, a database, a socket or a signing key.
The policy does NOT claim the ID exists or that the operator can write.

`HospitalProtectedDoctorNameService.saveName` refuses *every* attempted
write with `HOSPITAL NATIVE HOLD // PROTECTED DOCTOR NAME ISSUER NOT ENROLLED`,
even for valid candidate input; it does not launch a `Process`, emit
`nameSaved`, update the roster or generate a fabricated success receipt.
This preserves all current production UI behavior until a separate accepted
cutover occurs.

## Needed protected backend contract before an actual write

The PX/Connections **backend owners**, not this application candidate,
must approve and implement the separate route:

1. **Exact requester and scope:** a fixed root-owned, reviewable desktop
   request executable with immutable source identity and explicit name-only
   operation. Do not expose `store-command` to the desktop UID, use
   `bash -lc`, accept arbitrary SQL/argv, or reuse the read-only client.
2. **Independent consent/identity:** protected issuer authenticates actual
   operator UID and seat, verifies intended Patient/Doctor membership and
   authorized scope, checks the host/release, obtains explicit action-specific
   approval, and issues a short-lived, single-use signed authorization bound
   to the exact Doctor ID and requested name. Neither UI validation nor a
   supplied "consent" boolean proves authority.
3. **Atomic protected write:** writer validates signature, operation,
   nonce/replay fence, expiry, policy generation and exact subject; it must
   verify current Doctor existence and an independently protected
   **compare-and-set version** in the same SQLite transaction. A client
   `updatedAt` timestamp alone is not sufficient version proof.
   Update **only** display name and its modification timestamp, never role,
   status, permissions, Assignment, Room or Session. No automatic retry
   after ambiguous commit outcome.
4. **Verifiable outcome:** distinguish REFUSED, UNKNOWN and COMMITTED.
   The response must be bound to the original request and protected writer
   transaction: exact Doctor ID, committed effective name, canonical event
   identity, protected revision/digest and verifiable one-use commit
   evidence. A zero CLI exit or JSON saying `status: COMMITTED` is not
   proof without trust in executable/source and issuer/writer verification.
   If uncertain, refuse success and refresh protected state.
5. **Cutover plan:** protect backups, original WAL+SHM, old-writer fencing,
   release identity, systemd/socket ownership, SELinux, rollback and
   independent Nurse review. Confirm the installed Quickshell version.
   Only after explicit operator approval may HospitalW bind to the new
   client and remove the legacy editor's desktop command.

The exact native request and receipt schemas **remain to be agreed** by
PX/Connections owners. The candidate JavaScript schema above is a UI intent
proposal, not an authorized wire protocol or signed grant.

## Verification and recovery

- `node tests/hospital/test_doctor_name_protected_staging.js` exercises
  the actual candidate QML methods and pure policy against synthetic data.
- GitHub source checks guarantee the new candidate never starts a process or
  uses the legacy PX command. The host remains bound to its existing service.
- Do not mark a Doctor "SAVED" based on candidate input or a test fixture.
- H1 native protected reader and per-request watchdog are separate,
  independently reviewed milestones. They are not a write authorization.

**NEXT:** PX/Connections owner: respond to this interface with approved
native issuer/writer/receipt design. Application DOC can then implement an
isolated client and strict receipt verifier in a new source-only PR, followed
by disposable end-to-end security tests and Nurse 2 review. Production HOLD.
