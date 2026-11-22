# 🏥💜 Connections C3e // Native TimeW kernel packet observer (deny-only)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Connections C3e/C4b ↔ SwayPX/TimeW protected Scope A  
**STAFF //** External Hospital-compatible Connections DOC; live registration unverified  
**STATE //** Source-only Linux packet observation / NOT a source-admission verifier / production Restore HOLD

## IMPLEMENTATION

The file **services/connections/ConnectionsTimeWNativePacketObservation.py** supplies a dormant, imported-only Linux observer for **one already-connected SOCK_SEQPACKET socket**. It requires an actual kernel SO_PEERPIDFD tied to the socket's *original* peer, SO_PEERCRED, enabled SO_PASSCRED, and exactly matching SCM_CREDENTIALS for one bounded received packet. It checks that the exact process is still alive before and after the read and refuses inherited-fork sender substitution, missing kernel functionality, mismatched credentials, oversized/truncated packets and indefinite waits. It emits a packet digest and kernel peer diagnostic, **never the raw packet or an authority decision**.

This replaces neither the existing C3e test-only source-format verifier nor TimeW's selection logic. It is an executable **read-only observation substrate**, unlike test-only source identity claims. Its input socket is supplied by a future Connections host boundary, not opened by the module itself. No existing production service imports it, no listener/installer is introduced, and it neither creates a signing key nor executes a compositor command.

**Crucial limit:** A real Linux packet sender can forge a perfectly consistent selection/seat/receipt body. Observing Linux peer credentials is not proof that a protected SwayPX input gesture selected the actual live surface. Even if the packet claims production authority or C5 SPENT, this module deliberately does not parse it as a grant. Every native/production trust flag remains exactly False, with an empty safeActions list. The native source admission entry point **always raises HOLD**. No self-provided root, key, policy field, or caller boolean can change that.

The next separately owned native integration requires **accepted**, independently enrolled SwayPX release/process/seat provenance and compositor-internal selected-object lifetime witness; C3e/C4b protected challenge/signing root/receipts; C5 protected durable pre-side-effect one-use spend; and TimeW guarded resize, actual post-resize x/y observation, guarded move and UNKNOWN/no-retry. This module cannot solve those decisions.

## VERIFY

The dedicated **connections-c3e-timew-native-peer-observer.yml** CI runs Python compilation, a small static no-authority guard and real Linux kernel tests. Tests cover: legitimate packet sender still untrusted; forked child inheriting socket refused; SOCK_STREAM refused; disabled PASSCRED refused; missing/oversized/empty packets; bounded timeout; closed socket; unavailable SO_PEERPIDFD; malicious JSON saying it is authorized; and source-admission entry point always HOLD. No external network, non-test Sway commands, C5 grant, privileged process or installed host mutation.

## WATCH OUT FOR

- SO_PEERPIDFD is Linux-specific. If the actual kernel cannot provide it, the diagnostic **refuses**. Never replace it with pidfd_open on a possibly reused PID while claiming original socket peer identity.
- The received payload is **untrusted**, even when kernel credentials match; avoid feeding this result directly into TimeW Restore, Hospital grants, or a signing service.
- SwayPX [draft #166](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/166) identifies centered resize that can change x/y. No TimeW test assumption that x/y remains constant is a protected runtime fact.
- This is Connections-only code on a separate draft branch; it does not modify SwayPX #126/#158–#166, TimeW #2117, C5, Hospital, package policy, installer or workstation.

## NEXT / DECISIONS

Owner responses are tracked by [#2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119) and [TimeW native issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067). Get Nurse 2 exact-head independent review of this bounded source, then wait for C3e/C4b, SwayPX, and C5 approved installed roles before connecting any authenticated native producer. Merge, install, and production activation remain **separate operator decisions**. Scope A first, Scope B later. **PRODUCTION RESTORE HOLD.**
