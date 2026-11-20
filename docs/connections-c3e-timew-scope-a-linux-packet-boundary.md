# 🏥💜 Connections C3e ↔ TimeW Scope A // Linux packet custody ≠ compositor selection

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** C3e Identity/Connections ↔ TimeW selected live surface evidence  
**STAFF ROLE:** external Hospital-compatible Connections DOC; live Hospital registration not verified  
**ASSIGNMENT:** Real Linux packet sender custody linked to TimeW's selected-surface **fixture claim**, without inventing an authoritative compositor witness  
**OWNER COORDINATION:** [TimeW/Connections issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067)  
**STATE:** Source-only, CI-only, PRODUCTION HOLD

## IMPLEMENTATION

The operator's sequence is **Scope A first** (one explicitly selected floating *already-live* surface, same-session geometry only) then Scope B (authenticated persistent Brave-window ↔ Wayland surface mapping). TimeW's merged [#2100](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2100) defines a new, provisional \`MachineV2SelectedSurfaceReview.py\` schema/audience with no \`browser_window_ref\`, not a signer, a native compositor selection, or permission to restore.

This C3e source-only test performs three **strictly separate** observations:

1. **Kernel fact:** On a disposable Linux \`AF_UNIX SOCK_SEQPACKET\` connection, obtain \`SO_PEERCRED\`, TimeW's existing \`SO_PEERPIDFD\`/proc original-process lifecycle lease, and \`SCM_CREDENTIALS\` for the **actual single packet sender**. An inherited socket sent from a forked child fails; a STREAM reply's original-peer credential alone is insufficient.
2. **Caller-provided fixture contract:** Bind that packet to an independently supplied **CI-only expectation** for TimeW's exact Scope A fields, a 32-byte caller-controlled challenge, selection ID, per-surface lifetime/generation, con ID, compositor epoch, seat/session, current/saved geometry, brief fixture expiry, and a canonical selection hash. Two same-app/same-PID windows cannot be selected by a substituted container/lifetime field. A self-consistent packet + expectation still grants **zero** trust because both values may be attacker-controlled.
3. **Authority denial:** The actual Linux peer process is a **test sender**, not proven to be SwayPX's independently signed and enrolled compositor/seat service; its packet is not a protected user selection or certified per-surface lifetime. All compositor source, signature, seat, challenge replay, C5 consent, move/restore and production flags **remain hard FALSE**. Native issuer entrypoint always refuses.

A real SwayPX compositor/seat hook must produce independently protected selected-surface evidence *from its own live object lifetime and the operator's explicit selection*. This repository module cannot issue the evidence. The future source must revoke if surface destroyed/reused, seat/session/compositor/output/workspace/geometry changes, authorization times out, C5 consent isn't fresh, or the writer outcome is uncertain. Ordinary focus, title, PID, \`app_id\` and \`con_id\` alone do not prove intended surface.

## HOW TO USE

GitHub CI only. The job tests **actual Linux kernel credentials** with a synthetic packet, actual forked-child inherited descriptor, and TimeW's structural review compatibility; no running desktop socket, signer, service, key, Polkit rule, database, Brave extension or SwayPX production command is used.

## VERIFY

- [ ] 20 negative/positive-diagnostic Linux packet and spoof tests pass on exact head
- [ ] Existing TimeW Scope A fixture review and prior Sway original-peer Linux tests pass
- [ ] Static hard-deny check and Grammar pass
- [ ] Exactly four additive C3e tests/docs/workflow files
- [ ] Independent Nurse 2 and TimeW/SwayPX owner review of final exact head

## WATCH OUT FOR

This tests real **packet sender** identity, not real **source authority**. The \`expected_uid\`, challenge and selected claim are caller-supplied CI data. \`SO_PEERCRED\`, pidfd and \`SCM_CREDENTIALS\` do not establish root-enrolled release, compositor instance, active seat, intentional operator selection, or TimeW-specific C5 one-use grant. No cryptographically signed surface witness is implemented here. An apparent positive can never authorize a window move or browser restore.

The TimeW owner retains [draft #2102](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2102), which fixes selected vs unrelated tiled/fullscreen windows; the separate UI assertion repair [#2101](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2101) remains its owner work. This addition does not alter either branch or assume their later changes are on \`main\`.

**Release blocker:** TimeW/SwayPX/C3e/C4b/C5 owners need a reviewed protected compositor selected-surface protocol, source enrollment/rotation, real seat provenance, signed one-use consent and fail-closed geometry sequencing; Nurse 2 independently reviews and operator separately accepts. None is completed by this fixture.

## NEXT

Request SwayPX owner selected-surface hook/lifetime decision, independently review C3e kernel packet observation as a negative source boundary, then develop a separately approved protected compositor service and verifier. Keep Hospital #133 and its separate recovery signer/grants outside this TimeW scope.

## DECISIONS

Draft CI-only review; no merge, host write, compositor/native service, source authority issuance, signature, release key, real window movement or final operator acceptance.
