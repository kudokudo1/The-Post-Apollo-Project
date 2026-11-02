# Social Phone Bridge // KDE Connect presence discovery P1 v0

> **STATE //** Experimental source-only probe, **not a supported Android SMS/contacts backend**.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **DATE //** 2026-11-02
>
> **BASELINE //** `main` at `f250a3b632bbcd729fc40662d5645593f8958b21`, verified after PR #1018 merged. Recheck HEAD before further changes.
>
> **RELATION //** Follows [network-first ADR](./social-phone-bridge-network-first-adr-v0.md) and [P0 capability route planner](./social-phone-capability-policy-v0.md).
>
> **SCOPE //** `services/phone/KdeConnectPresence.py`, `tests/phone/test_kdeconnect_presence.py`, targeted CI and this contract. No edits to `MessagingW.qml`, `AppSelector.qml`, shared router, Identity Center or phone settings.
>
> **HOSPITAL //** External browser Doctor, Hospital-compatible, no verified live Hospital Room, Staff Role, Session or device assignment.

## 1 // Purpose and verified upstream interface

KDE Connect on Linux exposes a command-line program, `kdeconnect-cli`. Its upstream implementation documents `--list-available` as paired-and-reachable device listing and `--id-only` as IDs-only output. The CLI may enumerate multiple transports; **presence is not proof of Wi-Fi/LAN**. Some versions of KDE Connect may support other link providers, so a reachable device must not automatically become a NETWORK route.

The only command this optional diagnostic can invoke is:

```text
kdeconnect-cli --list-available --id-only
```

This call is for inventory only. It does NOT request `--refresh`, `--pair`, `--send-sms`, `--list-notifications`, contact data, device files, or Bluetooth configuration. The KDE Connect CLI can communicate with or autostart the existing user daemon over D-Bus, so **running the probe on the operator's machine still requires separate local execution approval**. Merely merging the Python file does not invoke it.

Sources:
- Upstream desktop CLI flags and listing implementation: https://github.com/KDE/kdeconnect-kde/blob/master/cli/kdeconnect-cli.cpp
- KDE Connect official Android transport description: https://github.com/KDE/kdeconnect-android/blob/master/README.md
- KDE Connect feature matrix and iOS limitations: https://userbase.kde.org/KDEConnect/en

## 2 // Mechanism

The standalone, importable Python module provides two independent operations:

1. `summarize(stdout, returncode)` is pure and safe for synthetic tests. It parses only bounded ID-only lines, refuses malformed/duplicate/unexpected values, and **never echoes any ID or device name**.
2. `probe(find_executable=..., runner=...)` is **opt-in**, calls the existing local `kdeconnect-cli` executable with one fixed argument list (no shell, no mutating flags), enforces a five-second timeout, and returns a minimal summary. It does not install KDE Connect or configure pairing.

Response contract `post-apollo.phone.kdeconnect-presence.v0` contains exactly:

- `provider: kdeconnect`, `execution: DISCOVERY_ONLY`;
- `state`: `CLIENT_NOT_INSTALLED`, `CLIENT_TIMEOUT`, `CLIENT_ERROR`, `INVALID_RESPONSE`, `NO_PAIRED_REACHABLE_DEVICES` or `PAIRED_REACHABLE_REPORTED`;
- `pairedReachableCount`: bounded integer, never an identity or ownership grant;
- `devicePlatform: UNVERIFIED`, `transport: UNVERIFIED`;
- `sms`, `contacts`, `notifications`, `callAudio`: all `NOT_CHECKED`;
- `routeEligible: false` unconditionally.

**None of these results may be converted into a `CapabilityPolicy.py` `READY` / `VERIFIED` route.** Pairing/reachability does not show which device is Android, which transport is active, which phone profile or permission is granted, or whether messages/contacts can actually be read/sent. A future privileged, scope-aware adapter must establish those separately.

