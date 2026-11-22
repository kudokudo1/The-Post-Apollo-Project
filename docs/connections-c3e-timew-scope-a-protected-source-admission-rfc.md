# 🏥💜 Connections C3e ↔ TimeW Scope A // Protected compositor-source admission RFC

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** C3e/C4b protected native origin ↔ TimeW selected same-session live surface  
**STAFF ROLE //** Connections DOC successor, external Hospital-compatible; live Hospital registration unverified  
**STATE //** SOURCE INTERFACE ACKNOWLEDGMENT PROPOSAL · NOT AN ENROLLED COMPOSITOR OR APPROVED INSTALLER  
**COORDINATION //** [Issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067), TimeW owner [PR #2114](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2114) exact `e2ed2ad5fa3fb6f359153b36eac36ef556619399` at drafting, SwayPX master `fb064cf3c82aa7b9e8d2375bb631773d5eb5a12f`  
**UPSTREAM //** Merged C3e source-only [#2105](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2105) Linux packet sender custody and [#2107](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2107) TimeW/Hospital purpose separation, merged TimeW #2100/#2102/#2109 synthetic selected surface + continuity

## IMPLEMENTATION // Actual trust chain, not just packet fields

One running compositor owns real Wayland surface objects, its internal input/selection state and the seat binding. Linux socket metadata such as `SO_PEERCRED`, per-packet `SCM_CREDENTIALS`, `SO_PEERPIDFD`, a reported process ID, or a `GET_TREE` `con_id` **cannot by themselves prove that the operator explicitly chose the specific currently live surface**. Another process can supply self-consistent fields or replay an old record; even a correctly signed test packet only demonstrates a signature under the test key.

**C3e's proposed bounded task:** Admit a protected per-surface evidence source only after the SwayPX owner supplies an actual **compositor-internal explicit selection and revocable lifetime witness**, and C3e/C4b can independently authenticate the **installed producer** and its role, host, release, process and active-seat provenance. C3e does not select windows, mint browser IDs, execute Sway commands, or grant TimeW geometry permissions. No C3e source here can currently prove a deployed SwayPX issuer.

### Owner-specific input / output boundary

| Owner | Must own | Interface refusal condition |
| --- | --- | --- |
| **SwayPX compositor owner** | Concrete click/selection event inside trusted compositor path, exact `wl_surface`/container identity, fresh object lifetime/generation, active seat/session and revocation on destroy/unmap/reuse, reset, focus/seat/lock/output/workspace/geometry changes | Focus event, title, app ID, PID or GET_TREE-only observation is not explicit selection |
| **C3e/C4b** | Independent operator-enrolled root/release/policy, installed compositor + service executable identity and kernel process/packet custody, authenticated active seat/session and protected producer audience; fresh verifier challenge and revocation | Process authentic but selection source not compositor-owned, signer key self-supplied, replay, stale floor, release drift, unknown origin |
| **C5 owner** | **Distinct TimeW** visible, exact selected-surface/checkpoint/window-key/before-target geometry consent under unlocked active seat with protected one-use spend before any side effect | Hospital staffing/Room Trash approval, UI toggle, expired grant or uncertain spend cannot substitute |
| **TimeW owner** | Consume only the approved evidence, match saved checkpoint and current selected surface, verify exact geometry and every intermediate stage, no auto-retry after uncertain resize/move | Synthetic valid form alone, stale lifetime, wrong target, changed unrelated inventory when proof binds it |
| **Nurse 2 / operator** | Independent source/native reviews and explicit merge/install/production acceptance | Green CI is not production authorization |

Scope A means exactly **one explicitly selected already-live floating nonfullscreen surface in the current compositor session**. Scope B, authentic persistent Brave window-instance ↔ Wayland surface and session/browser restore, is separate and remains HOLD. Do not reuse legacy Brave PAIR v1 `browser_window_ref`, or infer a window from the same Brave PID/title/app ID.

## Proposed protected evidence handshake, per selected surface

SwayPX must first approve a specific internal hook and release lifecycle, **before** Connections treats any returned bytes as protected selection. The following is a candidate contract for joint owner review, **not a chosen wire schema or service name**:

