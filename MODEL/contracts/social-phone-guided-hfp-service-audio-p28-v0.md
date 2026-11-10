# Social PHONE // P28 guided HFP service and WirePlumber setup

Status: proposed, GitHub-only implementation, no live host deployment or real-call certification.

## Scope and authority

Patient: The-Post-Apollo-Project. Bounded seam: existing Social PHONE / DEVICE calling setup and its exact embedded foot stage. Existing Room/Assignment identity and live Hospital attachment were not verified; this PR does not create one or assume another worker's ownership.

Operator intent: After Fedora's existing package installation path, continue through user-approved oFono service activation and WirePlumber HFP configuration from the *same* Social PHONE control. No auto-start on menu open, no system-wide silent mutation, no BlueFerry calls opt-in, no contact/message access, no pairing, and no production activation.

## Setup state machine

1. **PACKAGE_NOT_INSTALLED:** Keep existing Fedora package installer. On Silverblue, `rpm-ostree install ofono` stages a new deployment and needs a separately approved reboot. Mutable Fedora keeps its PackageKit / Polkit+DNF5 path.
2. **SERVICE_STOPPED:** With a loaded oFono systemd unit, use the exact staged terminal to review and separately approve a one-time `sudo /usr/bin/systemctl start ofono.service`. No `enable`, no persistent boot policy change.
3. **AUDIO_PATH_UNVERIFIED:** With an installed, active oFono unit, the same terminal verifies D-Bus `GetModems`, WirePlumber 0.5+, and service state; it will not widen D-Bus policy. Existing user and system HFP fragments are inspected conservatively.
4. **HFP backend absent:** Show exact user-only `51-bluez-ofono.conf` contents. Create with exclusive file creation only after `CONFIGURE HFP`. Never overwrite, follow a symlink, or rewrite other audio roles. Ask separately for `RESTART WIREPLUMBER`. If declined or restart fails, remove only the freshly created matching file; attempt to restore normal WirePlumber operation when a restart fails.
5. **HFP backend already set:** Verify and leave it intact. The terminal reports that modem/call audio is still unverified, and tells the user to use the separate `CALLS ON PC` opt-in.
6. **Failed/masked/unknown service or conflicting audio settings:** Fail closed for manual diagnosis; do not silently unmask, grant privileges, force package changes, restart unrelated services, or enable calls.

The UI's sanitized handoff remains `post-apollo.phone.calling-setup-handoff.v0`. It only reports the staged terminal request, not success. After stage closure, `CHECK AGAIN` reruns the existing read-only prerequisite diagnosis, and `READY_TO_CONTINUE` permits the next explicit setup action.

## Linux portability

- **Fedora Silverblue:** Package installation staged using rpm-ostree; service and audio steps after boot.
- **Mutable Fedora:** Package installation uses existing PackageKit or Polkit+DNF5 paths; service and audio steps use same generic helper.
- **Other Linux distributions:** The generic service and audio helper can run when oFono is *already installed*, a compatible systemd unit exists, WirePlumber 0.5+ is active, the user can query `org.ofono`, and approved `sudo` can start the system service if needed. A non-RPM distro may report package `UNKNOWN`, which is acceptable only when the oFono unit is independently `loaded`. Package installation for apt/pacman/zypper/emerge is **not implemented**.
- **OpenRC, runit, alternate Bluetooth audio managers, older WirePlumber, missing sudo:** Not automatically supported by this guarded path. Requires a separate compatible provider implementation.
- **UI staging:** Existing Sway/foot exact-app-id stage is reused. This does *not* certify the Post-Apollo UI on every compositor or desktop environment.

## Evidence and acceptance gates

- Repository tests assert never starting services on import or without interactive flag, exact typed consent per mutation, fail-closed conflicts, no broad D-Bus grants, safe non-overwrite, rollback after restart refusal, and legacy Fedora package handoff retained.
- CI validates the helper, existing PHONE handoff, sanitized QML contract, and original package installation tests.
- Host acceptance remains unverified: no Linux matrix, real iPhone hands-free modem, microphone, speaker, BlueZ conflict, post-reboot service persistence, or alternative desktop environment test has been performed. The operator must separately approve any host mutation and deployment.

## Recovery

- If a newly-created user WirePlumber fragment causes problems **after deployment**, remove only the specific `~/.config/wireplumber/wireplumber.conf.d/51-bluez-ofono.conf` content you approved and restart your user WirePlumber service with approval. The guided helper itself performs a bounded rollback on a failed restart when it knows it created that file.
- Leave pre-existing audio files, existing BlueFerry preferences, paired devices and contact/message services untouched.

## Pending

Review/merge by operator, deploy latest Social PHONE files to the host separately, inspect readiness in DEVICE and check real HFP audio on a non-emergency call. Expand distro-specific installation only with tested permission models and explicit acceptance.
