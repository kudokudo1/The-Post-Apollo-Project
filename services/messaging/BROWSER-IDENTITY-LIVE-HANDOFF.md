# Social browser identity handoff // opt-in runtime slice

**Implementation stage:** Browser-only session switching behind an explicit Settings toggle. This does not apply to Telegram, Discord/Vesktop, native Sessions, or provider authentication APIs.

## How it works
- The current contact/chat Settings workspace gains **USE ISOLATED BROWSERS**. This is OFF by default and holds state for the current Quickshell session only. When OFF, all prior service-specific browser profiles, Sway window classes and launch commands remain in use.
- When ON, the selected *saved* Post-Apollo layout identity is the source of the browser namespace. New Chromium profile directories use `post-apollo/identities/identity-N/<site>-browser`. These start signed out. A legacy profile is never assigned to `identity-1`, copied, moved or deleted automatically.
- Selecting a different identity in Settings waits for the single-writer store's confirmed save. Only then is the old identity's browser window hidden and the new identity bound. Nothing is revealed on top of Settings; after the editor closes, the chosen browser site opens in that identity's isolated profile.
- The browser launcher acquires an owner-only runtime selection marker with an unpredictable token and checks it before every Sway reveal. It hides other Post-Apollo managed browser windows by exact `con_id`, without logging out or killing their processes. Distinct identities use separate window classes.
- New profile directories are created only after explicit activation. Symlinks or insecure identity folders are refused; all newly created profile folders use owner-only mode. Flatpak profile roots stay within the browser sandbox data root.
- The bridge uses an exact scoped `site + identity + class + con_id` match at both queueing and actual command execution; it still refuses cross-identity commands and shared Social fast-follow in scoped mode. Settings and the original provider navigation remain unchanged.

## Known limitations / live acceptance gates
- Browser authentication continues to belong to each provider website. A saved account nickname is not proof of login.
- On first activation a fresh profile is empty; the operator signs in separately. LINE Chrome extension setup for a scoped profile remains blocked pending its own supported install flow.
- Scoped docking sync is guarded, but fast-follow of user-driven browser movement remains disabled until verified in live Sway. This is an intentionally limited initial handoff, not full feature parity with legacy motion.
- A browser process may map slowly after a canceled launch. Token checks prevent an old request from *revealing* the window, but real desktop testing should verify that a late native map cannot briefly occupy the wrong workspace. Do not activate in production without this check.
- Owner approval is required to merge/deploy this branch and run Quickshell/Sway tests. No credentials, profiles or running windows were modified during repository implementation.

## Rollback
In Settings, choose **USE LEGACY BROWSERS** and close Settings. This stops selecting scoped browser windows in the current runtime. Existing directories and login state are never erased. Alternatively leave the new feature unmerged and the current launch remains identical.

## Next
After live acceptance: add a verified scoped fast-follow handoff (if desired), recover across restarted Quickshell sessions with an operator-approved preference, separate Telegram multi-session handling, and explicit login/reconnection status.

Hospital-compatible external change. No registered Room, no production actuation.