1. **HELLO / CHALLENGE:** C3e independently chooses a fresh one-use 32-byte challenge for the fixed `timew-selected-live-surface-geometry-only` audience. Challenge issuance and spending are protected, not test-supplied. Bind the intended TimeW release and the exact active input seat, not a generic desktop caller.
2. **SELECT / SOURCE:** Following an explicit trusted operator action, SwayPX's internally admitted producer returns a challenge-bound short-lived record containing selected surface lifetime UUID/epoch/generation, current live container ID, compositor release/instance epoch, seat and login session, output/workspace, floating/nonfullscreen state, current `before_rect`, selection timestamp/expiry and a hash binding the exact reviewed saved checkpoint/window-key/target rect. Distinguish multiple windows from one Brave process; `con_id` alone is never an identity.
3. **AUTHENTICATE PRODUCER:** C3e checks original connection `SO_PEERCRED` with kernel lifetime identity (`SO_PEERPIDFD` or approved equivalent) and actual per-message sender as appropriate, plus independently signed installed SwayPX release/entrypoint/module/package bytes, actual process/LSM/systemd/seat origin, root-owner policy and revocation floor. Must bind **the emitter process** to the compositor's internal selection origin, not merely observe any local test socket peer. The producer may not select its own trusted root, release, current epoch or policy.
4. **VERIFY SELECTED OBJECT:** Require exact challenge, selection and issuer identity; validate actual selected surface is still live with unchanged lifetime and generation in the same compositor epoch/seat/session at a **trusted critical section**. SwayPX alone can issue/revoke this runtime claim. A compositor restart or surface destruction invalidates it. Validating only a prior signed snapshot and its expiry is insufficient.
5. **CONSENT / SPEND:** Obtain separate C5 TimeW-specific human-visible intent for exact selected surface, saved checkpoint and target geometry. Protect durable one-use grant spending **before any native side effect**. The grant may not be replayed between a resize and a move, and must not survive lock/seat/session/source revocation.
6. **EXECUTE / RECHECK:** TimeW initiates native action only under the approved compositor protocol. Before **each** non-atomic resize and move, SwayPX rechecks active selected lifetime, seat, output/workspace, current rectangle and command-specific target. Confirmed resize may legitimately alter original x/y in some compositors: the current CI assumption (width/height change at same x/y) needs real SwayPX verification and explicit owner acceptance. If any command or acknowledgment becomes uncertain, stop, return UNKNOWN/HOLD and do not automatically reissue.
7. **RESULT / REVOKE:** Acknowledgments must be bound to exact original command, object lifetime, consumed grant and current compositor release/session. They cannot become an authenticated Brave persistent identity or a generic geometry permission. Revoke on any relevant surface/seat/compositor/lock/output/workspace/geometry lifecycle drift, seat disconnect, timeout, signer/release downgrade or consent uncertainty.

### Provenance and domain requirements

The packet audience, SwayPX producer signer, C3e verifier/challenge issuer, and C5 spend authorization have **different meanings and must not alias by accident**. C3e #2107 already demonstrates synthetic TimeW/Hospital signature-domain separation, not a real operator-enrolled issuer. The existing Identity-only C3e-AF role enrollment is not an authorization to sign TimeW surface evidence. An installed signer/recipient must have an independently approved TimeW role, host/release scope, root pin, rotation and revocation; C4b/Identity enrollment must not silently translate into SwayPX surface selection.

`SCM_CREDENTIALS` plus the original `SO_PEERCRED` can confirm a **particular Linux process sent a particular packet** in a suitably configured Unix packet socket. It cannot tell whether that process generated the packet from a protected compositor selection, copied a forged `con_id` from GET_TREE, or borrowed a signing key. Preserve that boundary in every future API name and result flag.

## VERIFY // Adversarial native acceptance matrix

| Scenario | Required behavior |
| --- | --- |
| Two same-PID Brave windows; one actually selected | Exactly the compositor-internal selected object is eligible, regardless of app ID/title/PID collisions |
| A valid source packet from un-enrolled compositor or copied test public key | Refuse authority; no TimeW geometry dispatch |
| A forked child inherits the Sway control descriptor | Actual packet sender mismatch refuses; original-connection identity alone not enough |
| Legitimate compositor restarts; old live con ID reused for different surface | Old selection revoked; refuse stale lifetime/epoch/generation |
| Surface unmapped/destroyed or seat locked/switches between selection and first command | Refuse before native movement, revoke grant |
| Another window changes geometry while selected proof is alive | Revalidate scope of desktop inventory signed by proof, not independent synthetic snapshots |
| C3e TimeW signed fixture expires before the third stage | Refuse; no late move |
| C5 grant spent but resize succeeds and move reply is lost | UNKNOWN/HOLD, no automatic grant reuse, no blind second command |
| Compositor resize shifts position unexpectedly | Report and require SwayPX/TimeW owner-approved geometry state transition, not silent CI assumption |
| Hospital original-COMMIT proof or Identity C3e role substituted as TimeW | Wrong audience/key role refused |
| Source reports correct fields but not native operator selection | Source-only diagnostic; all authority flags remain false |
| SwayPX owner hook absent, external release signer unavailable or no active unlocked seat | Production HOLD, no fallback to raw Sway IPC or shell `swaymsg` |

## Concrete owner responses required before native implementation

**SwayPX:** Specify `ACCEPT / REVISE / HOLD` on compositor-internal selection hook, lifecycle/revocation and privileged endpoint. Identify exact owner-controlled files and process boundary, no cross-editing autoscroll or Company Map branches.

**C3e/C4b:** Specify `ACCEPT / REVISE / HOLD` on independently enrolled verifier root, real installed producer identity, protected native challenge and replay state and source-origin proof. This RFC is **C3e interface proposal**, not authority to enroll production keys.

**C5:** Specify `ACCEPT / REVISE / HOLD` on exact selected surface and rectangle approval, active seat, one-use durable spend and ambiguous two-command outcome semantics. TimeW cannot infer C5 from source evidence alone.

**TimeW:** Verify actual proposed native witness field semantics, in particular geometry after resize, per-command object revalidation, same-session only; no implicit Brave pairing, no unchecked native fallback.

## HOW TO USE / DECISIONS

Review this RFC and respond on existing [#2067 coordination issue](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067) with the owner decision and exact affected files. This does **not** implement/launch a SwayPX service, private key, socket, command runner, C5 approval or protected TimeW native consumer. No local host action.

**Scope A before B remains the operator direction. Production Restore HOLD** pending actual protected SwayPX source, independently enrolled origin, TimeW-specific C5 consent, native acceptance tests and final operator release.
