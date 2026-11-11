# MACHINE // Read-only native Brave launch preflight

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session recovery  
**STAFF ROLE:** External DOC (Hospital-compatible, live registration not verified)  
**ASSIGNMENT:** Prevent accidental registration or launch in the ordinary Brave profile  
**STATE:** Repository patch, no local activation

## Mechanism and live evidence

Brave stores browser data in a user-data directory. The `--user-data-dir`
switch isolates browser tabs, profile and extensions from the ordinary
Brave session.

**Native-messaging host registration follows a different Linux path.**
During the operator's native RPM Brave 1.94.121 test:
- The disposable browser profile path was verified in `brave://version`.
- A manifest under `<trial>/profile/NativeMessagingHosts` was
  *not* discovered; Brave logged "Can't find manifest".
- A manifest under
  `<trial>/xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts`
  **was** discovered after launching Brave with the environment variable
  `XDG_CONFIG_HOME=<trial>/xdg-config` scoped to that process.
- The extension successfully reported LOCAL TRANSPORT OBSERVED.

That is one real transport result, **not** authenticated browser-to-Sway
window identity, permission for tabs, or RESTORE authority.

## Implementation

`MachineBraveDisposableTrial.py init` creates a private, marked root
directly under /tmp with two separate 0700 directories:

- `profile/` for the browser's session, extension and tab state
- `xdg-config/` for isolated Linux configuration and native host manifest

`MachineBraveTrialLaunchPlan.py plan ROOT BINARY` is **read-only**.
It validates the existing marked root and native Brave executable shape,
then prints:
- `candidate_argv`: executable, `--user-data-dir=ROOT/profile`,
  `--no-first-run`, `--no-default-browser-check`
- `environment_overrides`: `XDG_CONFIG_HOME=ROOT/xdg-config`
- `expected_native_host_manifest`: exact path below
  `ROOT/xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts`
- The manual `brave://version` profile path verification gate

This does **not** launch Brave, execute host commands, install anything,
or change the current shell's environment. An executable filename alone
is never proof of vendor authenticity.

## HOW TO USE (separate operator approval required for local writes)

Before creating a test profile, check which Brave package is installed:

```sh
command -v brave-browser || command -v brave-browser-stable || command -v brave
flatpak info com.brave.Browser
```

Native Brave only. Flatpak browser paths remain unsupported.

Following separately authorized `init` and its recorded ROOT:

```sh
python3 -B -I services/time/MachineBraveTrialLaunchPlan.py plan \
  '<trial_root>' '/usr/bin/brave-browser'
```

Inspect both candidate_argv and environment_overrides. Launching the
browser is a **separate** operator action, using exactly the approved
process-local XDG_CONFIG_HOME and user-data directory. Do **not** run
`export XDG_CONFIG_HOME=...` in your normal interactive session.

In `brave://version`, Profile Path must begin with
`<trial_root>/profile/`. Abort if it shows the ordinary browser profile.

Within the disposable browser, use `brave://extensions` → Developer mode
→ Load unpacked → `integrations/machine/brave-topology/`. Use its
exact 32-letter ID for `MachineBraveDisposableTrial.py register ROOT ID`,
then `verify ROOT`. It must verify the isolated XDG native host manifest.
Only then, with explicit approval, use the test extension's ALLOW LOCAL
CONNECTION, TEST CONNECTION ONCE, REVOKE LOCAL PERMISSION controls.

Do not put a test manifest under
`~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts`. Do not
modify ordinary Brave or disable SELinux. Closing the disposable browser
does not itself delete its private data; cleanup requires a separate
operator-approved action on the exact marked trial path.

## VERIFY / WATCH OUT FOR

CI uses a fake, **never-executed** Brave executable and private /tmp
fixtures. It asserts that the preview includes XDG_CONFIG_HOME and that
the host manifest path is inside the same marked trial. It also verifies
no browser launch or profile data mutation from this command.

Real Fedora transport success is evidenced by the operator's earlier
manual test, not repeated by CI. Neither a successful preview nor a
native-messaging roundtrip can authenticate which Brave tab/window
belongs to which SwayPX container.

References:
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md

## DECISIONS

Repository-only repair. Remains subject to independent review and
operator merge approval. No workstation changes or production activation.
