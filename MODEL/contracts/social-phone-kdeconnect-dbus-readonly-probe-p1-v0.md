# Social Phone Bridge // Explicit read-only KDE Connect D-Bus diagnostic P1 v0

> **STATE //** ISOLATED REPOSITORY IMPLEMENTATION, LIVE DEVICE UNVERIFIED. No production phone integration.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **BASE //** `main` at `0b7f37b0bdf77439aabdb3e488c044f2a7fd85c6` on 2026-11-02 after operator merged PR #1022. Recheck HEAD, active assignments and PRs before continuing.
>
> **PROVIDER //** OpenAI / ChatGPT, external Hospital-compatible. No verified Hospital Room, Staff Role, Appointment, Session or checkpoint.
>
> **SOURCE //** Operator-selected [network-first Phone Bridge ADR](./social-phone-bridge-network-first-adr-v0.md), [P0 safe route selector](./social-phone-capability-policy-v0.md), [P1 presence](./social-phone-kdeconnect-presence-p1-v0.md), and [P1 D-Bus synthetic evidence](./social-phone-kdeconnect-dbus-evidence-p1-v0.md).
>
> **OWNER / SCOPE //** New standalone `services/phone/KdeConnectDbusProbe.py`, mock tests, dedicated CI and model-index link. No edits to shared Social UI/router, existing phone policy/evidence modules, Identity Center, Account Broker, device services, or local machine.

## 1 // Purpose and mechanism

This is the first **opt-in diagnostic that could inspect real KDE Connect daemon metadata** when deliberately run on an operator-approved local Linux host. It does not run when imported or on checkout, and it does not connect to the phone directly. It reads the *existing session bus* with systemd's `busctl` through a tightly limited set of commands.

The diagnostic is not a background service. It cannot send texts, sync contacts, change Bluetooth/Wi-Fi settings, pair/unpair devices, inspect message bodies, read call records, or claim a user-owned phone line.

Command boundary:
1. `org.freedesktop.DBus.NameHasOwner` on the session bus, to check whether `org.kde.kdeconnect` is **already running**; refuse to activate it.
2. `org.kde.kdeconnect.daemon.devices(true,true)` on `/modules/kdeconnect` to request only paired and reachable opaque IDs in memory.
3. For up to **four** such devices, allowlisted `org.freedesktop.DBus.Properties.Get` requests for `isPaired`, `isReachable`, `type`, `supportedPlugins` and `activeProviderNames` on `/modules/kdeconnect/devices/<opaque ID>` (the **lowercase** implementation path from `core/device.h`; an older upstream comment inconsistently capitalizes it).
4. Call only `org.kde.kdeconnect.device.loadedPlugins()` to inspect the local desktop daemon's instantiated plugin names.
5. Pass observations through `KdeConnectDbusEvidence.assess()`. Aggregate **redacted counts** of locally loaded `kdeconnect_sms`, `kdeconnect_contacts`, and `kdeconnect_telephony`. Discard all raw device IDs, names, providers, stdout and stderr before presenting any output.

Every subprocess call uses the same fixed options:

```text
busctl --user --auto-start=no --allow-interactive-authorization=no --timeout=2s --no-pager call ...
```

The child subprocess is also time-bounded to three seconds per call. No `busctl get-property` call is used: `Properties.Get` is invoked through `busctl call` specifically so **`--auto-start=no`** applies. If KDE Connect is inactive, the tool reports `SERVICE_NOT_RUNNING` and does not wake it. On a host without `busctl`, it reports `BUSCTL_NOT_INSTALLED`. It makes no host file writes and never invokes D-Bus mutator methods.

The code parses exact bounded D-Bus reply signatures (`b`, `as`, `v b`, `v s`, `v as`) and treats unexpected responses, inconsistent snapshots, duplicate/invalid device IDs, nonzero exit, subprocess errors and oversized results as failures. A partial result is **not** promoted to verified capabilities.

## 2 // Current output / capability boundary

Output schema: `post-apollo.phone.kdeconnect-dbus-probe.v0`.

`execution` is always `DIAGNOSTIC_ONLY`, never a message/call action. The object contains:
- `state` in `EXPLICIT_FLAG_REQUIRED`, `BUSCTL_NOT_INSTALLED`, `SERVICE_NOT_RUNNING`, `NO_PAIRED_REACHABLE_DEVICES`, `METADATA_REPORTED`, `BUS_TIMEOUT`, `METADATA_UNAVAILABLE`;
- `reportedPairedReachableCount`;
- `localSmsPluginCount`, `localContactsPluginCount`, `localTelephonyPluginCount`;
- `devicePlatform: UNVERIFIED` and `transport: UNVERIFIED`;
- `smsPermission: NOT_CHECKED`, `contactsPermission: NOT_CHECKED`, `callAudio: NOT_CHECKED`;
- `routeEligible: false` in **every** state.

It does **not** return raw identifiers, phone numbers, message previews, service secrets or personal contact details. It cannot identify a particular user or phone line, distinguish Android from iOS from the `phone` device type, or validate Wi-Fi encryption merely from a provider-name string.

