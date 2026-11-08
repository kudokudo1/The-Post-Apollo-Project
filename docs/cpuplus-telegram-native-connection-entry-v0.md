# CPU++ // Telegram native provider entrypoint

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** CPU++ Connected Accounts / Social secure provider integration (external Hospital-compatible only)  
**ASSIGNMENT:** Add one **working** CPU++ route to the existing Telegram native sign-in and authorized-session check, without inventing a second client or privileges.  
**STAFF ROLE:** External DOC-compatible; no verified live Hospital staff registration.  
**BASE:** `237eda15e8173234883dafdd7cb0d0b64b0b1061`  
**PERMISSIONS:** GitHub-only CPU++/Social navigation/inventory/test/docs. No desktop, keyring or provider-account changes; no shared Connections C4b/C5a host mutation, actual login, production permission grant or merge without separate authorization.

## IMPLEMENTATION

The operator decided that account-name editing **stays in both ID MANAGEMENT and SETTINGS → CONNECTIONS**. Both use the unchanged `CpuPlusIdAccountEditor` and original `SocialAccountDetailsStore`, not two data stores. The red Cancel fix (#1520) is already merged.

This next slice implements an actionable entry for a provider that already has a real native authorization flow: **Telegram**.

1. `services/connections/ConnectionsPolicy.js` exposes a new middle list row **TELEGRAM // NATIVE**, with an honest **CHECK SESSION IN SOCIAL** state rather than claiming the desktop knows current login. It discloses that Telegram is shared by default and private per-identity sessions require separate opt-in in Social. No session state, handle, key, message or credential enters the Connections inventory.
2. `widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml` provides the existing-layout **OPEN TELEGRAM** button only when that provider is selected in the middle bay. It emits a fixed navigation signal, not an arbitrary process/provider command.
3. `widgets/CpuPlusW.qml` passes only that signal when CPU++ SETTINGS → CONNECTIONS is open and Telegram is selected. `shell.qml`, which actually owns both widget instances, requests `MessagingW.openTelegramFromConnections()`, and closes CPU++ **only after** Social accepts the navigation.
4. `widgets/messanger/MessagingW.qml` opens its **existing native Telegram app index 2**, closes the Social settings overlay, and reuses `activateApp(2,false)`. The already-existing Telegram adapter performs its own `health` check and only reports READY after Telethon's `is_user_authorized()`. The actual QR/phone sign-in requires a separate explicit action in the existing in-Social wizard. This route does **not** change private/shared session selection, migrate session files, create a second Telethon client, authorize a company account, or automatically log in.

No new login/logout endpoint exists in CPU++. A checked Telegram session is evidence only for the current Social scope at the moment of that provider's check. A label in ID MANAGEMENT is not provider authentication. Cross-provider **CONNECT ALL** is still blocked on the shared, trusted, consent-grant host.

## HOW TO USE

After operator-authorized merge and separate deployment:

**CPU++ → SETTINGS → CONNECTIONS → middle TELEGRAM // NATIVE → right OPEN TELEGRAM.**

The CPU++ panel closes and the original Social Telegram pane opens. Its adapter checks the current shared/private session. If authorization is needed, choose the pre-existing QR or phone sign-in **inside Social**. Do not type a Telegram password or session token in CPU++. Social's private Telegram identity mode remains opt-in, defaulting to the legacy shared session if not enabled.

Saved account-name add/rename/remove remains accessible in both **ID MANAGEMENT** and **SETTINGS → CONNECTIONS → SOCIAL // IDENTITIES**.

## VERIFY

`tests/cpuplus/test_cpuplus_telegram_connection_entry.cjs` checks the actual fixed navigation chain, real Social native provider index, existing Telegram health/authorized check, stable selected scopes, no duplicate client and no new provider grants. The original C1 Connections inventory test expands from 8 to 9 services. New scoped CI runs Telegram session-isolation, login UI, native adapter, Social status and shared Connections default-deny regressions plus QML parser checks. Exact-head CI pending. These code/CI checks are not an authenticated real Telegram account test or a Wayland visual acceptance.

## WATCH OUT FOR

- Telegram already has working QR/phone support inside Social; **OPEN TELEGRAM is a real path to those controls, not a new credential broker**. It is not an automatic Connect, Reconnect or Disconnect operation.
- Native Telegram status can expire after a successful health check. CPU++ intentionally does not cache/represent it as its own live session.
- No generalized trusted Connections broker exists. `ConnectionsBroker.credentialActionsEnabled` remains false. Other provider authentication, explicit logout/revocation, identity/LLC authorization and CONNECT ALL need independently approved host contracts.
- The C4b Silverblue confinement owner has a separate active PR #1521, confined to tests/CI. Nothing in this branch edits that work.
- No actual operator's account, system keyring, user session file, production settings or Fedora desktop was touched.

## CHECKLIST

- [x] Accept operator choice to retain dual-path account-name editor
- [x] Verify current GitHub head, existing Telegram authentication and active Connections owner
- [x] Add truthful first-class Telegram row to existing middle Connections list
- [x] Add actionable OPEN TELEGRAM in right bay and route through shared shell to original Social owner
- [x] Preserve private/shared scope and explicit QR/phone consent; no account/credential copying
- [x] Add source/auth regressions and scoped GitHub CI
- [ ] Verify exact-head workflows, address failures
- [ ] Operator merge and separate Fedora desktop acceptance
- [ ] Trusted host, provider-specific verified disconnect/revocation, account-session selection
- [ ] Consent-queued CONNECT ALL and authorized organization switching

## NEXT

Continue provider-by-provider. First verify this actual CPU++ → Social Telegram route in native Quickshell and test both shared/private scopes on a safe account. Then design **real per-provider disconnect and reconnection** behind the Connections owner host and provider adapter contracts, with a revocable scoped permission state. Only after individual secure operations pass can CONNECT ALL sequence provider-specific consent requests. Do not expose a generic working-looking button before that functionality exists.

## DECISIONS

Existing 1000×834 three-bay CPU++ chassis, Social-owned Telegram adapter and account-label editing in **both** menus are retained. No second Telegram login client, new session file, credentials, Social identity switch, forced provider login, provider logout, broker permissions, source writer or desktop changes. This report is an external continuity checkpoint; final acceptance remains with the operator.
