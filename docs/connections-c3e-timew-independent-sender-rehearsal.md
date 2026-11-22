# 🏥💜 Connections C3e ↔ TimeW Scope A // Distinct Linux sender rehearsal (deny-only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections C3e/C4b protected packet provenance ↔ TimeW Scope A  
**ROLE:** Connections DOC external Hospital-compatible; live Hospital registration unverified  
**SCOPE:** Add test-only real Linux peer/ancillary coverage to merged C3e #2122. No changes to its reviewed observer, SwayPX, C5 or TimeW. Production Restore HOLD.

## IMPLEMENTATION

The existing, independently reviewed \`ConnectionsTimeWNativePacketObservation.py\` checks \`SO_PEERPIDFD\` for the socket's original peer, \`SO_PEERCRED\`, matching \`SCM_CREDENTIALS\`, and bounded data. Its output remains diagnostic and all geometry/restore/production flags remain FALSE. The new test suite exercises this unchanged module under more realistic and hostile Linux socket conditions.

- **True separate sending process:** a disposable fork child creates **its own new AF_UNIX SOCK_SEQPACKET connection** to a parent-owned, randomly named Linux abstract listening socket (no filesystem path or installed daemon). The parent accepts the connection and observes kernel-attributed child PID, UID and packet SHA while the child remains alive under a test-only release pipe. The packet's fake SwayPX selection / C5 SPENT / production claims remain *untrusted*; \`safeActions=[]\`.
- **Exited original sender:** the distinct child exits before observation. The observer must HOLD rather than infer a durable producer lifetime from earlier transport activity.
- **Idle receive:** the already connected socket's sending process remains alive but does not send a packet; a 50 ms receive timeout must produce HOLD, not indefinite waiting or authorization.
- **Real ancillary truncation:** a sender passes a legitimate Linux \`SCM_RIGHTS\` descriptor in addition to automatically supplied \`SCM_CREDENTIALS\`; the observer's bounded one-credential ancillary buffer must reject \`MSG_CTRUNC\`, not accept a partial proof.
- **No upgrade by caller:** the native admission placeholder refuses fabricated pinned root or C5 approval fields, even after kernel attribution succeeds.

The parent test process owns and closes all disposable sockets, file descriptors and child processes. It never contacts a real compositor, gets protected root/LSM/seat enrollment, creates an installed socket path, invokes \`swaymsg\` or moves a window.

## VERIFY

The new workflow \`connections-c3e-timew-independent-sender-ci.yml\` compiles the added test and runs the original 11 Linux observer tests **plus** the new external-sender tests against the unchanged implementation on GitHub Ubuntu. A green suite proves only this **kernel/transport refusal scope**. It is not a signed SwayPX receipt, true operator click, C5 spend or runtime source integration.

## WATCH OUT FOR

A kernel-authenticated packet sender is **not** necessarily an operator-authorized compositor or a truthful source of surface state. Real producer admission requires separately authorized SwayPX selection, externally enrolled C3e/C4b source release/host/process/seat identity, protected challenge and authenticated receipts, and independent C5 human approval plus one-use durable SPENT proof. None of those is created here.

Owner SwayPX [#168](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/168) has a candidate-only lifetime fixture, not a linked compositor selection. Owner TimeW [#2125](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2125) has deny-only SQLite/C5-spend/centered-resize outcome simulations, not a command source. Preserve separate ownership and the actual SwayPX resize x/y observation before a guarded move.

## NEXT / DECISIONS

Request independent Nurse 2 exact-head review and inspect the actual GitHub Linux job logs. Do not merge this draft solely because CI succeeds. Record integration progress on [TimeW #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067) and [Connections #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119). Native source approval/installation and live TimeW Restore remain HOLD; Scope A before B.
