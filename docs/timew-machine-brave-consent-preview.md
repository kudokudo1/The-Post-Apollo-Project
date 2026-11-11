# MACHINE // Opt-in current-window Brave tab preview

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser-window continuity after restart  
**STAFF ROLE:** DOC, Hospital-compatible external ChatGPT worker; no verified live Hospital attachment  
**ASSIGNMENT:** Explicit privacy gate before collecting real browser tab metadata, with a redacted one-window preview and revoke control  
**SCOPE:** Disposable Brave extension, relevant permission contracts and tests. No TimeW persistence or restore changes.

## IMPLEMENTATION

After prior live Brave/Sway focus and title-marker tests, and after the
synthetic-only restart recovery plan (PR #1828, on main), actual
per-window tab capture would require viewing real tab addresses.

Chrome/Brave's `tabs` permission can expose **addresses, titles and
favicons for tabs across the browser**, not merely one selected window.
It cannot be described as a per-window permission. This milestone
declares it as **optional** in manifest V3. Version is bumped to 0.4.0;
no required permissions, host permissions, incognito access, background
processes or content scripts are added.

New popup panel: **BROWSER TABS // EXPLICIT PRIVACY GATE**.

1. **ALLOW TAB ADDRESS ACCESS** invokes
   `chrome.permissions.request({permissions:["tabs"]})` only when
   explicitly clicked, within the user gesture. The click does NOT
   read a tab or save a URL. If Brave declines, the review is blocked.
2. **PREVIEW THIS WINDOW ONCE** is a separate explicit click.
   It first checks whether the optional permission is active, then
   verifies the popup's current window is normal and non-private
   *before* requesting its tab metadata. It reads exactly that normal
   window with `chrome.windows.get(id,{populate:true})`.
3. The existing pure `planSyntheticBraveSession` model is reused
   **in memory** to classify each tab by position only:
   `CANDIDATE ONLY`, `REQUIRES SENSITIVE REVIEW`, or
   `NOT ELIGIBLE`. The popup displays aggregate totals and
   classifications, never raw addresses, titles, query strings,
   URL fragments, favicons or tab IDs.
4. After classification the popup rechecks the current browser window
   and permission. If the window changed or permission disappeared,
   the preview is refused. Errors are generic and do not expose raw
   browser metadata.
5. **REVOKE ACTIVE TAB ACCESS** clears the preview and calls
   `chrome.permissions.remove({permissions:["tabs"]})`. It
   verifies the active permission is gone before reporting success.
   Chromium may remember a previous grant for future requests.
6. Any focus loss or popup shutdown clears the preview and invalidates
   pending asynchronous responses. Nothing is persisted, transferred to
   a native host or passed to TimeW SAVE/RESTORE.

**This is not session capture.** The actual address list remains
unavailable after the popup closes. No user records or snapshots
are written to disk. Future durable recovery requires a separately
reviewed storage policy, exact user choice and a protected
read-back/rollback process.

## HOW TO USE

After review and operator authorization for testing this specific
extension change in **disposable Brave only**:

- In test Brave, go to `brave://extensions` and reload the existing
  unpacked Post-Apollo MACHINE extension.
- Open the popup; use **ALLOW TAB ADDRESS ACCESS**. Brave can present
  a broad browsing-data warning because the permission is broad.
- Use **PREVIEW THIS WINDOW ONCE** to see anonymous per-tab
  eligibility categories. It does not save a session.
- Use **REVOKE ACTIVE TAB ACCESS** to remove active permission and
  clear the preview before closing.
- Do not activate this experiment in normal Brave or infer any
  permanent window identity from the anonymous counts.

No native-host reinstall, Quickshell change or SwayPX action needed.

## VERIFY

`test_machine_brave_consent_preview.mjs` uses simulated Chromium
permission/window APIs. It tests no read before consent,
declined and granted prompts, current-window-only read, query-token
redaction, private/popup refusal, focus-loss race, stale native-free
preview, revoke and no persistence. Existing topology, title-marker,
focus and tab-pattern contracts are updated to require *zero* required
permissions and only the two explicitly listed optional capabilities.

CI source and runtime mocks do not prove real Brave OS permission
prompt appearance, physical focus behavior or cross-version support.

Reference: https://developer.chrome.com/docs/extensions/reference/api/permissions
and https://developer.chrome.com/docs/extensions/reference/api/windows

## WATCH OUT FOR

- The `tabs` permission itself is **broad** even though the
  implementation only performs one current-window lookup after click.
  Requesting it may display a permission warning. Permission state can
  persist between popup lifetimes until actively removed.
- Browser `chrome.windows` data is a momentary snapshot. A window can
  change while inspection occurs; post-checks reduce but do not fully
  eliminate such races.
- Classifying an address as `CANDIDATE ONLY` does not establish that
  its path is non-sensitive or safe to store. No addresses are stored
  in this phase, and no automatic RESTORE rights are conferred.
- The separate focus-marker host continues to return temporary
  untrusted IDs. Browser sessions still lack durable protected
  identity or restart-safe cross-monitor association.
- This PR's source change is not itself a browser permission grant.
  Actual local approval is required before reloading a test browser.

## CHECKLIST

- [x] Validate main, staff role, code seam, old tests and Hospital protocols
- [x] Optional address permission behind explicit user click
- [x] Separate read-once current-window eligibility UI
- [x] Redact output, skip private windows, invalidate on focus loss
- [x] Explicit active-permission revocation
- [x] Simulated permission and privacy regression suite
- [ ] Exact-head CI and independent security review
- [ ] Operator acceptance for disposable Brave live test
- [ ] Operator decision on real URL selection/persistence requirements
- [ ] Separate protected durable session store and restore trust design

## NEXT / DECISIONS

Repository-only development in a draft PR. No merge, local changes,
production activation, browser profile modification, native connection
or TimeW SAVE/RESTORE integration is authorized by this checkpoint.
