# MACHINE // Disposable Brave transport trial, isolated XDG registration

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session recovery  
**STAFF ROLE:** DOC (Hospital-compatible, live registration unverified)  
**PHASE:** Correct disposable native-host registration after operator's Fedora/Brave proof  
**STATE:** Repository-only patch; no local activation or production host registration

## Mechanism and observed defect

Brave's browser data directory (selected by \`--user-data-dir\`) holds the
test profile and extension. **Native host manifests are resolved using a
different Linux configuration directory**. In the operator's native RPM
Brave 1.94.121 test:

1. \`/tmp/postapollo-machine-brave-trial-*/profile/Default\` was correctly
   used as the disposable browser profile.
2. The original repository tool registered
   \`profile/NativeMessagingHosts/org.postapollo.machine_brave_probe.json\`.
   Brave logged \`Can't find manifest for native messaging host ...\`.
3. The host independently executed and returned a valid nonce/response.
   SELinux was enforcing and no relevant AVC denial was observed, but the
   decisive browser error was a missing manifest.
4. The operator created a host registration under
   \`<trial>/xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts/\`
   and launched Brave with
   \`XDG_CONFIG_HOME=<trial>/xdg-config\`.
5. The extension reported
   **LOCAL TRANSPORT OBSERVED // WINDOW IDENTITY NOT VERIFIED**.

This proves a *single isolated transport roundtrip* on that Fedora/Brave
instance. It does not prove authenticated extension or process identity,
a reliable Brave-to-Sway mapping, tab capture, or ability to RESTORE.

Upstream background:
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md

## Implementation

\`services/time/MachineBraveDisposableTrial.py\` retains three operations:

- **init:** privately creates a fresh marked root directly under \`/tmp\`,
  a \`profile/\` for browser state, and a separate private \`xdg-config/\`.
  It ignores caller \`TMPDIR\` and never starts Brave.
- **register ROOT ID:** copies the unchanged transport-only Python probe
  into ROOT and writes an exact-origin manifest to
  \`ROOT/xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts/\`.
  Creates only missing, 0700, same-user, non-symlink subdirectories
  below the marked root. An existing private BraveSoftware path is
  allowed because Brave may create it before the ID is known.
  Refuses invalid IDs, non-trial roots, preexisting host registration,
  non-private folders, and symlinks. It does not write into
  \`ROOT/profile/NativeMessagingHosts/\` or the ordinary home profile.
- **verify ROOT:** reads the exact host bytes, executable permission,
  manifest path, one allowed extension origin, and private directory
  ownership/modes. Never starts a program or claims a browser roundtrip.

\`MachineBraveTrialLaunchPlan.py plan ROOT BINARY\` remains **read-only**.
It outputs the operator-reviewed Brave command *and*
\`environment_overrides.XDG_CONFIG_HOME\` pointing at the same marked
trial's \`xdg-config\`. It never launches Brave, installs an extension,
changes login settings, or grants optional nativeMessaging permission.

## HOW TO USE // Future separately approved operator trial

Repository source checks, **before any local mutations**:

\`\`\`bash
git status --short
python3 -B -I services/time/MachineBraveDisposableTrial.py init
\`\`\`

The \`init\` operation creates files; execute it **only after the
operator has separately authorized a disposable local trial**. Record the
returned \`trial_root\`, \`brave_user_data_dir\`, and
\`brave_xdg_config_home\`. Then:

1. \`python3 -B -I services/time/MachineBraveTrialLaunchPlan.py plan '<trial_root>' /usr/bin/brave-browser\`.
   Inspect the exact \`candidate_argv\` and
   \`environment_overrides.XDG_CONFIG_HOME\`. The plan does not start Brave.
2. With separate permission, launch only the test browser using the
   specified user-data directory and **process-local XDG_CONFIG_HOME**.
   Do not export XDG_CONFIG_HOME globally in the shell or change it for
   the user's normal desktop.
3. Confirm in \`brave://version\` that Profile Path begins with the
   temporary \`<trial_root>/profile/\` path. Stop if it uses ordinary Brave.
4. Within that test profile only, open \`brave://extensions\` → Developer
   mode → Load unpacked. Choose
   \`integrations/machine/brave-topology\`, NOT the temporary profile
   directory. Record the exact 32-letter ID of **Post-Apollo MACHINE**.
5. Run \`python3 -B -I services/time/MachineBraveDisposableTrial.py
   register '<trial_root>' '<extension_id>'\` and then
   \`... verify '<trial_root>'\`. Both must report a manifest under the
   *isolated XDG config*, never a normal Brave home or profile directory.
6. From the test extension popup click ALLOW LOCAL CONNECTION, then
   TEST CONNECTION ONCE. The only successful transport result is
   LOCAL TRANSPORT OBSERVED // WINDOW IDENTITY NOT VERIFIED.
   Click REVOKE LOCAL PERMISSION after recording the status.
7. Close the disposable browser. Treat trial contents as private
   browser data; deletion is **not** automatic and requires separate
   operator approval for that exact path.

If an older trial already has the original wrong-path registration,
do **not** blindly run register again or copy manifests into the
normal Brave configuration. Inspect/reconcile the test root separately;
this CLI explicitly refuses overwriting an existing host.

## VERIFY / WATCH OUT FOR

CI uses real \`/tmp\` fixture directories but a fake browser binary that is
never executed. It exercises init/register/verify and a plan read-back,
plus invalid IDs, symlinks, private modes, tampered bytes, duplicate
registration, interrupted writes and rollback.

Those CI checks do **not** repeat the Fedora browser test or validate
per-window identity. A valid manifest path, a successful one-shot local
connection, or A/B/A focus evidence grants **zero** restore authority.
No tabs, URLs, titles, profiles, secrets or page contents are captured.

No native system host installation, Quickshell reload, SELinux policy
change, Brave profile modification, Sway action, checkpoint change or
production activation is authorized by this patch.

## DECISIONS

Keep the corrected registration and launch preflight as one bounded
MACHINE patch. Independent review, CI, merge approval and any additional
local activation remain operator-controlled.
