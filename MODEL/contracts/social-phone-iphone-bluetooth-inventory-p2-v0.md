# Social Phone Bridge // Opt-in iPhone/Linux Bluetooth prerequisite inventory P2 v0

> **STATUS //** Repository-only, read-only command-line inventory with synthetic CI. No actual host inspection, phone connection, authenticated user, Bluetooth permission or iPhone support certified.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **DATE //** 2026-11-02. **BASE //** `main` at `d8c483cceb714782f0081c9e17b134ce0c20ceb9` after PR #1054 merged. Recheck HEAD, concurrent Phone/Identity work and ownership before further changes.
>
> **CONNECTION //** OPEN AI // CHATGPT, external Hospital-compatible worker only. No live Room, Staff Role, Assignment, Session or checkpoint established.
>
> **SCOPE //** New `services/phone/IphoneBluetoothInventory.py`, `tests/phone/test_iphone_bluetooth_inventory.py`, isolated CI, this contract and MODEL index. No changes to Identity Center, Social QML, Qt KDE receiver, BlueFerry, local host, Bluetooth settings or phone pairing.
>
> **DEPENDS ON //** [iPhone/Linux feasibility and opt-in pilot plan](./social-phone-iphone-linux-feasibility-p2-v0.md), [Phone Bridge network-first ADR](./social-phone-bridge-network-first-adr-v0.md), [proposed Identity Center trusted-host handoff](./social-phone-identity-host-integration-handoff-p1-v0.md).

## 1 // Concrete mechanism

An installed Linux system can report limited **local prerequisites** without pairing an iPhone or asking a D-Bus daemon for remote device metadata. This inventory is deliberately much narrower than an iPhone compatibility check.

`IphoneBluetoothInventory.py` is **inert on import**. Without the sole exact argument `--inspect`, it emits `EXPLICIT_FLAG_REQUIRED` and does no file/process inspection.

When explicitly invoked it performs, in order:

1. Confirm the Python runtime reports `linux`; other platforms exit without performing checks.
2. Use `shutil.which` to check for an executable named `blueferry` **without executing it**; this says only that a binary is on PATH, not whether BlueFerry is installed correctly, a backend process is running or a phone is paired.
3. Use `shutil.which` to locate `bluetoothctl` **without starting BlueZ**. Reject relative paths and malformed/nonprintable injected command paths.
4. List only **names** in `/sys/class/bluetooth`; count bounded `hciN` entries, without inspecting addresses, device symlinks, paired devices, USB identifiers or HCI capabilities. A missing/unreadable path yields unknown count, not zero and not a permission verdict.
5. If `bluetoothctl` exists, run exactly `[bluetoothctl, "--version"]` in a fixed 3-second bounded subprocess. Parse a strict, bounded major/minor version from stdout only. Discard stderr and all raw output; no D-Bus, `bluetoothctl show`, `devices`, `scan`, `pair`, BlueFerry diagnostic or service manager method is requested.

The CLI output is a single JSON object with `execution=OPT_IN_LOCAL_METADATA_ONLY`, a fixed state code, optional BlueZ version and adapter count, and whether the BlueFerry CLI executable was found. It intentionally does not include executable paths, system username, MAC addresses, hostname, paired devices, iPhone ID/model, package list, errors, phone numbers or messages.

**Limitations:** a vendor-modified `bluetoothctl --version` binary is external software; this tool does not attest its behavior, only restricts the arguments Post-Apollo supplies. Ordinary Linux sysfs/BlueZ metadata is not proof the controller works, is powered, supports Classic BR/EDR plus LE, or has permissions to access MAP/PBAP/ANCS. A version string is not a negotiated protocol capability.

## 2 // Supported version hints, not READY states

