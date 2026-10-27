# Social browser identity profiles // staged isolation boundary

**Status:** source implementation awaiting integration review. This document describes code behavior, not live session switching or browser authentication.

## What is implemented

The existing `XBrowser.py show|hide|status|setup` commands **without** `--identity` retain the exact current per-site Chromium profile paths, XWayland window classes, and Sway behavior. No legacy profile is copied, renamed, moved, deleted, or relabeled as a particular Post-Apollo identity.

A validated stable identity ID such as `identity-2` now has a distinct, deterministically derived browser profile path and XWayland class for **each** already-supported browser site:

- Native Chromium data root: `$XDG_DATA_HOME/post-apollo/identities/identity-2/x-browser` for X (and the existing distinct leaf for each other site).
- Flatpak browser data root: `~/.var/app/<browser-app-id>/data/post-apollo/identities/identity-2/x-browser`.
- Scoped XWayland class: `post-apollo-x-identity-2` (versus legacy `post-apollo-x`).
- `python3 widgets/messanger/XBrowser.py profile x --identity identity-2` returns a **read-only** JSON plan with `status: GEOMETRY_INTEGRATION_PENDING`, `authenticated: null`, `launchAvailable: false`, and `migrationPerformed: false`.

The plan does **not** inspect cookies, infer login state, create a directory, start Chromium, or change Sway. Unknown, malformed or path-like identity IDs are rejected.

Scoped **show/setup are deliberately refused** until all downstream window-geometry and transition requirements below are fulfilled. Scoped status and hide are exact-class operations only. This avoids the dangerous half-integration in which an isolated disk profile still binds to another identity's already-running window.

## Why this is not yet identity switching

`DiscordGeometry.py` currently recognizes the legacy `post-apollo-<site>` classes, and `MessagingW.qml` launches browsers without passing an identity ID. Both are intentionally untouched in this slice. Merely mapping a new profile path cannot safely switch live accounts: Sway focus, dock, hide, and the shared Social window need coordinated changes, with real browser behavior validated.

The separately owned `SocialIdentityStore.selectIdentity()` still changes **layout only**. The `SocialAccountDetailsStore` account label is never treated as proof of login or the active session. Telegram, Sessions and Vesktop are not changed.

## Activation gates for a later operator-approved integration

1. Teach the shared geometry helper to track exactly one `(site, identityId)` window class, with window `con_id` validation; no general substring matching.
2. Pin the *confirmed saved* active identity to the browser launch/dock, hide previous identity windows before revealing the target, and fail closed on unknown/in-flight storage state or stale process replies.
3. Prepare only the new scoped profile directory with owner-only permissions and reject symbolic links; **never** automatically import/copy old Chromium cookies.
4. Treat each new profile as signed-out/unknown until the user signs in through the provider site. Do not accept an account nickname as authenticated evidence.
5. Run synthetic cross-identity, Sway/XWayland and actual desktop focus/close/reopen tests before enabling scoped `show` or account switching.

**Rollback:** do not activate this optional scoped mode; legacy `show|hide|status|setup` and previously used profile directories behave exactly as before. No desktop files have been touched by this branch. Any future rollout needs an explicit operator decision about the legacy profile's ownership.

**Ownership:** GitHub source branch only; Hospital-compatible external contribution, not a registered Hospital Room or live Session.
