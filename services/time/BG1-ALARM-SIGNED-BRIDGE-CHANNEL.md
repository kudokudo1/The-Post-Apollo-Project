# 🏥 CLOCK // BG1-B2B17 Signed Bridge Round Trip (TRUST HOLD)

**Patient:** The-Post-Apollo-Project  
**Room:** Reliable Background Alarm Ownership  
**Role:** External Hospital-compatible DOC; no verified live Hospital registration  
**Assignment:** Prove the *native side* of a process-bound, single-use bridge control-channel exchange  
**Status:** GitHub-only, deny-only, pending exact-head verification and independent review

## IMPLEMENTATION

The existing signed native AF_UNIX Clock supervisor can now **issue a 256-bit nonce** only to its independently verified, installed-role **synthetic test** client. The client must acknowledge it on another canonical request from the *same* signed process (PID, kernel start ticks, release epoch, root fingerprint, and held pidfd identity). Every round trip goes through the existing real Linux socket and B2B9/B2B11 signed peer observation.

- Action \`PREPARE_BRIDGE_CHALLENGE\`: strict \`{"action":"PREPARE_BRIDGE_CHALLENGE","v":1}\` frame; returns the nonce to an independently verified **synthetic-only** signed client. Only one challenge can be issued per supervisor lifecycle.
- Action \`ACK_BRIDGE_CHALLENGE\`: strict canonical \`{"action":"ACK_BRIDGE_CHALLENGE","challenge":"<64-lowercase-hex>","v":1}\` frame. The first acknowledgment attempt consumes the nonce, even on wrong identity/token/timeout. Expiry: 20 seconds measured with monotonic time.
- Neither the request nor response may provide a signing key, installed root, source path, alarm revision, caller PID, UID, epoch, or authority policy. The supervisor obtains identity from the accepted socket and existing signed peer/pidfd witnesses.
- **Production has no challenge ledger.** It always refuses handshake requests, even if a host is able to start the foreground native supervisor. No production signer or enrollment is installed.
- \`ok=false\`, \`nativeToQmlChannelAuthenticated=false\`, \`quickshellDrainObserved=false\`, \`writerStopped=false\`, \`canTransferOwnership=false\`, \`canRing=false\` and \`canNotify=false\` remain true to the actual state. A socket round trip only proves that an enrolled native bridge process replied; it does **not** authenticate a QML engine or cause a Quickshell action.
- B2B15 QML remains unchanged, with \`nativeWriterDrainBridgeInstalled: false\` and \`alarmWriterBarrierPhase: "ACTIVE"\`. The public pause/release endpoints remain deny-only.

## HOW TO USE

No UI change, installation, key, host process, Quickshell reload or alarm action. Run the isolated GitHub workflow to test a real signed subprocess and AF_UNIX socket; never apply its synthetic hooks to a production source file.

## VERIFY

The new test suite covers accepted exact signed-process round-trip, same-process replay, one-use issuance, wrong token, changed PID/ticks/epoch/root/pidfd, missing pin, wrong signer, forged payload fields, malformed/canonical frame checks, monotonic expiry, shutdown scrubbing and permanent no-actuation QML/source holds. CI also reruns inherited B2B9–B2B16 trust suites and mounted B2B15 drain tests.

## WATCH OUT FOR

This is **not the completed native-to-QML control channel**. A challenge arriving at a signed Python bridge does not independently prove that the QML singleton accepted a command. **Do not turn on** \`nativeWriterDrainBridgeInstalled\`, \`beginInternalSaveDrain\`, or any writer release based on this result. The next stage must implement a protected QML-side receiving endpoint with independently authenticated native sender, real terminal saved-generation agreement, final synced file digest, old-writer process exit and restart prevention before a single-owner takeover.

A same-UID AF_UNIX socket path is not by itself a QML trust root. Never reuse Connections or Identity signing keys without their respective owner coordination.

## CHECKLIST

- [x] Read Syntagma and Clock B2B15/B2B16, confirm #2050 merged
- [x] Isolate Clock-owned draft from current main
- [x] Bounded signed native process challenge and single-use acknowledgment
- [x] Fail-closed origin, payload, replay, pidfd and timeout tests
- [x] No QML write, service install, alarm data or BG2 change
- [ ] Exact-head GitHub CI green and independent review
- [ ] Operator-authorized merge
- [ ] Authenticated QML-side receiving channel and real final-save receipt
- [ ] Terminate/fence old writer, migrate exclusive owner and BG2 ring
- [ ] Silverblue runtime acceptance

## NEXT

B2B18: independently trust the native sender **inside the QML bridge**, bind the one-use request to its exact Quickshell process and accepted-save generation, and keep disabled until both directions are proven. Do not infer any ownership right from this synthetic-only socket round trip.

## DECISIONS

Draft only. No local machine changes, merges, activation, installed signing keys, Clock FileView changes, process stops, ownership grants, sound or notifications. Final operator acceptance remains separate.