The upstream [BlueFerry Bluetooth protocol findings](https://github.com/erikwb/blueferry/blob/main/PROTOCOL.md), read 2026-11-02, report **MAP/PBAP observed with BlueZ 5.72+** and a **dual-bearer ANCS path requiring BlueZ 5.86+** with its bearer API. These are **project-reported minima, not official Apple/BlueZ compatibility certification or an assertion that the user's controller works**.

The inventory labels `mapPbapVersionMinimum` and `ancsVersionMinimum` as `DOCUMENTED_VERSION_MET`, `BELOW_DOCUMENTED_VERSION` or `NOT_CHECKED`. These are purely numeric version comparisons to upstream's claims, not proof of hardware capability. Upstream may change their test matrix; revalidate before a real pilot.

Every result, even one with a high BlueZ version and multiple controllers, contains:

```json
{
  "controllerClassicLeSupport": "NOT_CHECKED",
  "iphonePairing": "NOT_CHECKED",
  "iphonePermissions": "NOT_CHECKED",
  "blueferryDaemon": "NOT_CHECKED",
  "networkRoute": "NOT_CHECKED",
  "messaging": "NOT_VERIFIED",
  "routeEligible": false,
  "contentAccessEnabled": false
}
```

The full output also includes a fixed schema, execution label, state, `bluezVersion`, `adapterCount`, `blueferryExecutableFound` and version hint fields. No status from this component can make a phone route READY, authorize message content or override the network-first policy. Bluetooth remains a per-capability **explicit operator opt-in**, not an automatic fallback after a connection error.

## 3 // Use and what constitutes a local-machine action

CI uses **injected** `shutil.which`, subprocess and sysfs-listing fakes. It **never actually runs** `bluetoothctl`, reads real sysfs or starts a service. The only tested host behavior is generated by invented fixtures.

From a checkout on a Linux computer, the exact operator-invoked command would be:

```bash
python3 services/phone/IphoneBluetoothInventory.py --inspect
```

That command reads the operator's local environment and executes **only** `bluetoothctl --version`. It has no package installation, pairing or state-changing method, and is deliberately not run by the browser worker. A local host read has not been independently performed. If an operator has strict host-control rules, obtain explicit approval before running *any* local diagnostic, regardless of how read-only its intended commands are.

Running the module with no argument or unknown arguments provides only `EXPLICIT_FLAG_REQUIRED` and requires zero inventory calls. It does not activate an app or supply any Post-Apollo UI button.

## 4 // Verification and privacy boundaries

Isolated workflow: `.github/workflows/social-phone-iphone-bluetooth-inventory.yml`.

```bash
python3 -m py_compile services/phone/IphoneBluetoothInventory.py tests/phone/test_iphone_bluetooth_inventory.py
python3 -m unittest discover -s tests/phone -p 'test_iphone_bluetooth_inventory.py' -v
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

Synthetic tests cover default no-I/O invocation, exact `--inspect` argument, non-Linux rejection, allowed command list, tool absence, missing/unreadable sysfs, strict `hciN` counts, version bounds at 5.72/5.86, false return codes, timeouts, unsafe command paths, malformed stdout and sanitized summaries. No personal data is included in fixtures. Full existing Python Phone Bridge tests must remain green.

The inventory **cannot** determine the iPhone model/iOS version, installed BlueFerry service identity, Bluetooth pairing status, BlueZ D-Bus owner, profile negotiation, Linux adapter chipset, BR/EDR and LE support, trust of a particular phone/line, real ANCS entitlement, or Social tenant authorization. Those require a separately authorized, scoped hardware pilot and accepted Identity Center production-security Gate A.

Do not request `blueferry doctor` automatically; the upstream diagnostic may inspect the real Bluetooth/phone/backend state. Do not call session D-Bus `GetStatus` or `ListMessages` without explicit purpose-specific permission. Never log, transmit to GitHub, or write persistent hardware/message data during a future pilot.

## 5 // HOSPITAL HANDOFF

### IMPLEMENTATION
Added a tightly scoped Python opt-in read-only metadata inventory for Linux BlueZ/iPhone candidate prerequisites, with no BlueFerry or phone connection.

### HOW TO USE
Review the standalone file or its isolated CI. A user may explicitly invoke the CLI `--inspect` after accepting local diagnostic scope. No automatic host execution, pairing or UI integration.

### VERIFY
Check exact PR-head code/test CI, source read-back, and bounded command argument expectations. Green CI verifies synthetic output handling, not the user's installed BlueZ or iPhone compatibility.

### WATCH OUT FOR
Version and adapter count are **not** permission or feature readiness. Bluetooth Classic+LE support remains unchecked. Third-party BlueFerry is experimental and GPL-2.0-or-later; no code or binaries were copied. User's real iPhone and local Bluetooth controller remain unverified. The Identity Center host is not a production grant authority.

### CHECKLIST
- [x] Verify PR #1054 merged, current main, no open Phone/Identity ownership collision, and relevant Syntagma.
- [x] Implement fixed, explicit-only local metadata command and no-autostart default.
- [x] Add synthetic no-I/O, privacy, version and rejection tests with isolated CI.
- [ ] Exact-head CI successful, operator review and PR merge.
- [ ] Separately authorized read-only local hardware inventory on the user's computer.
- [ ] Explicit consent for any Bluetooth pairing, installation, daemon changes or SMS testing.
- [ ] Accepted security/Identity Center Gate A before real content routing.

### NEXT
Once reviewed, decide whether to run the exact read-only inventory on the operator's Linux desktop. If it identifies a candidate BlueZ version, separately evaluate the controller's Classic/LE capabilities and installed BlueFerry API in read-only mode **only after additional local approval**. Do not start or pair anything automatically. Keep Android KDE Connect and iPhone Bluetooth providers separate, with a single eventual Social UI.

### DECISIONS
Network-first policy preserved; Bluetooth opt-in only per capability. No Mac required for this candidate research. No claim of working SMS/iMessage, calls, FaceTime or delivery receipts. No local machine writes, production activation, real pairing, phone data access, PR merge or live Hospital registration.
