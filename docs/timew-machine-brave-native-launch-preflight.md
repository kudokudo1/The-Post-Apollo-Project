# MACHINE // Read-only native Brave launch preflight

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session recovery  
**STAFF ROLE:** External DOC (Hospital-compatible, live registration not verified)  
**ASSIGNMENT:** Prevent accidental use of the ordinary Brave profile during the proposed disposable native-host trial  
**STATE:** Repository-only review candidate; no local activation

## Fundamental mechanism

Brave keeps browser state in a **user data directory**: profiles, extension
state, local session records and cookies. Chromium supports the
\`--user-data-dir=/some/path\` command-line switch to select a different user
data directory. This mechanism is distinct from simply opening a different
window in an existing browser. A native messaging host manifests under a
browser-specific NativeMessagingHosts directory, but Brave packaging and the
actual resolution of a custom profile must be verified on the user's computer.

The project already has a disposable profile preflight in
\`MachineBraveDisposableTrial.py\`, merged in PR #1702, with partial-write
hardening from #1706. The new \`MachineBraveTrialLaunchPlan.py\` is a **pure
launch proposal**. It does not launch Brave, mutate paths, install
extensions/hosts, or inspect normal browser sessions.

It checks:
- Root is an existing marked, private, same-user temporary trial directly
  under /tmp, using the existing strict trial validator.
- Candidate binary is an absolute, executable, existing regular file with a
  native Brave executable name. Symlinks are resolved and target names must
  still resemble Brave. This is **not** vendor authenticity or package signing.
- Executable cannot be within the temporary profile itself.
- Output is only an argv array: executable,
  \`--user-data-dir=<trial_root>/profile\`,
  \`--no-first-run\`, \`--no-default-browser-check\`.

Every authority/observed-runtime field is false; status is
\`operator_review_required\`. This plan does not promise the command will
run, the CLI flags will be honored, the executable is genuine Brave, or
the native host will be discovered.

## HOW TO USE (only after local approval)

First inspect the installed browser package, e.g. from a terminal:

\`\`\`sh
command -v brave-browser || command -v brave-browser-stable || command -v brave
flatpak info com.brave.Browser
\`\`\`

These are read-only checks. They do **not** say which variant is active
if both are installed. For Flatpak, this planner intentionally refuses
the \`flatpak\` wrapper; determine the permitted sandbox file access and
launch semantics separately. Do not improvise a host installation in the
normal profile.

Only after explicitly authorized initialization of an empty trial root:

\`\`\`sh
python3 -B -I services/time/MachineBraveTrialLaunchPlan.py plan \
  '<trial_root>' '<absolute_native_brave_executable>'
\`\`\`

This prints **candidate_argv**. It does not run it. An operator must inspect
the executable, temporary path, and exact command before separately
approving a browser launch.

For a separately approved launch using that command, immediately open
\`brave://version\` and inspect the **Profile Path**. It must begin with the
returned temporary \`expected_profile_path_prefix\`. If the browser window
has the everyday Profile Path, STOP without loading any extension or
granting nativeMessaging. The test extension is loaded only into the
verified disposable profile via \`brave://extensions\` → Developer mode →
Load unpacked, from the approved repository checkout.

After recording the temporary profile's extension ID, the existing
\`MachineBraveDisposableTrial.py register ROOT EXTENSION_ID\` can create
the temporary native-host manifest under the trial. Use its \`verify\`
command for read-only manifest verification. Only then, and with separate
approval, use the test extension's **ALLOW LOCAL CONNECTION** →
**TEST CONNECTION ONCE** → **REVOKE LOCAL PERMISSION** controls.

Never register an experimental native host to
\`~/.config/BraveSoftware/Brave-Browser\` to make a disposable trial work.
Closing a test browser is not cleanup of its local profile contents;
delete a verified trial directory only after separate operator approval.

## VERIFY / WATCH OUT FOR

The automated test creates a fake named executable in a throwaway CI
directory but NEVER executes it. It rejects relative, missing,
non-executable, misleading-symlink, wrong-name, non-temp and
inside-trial paths. It verifies the output contains no debugging port,
tab/session payload or RESTORE authority; native extension permissions
and TimeW integration are unchanged.

This does **not** prove actual Fedora/SwayPX or Brave runtime isolation.
The independent Brave profile path check in \`brave://version\` is a
mandatory gate. A browser extension's ID may change across installations.
Native messaging transport success does not prove a Brave/Sway window
binding or permit tab/session capture.

External references:
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging

## DECISIONS

Repository-only read-only preflight. No live browser, host, checkpoint,
window or app manipulation. Keep PR draft until CI and independent review;
do not merge or activate without the operator's decision.
