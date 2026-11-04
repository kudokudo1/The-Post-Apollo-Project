# 🏥💜 CPU++ Connections // TASKS Recovery Inventory Field

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS encrypted draft recovery / CPU++ Connections UI  
**WORKER //** OpenAI ChatGPT · external Hospital-compatible; no live registration or staff lease verified  
**ASSIGNMENT //** Add a first-class visible TASKS field in CPU++ → SETTINGS → CONNECTIONS, matching the existing service-list and details layout  
**BASE //** GitHub `main` at `7e7bda394c7af6173d21bd152d574f013fb9b7de`, November 4, 2026  
**PERMISSIONS //** GitHub implementation/test/PR authorized. No local machine writes, keyring operations, merge, production activation or acceptance claimed.

## IMPLEMENTATION

### Verified layout and ownership

- `services/connections/ConnectionsPolicy.js` supplies **every service card** through the same object schema: `id`, `title`, `status`, `kind`, `accent`, `detail`, `context`, `consumers`, `permissions`, `setup`, `action`.
- `ConnectionsRegistry.qml` binds these rows to canonical service owners. `CpuPlusSettingsConnectionsListPane.qml` automatically renders each source with the same 53-pixel ActionButton tile, typography, hover/selected states, and spacing. `CpuPlusSettingsConnectionsDetailsPane.qml` displays each selected row in the same right-hand layout (title, status, detail, authorized-use preview, required access, setup/details).
- Before this patch, the inventory showed Social, Notifications, Proton Mail, NASA FIRMS, BBC, Al Jazeera and GDELT, **but no TASKS entry**, even though M13q #1267 was merged and TASKS → SYNC → RECOVERY already existed.
- The single TASKS real-data writer is `services/hub/ApolloHubTodoStore.qml` and all encrypted recovery flags are literal false. `ConnectionsBroker` only checks read-only OS Secret Service availability and refuses credential grants.
- No competing open TASKS/Connections PRs were found at preflight. Current Syntagma `AGENTS.md`, Hospital protocol and authority rules were inspected.

### Files changed

1. `services/connections/ConnectionsPolicy.js`: new `tasks-recovery` row **after Notifications** with the same eleven data fields as every other Connections service. The title is **TASKS // DRAFT RECOVERY**. Its status is **RECOVERY // OFF** when the known broker and TASKS authority flags are all disabled; otherwise **RECOVERY // STATE REQUIRES REVIEW**, never READY. The detail shows allowlisted keyring-presence states, e.g. `KEYRING // NOT CHECKED` or `KEYRING FOUND // UNLOCK UNKNOWN`. No external raw text, draft, token or key enters the row.
2. `ConnectionsRegistry.qml`: adds only read-only bindings to existing `ConnectionsBroker.status/checking/credentialActionsEnabled` and `ApolloHubTodoStore` recovery/host flags. No second keyring connection, file persistence, service registration, account selection or write authority is created.
3. `widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml`: when TASKS is selected, renders a small **TASKS RECOVERY // SECURITY STATUS** section in the existing details column, using its **GohuText, QuietText, ActionButton, magenta/cyan/orange palette, spacing, and scrolling**. It shows keyring presence, the shared broker owner, and capture, unlock/preview, checkpoint-delete disabled statuses. Its **CHECK KEYRING** button invokes only the existing C2a explicit `ConnectionsBroker.checkAvailability()` presence probe, just like the broker column for other providers.
4. `tests/cpuplus/test_cpuplus_connections_c1.js`: updates the original inventory contract from seven to eight entries and verifies TASKS row in the correct position, default OFF status, presence-only label, and refusal on unexpectedly enabled flags.
5. `tests/cpuplus/test_connections_tasks_recovery_field_c1r.cjs`: asserts all eight entries have the identical card schema, live status allowlist, no arbitrary host-text leak, no credential-grant inference, saved-task sole-writer continuity, and reuse of the existing Details/ListPane styling and explicit presence-only probe.

### UI after merge + local installation

