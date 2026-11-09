# MACHINE // Disposable Brave native-host transport experiment

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session recovery  
**STAFF ROLE:** DOC (external Hospital-compatible; live registration not verified)  
**ASSIGNMENT:** Prepare reversible disposable-profile native host test while protecting the real Fedora/Brave profile  
**STATE:** Repository implementation and isolated CI only; no local activation

## Mechanism and isolation

On Linux, Chromium resolves user-level native-messaging hosts under the
selected **browser user-data directory** in NativeMessagingHosts. Overriding
that directory with --user-data-dir is supported by Chromium. Brave is
Chromium-based but actual Brave packaging, command and Fedora/SwayPX behavior
must still be checked on the operator's workstation.

References:
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/common/chrome_paths.cc
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md

The repository adds services/time/MachineBraveDisposableTrial.py with three
strict, explicit commands:

- init: create a brand-new private postapollo-machine-brave-trial-* directory
  in the current OS temporary directory; a fresh profile/ subdirectory and
  a tiny UUID marker. Does not launch Brave or install anything.
- register ROOT EXTENSION_ID: accept only a marked root directly under the
  OS temporary directory, owned by the invoking user and private (0700).
  Copy ONLY the source-reviewed transport-only MachineBraveNativeProbe.py
  into the trial root as an executable, and write ONLY an exact-origin JSON
  host manifest into ROOT/profile/NativeMessagingHosts. Refuses existing
  registrations, invalid IDs, symlinks, unexpected paths and overwrites.
- verify ROOT: read-only validation of exact host source bytes, executable
  mode, generated manifest path, single allowed extension origin, and
  private directories. Never starts a process or tests native messaging.

No ~/.config/BraveSoftware, XDG desktop configuration, original browser
profiles, TimeW checkpoints or Sway windows are touched by these routines.
They do not run under sudo or write to any system registration folder.
No routine performs cleanup/deletion of the trial profile; closing the
browser and removing a trial after review requires separate operator
approval and an explicit path check.

## HOW TO USE (future operator-approved local experiment)

**Approval gate:** These commands perform local filesystem writes.
Do not run on the operator's machine until specifically approved for this
disposable experiment, and confirm current repo checkout/working tree first.

From an approved checkout of the tested revision:

1. Run python3 -B -I services/time/MachineBraveDisposableTrial.py init
   and record the exact returned trial_root and brave_user_data_dir.
2. Identify the real installed Brave executable. Start a *separate* Brave
   process with --user-data-dir=<the returned brave_user_data_dir>.
   Confirm in brave://version that its profile directory belongs under
   that exact temporary path. STOP if it shows the everyday profile.
3. In the disposable Brave only, open brave://extensions, enable Developer
   mode and choose Load unpacked for
   integrations/machine/brave-topology/ in the approved repository checkout.
   Record the 32-letter extension ID from this **disposable** instance.
4. Run python3 -B -I services/time/MachineBraveDisposableTrial.py register
   <trial_root> <extension_id>, then run its verify command on the same
   root. Neither command launches Brave or grants permission.
5. In that trial extension popup, click ALLOW LOCAL CONNECTION, then
   TEST CONNECTION ONCE. Record only success/failure status, never tabs,
   URLs or titles. REVOKE LOCAL PERMISSION after the test.
6. Close the disposable Brave instance. Its trial directory may contain
   browser history after use, so treat it as private. Review and authorize
   removal of ONLY that verified trial path separately. Do not remove the
   normal Brave profile or invoke arbitrary recursive cleanup.

If the trial uses a sandboxed/Flatpak Brave, host visibility and
--user-data-dir behavior must be verified independently; the process may
not see an external repo or temporary host executable. Stop rather than
installing a host into the normal profile to work around it.

## ACCEPTANCE / FAILURE RULES

- Registration preflight PASS means only the temporary manifest and
  transport host have the expected bytes/permissions. It is NOT a real
  browser/host roundtrip.
- LOCAL TRANSPORT OBSERVED means only a challenge was sent and the host
  replied. It is NOT a verified Brave/Sway window pair.
- Browser/OS focus correlation from #1690 is still unverified diagnostic
  evidence, NOT an OS handle, private-window proof or restore authority.
- If a profile path is not temporary, native host cannot be found, extension
  ID changes, two instances share a profile, a browser starts on the normal
  profile, or any private-window ambiguity occurs: abort.
- No browser data, tab sessions, snapshots, credentials, network services,
  checkpoint revisions, window moves, app relaunch, or RESTORE actions.
- Consent for later sensitive tab/session metadata is a separate gate.

## Tests

CI exercises a *real private temporary filesystem* with init, register and
verify; safe rejection of bogus extension IDs, preexisting paths, bad markers,
symlinks, duplicate registration, tampered host and manifest; and a separate
Python -B -I CLI subprocess roundtrip. It checks unchanged Brave manifest,
native host and TimeW QML constraints.

This is a **file-system experiment in a disposable CI directory**, not a
live Brave extension load or native-messaging roundtrip on Fedora/SwayPX.

## DECISIONS

The tool never implicitly acts on the real browser or machine. The current
development assignment remains MACHINE; all local writes, Brave startup,
extension installation, production activation, cleanup and final acceptance
remain separately operator-controlled. A diagnostic success grants no
pairing/session restoration permission.
