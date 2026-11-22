# Post-Apollo System Tray // Persistent SNI registry

**Status:** Candidate integration, not deployed or accepted. **Owner:** System Tray / desktop startup integration. **Source:** [sni-watcher 0.3.0](https://github.com/MasonRhodesDev/sni-watcher), an independently maintained MIT-licensed Rust project. The upstream source and service were inspected, but this is **not a security endorsement or a native Post-Apollo compatibility test**.

## Why icons disappear on Quickshell reset

Tray applications register a D-Bus object with `org.kde.StatusNotifierWatcher`. Quickshell currently runs both the visual tray and (when uncontested) the watcher service. `scripts/restart_quickshell_safe.sh` terminates Quickshell to avoid the Qt shader teardown crash. If Quickshell owns the D-Bus watcher, that termination destroys its in-memory registry. Some clients such as Electron applications do not re-register after a watcher replacement. The `TRAY / NO ICONS` label accurately shows an empty registry; adding QML placeholder icons would conceal the failure, not repair it.

**Approved direction for a durable implementation:** Keep ONE user-session watcher running independently of Quickshell, started **before** the graphical session and app autostart. Quickshell then acts as the tray host. A Quickshell reset must not stop, restart or steal the independent watcher.

## Inspect (no changes)

From the checked-out Post-Apollo project:

```bash
bash scripts/tray/persistent_watcher.sh --status
```

The output reports the actual watcher bus owner, presence/activation of the candidate user service, and whether a persistent service is verified. The script does not call an absent D-Bus destination (which could activate it) and does not restart processes.

Interpretations:

- `PERSISTENCE_NOT_VERIFIED`: current service registration is not proven durable. If `WATCHER_CURRENT_OWNER` shows `quickshell`, restarting Quickshell can drop items.
- `PERSISTENT_WATCHER_ACTIVE`: a Type=dbus `sni-watcher.service` is active, owns the expected bus name, and a watcher name is present. Further native host compatibility and item persistence checks are still needed.
- `WATCHER_CURRENT_OWNER=ABSENT`: no bus registration presently exists; **do not** fabricate icons or repeatedly restart applications without diagnosing startup.

Optional independent read-only check:

```bash
busctl --user --no-pager list | grep 'org.kde.StatusNotifierWatcher'
```

## Candidate one-time activation, intentionally not automatic

**Deployment is a separate operator-approved change to the host. No installation or activation has been performed by this repository work.**

1. Independently review the exact packaged watcher build, runtime privilege requirements, licensing and compatibility with the installed Quickshell/Qt and Fedora Silverblue deployment. The upstream Fedora COPR is a third-party package source, not an already trusted Post-Apollo dependency. Verify package signatures/provenance before any installation. Never layer an unreviewed RPM automatically.
2. Install an authorized `sni-watcher` 0.3.0+ RPM in the OS using the chosen Silverblue-compatible, operator-approved package workflow. The package is expected to provide `/usr/bin/sni-watcher`, a D-Bus user service and an early-start user unit. Do not copy an unversioned binary into the live Quickshell tree.
3. Only **after** the unit is installed and reviewed, explicitly arm it for the next login. This writes an enablement symlink, **not** a live D-Bus takeover:

   ```bash
   bash scripts/tray/persistent_watcher.sh --enable-next-login
   ```

   The guard requires `Type=dbus`, `BusName=org.kde.StatusNotifierWatcher`, `ExecStart=/usr/bin/sni-watcher`, `Before=graphical-session-pre.target` and `WantedBy=graphical-session-pre.target`. It never runs `systemctl --user enable --now`, never restarts Quickshell, and never installs packages.

4. At the **next normal graphical login**, confirm `sni-watcher.service` is active and is the D-Bus owner **before** Vesktop/Lutris start. If `graphical-session-pre.target` is not reached by your Sway login path, the service may not auto-start: **stop rollout and adjust the startup ownership in a separately reviewed change** instead of pretending enablement is sufficient.
5. Collect `RegisteredStatusNotifierItems` before and after an **operator-approved** Quickshell restart:

   ```bash
   busctl --user get-property org.kde.StatusNotifierWatcher /StatusNotifierWatcher org.kde.StatusNotifierWatcher RegisteredStatusNotifierItems
   ```

   The registry and icons for still-running apps should persist, and the watcher D-Bus owner must not change. Check app launch **before** and **after** the host appears, native menu clicks and full-screen tray ordering. Newly installed watcher cannot retroactively recover apps whose original registration failed; one fresh app launch or the next login may be required.

## Important failure and rollback rules

- **Never start or restart the watcher while Quickshell is the active tray host.** The reviewed upstream daemon requests the watcher name with `REPLACE_EXISTING`; running it live can take over the registration service and trigger precisely the icon loss being repaired.
- **Never enable multiple competing watchers.** Identify existing KDE/Waybar/SNI owner before activation. Do not use a periodic job that toggles each application's tray setting or repeatedly kills applications.
- The upstream unit uses `OOMScoreAdjust=-900`; verify it is supported by the user-service environment and does not introduce a host startup failure.
- The upstream registry restores only entries whose D-Bus owner remains alive, not icons for apps that truly exited. It cannot make an app that never registers produce a tray icon.
- **Rollback requires separate local approval:** `systemctl --user disable sni-watcher.service` removes enablement for future logins. Do not stop/restart the current watcher until the UI host and registered applications have a safe handoff plan. Package removal and Silverblue rollback are separate operations.
- Keep `scripts/restart_quickshell_safe.sh` unchanged until a native tray persistence test passes. The script's existing Quickshell kill/restart is precisely why independent watcher ownership matters; changing it without a watcher does not repair registration.

## Acceptance gate

- [ ] Trusted package/source and native unit ownership reviewed
- [ ] Installed service present and future-login enablement explicitly approved
- [ ] Sway login reaches early-start target before clients
- [ ] Watcher D-Bus owner remains the same across Quickshell reset
- [ ] Vesktop and Lutris retain icons and their real context menus
- [ ] No changes to tray position, orange hover, pointer mask or fullscreen ordering
- [ ] Operator accepts live behavior

**Current evidence:** repository preflight/test only. No live workstation data, package installation, restart or claim of Hospital registration.
