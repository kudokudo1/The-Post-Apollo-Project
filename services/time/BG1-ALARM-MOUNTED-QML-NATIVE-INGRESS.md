# 🏥 CLOCK BG1-B2B18 // Mounted QML Native Ingress (Trust Hold)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Clock Reliable Background Alarm Ownership  
**ROLE:** External Hospital-compatible DOC; live registration unverified  
**SCOPE:** QML receiving seam and pure candidate parser only, default disabled  
**STATUS:** Draft, no installed authorization or operator runtime acceptance

## IMPLEMENTATION

B2B17's native supervisor challenge path is merged, but it establishes only a signed **Python socket peer**, not an authenticated native-to-QML command channel. Quickshell.Io has a \`SocketServer\` type and \`Socket\` handlers; this milestone mounts one in the real \`AlarmManagerService.qml\` **with \`active:false\` and \`path:""\`**. It cannot bind, receive a real connection, call the private writer drain or change any alarm data.

The mounted handler's only permitted action is to call a private \`nativeBridgeIngress.inspectFrame(message)\` function. That method refuses immediately unless both the independently pending \`nativeWriterDrainBridgeInstalled\` trust gate and receiver activation exist. The trust gate remains immutable \`false\`. There is no QML-side peer-credentials API or installed signing-root attestation in this change. A socket path or JSON field is not a signed native identity.

New \`AlarmNativeBridgeInboundPolicy.js\` provides strict, no-side-effects parsing for a future \`OBSERVE_FINAL_CANDIDATE\` frame: exact canonical JSON, a 256-bit nonce, source SHA-256 digest, positive safe-integer accepted generation, and no duplicate/extra fields. It checks whether the candidate generation matches the *already locally observed* QUIESCING drained status. It **does not** accept that digest as an independently pinned disk witness. All results, including a candidate match, retain \`ok:false\`, \`nativeSenderAuthenticated:false\`, \`writerStopped:false\`, \`releaseAcknowledged:false\`, \`canTransferOwnership:false\`, \`canRing:false\`, \`canNotify:false\`.

The existing public QML pause and release methods still refuse. \`alarmWriterBarrierPhase: "ACTIVE"\`, \`nativeWriterDrainBridgeInstalled: false\`, and the only \`alarmFile.setText\` call are unchanged.

## HOW TO USE

No user-facing UI. The receiver is mounted but permanently inactive. The supplied test suite simulates candidate messages and runs the actual extracted QML inspection method without loading Quickshell or touching any real alarms.

## VERIFY

The new Node suite checks exact canonical frames, duplicate fields, forged authority booleans, invalid nonces/digests/generations, malformed and oversized frames, final-generation mismatch, immutable listener-disabled state, and no write/scheduler/audio/ownership path from the mounted \`onRead\`. Dedicated CI reruns B2B4/B2B6/B2B15 and Clock V2/notes contracts, plus native B2B17 signed-socket regressions. Exact diff scope is eight Clock-only files.

## WATCH OUT FOR

**Not a completed authenticated QML channel.** Quickshell's SocketServer does not independently prove the connecting process identity in QML. Even an unguessable nonce or socket file permission is insufficient to authorize a release. Next work must first provide a separately approved native-installed trust/credential verifier or another independently authenticated, process-bound QML transport. Only then can the private drain be joined to the live authority path, and only after the final V2 file fsync and old-writer exit/restart fence may ownership move.

No QML load on Silverblue, installed credentials, background alarm service, user file write, local shell restart, or production pause is authorized by this milestone.

## CHECKLIST

- [x] Recheck current repo and B2B17 merged state
- [x] Mount default-disabled QML receiver in existing singleton
- [x] Add canonical candidate parser with final-save generation comparison
- [x] Keep real QML write, tick, pause, release and ringing paths unchanged
- [ ] Exact-head CI and independent review
- [ ] Operator-authorized merge
- [ ] Independently authenticated native sender at QML ingress
- [ ] Durable final generation and file sync receipt, process exit and restart fence
- [ ] Exclusive background ownership, BG2 sound and Silverblue acceptance

## NEXT

Implement the **real native-to-QML trust bridge**, not another caller-supplied "trusted" flag. Reconcile package-signed Clock role, kernel peer identity, session/lifetime, and a QML-verifiable channel without altering adjacent Connections/Identity owners. Once independently verified, make one bounded native request invoke the existing private accepted-save drain, bind its last saved generation to the native fsync witness, fence the old writer and only then approach ownership transfer.

## DECISIONS

Draft only; no user-machine modifications, installation, merge, native permission activation, alarm file mutation, QML restart, writer release, sound, notification or BG2 changes. Final operator acceptance remains distinct.
