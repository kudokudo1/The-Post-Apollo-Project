# 🏥💜 Connections C3e ↔ TimeW ↔ SwayPX // Per-surface trust interface proposal

**STATE:** PROPOSAL / REVIEW REQUEST / NOT ACCEPTED · **PRODUCTION:** HOLD  
**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** C3e / Identity Center ↔ TimeW protected window provenance  
**STAFF ROLE:** Connections DOC successor (external Hospital-compatible; live registration not verified)  
**ASSIGNMENT:** Separate selected-live-surface geometry from authenticated Brave window identity. Supply an exact interface for TimeW, SwayPX, C5 and independent Nurse 2 owner reviews without crossing code ownership.  
**COORDINATION:** [TimeW ↔ Connections issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067).  
**PRECONDITIONS:** Source-only #2087, #2089, #2091 merged; #2093 merged into #2091 feature branch, requiring separate application-`main` reconciliation #2096. No installed native trust.

## 1. WHY TWO MODES MUST NOT BE CONFLATED

Linux `SO_PEERCRED` identifies the original socket peer, but not necessarily the sender of later inherited `SOCK_STREAM` reply bytes. `SO_PEERPIDFD` retains original process custody, not browser window custody. C3e #2089 tested `SCM_CREDENTIALS` on packet sockets for a **native bridge**, not Sway's browser-surface identity. #2091 tested `GET_TREE` frames from a fake Sway server. #2093 proved with a real fork that a child can send through a parent-established STREAM socket without changing `SO_PEERCRED`.

SwayPX `sway/ipc-server.c` exposes `IPC_GET_TREE`, which serializes `ipc_json_describe_node_recursive(&root->node)`; `sway/ipc-json.c` emits `pid` and `app_id` from each view. The tree offers no independently enrolled Brave **window instance** to **wl_surface** claim. A title, `app_id`, `pid`, focus state, `con_id`, extension-supplied UUID or native-messaging claimed origin is not such proof.

The TimeW `MachineV2PairConsent.py` `PAIR_SCHEMA=post-apollo.timew.external-window-pairing.v1` **requires** `browser_window_ref` UUIDv4, `live_con_id`, checkpoint/window keys, app/workspace/output/session and the separate signed one-use consent. C3e **must not invent a trusted browser_window_ref** to make a manually selected compositor surface fit that existing schema. TimeW must accept a separately reviewed mode/schema/audience or maintain HOLD.

## 2. CANDIDATE SCOPE A // OPERATOR-SELECTED LIVE SURFACE, GEOMETRY ONLY

**Proposed first, narrower feature, not an approved release.** An independently pinned SwayPX compositor / protected seat service observes the operator **selecting the specific already-live floating surface**. The service binds the selection to one compositor instance, immutable live surface lifetime, compositor container ID, current output/workspace, seat, session and brief expiry. This means: **move/resize only the explicitly selected live surface to a reviewed saved rectangle**. It does NOT establish persistent Brave identity; does not automatically find the former Brave window after a restart; does not recover tabs, browser state, or select an arbitrary one of two same-PID windows.

**Minimum proposed protected response:** versioned audience `timew-selected-live-surface-geometry-only`; fresh caller challenge digest; independently installed SwayPX compositor identity and release-pinned verifier; protected active-seat/session identity; compositor lifetime epoch; surface lifetime handle plus destruction/recreation epoch that is **never derived only from con_id**; exact selected live container / output / workspace / floating state / current geometry; selection time and expiry; exact selected saved checkpoint and window-key/target-intent digest from trusted review; a one-use decision nonce. Sensitive process IDs, PIDs and raw surfaces need not be sent to untrusted UI.

**Important:** A JSON packet with these fields is NOT proof by itself. An authenticated protected native compositor endpoint must itself create and verify the evidence, with nonce replay defenses, independent release enrollment, current seat checks and revocation when surface/compositor/session/seat/output/workspace/geometry changes. A caller-provided `selected=true` is always untrusted.

**Required TimeW owner decision:** accept a **distinct, geometry-only audience and proof schema** (or explicitly refuse Scope A). Do NOT shoehorn ephemeral surface selection into the existing browser-identity PAIR signature; do not weaken current two-window rejection for existing PAIR v1. TimeW may consume only exact fresh selected-surface evidence and check its current geometry before dispatching its two non-atomic commands. No implicit browser-window UUID and no automatic restart pairing.

**Required SwayPX owner decision:** whether a protected compositor-internal selection event and per-surface lifetime token can be provided without exposing unrestricted IPC, trusting a title, or colliding with the ongoing input/autoscroll ownership. This document does NOT assign SwayPX implementation authority.

