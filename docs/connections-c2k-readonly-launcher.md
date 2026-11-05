# 🏥💜 Universal Connections // C2k explicit status-only launcher

**PATIENT //** kudokudo1/The-Post-Apollo-Project  
**ROOM //** Universal Connections · CPU++ SETTINGS  
**STAFF //** External Hospital-compatible OpenAI/ChatGPT; no live Hospital registration  
**ASSIGNMENT //** Add an explicit process owner for the already-merged C2j read-only host-status server, without elevating socket presence to application authentication  
**BASE //** main a7ba5a428d41fb1043b1f49175600a1c44702fdd  
**PERMISSIONS //** Repository-only draft, tests and documentation; no live Fedora installation, Quickshell reload, systemd unit, credential, account, NASA call or production activation

## IMPLEMENTATION

The host is a Python background **process**, not a Weather Station screen. The launcher is Post-Apollo-owned code that starts the existing C2j server when explicitly requested and keeps it alive until a stop signal. CPU++ remains the operator-facing status viewer.

- New `services/connections/ConnectionsHostReadOnlyLauncher.py` accepts **only** `--run-readonly`; no invocation without that flag creates a host.
- Uses existing `ConnectionsHostStatusServer` and the fixed C2i Unix socket protocol. Its authoritative state getter always returns `IDLE`. Real Weather requests and approvals are **not** consumed.
- Requires a private, owned `XDG_RUNTIME_DIR`; delegates socket owner/mode and protocol restrictions to existing C2j.
- No autostart, new UI element, systemd installation, detached daemon, arbitrary command/provider/endpoint, credentials or API access. A second launcher cannot take over an occupied status socket.
- SIGTERM/SIGINT close the server and remove only its own socket. The existing CPU++ observer still labels responses `OBSERVED_UNVERIFIED` and its permission flags stay false.
- Disposable Linux subprocess tests call the **real C2i inspector** and verify lifecycle, socket collision, unsafe runtime refusal, unknown commands, no-start behavior, and cleanup.

## HOW TO USE

**Normal Post-Apollo:** No new action is available to the operator. This branch must be reviewed and merged before any optional local launch/deployment work. The existing CPU++ path remains:

CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST

With no explicitly running host, expect NO LOCAL CONNECTIONS HOST. In isolated CI, a host spawned by C2k reports local `IDLE` as an unverified observation. **Do not treat it as a real Weather or NASA connection.**

## VERIFY

Run on a disposable GitHub runner using the C2k workflow. The tests start actual Python processes with `python -I` and disposable private runtime paths, then run C2i/C2j regressions. No local workstation operation is performed by this branch.

## WATCH OUT FOR

**This C2k implementation does not establish trusted host identity.** Neither a Python executable path nor a Unix socket, a matching UID, a fixed command line, a PID, nor a hash stored alongside the user's editable source is an independent trust root. Same-UID malware can impersonate an observation. A future deployment must establish verified installation provenance, appropriately isolated host authority, and cryptographically or OS-enforced peer/consent mechanisms before changing `hostAuthenticated` or allowing any credential operation.

`--run-readonly` is an explicit **status-only launch request**, not NASA consent, provider activation, a background autostart registration, or an assertion that the binary is trusted. The test exercises the skeleton; the real trust proof remains the next security milestone.

## CHECKLIST

- [x] Verify C2j #1279 merged and no open Connections PR overlap at preflight
- [x] Reuse existing C2j status server and C2i fixed inspector
- [x] Isolated, explicit-only process start/shutdown path
- [x] Separate-process and refusal regression test coverage
- [x] Add dedicated GitHub CI and deny-only assertions
- [ ] Exact-head CI completion and independent review
- [ ] Operator merge and desktop acceptance
- [ ] Verified installation and peer identity
- [ ] Approved auto-start/lifecycle integration
- [ ] Consent, revocation, credential isolation, real NASA activation

## NEXT

Review CI and this status-only launcher. Then design and approve a *separately trusted installation/launch authority* (for example, reviewed root-managed packaging/service identity with OS-enforced isolation), with an explicit receiver-side proof. Do not enable production key/grant flags until this is actually established and tested.

## DECISIONS

No automatic desktop behavior, source edits outside this bounded seam, credential grants, API requests, local machine changes or merge. This is a reviewable **draft** integration milestone with the security boundary explicitly unchanged.