The module has no persistent storage, phone-number parameter, chat retrieval, message sending, secrets, or auto-running timer. Its diagnostics omit device IDs/names/addresses and raw stdout/stderr.

## 3 // Operator diagnostic (future separately approved execution)

After explicit approval for a local **read-only device-list diagnostic**, from the repo root:

```bash
python3 services/phone/KdeConnectPresence.py
```

It prints a minimal JSON response with count and unknown capability states. It might start an already-installed KDE Connect user daemon, and can reveal to the person running it whether paired devices are reachable. It neither changes pairing nor adds new service configuration. If no CLI is installed, it reports `CLIENT_NOT_INSTALLED`, **not** a request to install one.

Do not run on the operator's desktop just to produce evidence without permission. No actual iPhone or Android device was observed, queried or modified during this repository task.

## 4 // Offline verification

```bash
python3 -m py_compile services/phone/KdeConnectPresence.py tests/phone/test_kdeconnect_presence.py
python3 -m unittest discover -s tests/phone -p 'test_kdeconnect_presence.py' -v
```

The targeted CI `.github/workflows/social-phone-kdeconnect-presence.yml` uses mocks for executable lookup and the subprocess runner. Test cases cover empty, single/multiple, duplicate, malformed and excessive IDs; missing binary; timeout; nonzero exit; OS error; no raw ID/secret leakage; no mutating flags; and the absence of unsupported capability declarations. These tests **never invoke the real CLI**.

## 5 // Missing evidence / gate for the next P1 increment

Before any real SMS/contacts adapter may be marked ready:

1. Verify the exact local KDE Connect version and whether the client/daemon are present, without changing installed packages; operator approval for local probe is separate.
2. Determine a **trusted transport** (LAN vs Bluetooth vs unknown), paired device identity and authorization grant; avoid exposing IDs in QML, PRs or logs.
3. Verify the device is Android and that Android KDE Connect is legitimately paired and reachable with the relevant plugin permissions, with revocation.
4. For messages/contacts, inspect KDE Connect's current **D-Bus** capability/API and plugin evidence, distinguish notification previews vs complete message retrieval, and test only on explicitly approved disposable data.
5. Only the Social integration owner may wire normalized read/send results and status into the existing selector, conversation feed or shared router. Provider-confirmed send results and duplicate prevention remain mandatory.
6. Keep iPhone network feasibility and experimental Bluetooth MAP/HFP investigations as separate assignments. KDE Connect iOS does not supply Android-equivalent SMS integration.

## 6 // Hospital-compatible handoff

### IMPLEMENTATION
Isolated, opt-in presence-only KDE Connect inventory parser and executable probe; no phone/messaging/calling backend.

### HOW TO USE
Synthetic tests above; real `probe` execution requires separate local permission and existing KDE Connect.

### VERIFY
Use exact GitHub PR SHA, targeted CI and offline tests. No phone handshake, actual Wi-Fi path, SMS, contacts or audio is certified.

### WATCH OUT FOR
New KDE Connect versions may expose Bluetooth as an active link provider; **never infer network transport from the CLI's paired/reachable list**. Probing may start the existing user daemon. Local working tree and running Quickshell are untouched by this repo-only PR.

### CHECKLIST
- [x] Verify merged P0, read ADR and shared source contracts
- [x] Inspect upstream `kdeconnect-cli` behavior
- [x] Add isolated presence snapshot and mock tests
- [ ] Exact-commit CI and operator review
- [ ] Local diagnostic approval and observed capability truth
- [ ] Trusted pairing/transport/permission proof before messaging

### NEXT
After PR review, request separate operator approval for a bounded local presence check, or build a strictly isolated D-Bus capability-contract research fixture with no real phone data.

### DECISIONS
The network-first architecture and opt-in per-capability Bluetooth fallback remain unchanged. **Presence is not a route, connection to a verified Android phone, messaging permission or call audio support.** No automatic pairing, login, integration, merge or production activation.
