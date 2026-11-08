# Social PHONE P26 // Silverblue host oFono installation boundary

> **STATE //** GitHub-only P26 proposal, not deployed or live verified. Operator Fedora 44 Silverblue host evidence on 2026-11-08: `test -e /run/ostree-booted` reports OSTREE HOST, `rpm -q ofono` says not installed, `rpm-ostree status` says idle, current booted deployment contains local `blueferry-backend-0.9.1-1.fc43.noarch`. Older pinned deployments exist. Do not infer the current working tree or live Quickshell matches the PR.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`. **ROOM //** Social PHONE CALLS P25 continuation, Silverblue setup P26. **ASSIGNMENT //** Correct only the Fedora host package-install route without enabling calls, changing services or Bluetooth, modifying desktop files, or performing deployment/reboot.
>
> **WORKER //** OPEN AI / CHATGPT, external Hospital-compatible DOC for bounded source work. No verified Hospital Room, role registration, Assignment or Session. Operator final authority.

## IMPLEMENTATION

- Existing PHONE -> DEVICE -> SET UP CALLING uses an in-panel `foot` stage and `PhoneCallingSetupHandoff.py`. On mutable Fedora it chooses PackageKit or Polkit/DNF5; that is not a correct host package-layering route for OSTree/Silverblue.
- The handoff and terminal session now detect `/run/ostree-booted` independently. For an atomic host they require a trusted system `rpm-ostree` executable from the same restricted `/usr/bin` or `/bin` discovery list. **Do not fall back to DNF5 or PackageKit on an OSTree host.** The existing mutable Fedora behavior remains.
- The interactive terminal first runs read-only `rpm-ostree status --json` to establish the currently booted deployment is first and that no staged/pending deployment will be displaced. If status is malformed, inaccessible, or a pending/staged deployment is visible, fail closed.
- Before `rpm-ostree install ofono`, the user must type exactly `INSTALL OFONO` in the existing visible terminal. Neither opening PHONE nor clicking SET UP CALLING performs the install. This exact opt-in authorizes **only** the requested host package transaction; system Polkit privilege remains separate. No `-y`, `--apply-live`, automatic reboot, service start, BlueFerry calls enable, audio routing or pairing changes.
- A successful `rpm-ostree install` response means a new deployment was requested, **not** that the running host now has oFono. The terminal instructs the operator to inspect `rpm-ostree status`, reboot **separately** only after approval, then return to PHONE and use CHECK AGAIN. UI copy warns that the old running deployment still reports package missing before reboot.
- The handoff emits only sanitized tool identifiers. `RPM_OSTREE` is added to the existing fixed allowlist, and PHONE handles it without exposing paths or backend errors. Existing Stage Director ownership, stage geometry, call buttons, contacts, messages, BlueFerry identity/grants, and audio are unchanged.

## HOW TO USE

After reviewed merge and **separately authorized** desktop update, use **Social -> PHONE -> DEVICE / HFP SETUP -> SET UP CALLING** if the live read-only prerequisite diagnosis still reports `PACKAGE_NOT_INSTALLED`. Inspect the interactive terminal's host type and the package request. Type `INSTALL OFONO` only when you authorize staging a new Silverblue deployment. Otherwise close/cancel. After success, verify `rpm-ostree status` and the pending new deployment. **No automatic reboot**. After your separately approved reboot, check `rpm -q ofono`, `systemctl show ofono.service --no-pager -p LoadState -p ActiveState`, and PHONE -> CHECK AGAIN. Only then consider separately authorized D-Bus, WirePlumber/BlueZ HFP and BlueFerry call-enable changes.

On the currently installed version, **do not use SET UP CALLING** for Silverblue: it still uses the old PackageKit/DNF5 path until this source is merged and deployed.

## VERIFY

- Added `tests/phone/test_phone_ostree_install.py`: marker selection, trusted system executable, no mutable-host fallback on atomic Fedora, existing stage ownership, status preflight refusal for malformed, staged, or pending deployments, explicit confirmation refusal/acceptance, exact host-package argv, failed transaction, and reboot messaging.
- Updated PHONE setup workflow to compile and run the new synthetic tests alongside existing mutable Fedora, stage safety, service diagnosis, HFP status, and UI contracts.
- No real system package install, pending deployment creation, reboot, live HFP test, Bluetooth operation, local checkout change, or Quickshell restart performed. CI and operator review remain separate evidence gates.

## WATCH OUT FOR

- `rpm-ostree status --json` validation intentionally fails closed if a build/version gives a different shape. Do not weaken this check merely to make an install run; inspect the live read-only JSON shape first.
- `rpm-ostree install` by default builds an offline deployment; never add `--apply-live` to shortcut the approval/reboot boundary. On a layered host with an old BlueFerry local package and pinned deployments, inspect the new deployment before reboot rather than assuming existing layers are intact.
- oFono installation is only the first HFP prerequisite. System D-Bus permissions, oFono service ownership, WirePlumber HFP backend, BlueZ conflict, real microphone/speaker routing and a safe non-emergency call remain unverified.
- Any HOST installation, reboot, system service start, audio change, Bluetooth change or local checkout deployment requires a new explicit operator approval. Do not merge automatically.

## CHECKLIST

- [x] Recover P25 and user Silverblue/current deployment evidence.
- [x] Read Syntagma authority/Hospital protocols; inspect current PHONE source/PR ownership.
- [x] Restrict atomic host to `rpm-ostree` and retain ordinary Fedora path.
- [x] Preserve user confirmation, status preflight, stage ownership, and no-auto-reboot boundary.
- [x] Synthetic tests and workflow.
- [ ] Exact-head CI and diff review.
- [ ] Operator PR review/merge authorization and separately approved local update.
- [ ] Verify pending/new booted host after a future approved package transaction.
- [ ] Separate approved HFP configuration and physical calls/audio acceptance.

## NEXT

Review exact-head PR CI, then operator decision on merge/deploy. Confirm live `rpm-ostree status --json` shape read-only before trusting installer preflight on Fedora 44. Do **not** stage oFono until the operator approves that specific host deployment. After rebooted installation, verify oFono service first, then hand off to the HFP/audio owner if broad configuration changes are needed.

## DECISIONS

Preserve source-vs-live and user-approval boundaries. Keep setup in the existing Social PHONE terminal, not an external workaround. Atomic Silverblue host uses `rpm-ostree` exclusively, with explicit typed consent and offline deployment. Reboot and HFP activation are separate authorized actions. The previous phone data functionality remains unaffected. Recovery: close the draft PR before merge or revert the bounded commit after merge; no local rollback exists because local state was not modified.
