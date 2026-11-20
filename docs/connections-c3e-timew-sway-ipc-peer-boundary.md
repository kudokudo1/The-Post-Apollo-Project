# 🏥💜 Connections C3e ↔ TimeW // Kernel Sway IPC peer custody, not Brave surface identity

PATIENT // The-Post-Apollo-Project  
ROOM // Connections C3e/Identity ↔ TimeW native trust evidence  
STAFF ROLE // DOC succession, external Hospital-compatible; live Hospital registration unverified  
ASSIGNMENT // Read real Linux kernel origin of original Unix STREAM peer, then parse a disposable **fake Sway** GET_TREE response with no authority  
BASE // [#2091](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2091) (draft), which is based on main after #2089's operator merge  
COORDINATION // [#2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067)  
PRODUCTION // HOLD

## IMPLEMENTATION

A connected Sway IPC Unix STREAM socket can expose its **original connected peer's** PID/UID/GID via Linux SO_PEERCRED. The TimeW source's existing \`SO_PEERPIDFD\` and /proc lease can confirm that original task is still alive with the original birth ticks, executable device/inode and credential group. The new source-only wrapper reads those real kernel facts on a disposable AF_UNIX socketpair, pins a **caller-supplied fixture UID + birth tick**, then invokes the prior bounded GET_TREE parser against a **fake server thread**. It rechecks pidfd custody after the reply.

This is **not** a verified SwayPX process or installed release. The expected identity is not read from protected root policy. A Unix stream endpoint may be inherited or transferred, so SO_PEERCRED does not necessarily establish which task sent a later response, and the JSON is not a signed compositor statement. The wrapped fake Sway IPC parser remains non-authorizing even when two same-PID Brave windows are detected. No live SWAYSOCK is opened, no filesystem changes or installation occur. All compositor, browser, active-seat, TimeW pairing signer, C5 human consent, geometry and production flags remain FALSE; the native entrypoint refuses unconditionally.

## HOW TO USE

GitHub Actions only. The suite exercises genuine Linux kernel process credentials and pidfd custody while a Python test-owned server writes synthetic Sway frames. Unlike \`SOCK_SEQPACKET\` per-message SCM_CREDENTIALS used for #2089's *native bridge*, this STREAM preflight makes **no response-sender attribution claim**.

An additional real Linux fork test lets a child inherit the open STREAM endpoint and transmit the fake response while `SO_PEERCRED` remains pinned to its original parent. The observation is retained solely as diagnostic; `actualSwayIpcReplySenderProven` remains false. This explicitly demonstrates why checking only the original endpoint is insufficient for native authorization.

## VERIFY

- [ ] Exact-head 13/13 CI Linux tests
- [ ] Source static no-authority check and Grammar
- [ ] Four additive C3e-only files
- [ ] Nurse 2 review of kernel peer scope and inheritable-stream limits
- [ ] TimeW + SwayPX owners agree authoritative per-surface evidence design

## WATCH OUT FOR

No root controller-owned release, signed SwayPX service, active unlocked seat, trusted compositor socket-path provenance, browser renderer-instance identity, per-window Wayland surface proof or C5 TimeW-specific consent is provided. Do not promote the test-origin field to protected signer inputs. A browser's PID/title/focus/window UUID still cannot identify a particular wl_surface; manual operator selection may be a narrower **proposed** first release, but cannot be silently declared sufficient by Connections.

## NEXT

After independent review, resolve the **actual** per-window authority source with SwayPX and TimeW owners. Prefer a separately approved active-session selected-surface contract over fabricating a persistent Brave identity. Keep the TimeW PAIR domain and C5 one-use consent separate.

## DECISIONS

CI-only draft. No TimeW/SwayPX/Hospital/C5 changes, executable keys, native services, local machine writes, real window commands or production permissions. Operator merge/activation/acceptance separate.
