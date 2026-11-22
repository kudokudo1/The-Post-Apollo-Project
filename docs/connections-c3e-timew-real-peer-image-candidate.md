# 🏥💜 Connections C3e // Actual Linux peer executable/host-state candidate (untrusted)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** C3e/C4b Connections ↔ TimeW Scope A native source enrollment  
**STAFF //** External Hospital-compatible Connections DOC, live registration unverified  
**STATE //** GitHub-only read-only executable-image observation / NOT source enrollment / production Restore HOLD  
**SOURCE //** SwayPX candidate-only drafts [#168](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/168), [#169](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/169), [#170](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/170); Connections packet custody [#2130](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2130)

## IMPLEMENTATION

A future C3e producer verifier needs more than the packet's correct Linux sender PID. It must independently establish that the **installed producer process and executable** match an authorized SwayPX release and host, not a same-user imposter that can send identical packets. Prior Identity-specific CI process reading cannot be silently promoted to the TimeW role.

New imported-only source: **services/connections/ConnectionsTimeWNativePeerImageCandidate.py**. Given an already connected exact Linux AF_UNIX SOCK_SEQPACKET socket, it obtains **SO_PEERPIDFD from the socket itself**, not \`pidfd_open\` on a caller-supplied PID. It keeps this original-peer handle open during bounded read-only inspection of the exact kernel PID's \`/proc/<pid>/stat\` start ticks, status UID/GID fields, cgroup v2 path, LSM current label, and the executable bytes opened from \`/proc/<pid>/exe\`. It hashes the real executable bytes with SHA-256 while checking inode, size, mode, timestamp and same \`/proc\` executable target before/after; repeats process fields and pidfd liveness before returning.

The result is **ACTUAL_LINUX_PEER_IMAGE_OBSERVED_UNENROLLED**. Every source/consent/selection/geometry/production authority flag remains explicitly **False**, with \`safeActions=[]\`. No caller-provided release hashes, roots or booleans can change its outcome, because none are accepted. It opens no network listener, key, systemd unit, compositor IPC, executable subprocess or protected operator source.

**Essential limitation:** this is a read-only **connected-original-peer process snapshot**, NOT an attestation of the process executable at the exact instant a separate packet was sent. The process could exec between this observation and a packet; \`SO_PEERPIDFD\` pins the process lifetime, not the executable image across time. The process might also genuinely match an installed executable yet lie about a selected surface. The future actual verifier must combine source process custody, independently approved release signing/host/seat enrollment, source-issued challenge/receipt and compositor-internal selection, with per-command fresh checks. Do not cache this candidate as source authorization.

## VERIFY

The new dedicated Ubuntu CI compiles the module and runs the entire existing C3e native observer test family plus new host-state tests. They exercise:
- Actual *separate child process* that opened its own Unix seqpacket client and remains alive: kernel original-peer PID/UID/GID, real executable SHA-256, cgroup and LSM are observed while its pidfd is live, all authority flags denied.
- Original process exits before observation: HOLD; never retarget a reused numeric PID.
- Unsupported original-peer \`SO_PEERPIDFD\`, wrong socket/timeout: HOLD.
- Simulated process start-tick, cgroup, and executable-inode drift during source read: HOLD.
- A packet or local process pretending to be a trusted TimeW/C5 issuer never upgrades the result.

Existing #2122/#2126/#2130 packet sender and ancillary descriptor tests remain unchanged. Any real SwayPX/C4b build, manifest, signed release, SELinux/seat policy, source key, C5 consent or native TimeW command is **out of scope**.

## WATCH OUT FOR

**Cooperative monotonic deadline:** The imported observer now starts a fixed 2-second monotonic budget at the beginning of kernel-peer measurement. It checks before/after bounded `/proc` reads, around each executable-image chunk, and again before returning a diagnostic. A late image read raises `OBSERVATION_DEADLINE_EXPIRED` and closes its executable fd and original-peer pidfd; this cannot be promoted into source/geometry/C5 authority. The bound is **cooperative only**: an OS read blocked indefinitely *inside one syscall* cannot be interrupted by these in-process checks. A future installed Connections supervisor must enforce a separate hard external deadline on the child/worker process, and independent NRS-2 review of stall/cancellation/cleanup is required before native enrollment.

- A SHA-256 measurement is not proof that a signed release is operator-enrolled. It is a fact about bytes at read time. No private key/root is minted; no release floor, issuer signature, host trust or seat origin is approved.
- \`/proc\` and LSM access can fail because of permissions, kernel policy or replaced/changed process state; all failures HOLD. Do not add a fallback to caller metadata, PID/title or raw GET_TREE.
- A process that execs *after* return is not covered; before native authority, a stronger sender-owned protected root/host/seat transaction and per-request process/release revalidation are required.
- The SwayPX #170 unmap/destroy candidate watcher is **not linked** to the compositor and cannot be used as producer signing/selection evidence.
- C5 currently has TASKS-specific CI consent and a fake signed reviewer. No accepted TimeW human approval and durable one-use SPENT-before-resize authority exists.
- This creates no SwayPX/C5/TimeW/Hospital worker-file changes or Fedora host mutation.

## NEXT / DECISIONS

Request independent Nurse 2 exact-head review for original socket pidfd binding, safe image byte/inode measurement, cross-read process changes, no escalation paths and negative source/consent flags. Retain **DRAFT / UNMERGED** until CI/review/acceptance. C3e/C4b still needs the owner-approved installed SwayPX producer and protected independent release root/host/process/seat/challenge identity; SwayPX needs true explicit selection; C5 needs TimeW-specific durably spent consent. Track [#2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067) and [#2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119). **Production Restore HOLD.**
