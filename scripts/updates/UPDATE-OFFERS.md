# UPDATE OFFERS // Post-Apollo Notifications

This is an opt-in **decision layer** for updates, not a replacement for the
OS package manager or existing shell updaters. The Quickshell session checks
approximately every six hours, starting after Notifications history is ready.

## Sources observed

* **Fedora Silverblue:** reads \`rpm-ostree status --json\` for an already
  staged deployment, then (if no pending deployment exists) uses
  \`rpm-ostree upgrade --check\` for an offered base-image update. These checks
  do not create a new deployment. Offers distinguish **AVAILABLE** from
  **REBOOT PENDING**. An available OS update may include Kitty when Kitty
  is installed as an OS-managed RPM.
* **Oh My Zsh:** compares the installed \`~/.oh-my-zsh\` Git checkout HEAD
  with the remote branch configured as its upstream. Only well-formed remote
  references are considered. Remote differences are **REVIEW**, not proof
  that a fast-forward or the upstream maintainer's update is safe.
* **Powerlevel10k:** similarly checks recognizable Oh My Zsh custom theme
  and manual checkout paths when they are Git checkouts with tracking
  branches. Other plugin managers need their own integration.

* **Flatpak user/system:** separately checks installed Flatpak updates in the
  user and system installations. Each offer uses the exact refs, remotes and
  upstream commits. **DOWNLOAD** opens Kitty and requires a typed DOWNLOAD
  to cache pinned commits (Flatpak no-deploy), or APPLY to download and
  deploy those commits. GNOME Software may already be downloading updates.
* **Firmware / Secure Boot:** reads fwupdmgr's JSON update list when
  available. **OPEN UPDATES** opens the native GNOME Software Updates page.
  Post-Apollo never flashes firmware or alters the Secure Boot database.

GNOME Software's **System Updates** plus Files, Firefox, codecs and other
entries under **Requires Restart** can be individual changes within one
Silverblue rpm-ostree deployment. These do not get duplicate RPM alerts.
**Kitty installation provenance matters:** Kitty can be part of the Silverblue
deployment, layered, installed by its own binary installer, or installed in a
container. This pass deliberately does not run Kitty's standalone installer
or infer an update from a different packaging channel. A separate Kitty
offer requires provenance-aware detection and an approved updater.

If a program, check command or upstream configuration is unavailable,
the probe returns **no offer**; it does not claim that everything is current.

## Decisions in Notifications Hub

Each **current, fingerprint-matched** offer has two buttons:

* **REVIEW**: opens a new Kitty terminal, checks that the same update is still
  offered, prints the type of operation, and demands the exact typed word
  \`APPLY\` to run an update. Closing the terminal or typing anything else
  cancels. A staged OS deployment only displays its status and reboot advice.
* **NOT NOW**: writes a scoped 24-hour deferral for this exact version
  fingerprint into the current user's XDG State folder:
  \`~/.local/state/post-apollo/update-offer-deferrals.json\` by default.
  Stored with private permissions and an atomic rename. If the offer changes,
  a new fingerprint can be offered.

The **history record is not an authorization token**. Buttons are enabled
only for offers in the current session's private scanner map; every terminal
review rechecks the OS or Git source and refuses stale fingerprints.
Source IDs and arbitrary history text are never executed as commands.

Actions do not fire automatically from popups, refresh loops, DND or
snooze changes.

## What Apply does and does not do

| Source | After separate typed APPLY |
|---|---|
| Silverblue, update available | \`rpm-ostree upgrade\` stages deployment. A later reboot must be initiated separately. |
| Silverblue, already staged | Read-only review; **no reboot and no extra update**. |
| Oh My Zsh | Runs the installed official \`tools/upgrade.sh\`, only if checkout has no local changes. |
| Powerlevel10k | \`git pull --ff-only\` on recognized checkout, only if local working tree is clean. Restart Zsh afterward. |
| Flatpak (user/system) | Review terminal requires typed DOWNLOAD for download-only or typed APPLY to deploy pinned commits. |
| Firmware | OPEN UPDATES opens GNOME Software/fwupd; Post-Apollo does not install firmware. |

No arbitrary command from a notification, auto-reboot, forced Git update,
automatic configuration change, or background elevation exists here.

**NOT NOW only changes Post-Apollo's offer cadence.** It does not disable
GNOME Software, \`rpm-ostreed-automatic\`, a pre-existing Oh My Zsh auto-update
mode, a systemd timer or any other package manager. Automatic system update
policies must be reviewed separately when a unified approval-only mode is
desired.

## Read-only operator preflight

\`\`\`bash
cd ~/.config/quickshell
python3 scripts/updates/update_offers.py scan
rpm-ostree status
git -C ~/.oh-my-zsh status --short
\`\`\`

## Dedicated Sway + Kitty + Zellij reviewer

Update REVIEW / DOWNLOAD now invokes `scripts/updates/launch_review.py` instead
of opening an undifferentiated Kitty window. It gives Kitty a unique Wayland
app-id `post-apollo-update-review`; a bounded Sway tree lookup matches that
**specific Kitty PID**, floats it, gives it a 2px border, sizes it to 900x580,
and centers it. No permanent Sway rule or global desktop reconfiguration is
made, and a failed Sway placement does not block reviewing the update.

When the dedicated, opt-in Zellij 0.45 header plugin is installed, Kitty runs
an isolated **Zellij session with two panes**: a magenta one-line Post-Apollo
header (including a top-right red **×**) and the existing Python update
reviewer. This is not your main Kitty/Zellij session.

**One-time setup after syncing this repository:**

```bash
cd ~/.config/quickshell
bash scripts/updates/zellij/build_header.sh
python3 tests/notifications/test_update_review_window.py
```

The build script requires existing `cargo` and `rustup` tools, installs
the WASI target, compiles the pinned Zellij 0.45 plugin, and copies only the
compiled `.wasm` to
`~/.local/share/post-apollo/zellij/post_apollo_update_header.wasm`
(or your `XDG_DATA_HOME`). It **never** runs automatically from a notification.
If Zellij or the compiled header is unavailable, the old Kitty terminal
remains accessible with `--hold`, still Sway-positioned, but without a
fake/nonworking custom X.

**Clicking × detaches the entire dedicated Zellij session.** The Kitty window
disappears, but any in-progress download/install continues safely in the
detached session. Zellij may ask once to grant this plugin only
`ChangeApplicationState` permission; without it the X is grey/disabled.
It has no permission to run shell commands or read pane contents.

Recover detached sessions with `zellij list-sessions` and
`zellij attach SESSION_NAME`. The update session names begin with
`apollo-updates-`. To avoid accidentally launching two write operations,
the update script also holds a per-source filesystem lock **only while an
approved updater is actually running**. A second updater for that source
refuses to start. Do not `zellij kill-sessions` during a live update.

The one-row Zellij header is an actual WebAssembly plugin; it is not a
faked terminal printout. The Sway window placement is a separate concern
and is not controlled by the plugin. There is no automatic reboot or
automatic update approval. Exited update-review sessions have session
resurrection disabled, so stale updater commands are not re-created.

## Acceptance limits

CI uses fabricated Silverblue status/available-update and Git remote responses.
It checks that declined reviews never run updater commands and that even an
accepted review stages the OS without reboot. That is **not** a claim of a
successful machine-specific update or desktop popups.

For live acceptance, first verify that available offers are correct, the
buttons display and stay interactive in Notifications Hub, NOT NOW defers one
fingerprint for 24 hours, REVIEW opens the intended terminal, and a canceled
review performs no action. Do not deliberately corrupt the OS or shell to
force an update alert.
