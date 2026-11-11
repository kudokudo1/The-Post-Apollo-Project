# MACHINE // Absolute in-flight metadata request deadline

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave archive
STAFF ROLE // External Hospital-compatible DOC; live Hospital attachment not verified
ASSIGNMENT // Refuse slow-trickling archive requests under one monotonic request lifetime
SCOPE // MACHINE-owned broker/cancellation seam, automated synthetic tests; no trusted C3e/C5 authorization or real archive access

## IMPLEMENTATION

PR #1883 is verified merged to main. It established a two-second, negative-only socket/session cancellation guard. Its original framed-read routine, however, relied on the socket's per-`recv` timeout. A client sending a few bytes repeatedly could reset that per-operation wait and occupy the request handler for longer than the overall lease, even though the broker would eventually deny.

This increment enforces **one monotonic deadline across every byte of the frame**:

- `InFlightGuard.remaining_ns()` computes the *remaining* duration from the same original creation timestamp. Time expiry or regression causes irreversible cancellation.
- `InFlightGuard.receiving_valid()` rechecks the live pidfd lease and Linux session/cgroup/namespace identity before and after each partial socket read. It deliberately does not inspect pending input bytes because the **first** frame may validly be waiting in the socket buffer.
- `MachineBraveProtectedMetadataContract._receive_exact` uses that same budget to set each individual `recv` timeout. Additional client bytes do not reset the overall clock. Partial header, partial body, idle client, disconnect, elapsed lease or changed process/session fail closed.
- After exactly one frame is consumed, the existing post-frame `guard.valid()` checks for extra pipelined bytes, EOF/half-close, process and Linux session-context drift. The original socket timeout is restored before the fixed refusal response.
- `handle_once` now passes the guard to the framed reader. The broker remains **unconditionally deny-only** and cannot reach protected archive metadata.

No service, network listener, background watcher, native-messaging host, browser permission, signed issuer, process verifier, consent verifier, replay ledger or restore operation is added. The cumulative deadline mitigates slow request occupancy but makes **no** new authority claim.

## VERIFY

Dedicated synthetic Linux tests exercise:

- An intact one-frame request and a fragmented but timely first frame, both accepted for *parsing only*, never authorization.
- A real socket client sending one byte every 70 ms under a deliberately shortened 300 ms test lease. The entire request refuses within the cumulative budget even though the peer continues sending bytes.
- An idle client that sends nothing, refused within its own shortened budget, and restoration of the caller-owned socket's prior timeout.
- A Linux session-context change injected during the **partial header read**, causing immediate irreversible invalidation, not merely a check after full frame completion.
- An oversized frame, EOF after a partial length header and preserved exact-frame source contract.
- Previous real kernel pidfd exit and different-executable `execve` tests, real `setsid` cancellation, and privileged separate-UID archive-bypass tests.

CI uses synthetic sockets and temporary Linux processes only. It never opens user browsing data, encrypted archive files or a live desktop connection.

## HOW TO USE

No user action or new widget control. This is a source-level security safeguard, not a deployed feature.

The dedicated repository regression is:

```bash
python3 -B -I tests/timew/test_machine_brave_absolute_frame_deadline.py
```

The existing protected metadata broker GitHub workflow runs this alongside prior MACHINE security tests.

## WATCH OUT FOR

- A **monotonic deadline** limits the duration of one request but cannot authenticate the caller or prove user intent.
- Under load, heavy /proc checks or scheduler stalls may cause a legitimate synthetic request to be refused. That is intentional fail-closed behavior, not a reason to grant more time from each incoming byte.
- A Linux session ID/cgroup/namespace match is not verified logind state or an active unlocked desktop seat. C3e/DOC owns authoritative signed live host/process/seat evidence; C5 owns purpose-bound one-use consent.
- Merged Connections C3e-Z #1874 verifies **synthetic** signed release/host fixtures, not production process or active-seat provenance. An independently reviewed live witness for MACHINE remains unavailable.
- A genuine signed witness, secure listener and operator-authorized service-owned archive migration are not part of this increment.
- No new positive metadata, ciphertext transfer, deletion, automatic browser import, Sway window move or RESTORE path is enabled.

## CHECKLIST

- [x] Reconstruct merged #1883, Syntagma and C3e/C5 ownership
- [x] Enforce one absolute request lifetime across partial reads
- [x] Recheck kernel lease/session observations during each chunk
- [x] Keep post-frame EOF/extra-byte and unconditional denial rules
- [x] Synthetic real-socket trickle, timeout, drift and legacy regression tests
- [ ] Exact-head CI and independent Nurse 2 review
- [ ] Independently issued, verified live C3e process + unlocked-seat witness contract
- [ ] C5 one-use purpose authorization with replay-resistant consumption
- [ ] Operator-approved protected service and archive migration
- [ ] Read-only TimeW integration and safe multi-monitor restore

## NEXT / DECISIONS

This is a MACHINE-owned defensive dependency milestone, not a takeover of Connections or C5. Once owners deliver independently verified live host/seat and one-use consent interfaces, MACHINE may build a separately reviewed admission adapter. Until then the protected archive broker remains deny-only. No local machine writes, production activation, PR merge or live archive access performed.
