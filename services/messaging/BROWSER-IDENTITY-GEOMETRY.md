# Social identity-aware Sway geometry: passive bridge

**Status:** Opt-in, passive identity-aware Sway discovery. This does not enable live identity switching, profile migration, authentication, or provider launch.

## Bounded changes
- Geometry now recognizes exactly the `identity-N` IDs and `post-apollo-<site>-identity-N` XWayland classes established in the merged browser profile-boundary PR.
- `snapshot_from_tree(tree, browser_identity_id="identity-2")` discovers only the selected identity's exact browser classes, including hidden scratchpad windows. It includes `conId`, `windowClass`, identity ID, visibility and geometry. Duplicate same-class or invalid/missing container IDs fail closed.
- `sway_criteria` and `build_sync_command` can construct exact `[con_id="N"]` scoped commands for planning; their identity, class and container ID inputs are validated.
- The bridge's optional `mode.browserIdentityId` selects the passive namespace. A changed identity clears browser readiness/docking and stale queued browser/Social geometry. It does not clear Vesktop commands.
- While scoped mode is selected, browser `focusX`, `fast_follow`, and queued browser/Social sync remain disabled. This is discovery, not account activation.

## Compatibility
- Existing host `MessagingW.qml` still sends legacy mode without a browser identity; all legacy site window discovery, browser launch/docking and Vesktop handling remain the default and unchanged.
- The scoped `XBrowser.py show --identity` remains blocked. No profiles are copied, directories prepared, provider sessions read, cookies imported, or local windows launched.
- A saved account nickname is not an authenticated session.

## Verification
Offline tests use synthetic Sway trees and never touch the operator desktop. They exercise exact match, hidden window, ambiguous class, invalid input, change-of-ID invalidation and blocked scoped actuation, plus legacy contracts. CI passing does not certify live Sway and browser focus.

## Next activation gate
Coordinate the saved active identity in the host, scoped browser launcher, and geometry bridge in one separately reviewed change. Verify exact discovered `con_id` before issuing scoped focus/move; guard delayed async replies, prepare owner-only non-symlink profile directories, determine legacy profile ownership explicitly, and validate real Sway hide/show/restore/rollback. Only then enable scoped launch and switching with operator approval.

**Rollback:** leave `browserIdentityId` absent from mode. Existing profiles and sessions remain in their unchanged legacy locations.

**Hospital:** external Hospital-compatible contribution, not a registered live Room, Assignment, or Session.
