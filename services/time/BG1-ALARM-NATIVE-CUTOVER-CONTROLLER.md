# Hospital CLOCK // B2B20 Native Offline Cutover + BG2 Fixture Alarm Engine

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, live registration unverified
ASSIGNMENT // Native-owned old-writer launch hold, kernel exit, final V2 sync, durable recovery
STATUS // Draft only; synthetic fixture, production HOLD

## IMPLEMENTATION

Existing Quickshell AlarmManager remains ACTIVE and still solely owns the live V2 alarm file, scheduler, sound and notifications. Its native message receiver remains disabled. No incoming JSON message is permitted to pause or release it.

This implementation assembles a coherent, physically exercised *offline cutover* sequence rather than additional independent trust observations:

1. A participating old-writer launcher durably reserves its ONLY slot under Linux flock plus a SQLite FULL-sync journal in a private 0700 disposable directory. Launch is reserved BEFORE a process is spawned; an interrupted launch remains blocked rather than silently retried.
2. A native-side controller validates the reserved PID and kernel start ticks against the actual AF_UNIX accepted peer and acquires its SO_PEERPIDFD. It holds a process-exclusive gate lock while controlling the transition.
3. It commits HOLD_PENDING BEFORE any external supervisor is allowed to stop the writer. Future participating launch reservations refuse, including after controller death. This component never signals or kills a process.
4. It requires a genuine Linux pidfd exit witness, then opens the independently pinned V2 alarm file and synchronizes its bytes and parent directory with the existing B2B16 verifier. Wrong digest, unsafe file, symlink or changed source refuse.
5. It rechecks source bytes before selecting a DISPOSABLE native fixture. The durable SQLite journal records FIXTURE_NATIVE_SELECTED. Every result still has productionAuthority=false, installedRestartFence=false, nativeOwnsAlarmFile=false, canTransferOwnership=false, canRing=false, canNotify=false.

CI uses real subprocesses and AF_UNIX kernel evidence, actual SQLite transactions and process-shared locks, and actual fsync. It tests crashes/interruption, stale launch, concurrent controller, exited process, final file corruption, bad pins and unsafe disk paths.

## BG2 NATIVE SCHEDULER / DURABLE OUTBOX

This same coherent package also implements the real Python V2 alarm transition algorithm, cross-checked against the existing AlarmManagerPolicy.js. The parity suite compares Python and QML/Node for one-time/weekly alarms, grace and missed windows, snooze, expiry, disabled/paused states, restarts, midnight carry and local daylight-saving transitions.

The synthetic native engine is constructed only from a B2B20 controller after the real old-writer pidfd reports exit and the SQLite journal has reached FIXTURE_NATIVE_SELECTED. It reads and validates the complete V2 alarm document, computes the native tick, persists an event PREPARED in SQLite BEFORE replacing V2 bytes, atomically writes and fsyncs the new file and its directory, marks SAVED, and then allows delivery to a disposable callback. This is a real native V2 file mutation on the CI fixture, not a live user-alarm write.

The outbox marks DELIVERING before invoking the callback and DELIVERED only after callback return. A crash while DELIVERING is **uncertain** and is NEVER automatically replayed. A crash after source rename but before the SAVED journal commit is reconciled using a pinned expected digest; an uncommitted or unexpectedly modified file remains held for review. This is conservative at-most-once handling, NOT finished exactly-once sound/notification delivery. Production needs a provider-level idempotent acknowledgement protocol and installed supervisor restart recovery.

The native engine's background loop runs without the old writer in tests. It deliberately has NO production sound/notification backend, no installed native ownership lease and no enable path. Every public report keeps canRing=false and canNotify=false.

## HOW TO USE

No host action, QML restart, installed keys, systemd changes or live alarm modification. Tests run on a disposable GitHub runner.

## VERIFY

Dedicated synthetic Linux process tests, Python-versus-JavaScript Clock V2 differential parity tests, actual native fixture alarm-file write and crash-safe delivery-outbox tests, plus inherited native B2B16/B2B17/B2B19, mounted B2B15 and existing Clock alarm/notes suites. Exact eight-file Clock-only review boundary.

## WATCH OUT FOR

This proves the controller sequence and durable failure handling, NOT a production restart fence. The live Quickshell process is not launched through this fixture and same-UID processes can bypass the gate. The installed service owner must independently bind the real launcher, old writer session and native signed role; systemd restart inhibition/desktop integration remains unfinished. A synced file snapshot is not an exclusive lease. Never flip the native QML bridge or activate BG2 on this evidence alone.

## CHECKLIST

- [x] Verify Syntagma rules and current merged Clock checkpoint
- [x] Implement durable one-use old writer launch slot and crash hold
- [x] Verify real kernel process exit and final V2 fsync
- [x] Port native V2 scheduler and cross-check exact JS scheduling outputs
- [x] Build fixture native atomic alarm-file writer and SQLite occurrence outbox
- [x] Keep all production, transfer and sound rights denied
- [ ] Exact-head CI and independent security review
- [ ] Operator-authorized merge
- [ ] Native installed role, actual Quickshell launcher stop/restart fencing
- [ ] Real accepted-save generation to final sync receipt
- [ ] Installed BG2 sound/notification idempotent delivery, reboot/resume and Silverblue tests

## NEXT

Integrate a real installed native supervisor with a protected launcher and verified Quickshell lifecycle. Resolve real QML accepted-save generation (or independently approved offline shutdown) and source ownership. Native scheduling and fixture outbox are now implemented here, but require real provider-level idempotent sound/notification delivery and Silverblue recovery verification before production actuation.

## DECISIONS

Draft. No local machine changes, merge, installation, process signal, live alarm file edit, synthetic permissions expansion, real output or BG2 activation. Operator final acceptance separate.
