# 🏥💜 Connections C3e // Unexpected SCM_RIGHTS cleanup hardening

**PATIENT:** The-Post-Apollo-Project · **ROOM:** Connections C3e/C4b ↔ TimeW Scope A  
**STAFF ROLE:** Connections DOC, external Hospital-compatible; live Hospital registration not verified  
**STATE:** Isolated source-only patch / production native source and Restore HOLD  
**SOURCE:** Nurse 2 retrospective review [#6012800215](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2126) of merged #2126 at \`37dc90fbbf8911f116bea45bf1d7c6c2bed393b7\`

## IMPLEMENTATION

The merged read-only Linux observer uses \`recvmsg()\` to obtain a diagnostic packet and kernel \`SCM_CREDENTIALS\`. Unix ancillary \`SCM_RIGHTS\` are **live open file descriptors** in the receiver, not merely untrusted bytes. Raising a HOLD on truncation or invalid credentials before closing any descriptors actually delivered by the kernel could leak those handles in a future persistent service.

\`services/connections/ConnectionsTimeWNativePacketObservation.py\` now:

1. Receives ancillary messages with Linux \`MSG_CMSG_CLOEXEC\` so any delivered handles are non-inheritable across exec. If unsupported, it refuses before receiving.
2. Iterates **all** returned \`SCM_RIGHTS\` entries **before** any flags/packet-credential validation. Converts each complete native-sized integer to a descriptor and calls \`os.close(fd)\`; partial trailing bytes are invalid. Continues closing later entries even after a malformed earlier one.
3. Refuses every packet containing \`SCM_RIGHTS\`, even if all handles were closed and credentials otherwise match. A malformed descriptor or closure error is HOLD. \`MSG_CTRUNC\` with no delivered rights remains HOLD by the existing logic.
4. Leaves the original \`SO_PEERPIDFD\` original-sender and \`SO_PEERCRED\`/per-packet sender logic, packet-bounds, diagnostic-only output and production authority denial unchanged.

The kernel disposes of descriptors it **could not** deliver on truncation. This observer cleans up descriptors it actually receives. No \`SCM_RIGHTS\` path conveys trusted SwayPX selection, signing roots, C5 consent or a native operation.

## VERIFY

Tests include two deterministic real OS descriptor-closure cases using a test-only receiver wrapper that attaches genuine \`os.dup\` handles after a real Linux packet read, including multiple entries and malformed trailing data; they verify that the actual handles are closed with \`fstat() → EBADF\` while unrelated open handles remain valid. Another test sends a real \`SCM_RIGHTS\` message to Linux with \`SO_PASSCRED\` enabled and checks the receiver's \`/proc/self/fd\` count before/after HOLD. A further test asserts \`MSG_CMSG_CLOEXEC\` was used. Original distinct Linux sender, process-exit, timeout and kernel-truncation cases are preserved.

The Linux CI workflow compiles and runs the entire \`test_connections_c3e_timew_native_*.py\` family with the new tests, plus the existing static denial and Grammar checks.

## WATCH OUT FOR

- Python's \`recvmsg()\` returns **live SCM_RIGHTS fds** even when the cmsg is unacceptable. Merely rejecting on \`MSG_CTRUNC\` does not necessarily close every delivered descriptor. This fix makes cleanup unconditional *before* refusal.
- File descriptor numbers may be reused after closure; tests check \`EBADF\` immediately after the call. The observer's own temporary peer pidfd is separately closed in its existing \`finally\`.
- This patch **does not** establish a protected SwayPX producer, explicit operator-selected native surface, installed C3e/C4b release/seat/root, per-command receipt or C5 spent-once permission.
- No new socket service, compositor command, TimeW production consumer, C5 key, host installation, worker-owned source or real window action.

## NEXT / DECISIONS

Require exact-head GitHub Linux regression PASS and an independent Nurse 2 source review of cleanup on every refusal path and FD lifecycle. Leave this as a draft PR pending operator merge decision. SwayPX #166/#168, C3e/C4b producer enrollment, C5 one-use consent and TimeW native Restore retain separate owner/release gates; production Restore HOLD.
