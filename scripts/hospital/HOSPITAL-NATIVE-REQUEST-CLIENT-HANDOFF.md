# 🏥 Hospital Room Trash++ // Native C5-H2 client integration

PATIENT // The-Post-Apollo-Project
ROOM // Hospital Room Trash/Restore (source-owned)
STAFF // External Hospital-compatible DOC; no verified live Hospital registration
ASSIGNMENT // Consolidated source integration after merged #2045 and C5-H2 #2056
SCOPE // Hospital-owned C client, Room service/UI, read-only bin errors, tests
DEPENDENCIES // PX #130 (draft, atop PX #121), Connections #2056 (merged)

## IMPLEMENTATION

The application used to run \`px hospital room-lifecycle-trash\` and
\`room-lifecycle-restore\` directly. Those CLI requests cannot complete the
C5-H2 independently authenticated operator consent/seat/retention chain and
must not be promoted into usable desktop delete actions.

This change removes that mutation route from
\`services/hospital/HospitalRoomLifecycleService.qml\` and adds:

- \`services/hospital/native/hospital_room_request_client.c\`: an intentionally
  small compiled native executable source. The **production path is fixed**
  to \`/usr/libexec/post-apollo/hospital/hospital-room-request\`. It refuses
  to run unless that exact ELF inode is root-owned, unwritable by unprivileged
  users, and is the executing \`/proc/self/exe\`; verifies root-owned
  \`/run/post-apollo/hospital/issuer.sock\` path ancestry and the actual root
  kernel peer via \`SO_PEERCRED\`.
- Fixed Linux \`SOCK_SEQPACKET\` handshake:
  receives the precise C5-H2 \`READY\` frame, sends exactly
  \`{"action":"TRASH"|"RESTORE","roomId":"exact","schema":"postapollo.connections.hospital.native-request.v1"}\`,
  receives only a bounded \`COMMITTED\` native issuer reply.
  The client cannot accept a caller-selected socket, executable, key,
  public verifier, private signing key, DB path, grant file, or policy.
- QML asks this client for availability using \`--check\`, but **availability
  is not approval**. Only a deliberate second Room click starts an action.
  C5-H2 then independently proves the installed client, live operator seat,
  effective interactive Polkit, PX authoritative source review, retention,
  host identity and protected one-use commit.
- After a successful native request, QML requires exact source receipt
  \`schema/status/action/roomId/revision/originalPreserved/burnAllowed\`
  before treating the action as confirmed.
- The canonical TrashLifecycleActionDeck remains visibly locked at
  \`ownerApproved:false\`, \`policyReviewed:false\`,
  \`protectedResource:true\`, \`retentionHold:true\`, and
  \`burnCapable:false\`. An adjacent explicit **REQUEST NATIVE APPROVAL**
  control is the real route. This avoids claiming that the native-client
  availability probe is a pre-existing human approval.
- The existing Trash++ Hospital RESTORE row consumes the shared native
  service. No GIO, managed-copy or Burn code is modified.
- When PX main does not implement \`room-lifecycle-bin\` or
  \`room-lifecycle-review\`, Hospital displays
  **HOSPITAL BACKEND NOT READY** rather than raw argparse command usage
  or a misleading empty bin.

## VERIFY

The new C test compiles the production client with GCC and checks that an
uninstalled executable refuses. A second test-only compile runs
\`AF_UNIX SOCK_SEQPACKET\` socketpair fixtures checking:
C5-H2 READY-before-request, the exact action/Room schema, a COMMITTED reply,
invalid READY refusal, REFUSED status refusal, and Room-ID validation.

Source assertions verify installed path fixed, no client-selectable key or
path, QML never invokes an unsigned PX mutation command, native receipt
validation, Hospital Burn absence, and preservation of the existing
GIO/managed-copy and Hospital source boundaries.

CI workflow: \`Hospital Native Request Client / Backend Readiness\`.

## WATCH OUT FOR // HARD RELEASE GATES

1. **PX and Connections still do not share a working native writer protocol.**
   C5-H2 sends an authenticated prepare/commit exchange over
   root-controlled \`/run/post-apollo/hospital/px-writer.sock\`
   using \`SOCK_SEQPACKET\` and \`SCM_CREDENTIALS\`.
   Draft PX #130 currently exposes a **different** \`SOCK_STREAM\`
   \`hospital-room-writer-v1.sock\` with review/bin/trash/restore RPC.
   PX owns reconciliation, trusted retention source, issuer UID routing and
   native writer executable proof. Do **not** add a fake client adapter
   pretending the two sockets are interchangeable.
2. The new native client is **source only**. It is not installed, compiled
   on the user's machine, enrolled in the issuer's root-owned ELF digest
   policy, signed as a release, or authorized for production. The unit test
   fixture accepts no real grant or Room operation.
3. The root-issued signer from C5-H2 is not installed; the protected PX
   runtime is not installed. \`--check\` tests installed client/socket
   appearance, not full upstream readiness; the issuer must still refuse if
   Polkit, retention, legal hold, current Room, or writer provenance fail.
4. Until PX native read paths are deployed, the QML \`review\` and
   \`room-lifecycle-bin\` read-only routes still use the older PX CLI
   and may return NOT READY. No insecure DB fallback is added.
5. The QML compatibility property \`permissionReady\` means only
   **request transport installed + Room preview loaded**. It is *not*
   permission granted, signed consent or authority to change source.
6. Production additionally requires mutually verified signer/writer
   endpoint, secure systemd/SELinux and owner root key custody, approved
   v10→v11→v12 migration, WAL-aware backup/restoration and old-writer fencing,
   Room/Assignment/Bed writer reconciliation, independent security review,
   and operator acceptance.
7. No local machine files, services, permissions, SQLite data or external
   sessions were modified. This PR must remain draft until the owner
   reviews native request client executable identity and release boundary.

## HOW TO USE // AFTER OWNER-APPROVED RELEASE ONLY

Hospital → Surgery → SHOW WORKERS → ROOM → TRASH++ review →
REQUEST NATIVE APPROVAL → CONFIRM EXACT ROOM → native Polkit approval.

Trash++ → TRASH → HOSP → exact Room → REVIEW → CONFIRM →
native issuer + protected PX Restore.

Until installed, the menu reports HOSPITAL BACKEND NOT READY and Room
mutations are unavailable. Hospital BURN remains unsupported.

## NEXT

**PX owner:** reconcile C5-H2 prepare/commit protocol and source-writer
endpoint on PX #130; never modify the separately owned PX branch from the
Hospital UI lane.

**Connections owner:** review pinned ELF client identity and release
enrollment, Polkit/active-seat human approval and no cached grants.

**Hospital/Trash++ owner:** after protected PX read route is available,
switch Room/Bin reads to its reviewed native client, verify exact source
state across both screens, and run real install acceptance.

## DECISIONS

One coordinated Hospital source PR instead of tiny incremental prototypes.
No merge, local installation, production activation or Burn is authorized.
Operator final acceptance remains separate from CI success.