```text
CPU++ → SETTINGS → CONNECTIONS

CONNECTIONS // SOURCES                 CONNECTIONS // ACCESS
SOCIAL // IDENTITIES                   TASKS // DRAFT RECOVERY
NOTIFICATIONS                          RECOVERY // OFF
TASKS // DRAFT RECOVERY   ◀ SELECT     KEYRING // NOT CHECKED
PROTON // MAIL                          AUTHORIZED USE // PLANNED
NASA FIRMS // FIRES                     TASKS // EDITOR / LOCAL RECOVERY
BBC // WORLD NEWS                      REQUIRED ACCESS
AL JAZEERA // NEWS                     ENCRYPTED CAPTURE / UNLOCK & PREVIEW /
GDELT // NEWS ANALYSIS                  SCOPED DELETE // DISABLED
                                        TASKS RECOVERY // SECURITY STATUS
                                        CHECK KEYRING
                                        SETUP / DETAILS
```

All other sources retain their existing fields and ordering. The existing CPU++ left overview inventory uses `ConnectionPolicy.counters()`; TASKS is classed as `local`, so it does **not** inflate keys-needed, mail-adapters-pending or public-source counts.

## HOW TO USE

After PR review/merge and a separately approved local update, open **CPU++ → SETTINGS → CONNECTIONS**, select **TASKS // DRAFT RECOVERY** in the center source list, then inspect its details on the right. Choose **CHECK KEYRING** for a fresh, read-only check of whether the OS Secret Service is reachable. The `SETUP / DETAILS` button explains where **TASKS → SYNC → RECOVERY** resides; it is guidance, not a browser-opening or automatic widget switch.

The new field does **not** install a secret, create a credential, grant consent or enable actual unfinished-draft capture.

## VERIFY

- The existing standard Connections row schema, ListPane delegate, details bay and UI controls are reused, not replaced.
- All eight rows are uniquely selectable. TASKS sits directly after Notifications. Native tile style, spacing and details area remain unchanged.
- Keyring `SERVICE_ACQUIRED` means **found / unlock unknown**, not recovery ready or authentication.
- Unknown raw status text is projected to a fixed unverified label, never displayed verbatim.
- Any unexpected enabled broker/TASKS flag produces **STATE REQUIRES REVIEW**, not an enabled authority or misleading OFF claim.
- No extra FileView, Process, Secret Service session, keyring read/unlock, credential field, or saved-task writer is introduced. Other users' Social/Notifications/GitW services remain owned by their existing components.
- GitHub CI parses QML and runs original C1, C2a, TASKS M13q and M11d regression tests. Real Fedora visual geometry, click selection and live status binding must be verified separately after installation.

## WATCH OUT FOR

- **Field is not a credential.** This adds visible status/permissions like the other providers; actual OS-key release and authenticated feature consent are separate planned integrations.
- The C2 broker remains read-only, and the M13p fake-review contract does not become a grant. Recovery and credential actions remain disabled.
- CPU++'s existing details bay is scrollable. Selecting TASKS displays a longer status section, so users may scroll to see `SETUP / DETAILS` on compact sizes. Actual desktop screenshot testing is pending.
- Native readiness requires independently verified source generation and explicit user opt-in. A working keyring alone is insufficient.
- No click-to-navigate action was added to TASKS because it would require a separate cross-widget routing contract. `SETUP / DETAILS` states the navigation path without opening a browser or moving the active window.
- Do not pull, reset or overwrite the user's dirty `~/.config/quickshell` checkout to install this change.

## CHECKLIST

- [x] Read canonical Syntagma/Hospital rules and check current GitHub ownership/PRs
- [x] Audit the seven existing service-card fields and details layout
- [x] Add TASKS as the eighth first-class same-format Connections entry
- [x] Bind real read-only broker/TASKS status and preserve fail-closed wording
- [x] Add TASKS-specific security details and existing check button
- [x] Update C1/field contract tests and CI
- [ ] CI green, independent review and operator merge approval
- [ ] Native Fedora CPU++ selection/layout/status/click acceptance
- [ ] Authenticated scoped opt-in/key release and real-draft recovery development

## NEXT

After merge and explicit local deployment approval, validate visually on the actual CPU++ Connections screen: TASKS tile between Notifications and Proton; selection turns magenta; right-hand fields match adjacent services; click CHECK KEYRING changes only the shared status. Later, coordinate the credential broker owner for real opt-in/status, without granting recovery until authorization and source revision checks pass.

## DECISIONS

Use the existing canonical Connections inventory, no new separate panel type, no credentials installed, and no activation of encrypted recovery. One real TASKS writer remains. Implementation changes are on GitHub only; no local workstation edits, automatic merges, live Hospital registration or final operator acceptance.
