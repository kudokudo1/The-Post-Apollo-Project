# MACHINE // Brave optional native-messaging connection (transport probe)

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** TimeW MACHINE / future browser session recovery  
**ROLE:** External Hospital-compatible DOC; not registered in live Hospital  
**PREDECESSORS:** #1674 Brave zero-required-permission window inventory;
#1679 read-only Sway focus witness, both merged  
**STATE:** GitHub draft; no local installation, no authority to restore

## Fundamental mechanism

Chromium/Brave extension code runs inside Brave. Linux native-messaging
hosts run as separate local programs. An extension with `nativeMessaging`
permission can ask the browser to launch a registered host and exchange
JSON messages through the host's stdin/stdout. Each JSON payload is
preceded by a four-byte unsigned integer length in native byte order.

A **successful exchange** means only that a message reached a local
process and a framed response came back. It does **not** certify
the extension's privilege against arbitrary local processes, the native
browser window that initiated the call, the same-window correspondence
to a Sway client, a persistent tab session or permission to RESTORE.

Chrome documents both optional API permission requests and native
messaging's host/allowed-origin contract:
- https://developer.chrome.com/docs/extensions/reference/api/permissions
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- https://chromium.googlesource.com/chromium/src/+/main/extensions/docs/security_faq.md

Chromium's security FAQ explicitly warns that native messaging is not
itself a secure communication channel. The extension origin supplied to
the host on Linux does not provide the calling native window handle.

## Implementation

**Existing extension retained:** `integrations/machine/brave-topology`

- `manifest.json` still has `permissions=[]`,
  `host_permissions=[]`, `incognito=not_allowed`. It now declares
  exactly one `optional_permissions`: `nativeMessaging`.
- The original window inventory continues to work independently with
  no host or permission. No background worker, site content scripts,
  browser history, tab URL/title access, automatic host calls or storage.
- The popup adds explicit:
  - **ALLOW LOCAL CONNECTION:** requests nativeMessaging permission
    during a click gesture. Granting permission launches **nothing**.
  - **TEST CONNECTION ONCE:** checks permission first, then sends only
    a fresh random UUID challenge and a fixed request kind.
  - **REVOKE LOCAL PERMISSION:** asks Brave to remove nativeMessaging.
    Revocation does not itself unregister an installed local host; these
    are separate controls. The extension cannot guarantee a new browser
    permission prompt if a permission is granted again later.
- All status messages make explicit that even a successful test
  leaves browser/Sway window identity unverified. On failure the UI
  reports a generic bounded state and does not print native-host paths,
  private notes or browser error details.

**Native host:** `services/time/MachineBraveNativeProbe.py`

- One-shot native-framed JSON read; max inbound/outbound payload 4096 bytes.
- Only action: `machine-brave-native-transport-request-v1` with one
  canonical UUID. Unknown keys, tabs, URLs, PIDs, window identities,
  commands, actions and oversized/truncated/malformed JSON are rejected.
- Replies with the nonce, `transport_observed`, and every authority bit
  set false: extension-origin authenticated, browser/Sway binding,
  incognito exclusion, session identity, capture and RESTORE.
- No Sway IPC, subprocess, filesystem read/write, Python imports from
  the machine checkpoint database, network access or background loop.
- The caller-origin argv is syntax checked but **not** treated as a
  security authentication signal; physically local processes could
  spoof it. The independently installed native-host manifest must
  restrict the expected browser extension ID, but even this does not
  provide application-window binding or local-process authentication.

**Host manifest preview:** `services/time/MachineBraveNativeManifest.py`

- Outputs, on stdout only, the standard native host manifest with an
  exact `allowed_origins` entry for an operator-supplied 32-letter
  Brave extension ID, plus an absolute path to the host executable.
- No wildcard origins, registry changes or filesystem writes.
- No host manifest is included in an installable location by this PR.
  Actual install needs a reviewed real extension ID, browser-specific
  Linux host-registration directory, executable permission on the
  target host, and explicit operator permission. These values are not
  invented by the repository.
- Even when installed, this restricted host is intentionally
  *transport-only*. It is not a conduit to the existing Sway witness.

## VERIFY

`test_machine_brave_native_probe.py` launches the actual Python host
under `python3 -B -I` with Chrome-compatible native message framing,
temporary XDG home and no compositor socket. It checks valid response,
nonce, rejection of secret fields, forged origin formats, second-origin
non-authentication, oversize/truncated/invalid payloads and no SQLite.

`test_machine_brave_native_probe.mjs` checks that the JS projection
rejects unverified host claims, forged session/window identity,
wrong nonces and extra private fields.

`test_machine_brave_native_manifest.py` verifies one exact allowed
origin, strict host path, output-only preview and no file installation.

`test_machine_brave_native_probe_contract.py` asserts zero required
extension permissions, optional-only nativeMessaging, explicit button
events, no host activity from the window-inventory module, no new
TimeW QML process, and no host ability to capture or restore.

Existing Brave inventory, Sway focus witness, M2b-M2d2 and v1/v2
checkpoint tests remain in scope. These are **source and disposable
synthetic tests**. The actual Fedora/Brave runtime connection has not
been tested or installed.

## WATCH OUT FOR / NEXT

1. Do not interpret transport success as an identity certificate.
   A user click does not prove an OS window handle either.
2. Independently review the host implementation, optional permission
   UX, browser ID, and exact Brave native-host registration path.
3. Operator specifically approves and performs any local install,
   executable permission change or extension reload. None here.
4. Validate the real connection with a disposable test profile first.
5. Design authenticated browser-to-host *per-window* association in a
   separate security milestone; current Sway focus remains evidence
   only. No app/window move on ambiguous or unverified identity.
6. Separately obtain consent for sensitive tab/session descriptors,
   secure local retention and safe reconstruction. This feature
   does not save any tabs or issue RESTORE.
7. Do not merge or activate this draft without the required review.

**No user Brave profile, local desktop, existing checkpoint, native
host registration, browser session, Sway window or Quickshell process
was modified by this repository implementation.**