## 3. CANDIDATE SCOPE B // AUTHENTIC BRAVE WINDOW-INSTANCE ↔ SURFACE BINDING

This is a separate, stronger future feature, not required for narrowly selected live-surface geometry.

The browser-side issuer must authenticate the **particular Brave window instance**, not merely native host PID, extension origin argument, title or tab list; the compositor-side verifier must authenticate the exact **wl_surface / container lifetime**; a protected cross-source protocol must bind both under a fresh session-specific challenge and mutually independently enrolled executable/release trust roots. Two Brave windows sharing PID, app ID, title, focus history or browser session must remain distinguishable.

No current source demonstrates the required trusted bridge. Until a reviewable design and live native proof exist, **persistent Brave-to-Sway pairing and automatic matching remain HOLD**.

## 4. C3e / C4b / C5 / TimeW OWNER INTERFACE

| Owner | Supplies | Must never infer |
| --- | --- | --- |
| **SwayPX** | Native compositor/seat-revocable per-surface selection + lifetime evidence (Scope A) or individually bound surface endpoint (Scope B) | Browser extension ID, tab identity, consent or persistent Brave identity |
| **Brave / TimeW owner** | Verifiable browser-window identity only for Scope B; exact saved↔live geometry review and side effects | That current PID/title/focus proves window identity |
| **C3e / C4b** | Independently enrolled release and process/root provenance, fresh challenge and separate audience-bound verifier / issuer, with protected replay/revocation | That correctly formatted caller JSON, `SO_PEERCRED` alone or test key proves a compositor or browser |
| **C5** | TimeW-specific visible exact-action operator consent, active unlocked seat/Polkit evidence, per-use grant and protected one-use spending | That a Hospital Room Trash/Restore issuer or approval can authorize TimeW |
| **TimeW** | Verify issuer-typed, versioned audience, exact selected surface or full browser match, saved checkpoint, before/after rectangles, expiry and one-use spend | That a diagnostic correlation is an authenticated pairing |
| **Nurse 2** | Independent source/native acceptance and adversarial trust-boundary review | A successful CI result is live deployment |

**Separate key domains:** Never reuse Hospital Room signer keys, action IDs or audiences for TimeW. An independently pinned C3e key is not permitted to sign absent real origin evidence and C5 consent. C3e observation may only remain **diagnostic** until issuer and source provenance are reviewed.

## 5. FAIL-CLOSED GATES / DECISION RECORD

**Refuse** when: two plausible live surfaces without a protected explicit selection; stale or reused compositor/window generation; orphaned surface; mismatched active seat/session; app spoofing; changed output/workspace/geometry; forged or untrusted browser reference; old signed grant; same-PID ambiguous browser claim; conflicting source assertions; stale installed release key or revoked signer; synthetic/absent production source; missing human review; or the consent spend outcome is uncertain. Loss of knowledge is **UNKNOWN / HOLD**, never permission to redispatch.

For Scope A, TimeW must revalidate that the exact protected surface still exists with unchanged lifetime and geometry immediately before each non-atomic `resize` and `move` operation. Spending before side effects and crash/uncertain-outcome handling remain owner requirements; no retries based solely on absent response. The existing 10-second TimeW PAIR lease is a reference bound, **not automatically a validated duration for a new mode**.

**Pending owner decisions (none accepted by authoring this):**
1. **TimeW:** Is a deliberately new operator-selected same-session **geometry-only** proof acceptable, or must V2 wait for full authenticated Brave window binding?
2. **SwayPX:** Which protected compositor-side hook can attest the selected surface's lifetime under an active seat, and what explicit lifetime/revocation evidence can it provide?
3. **C3e / C4b:** Where is independently approved native release/seat/compositor signer enrollment anchored, with installed protected roots and rollback policy?
4. **C5:** Which separate TimeW-only authorization action and one-use grant audience bind exact selected surface, checkpoint, before/target geometry and consent?
5. **Nurse 2:** Does the chosen model withstand inherited sockets, two same-PID windows, replay, focus drift, stale con_id and process restart?

## 6. RECOVERY / NEXT

Review this decision record at issue #2067 and the scoped SwayPX owner issue. After written owner decisions, create separate implementation PRs **only in owner-authorized directories**, with actual native proofs and adversarial tests. Keep Hospital protected writer #133, TimeW production restore and all live system changes on HOLD until each gate is independently accepted.

## DECISIONS

**PROPOSED, not canonical.** No UI action, native socket, installed key, system unit, SwayPX change, TimeW geometry execution, C5 grant, Hospital data write or production release. The user retains final approval and acceptance.
