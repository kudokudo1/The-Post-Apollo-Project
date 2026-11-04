# 🏥💜 TASKS M13q // Shared Connections Recovery Status Pane

**PATIENT //** \`kudokudo1/The-Post-Apollo-Project\`  
**ROOM //** TASKS encrypted draft recovery  
**ASSIGNMENT //** Mount a read-only keyring/recovery-readiness view in TASKS without credentials, grants or a new task writer  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible, live Hospital registration/lease unverified  
**BASE //** current GitHub \`main\` at \`c037f79f086386bc5f3e4c045a3b8949ebb81a80\` (November 4, 2026)  
**AUTHORITY //** GitHub branch/PR only. No local workstation edits, current-user keyring operations, production activation, merge or live Quickshell restart.

## IMPLEMENTATION

### Verified starting state

- M13l's **operator-supplied** native Fedora PASS confirmed only synthetic QML → Node → private Secret Service → IPC process exit and cleanup. M13m #1254, M13o #1258 and M13p #1263 are merged into GitHub main as of this M13q preflight.
- \`services/hub/ApolloHubTodoStore.qml\` is the single authoritative real-task store. Exactly one \`FileView\` and one \`todoFile.setText()\` remain. Real recovery, storage, unlock and encrypted host activation flags are literal false.
- CPU++ already has \`SETTINGS → CONNECTIONS\`. The only shared credential-probe owner is \`qs.services.connections.ConnectionsBroker\` with \`status\`, \`checking\` and \`checkAvailability()\`. The broker has no active credential grant authority (\`credentialActionsEnabled: false\`). Its \`SERVICE_ACQUIRED\` status proves at most Secret Service daemon presence, not unlocked collection, key existence, user opt-in, or scoped authorization.
- The existing TASKS \`SYNC\` main mode has \`widgets/tasks/TaskSyncConnectionsPane.qml\` with four submodes (Overview, Map, Review and History). Its GitHub Projects navigation and remote-owner boundary must be preserved. There were no competing open TASKS/Connections PRs at M13q preflight.

### Files and UI behavior

1. \`widgets/tasks/TaskRecoveryStatusPolicyM13q.js\` is a **pure QML display policy**. It maps a fixed allowlist of shared broker status strings into bounded visible labels. Unknown/hostile text never propagates to the UI. All capture, decrypt, preview, restore, delete and source-write authority fields remain false. If any previously false TASKS/broker activation flag is unexpectedly true, the panel says **STATE REQUIRES REVIEW**, not READY.
2. \`widgets/tasks/TaskRecoveryStatusPaneM13q.qml\` imports the existing \`qs.services.connections\` and \`qs.services.hub\` owners **read-only**. A live binding displays the current shared keyring status, recovery disabled state, unavailable capture/unlock/delete operations, and checkpoint *not inspected*. It does not instantiate a service, FileView, Process or timer. No draft plaintext or key material is rendered.
3. The **CHECK KEYRING STATUS** button only calls the existing \`ConnectionsBroker.checkAvailability()\` on an explicit click; this is the already-reviewed **read-only D-Bus NameHasOwner presence probe**. It does not unlock a collection or read, create, change or delete any secrets. Opening the pane triggers no probe.
4. The existing \`TaskSyncConnectionsPane.qml\` adds a fifth **RECOVERY** submode. The tab rail derives widths from \`submodes.length\` to fit five tabs. Existing OVERVIEW/MAP/REVIEW/HISTORY content, mapping logic, GitW navigation and TASKS main mode stay in their original positions. Recovery is not mounted as a new standalone window and no \`TasksW.qml\` edit is needed.
5. No credential or recovery setting is enabled. A future authoritative host must provide authenticated per-feature consent/expiry/revocation and real checkpoint metadata before user-facing Recovery controls can be activated.

### Intended presentation

\`\`\`text
TASKS → SYNC → RECOVERY
DRAFT RECOVERY // STATUS
RECOVERY // OFF
KEYRING NOT CHECKED           [CHECK KEYRING STATUS]
  OR KEYRING FOUND // UNLOCK UNKNOWN
RECOVERY PERMISSIONS // NOT ACTIVE
DRAFT CAPTURE // DISABLED
UNLOCK + PREVIEW // DISABLED
CHECKPOINT DELETE // DISABLED
TRUSTED RECOVERY APPROVAL // NOT CONNECTED
ENCRYPTED CHECKPOINT // NOT INSPECTED
SAVED TASKS // EXISTING WRITER ONLY
CPU++ > SETTINGS > CONNECTIONS
READ ONLY // NO CAPTURE // NO KEY RELEASE // NO RESTORE
\`\`\`

This is a live observation of **shared C2a presence status only**. It is not evidence of a retrievable real draft. The panel intentionally has no \`ENABLE\`, \`RESTORE\` or \`DELETE\` controls.

## HOW TO USE

Once approved and eventually incorporated into the operator's desktop, open **TASKS → SYNC → RECOVERY**. The keyring label follows shared CPU++ Connections state. Click **CHECK KEYRING STATUS** only when you want a fresh read-only presence check. The button becomes unavailable while a check is in progress.

Until an operator-approved local update, this UI exists on the GitHub PR only; **do not pull/reset the user's dirty live \`~/.config/quickshell\` tree**.

## VERIFY

CI must run:
- Qt 6 \`qmlformat\` parsing of the new pane and updated SYNC container (syntax only, not a running Quickshell acceptance).
- Pure policy tests for not checked, service present, negative and malformed statuses, in-progress check, and unexpected enabled flags.
- UI wiring tests ensuring it imports only canonical C2/hub owner status, invokes only the explicit existing read-only probe and creates no local FileView/Process.
- M9a SYNC/GitW navigation regression, existing C2a broker tests and M11d one-writer inventory.
- Exact source guard: original \`ApolloHubTodoStore\` and \`ConnectionsBroker\` remain unchanged, active grants false.

A green source/CI suite does **not** certify the actual widget's visual geometry, click region, keyboard navigation, or Fedora runtime. These need an operator-authorized desktop check after integration.

## WATCH OUT FOR

- **Read-only ≠ automatic:** The pane does not start a keyring check on load. The check button explicitly starts the shared C2a probe and updates a status string, not the credential store.
- \`SERVICE_ACQUIRED\` does not mean unlocked, user consent, or recovery availability. Checkpoint metadata is not inspected.
- The \`SYNC\` label has previously meant GitHub mapping; the new RECOVERY tab is *local*, not a network sync feature. The cyan header description changes only when RECOVERY is selected.
- If another worker changes the shared C2 broker's status names or its public probe API, the policy will report UNVERIFIED rather than guessing.
- Five tab labels in the compact portrait chassis may be tight; verify with a real Quickshell screenshot and adjust text size, tab label, or overflow **in a separate visual acceptance pass**, without disrupting old tabs.
- M13p fake approval and M13o fake encrypted checkpoint storage are not connected to this pane. They may not be treated as credentials or durable real-source receipts.

## CHECKLIST

- [x] Read Syntagma, Hospital authority, current main, merged milestones and TASKS/Connections ownership
- [x] Add read-only display policy and live-binding status pane
- [x] Add Recovery submode to existing TASKS Sync Connections, preserve GitW controls
- [x] Limit explicit action to existing C2a presence-only probe
- [x] Add static/model/CI regressions and recovery handoff
- [ ] Green CI, independent technical review and operator merge decision
- [ ] Native Fedora Quickshell render, click/keyboard/size QA under separate approval
- [ ] Shared C2 trusted broker authentication/consent, real TASKS source revision and scoped Secret Service key release
- [ ] Actual opt-in capture, unlock/preview, retention/delete and restart/reboot verification

## NEXT

**M13r proposal:** after independent review and operator UI acceptance, coordinate with the Connections owner to display a real, authenticated, scoped consent/readiness receipt (not a simulated review) and with TASKS editor owner to identify the unsaved-draft capture seam. Do not enable real draft capture until source revision, key release, storage retention and explicit user opt-in are independently reviewed.

## DECISIONS

No second credential manager, source writer, keyring client or detached window; retain one shared CPU++ Connections probe and existing TASKS window. M13q is **status only**, no production recovery grants or automatic OS operations. No local workstation change, live Hospital registration, merge, or operator final acceptance claimed.
