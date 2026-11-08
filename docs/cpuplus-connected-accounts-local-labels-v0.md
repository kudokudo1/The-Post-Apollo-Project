# CPU++ // Social account-name management inside Connections

> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
> **ROOM:** CPU++ Connected Accounts management (external Hospital-compatible handoff; no live registered Room confirmed)  
> **ASSIGNMENT:** Reuse working local Social account-name editor in the existing CPU++ SETTINGS → CONNECTIONS right bay.  
> **PROVIDER:** OPEN AI // CHATGPT  
> **STAFF ROLE:** unassigned (DOC-compatible development work)  
> **PERMISSIONS:** Bounded review-branch QML, tests, CI and this handoff only; no local desktop writes, Connections broker changes, credentials, host trust activation, production sign-in, company switching or PR merge.

## IMPLEMENTATION

CPU++ already has a three-bay `SETTINGS → CONNECTIONS` layout, with a left read-only overview, middle service list and right details/authorized-use pane. The `SOCIAL // IDENTITIES` row already reflects the active local Social ID and count of saved local account names via `ConnectionsRegistry`. It did not expose their working editor.

The right details bay now embeds the **existing** `CpuPlusIdAccountEditor` exactly once below the Social service details, visible only when the middle service is `social`. It binds the editor to the live `SocialIdentityStore.snapshot.activeId` and uses the original `SocialAccountDetailsStore` writers for **add**, **rename**, and confirmed **remove** of saved service-account display names. It does not copy these records into Connections or create an alternative writer. The original account editor keeps its validated inputs, guarded delete, storage-state feedback and service picker. Selecting a different Connections service resets the local editor's pending removal confirmation; changing the active Social ID also resets the editor in its existing component.

`CpuPlusW.qml` now suppresses its main-mode keyboard shortcuts while text is being edited in this Connections editor, preserving the same keyboard-focus safety already used for ID MANAGEMENT.

This is actual **local account-name management**, not provider connection state. It does not alter identity selection, provider login/logout, registered app grants, OAuth/Telegram sessions, backend credentials, organization-switch permissions or the fixed CPU++ geometry.

## HOW TO USE

After authorized merge and separate desktop deployment:

**CPU++ → SETTINGS → CONNECTIONS → middle `SOCIAL // IDENTITIES` → right `CONNECTED ACCOUNTS // SAVED NAMES`.**

The right editor displays labels for the currently active local Social ID. Select a known service or use **CHOOSE SERVICE** → **FILTER SERVICES**. Use **+ ACCOUNT NAME**, **SAVE ACCOUNT NAME**, or select a saved name and use **REMOVE ACCOUNT NAME → CONFIRM REMOVE LABEL**. Status clearly reads **LOCAL LABELS ONLY // NOT PROVIDER SIGN-IN STATUS**.

For actual provider status, select the provider's separate service row (e.g. Proton) in the middle Connections list. These current statuses do **not** claim authentication; provider sign-in and reconnect/disconnect are still independently blocked until a trusted provider host can verify them.

## VERIFY

`tests/cpuplus/test_cpuplus_connections_local_account_editor.py` asserts original component reuse, correct active-ID binding and middle/right placement, keyboard focus guard, existing Social store ownership and closed Connections authority. Dedicated CI also runs the original CPU++ Connections C1, ID editor, Social account store/backend UI, broker-denial and Settings geometry tests, plus Qt 6 syntax checks. **Exact PR-head CI and real Quickshell visual/interactive acceptance must be checked separately.**

## WATCH OUT FOR

- A locally saved email, handle or nickname does not prove that account's provider authenticated.
- The shared `ConnectionsBroker.qml` still reports `credentialActionsEnabled: false`; `ConnectionsRequestStatus.qml` still reports `hostAuthenticated: false`.
- This work intentionally adds **no fake CONNECT, RECONNECT, DISCONNECT or CONNECT ALL button**. Those operations need provider-specific trusted host callbacks, caller authentication, user consent, checked session/revocation state, and a reviewable action queue.
- Two CPU++ routes now offer the same local editor, but both write to the **same** Social owner, not duplicated storage. Concurrent writes remain governed by its original revision/validation rules.
- No local Quickshell deployment or real user-data test was performed by this external browser worker.

## CHECKLIST

- [x] Recover earlier CPU++ #1495 handoff and verify merged state
- [x] Recheck main, open owner PRs and current Connections trust flags
- [x] Reuse original editor inside the existing CPU++ Connections detail bay
- [x] Bind active local Social ID and clear confirm state on service switch
- [x] Preserve focus/keyboard guard, no second writer, no provider authentication
- [x] Add source/backend/CI regressions
- [ ] Exact-head workflow results and resolve any failures
- [ ] Operator merge and separate desktop deployment authorization
- [ ] Native Quickshell appearance, input and persistence acceptance
- [ ] Trusted provider-specific Connect/Reconnect/Disconnect, followed by consent-driven Connect All

## NEXT

Implement the **trusted provider-action host contract** through the shared Connections ownership boundary. Start with one provider that actually supports verified authentication rather than mass-adding dormant buttons. Define exact source owner, signed or otherwise authenticated host/caller identity, provider operation and revocation statuses, checked account session state, consent prompt/queue and error transitions. Expose actions in the existing right details bay **only after** the host can prove support. Next implement CONNECT ALL as a sequential, per-provider, independently authorized consent queue. Keep verified organization switching behind separate identity/session authorization.

## DECISIONS

Retain CPU++ fixed 1000×834 chassis, left overview / middle selection / right actions, and the existing Social account-name writer. No new window, data store, identity selector, provider login, permission grant, credential broker, local machine mutation or automatic merge. GitHub code is technical truth; the operator retains final acceptance. The TASKS M15e job belongs to its separate TASKS worker/PR #1509 and is outside this scope.
