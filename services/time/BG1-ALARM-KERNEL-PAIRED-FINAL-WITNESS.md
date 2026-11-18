# Hospital CLOCK BG1-B2B19 // Kernel-Paired Final-File Rehearsal (TRUST HOLD)

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC; live registration unverified
ASSIGNMENT // Join signed native process continuity, separately pinned synthetic QML peer, B2B17 one-use challenge, and B2B16 actual V2 file sync
STATE // Draft, deny-only, no production control authority

## IMPLEMENTATION

B2B18 mounted a QML SocketServer receiver but kept it inactive with an empty path. That QML API does not expose Linux SO_PEERPIDFD or a protected native signer. An incoming socket message alone cannot authorize pausing the alarm writer.

This stage implements one coherent NATIVE-ONLY rehearsal.

- New AlarmKernelPairedFinalWitness.py binds two actual accepted AF_UNIX socket peers from distinct Linux processes. The first must match B2B9's signed installed Clock UI bridge origin and independently pinned release root/epoch/sequence. The second must match a separately pinned synthetic QML stand-in PID, kernel start ticks and executable. Both are checked again on each observation; changing either peer or native signed manifest refuses.
- Both pins and expected source path/digest originate outside socket-provided payloads. The synthetic source is the exact time-alarms-v2.json, opened and synchronized through B2B16's real Linux fsync implementation.
- The challenge reuses B2B17's one-use, process/pidfd-bound ledger. Wrong or replayed acknowledgment fails. A successful round trip does not prove a delivered native-to-QML command.
- A matching candidate generation and independently pinned source digest can yield fileSyncObserved true and parentDirectorySyncObserved true. It NEVER yields an exclusive file lease, signed final revision, old-writer exit, restart fence, or native ownership.
- The second process is a test STAND-IN, not actual Quickshell. This implementation does not authenticate QML code, QML's socket receiver or an installed QML release.
- Production construction is prohibited. Every returned report retains ok false, nativeToQmlChannelAuthenticated false, qmlInstalledSourceAuthenticated false, writerStopped false, releaseAcknowledged false, oldWriterRestartPrevented false, canTransferOwnership false, canRing false, and canNotify false.

## HOW TO USE

No UI, deployment or live machine action. CI creates temporary signing keys, two real subprocesses and socket connections, a private V2 alarm file, and cleans up the fixtures.

## VERIFY

Dedicated tests: genuine signed native process + separate QML stand-in, pidfd and source fsync, B2B17 single-use challenge, incorrect signing root, wrong peer process pins, exited peer, forged signed manifest, bad candidate digest/generation, changed source and disabled production constructor. CI reruns B2B17, B2B16, B2B9, B2B1 and mounted B2B15 safety tests with a strict 4-new-file scope.

## WATCH OUT FOR

NOT the completed native-to-QML command channel. The native process observing two peers does not let the QML receiver validate the native sender. The installed protected transport must be independently verified inside or before QML before invoking any private drain. A synchronized file snapshot does not prevent a later FileView write.

No installed release root, protected Silverblue native service, systemd restart fence or actual alarm process changes. Do not enable nativeWriterDrainBridgeInstalled or beginInternalSaveDrain based on this rehearsal.

## CHECKLIST

- [x] Recheck current Syntagma and Clock source/PR ownership
- [x] Build native-only independent kernel-peer and signed role pairing
- [x] Bind existing B2B17 challenge to B2B16 file sync
- [x] Default-deny all release/ownership/audio/notification rights
- [ ] Exact-head CI and independent review
- [ ] Operator-authorized merge
- [ ] Installed, independently QML-verifiable protected transport
- [ ] Real accepted-save drain, final receipt and old-writer restart fencing
- [ ] Exclusive native owner, BG2 ringing, Silverblue acceptance

## NEXT

Select and implement ONE protected installed control transport that allows QML to independently verify the native sender, or reorganize actuation so the QML receiver cannot authorize release at all. Only then bind the private accepted-save drain to a protected single-use request, fsync final revision, stop/restart-fence old writer, and transfer ownership.

## DECISIONS

Draft only. No local edits, QML reload, live sockets, user alarm data changes, production keys, service installation, merge, release, sound, notification or BG2. Operator final acceptance separate.
