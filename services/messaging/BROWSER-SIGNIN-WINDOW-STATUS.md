# Social browser sign-in window checks // initial recovery surface

**Status:** Proposed, browser-only, provider-owned manual sign-in. This is not an authentication API or an account-verification service.

## What the new Settings controls mean

Under **Social → USER // SETTINGS → LINKED ACCOUNTS**, select a supported browser-backed service while **USE ISOLATED BROWSERS** is active.

- **CHECK WINDOW** calls the read-only `XBrowser.py inspect <site> --identity <identity-N>` command. It inspects only Sway's exact XWayland class and validated container ID. The result distinguishes `NOT_OPEN`, `OPEN_VISIBLE`, `OPEN_HIDDEN`, `AMBIGUOUS_WINDOW`, and `UNVERIFIED_WINDOW`. Failure is displayed as unavailable.
- Every result explicitly says **SIGN-IN UNKNOWN**. An open window, existing Chromium profile, account nickname, or saved email/phone number does **not** prove a successful or unexpired website login.
- **OPEN SIGN-IN WINDOW** closes Settings and routes the selected browser-backed app through the existing `MessagingW.activateApp(index)` and isolated `XBrowser.py show --identity` path. The actual website owns credentials, two-factor prompts, login, expiry and any interactive reconnection. No cookie is read, copied, or deleted.
- An inspection is manual, not a continuously refreshed provider login monitor. A result belongs to its exact selected service and saved identity; stale subprocess output after selection changes or editor close is ignored.
- Unsupported/native providers such as Telegram, Sessions and Vesktop do not offer this browser action. Their authentication remains separate.

## What stays unchanged

The current contact/chat Settings layout, all 32 stable app service IDs, the left-rail preview, browser profile isolation, no automatic legacy-profile migration, Telegram, Vesktop and native adapters are unchanged. Isolated browser mode remains off by default and is still scoped to the current Quickshell session.

## Recovery and limits

1. Select a saved Post-Apollo identity and opt into isolated browsers if desired.
2. Select a browser-backed service in Linked Accounts.
3. **CHECK WINDOW** distinguishes a hidden browser from one that has not mapped. It cannot diagnose provider login expiry.
4. **OPEN SIGN-IN WINDOW** lets the operator interact directly with the provider's existing website sign-in and reconnect flow, without a forced logout, profile reset or automated credential exchange.

The status may be stale until checked again. An ambiguous or unverified window remains a blocked/unknown diagnostic, not permission to attach. Real Sway focus, delayed browser mapping, and provider login must still be accepted in a live desktop run.

## Verification and rollback

Run `python3 -m unittest discover -s tests/messaging -p 'test_social_browser_signin_window.py' -v` and the existing Social browser, geometry, identity and settings regression suites. The added diagnostic is read-only, and the action reuses the existing launch path; rollback is omitting this PR. No migration or stored authentication status exists.

**Hospital-compatible external repository work:** not a registered Room, Assignment, or deployed desktop change.
