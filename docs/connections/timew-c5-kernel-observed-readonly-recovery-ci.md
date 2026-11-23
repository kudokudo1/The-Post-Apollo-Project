# 🏥💜 DOC 5 // Actual kernel-attributed TimeW C5 recovery packets: still not independently trusted

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · TimeW C5 Scope A  
**STAFF ROLE //** DOC 5, external Hospital-compatible; live Hospital session not verified  
**ASSIGNMENT //** Independently protected one-use SPENT and read-only original-operation recovery  
**IMPLEMENTATION //** Hosted Linux root CI-only negative integration, four additive DOC 5 files  
**PRODUCTION //** TimeW Restore HOLD · Sign-In HOLD · Autoscroll HARD OFF

## IMPLEMENTATION

This milestone consumes the **existing merged TimeW/C3e Linux per-packet kernel observer** at \`services/connections/ConnectionsTimeWNativePacketObservation.py\` **unchanged**. It already uses Linux \`SOCK_SEQPACKET\`, \`SO_PASSCRED\` with \`SCM_CREDENTIALS\`, \`SO_PEERPIDFD\` for the socket's original peer process, bounded packet reading and cleanup of unexpected \`SCM_RIGHTS\` descriptors. It returns **packet hash, length and kernel-observed PID/UID/GID but no raw payload or trusted source claim**.

The additive \`tests/connections/timew/TimeWC5KernelObservedRecoveryCI.py\` does not create sockets. It requires two distinct, caller-created receivers under a **disposable GitHub-hosted Linux root test process**. It computes a **PRIVATE TEST ENCODING** of each caller-supplied untrusted C5 history and SwayPX native outcome response, checks the actual received packet's SHA-256/length, and validates the original observer's full no-authority result. Only then does it invoke the unchanged DOC 5 [#2350](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2350) dual-return comparator against the caller-supplied values.

- **Kernel attribution** can establish which Linux process sent a bounded packet, and reject a different inherited-descriptor sender, while the original peer remains alive. It does not prove that either process is an independently enrolled C5 protected custodian, the original SwayPX compositor, a selected native window, or a real operator.
- **SHA-256 equality** establishes correlation to a *caller-selected expected test object*, not signature validity or trusted packet contents. There is deliberately no parser that accepts these bytes as an approved C5/native protocol.
- **One original operation** is preserved by the inherited #2333/#2350 comparator, with exact C5 grant/source/seat and selected-XDG boot/output/workspace/scale/transform and IEEE754 bit patterns. Contradictory native READY/TIMEOUT, output-level PRESENT, changed C5 history and one-ULP geometry remain UNKNOWN/HOLD.
- **Two different observed local PIDs** may be established by real after-fork **pathname** AF_UNIX connectors in the test. They still share one test machine/root. Different PIDs are not separation of custody, independent current-head or a production signing/issuer role. The result exposes this distinction without any authority.

The adapter is a *reader*, not a connector or daemon. Tests create and dispose of the short-lived socket pairs and temporary pathname listeners on GitHub CI only. No Quickshell, desktop, TimeW store, NAS, service, key, C3e IPC router, compositor, input/seat, selected-window move, signing, grant issuance, C5 spending or production changes are present. This source requires the CI environment flag and effective root as an **operational test isolation guard**, not an authentication mechanism.

Both results are always \`KernelRecoveryObservation\` with **all** protected C5/current history/H0/native signer/terminal/production/command/retry/undo fields \`False\` and \`safe_actions=()\`. Failed kernel observation returns HOLD without calling the comparator. A successful kernel observation preserves only the **already non-authorizing** original #2350 diagnostic and remains \`KERNEL_OBSERVED_UNENROLLED_TWO_RETURNS_UNKNOWN_HOLD\`.

## HOW TO USE

In GitHub, review the four added files and the dedicated workflow. The real Linux tests run **only** under root on a disposable GitHub-hosted Ubuntu runner. The workflow guards against outside forks and does not run on the operator's machine.

\`\`\`sh
# Runs inside guarded GitHub Actions only; do not run on the live workstation.
sudo -n env GITHUB_ACTIONS=true RUNNER_ENVIRONMENT=github-hosted \
  python3 -B -I tests/connections/timew/test_timew_c5_kernel_observed_recovery_ci.py
\`\`\`

Inherited independent C5 return-comparison (#2350), original-operation lookup (#2333), and Linux packet-observer suites run separately. The new adapter has no automatically installed endpoint or control.

## VERIFY

Adversarial tests use actual kernel-delivered messages rather than mocking a \`SO_PEERCRED\` struct. They cover:

- Exact two-packet hash/length matching that *still denies* C5/spend/native action; same-process and separately connected real process cases;
- A role-swapped packet, wrong actual bytes, wrong operation/seat/window, cross-domain C3e audience, forged source and extra authority fields;
- Stream instead of seqpacket, missing per-packet credentials, nonexistent kernel pidfd, malformed/oversized expected JSON, missing or duplicate receiver;
- A different process sending on an inherited Unix FD and unexpected \`SCM_RIGHTS\` cleanup/refusal;
- Honest kernel identity accompanying C5 local/ACTIVE/contradictory terminal state, forced TIMEOUT, output PRESENT, false selected-XDG frame, or attempted MOVE after unverified resize;
- A forged original recovery plan and non-hosted guard denial.

No positive authorization or production permit can be returned by this test, regardless of whether the Linux kernel reports two different PIDs.

## WATCH OUT FOR

**This milestone does not fix the missing separately protected custodian.** The operator-approved sequence remains ordinary TimeW data local now, independently administered protected hardware later. A local UID, root-run GitHub CI, temporary pathname socket, packet digest, a valid-looking SPENT, two PIDs or a locally matching history sequence is not an independently current, rollback-resistant grant keeper.

The actual production contract still requires: real original selected-XDG and operator H0 approval; a separately enrolled TimeW-specific one-use durable PRE-ACTION SPENT and revocation history; authenticated actual SwayPX native per-step ACK and selected-view final-frame settlement; a final signed terminal result; read-only original-operation recovery and operator approval for physical roots, signer roles, accepted wire, installation and activation.

The SwayPX owner controls true native source/selected-buffer evidence, TimeW controls the receipt consumer and local preview/Save, DOC1/2 control general independently enrolled producer/release/host trust, and DOC5 controls **C5 TimeW consent and recovery**. No cross-owner production authority is inferred from reusing the **already merged low-level kernel observer**.

## CHECKLIST / NEXT / DECISIONS

- [x] Recheck canonical Hospital protocols, DOC5 assignment and current branch ownership.
- [x] Reuse original Linux TimeW packet observer and DOC5 dual recovery comparison unchanged.
- [ ] Exact-head GitHub CI, raw test counts and changed-path audit.
- [ ] Independent Nurse 2 PRE-MERGE source/CI review while draft remains open.
- [ ] Operator-controlled merge disposition.
- [ ] Future authenticated C5 current-head read-only recovery endpoint and source settlement, separately reviewed and installed.

**DECISIONS //** Test-only kernel process attribution now joins two C5/native recovery observations without creating any trusted source, grant or Restore command. **TIMEW RESTORE HOLD.**
