# Hospital CLOCK // B2B20 Durable Native Offline Cutover

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

## HOW TO USE

No host action, QML restart, installed keys, systemd changes or live alarm modification. Tests run on a disposable GitHub runner.

## VERIFY

Dedicated synthetic Linux tests and inherited native B2B16/B2B17/B2B19, mounted B2B15 and existing Clock alarm/notes suites. Exact four-file Clock-only review boundary.

## WATCH OUT FOR

This proves the controller sequence and durable failure handling, NOT a production restart fence. The live Quickshell process is not launched through this fixture and same-UID processes can bypass the gate. The installed service owner must independently bind the real launcher, old writer session and native signed role; systemd restart inhibition/desktop integration remains unfinished. A synced file snapshot is not an exclusive lease. Never flip the native QML bridge or activate BG2 on this evidence alone.

## CHECKLIST

- [x] Verify Syntagma rules and current merged Clock checkpoint
- [x] Implement durable one-use old writer launch slot and crash hold
- [x] Verify real kernel process exit and final V2 fsync
- [x] Keep all production, transfer and sound rights denied
- [ ] Exact-head CI and independent security review
- [ ] Operator-authorized merge
- [ ] Native installed role, actual Quickshell launcher stop/restart fencing
- [ ] Real accepted-save generation to final sync receipt
- [ ] Native BG2 scheduling, sound, notification, reboot/resume and Silverblue tests

## NEXT

Integrate a real installed native supervisor with a protected launcher and verified Quickshell lifecycle. Resolve real QML accepted-save generation (or independently approved offline shutdown) and source ownership. Only then authorize native alarm actuation and perform Silverblue recovery tests.

## DECISIONS

Draft. No local machine changes, merge, installation, process signal, live alarm file edit, synthetic permissions expansion, real output or BG2 activation. Operator final acceptance separate.
