# 🏥💜 Company M28c // Attached Quickshell child PID to optional kernel pidfd bridge

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network / Stage Director Native MapLibre
ASSIGNMENT // Report actual Quickshell attached native Qt process PID to optional M28b Qt QML bridge
STAFF ROLE // Nurse 2, external operator-delegated Company integration worker
PROVIDER // OPEN AI // CHATGPT
CONNECTION // External Hospital-compatible, not registered
BASE // Company main baf75be6dfa56eb1bde50144dfd51d78cd01519e
DEPENDENCIES // Company M26 #1385 merged; SwayPX M28a #82 merged; SwayPX M28b v2 wire/Qt QML plugin PR pending
PHASE // Source review; no local install or activation

## IMPLEMENTATION

The normal Company Coverage UI owns an attached `Quickshell.Io.Process` through `CompanyVectorSidecarController.qml`. It launches `CompanyVectorSidecarLaunch.py`, which replaces itself using `os.execv`, then the user-local M15 bridge replaces itself with the Qt MapLibre binary using `os.execve`; the single Linux PID remains stable. Official Quickshell Process documentation confirms a read-only `processId` property, which is the PID of that **actual attached child**, unlike `Quickshell.processId` (the parent).

M28c preserves the existing buttons, no new process or network calls, and adds:
1. On the **real** existing `vectorRunner.onStarted` callback, validate `vectorRunner.processId` as a finite positive 32-bit integer and emit `nativeChildStarted(pid)`.
2. `CompanyCoveragePane` forwards `nativeVectorChildStarted(pid)` from that controller. Existing `nativeVectorLaunchRequested(bool online)` and `nativeVectorClosed()` lifecycle signals remain unchanged.
3. `CompanyNetworkW` routes the actual attached child PID to `CompanyVectorBridgeLink.reportChildPid(pid)`, which delegates only when the **optional**, disabled-by-default, already bound M25/M28b native Qt bridge supports `reportNativeChildPid()`. Missing plugin and protocol v1 fail closed; Company still opens the usual standalone MapLibre window.
4. M28b's C++ Qt plugin then opens a kernel pidfd for this exact QProcess PID and transfers the fd over its existing QPA Wayland connection to the physically selected Company server. **The user cannot enter arbitrary process IDs through this path.**

No local M15 installer changes, subprocess spawning, file-writing token, network request, process kill, password or map actor scene actuation.

## HOW TO USE

No new user action. Existing **Company → Coverage → VECTOR VIEW → OFFLINE TEST / ONLINE STREETS** remains the baseline. The optional `vectorBridgeOptIn` property stays false until a separately verified matched SwayPX v2 server and Qt plugin is installed/activated. No import of the plugin is required for normal Company startup.

## VERIFY

- Syntagma AGENTS / Hospital / Authority and current Company+SwayPX heads checked.
- Official Quickshell Process interface checked for `processId` and its actual managed child process semantics.
- CI tests ensure only the real attached Process can originate the PID event, no user-entered PID, no detached launch or shell command, and that the M15 exec chain preserves PID.
- Original M26, M18, M19b and M13 source/runtime unit regressions rerun.
- Live Qt/QML v2 plugin binding, SwayPX physical pairing, kernel pidfd receipt and actual Wayland actor match remain to be tested in isolated native compositor before any local activation.

## WATCH OUT FOR

- **CRITICAL:** The PID signal cannot authenticate the executable. The selected Quickshell client and native pidfd prove a managed process generation, not that executable is the approved map. SwayPX must still validate M15 executable identity before rendering or input.
- Process.started can race with the private launch-intent ACK; M28b C++ should queue a single pending PID and send its pidfd only after the server's `LAUNCH_CANDIDATE` result. No retries of old/stopped processes.
- Child may exit before receipt; M28b fails closed.
- No environment/argv/disk secrets, no separate Wayland connection, no live production migration.
- Do not promote a `KERNEL_PIDFD_CANDIDATE_ONLY` status into actual Company embedded map, lease, clipping or focus authority.

## CHECKLIST

- [x] Recheck current Company controller, M26 bridge and upstream SwayPX native boundary
- [x] Forward read-only attached Quickshell Process.processId on started
- [x] Preserve existing offline/online consent and native map lifecycle
- [x] Require optional bound Qt module with new Q_INVOKABLE method
- [x] Add M28c tests and original M13/M18/M19b/M26 regressions
- [ ] Exact-head CI green and branch reviewed
- [ ] Merge after green under operator-delegated Company scope
- [ ] M28b selected host v2 Wayland fd receipt and Qt plugin CI green
- [ ] M28d exact executable M15 runtime verification
- [ ] M21 candidate actor ledger and test real pixel/input containment
- [ ] Controlled local install and user visual acceptance

## NEXT

Verify the exact Company PR checks and keep the M28b SwayPX v2 protocol and QML bridge in sync. After kernel birth transfer is verified in isolated CI, add a stable M15 executable inode/hash/provenance test. Only then consider M21 native actor custody and independent scene clipping/injection tests.

## DECISIONS

Bounded Company integration GitHub implementation authorized. No changes to Weather WATCH/Chrome, no user-local writes, no live Quickshell/SwayPX restart, no final user acceptance assumed.