**Critical protection:** `METADATA_REPORTED` and nonzero loaded-plugin counts are still *local desktop metadata only*. They must NEVER be converted to `CapabilityPolicy.py` `VERIFIED`, `GRANTED`, `READY`, `ROUTE_CANDIDATE` or sender authority.

## 3 // Usage

There is no existing Post-Apollo UI control for this low-level probe. It is **not run automatically** by any code in the branch.

To run *offline tests* in a checked-out repository, without connecting to real D-Bus:

```bash
python3 -m py_compile services/phone/KdeConnectDbusProbe.py tests/phone/test_kdeconnect_dbus_probe.py
python3 -m unittest discover -s tests/phone -p 'test_kdeconnect_dbus_probe.py' -v
```

For a future **separately operator-approved** local diagnostic, after reviewing installed KDE Connect and systemd versions, execute explicitly from the repository root:

```bash
python3 services/phone/KdeConnectDbusProbe.py --probe
```

Omitting `--probe`, supplying any other flag or importing the module never accesses D-Bus. Running the approved diagnostic only reads KDE Connect metadata **if the daemon already owns its bus name**. It will not launch or configure KDE Connect. Output is deliberately insufficient to claim a working phone integration.

Because real D-Bus behavior, property export, and default timeouts vary with KDE Connect and systemd builds, the local diagnostic must be accepted on a separate permitted test device/session. If one property is not exported, report `METADATA_UNAVAILABLE` and investigate the installed version instead of silently widening to `GetAll` or arbitrary methods.

## 4 // Verification and upstream basis

- KDE Connect [daemon D-Bus service/objects](https://github.com/KDE/kdeconnect-kde/blob/master/core/daemon.cpp) and [`devices(bool,bool)` method](https://github.com/KDE/kdeconnect-kde/blob/master/core/daemon.h).
- KDE Connect [device object path and properties](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.h), [plugin lifecycle](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.cpp), and [SMS/Contacts/Telephony interfaces](https://github.com/KDE/kdeconnect-kde/tree/master/plugins).
- [systemd busctl manual](https://www.freedesktop.org/software/systemd/man/latest/busctl.html) documents `--auto-start=no` for **call** commands, `Properties.Get`, `--user`, and timeout options.
- Mock tests cover fixed command allowlists, non-activation, no-shell subprocess invocation, the exact lowercase object path, D-Bus signature parsing, malformed/untrusted IDs, stale pairing state, oversized replies, empty result, plugin aggregation and output redaction. All tests use an injected fake subprocess runner. They **never** access the real user bus.
- The GitHub CI workflow for this scope is `.github/workflows/social-phone-kdeconnect-dbus-readonly.yml`.

## 5 // Scope still missing

A subsequent assignment, after operator review and local diagnostic evidence, needs:
- The installed KDE Connect/systemd version and a permitted disposable paired Android phone.
- Independent evidence the link is **network** rather than Bluetooth, and trusted user/device/line binding with revocation.
- Proof of Android-side SMS/Contacts plugin permissions and ability to read particular requested data, without exposing real content in a PR or log.
- A truthful provider result/acknowledgement contract and duplicate-send protection before any SMS send.
- Integration-owner review before wiring existing Social selectors/conversations, and a separate verified audio bridge for cellular calls.

The current diagnostic **cannot** solve iPhone iMessage restrictions, FaceTime, Android call audio, or organizational phone authorization.

## 6 // HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Standalone opt-in no-autostart D-Bus metadata diagnostic, isolated unit tests and CI, index and contract; no live desktop edits.

### HOW TO USE
Offline test command above. Optional `--probe` is **not** a license to run on the operator's PC without context-specific permission.

### VERIFY
Check exact-head GitHub CI and file diffs; runtime device/daemon not assessed by CI. No Android/iPhone permission, Wi-Fi transport or actual messaging function certified.

### WATCH OUT FOR
D-Bus property export and naming may differ by installed version. A `LOCAL_PLUGIN_LOADED` count isn't a phone permission. The D-Bus session may contain private identifiers, which remain in memory and are never emitted. The tool must not be wired into Social without a real trust boundary.

### CHECKLIST
- [x] PR #1022 merge and main baseline verified; Syntagma and phone contracts read.
- [x] Narrow read-only busctl allowlist and explicit flag guard.
- [x] Mocked error/timeout/privacy and non-mutation tests.
- [ ] Exact-head GitHub CI.
- [ ] Operator review and merge.
- [ ] Separate local diagnostic permission and real-device verification.

### NEXT
After PR acceptance, use the existing Social settings path only after a trusted phone-owner and transport capability broker is designed. A one-time operator-approved diagnostic on a known Android device can establish the next factual gate.

### DECISIONS
Operator direction unchanged: **network first, Bluetooth per-capability opt-in fallback, Android and iPhone targets, single Social Hub UI**. The diagnostic does not select a production broker, authorize provider access, or create a live Hospital assignment.
