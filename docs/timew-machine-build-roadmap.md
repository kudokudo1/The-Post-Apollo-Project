# TimeW // MACHINE: proposed implementation roadmap and worker recovery

**State:** PROPOSED architecture and build sequence, captured 2026-10-23 from operator discussion. Not an approved executable assignment, technical feasibility certification, or permission to modify the live desktop.
**Patient:** `The-Post-Apollo-Project`. **Scope:** TimeW MACHINE session engine; no live Hospital registration verified.
**Product purpose:** A video-game-style, recoverable desktop session system with Revive, Respawn, persistent progress, independently branching lives and two-parent merges. The operator wants the *experience* restored, not necessarily old process RAM.
**Long-term vision (merged):** [MACHINE branching lives and session recovery vision](./timew-machine-branching-lives-vision.md), PR #589. **Existing foundation:** [PR #579](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/579) session-local marker timeline and [PR #582](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/582) metadata-only Sway checkpoint *design contract*. These are not complete session restoration.

## 1 // Architecture proposal

Keep **TimeW.qml** as presentation/control, not the durable source of truth. Make an independently testable, local-first MACHINE core/service or helper, initially considering Python but only after checking existing Post-Apollo service patterns and runtime constraints. Independent persistence and crash recovery matter because restarting Quickshell must not erase saved checkpoints.

Bounded components and responsibilities:
- **TimeW UI:** inspect lives/checkpoints, request capture, preview restore, choose Revive vs Respawn, review merge/conflicts, approve exact operations.
- **MACHINE coordinator:** scopes permissions and operations, validates proposals, plans preconditions and records outcomes.
- **Sway/SwayFX adapter:** capture read-only output/workspace/tree layout metadata; later approve narrowly scoped window placement commands with fresh-state revalidation.
- **App adapters:** opt-in capture/reopen recipes and capability limits per browser, terminal, editor, media or other application, never assume arbitrary app memory is portable.
- **Timeline store:** immutable checkpoint records, parent relationships, artifacts, references, operation journal and capability/errors.
- **Merge engine:** common-ancestor comparison for supported typed objects, conflict lists, explicit choices, child with two parents. Never merge raw live RAM.

**Potential storage:** owner-local SQLite for metadata/graph/journal and an explicitly permissioned, separately managed local object store for approved artifacts. This is a proposal, not a selected path, schema, encryption policy or data retention decision. Avoid private session artifacts in public Git repositories.

## 2 // Proposed eight staged milestones

1. **Foundation / isolated tests:** design stable checkpoint IDs, schema versions, atomic persistence, parents, scope/permissions, failure journal and migration; test on synthetic records without desktop writes.
2. **Read-only Sway capture + approved local save:** user-triggered capture preview with inclusion/exclusion, validate monitor/workspace/window metadata, then separately approved immutable save; reload after Quickshell restart. No screenshots/content by default.
3. **Revive:** restore-preview matching currently existing windows and connected monitors; conservative one-window actions with operator approval, partial failure evidence, and no automatic process launch.
4. **Application recovery:** add adapters one by one, starting with a safe simple application; support explicit launch recipes and supported browser session/tab metadata, including caveats for playback, unsaved forms and private data.
5. **Respawn:** safeguard unsaved work, classify running processes as reusable/safely restartable/blocked, approve specific replacements, rebuild sessions with lazy activation. Reduced RAM is a goal to measure, not a promise.
6. **Branching lives:** immutable history DAG, branch names, checkpoints with stable parent IDs, correct checkout/revival semantics, clear distinction between shared files and timeline-private mutable data.
7. **Merging:** find merge base, compare both branches by data type, show conflict resolution (keep B/C/both/manual/defer), build two-parent child *without destroying parents*. Do not claim independent file history without actual isolation/versioning.
8. **UI, reliability, acceptance:** visual graph and navigation, diagnostics, recovery from crashes/partial operations, resource/performance tests, dry-runs and explicit operator acceptance.

**First recommended implementation milestone:** M1 read-only capture preview and synthetic checkpoint persistence architecture; optionally first real local save only after explicit consent/storage decisions. Do not launch, terminate or move apps in M1.

## 3 // Distinct state classes and merge policy

| Layer | Proposed handling | Important limitation |
|---|---|---|
| Sway desktop layout | Save selected output/workspace/window associations and optional geometry | Window IDs transient; monitor topology may differ |
| App/session context | Versioned, opt-in adapter manifests; reopen only what app supports | Tabs/URLs do not imply full page/playback/unsaved restoration |
| Persistent files/progress | Shared by default; isolate explicitly selected timeline-owned work; Git worktrees where appropriate | Shared paths do not become branches automatically |
| RAM/processes | Reuse in Revive; rebuild/delay selected apps in Respawn | No generic lossless process-memory merge |
| Git/Hospital records | Preserve their separate sources of truth | Never equate desktop checkpoint with Git commit or Hospital Room checkpoint |

Merging conflicting edits to the same document or settings requires ancestor-aware checks (when possible) and explicit resolution. No default silent selection based on newest timestamp. Files created since a checkpoint must survive normal Respawn/Revive.

## 4 // Proposed operator experience

Candidate, not final UI: TIMELINE graph/detail; CAPTURE preview; RESTORE PREVIEW with Revive/Respawn selection; MERGE PREVIEW showing two parents, merge base, compatible items, conflicts, exclusions, lazy-load choices and resulting child. MACHINE likely needs a larger self-contained interface while remaining reachable from TimeW. Follow approved Post-Apollo visual/color/icon grammar; do not treat conversational diagrams as frozen UI.

Before applying anything: show exact differences; what is reversible, what is unsupported, what will be saved, moved, restarted or left alone; ask for scope-specific confirmation. A merge of inventories need not eagerly launch every app/tab.

## 5 // Technical investigation before executable work

- Inspect current `widgets/TimeW.qml`, `services/time/`, existing Sway/Quickshell connectors, clock/menu composition and native component patterns.
- Inspect current `main`, open PRs, ownership/Room/Assignment state, Syntagma `AGENTS.md` and relevant `OPERATE` protocols. External ChatGPT is Hospital-compatible, not necessarily registered.
- Verify Sway IPC read and action capabilities and their focus/window-ID race behaviors on disposable test sessions.
- Inspect existing process/service/DB writers before choosing Python/SQLite or introducing any daemon or polling loop.
- Determine browser restore mechanisms, separate profiles, inactive tabs, session export access, privacy and portability; verify behavior per version.
- Assess file snapshot/isolation choices (Git worktrees for Git work, explicit file snapshots for other files), retention, backup/export and conflict semantics.
- Design crash-window journals, idempotency and uncertainty states before operations that terminate/relaunch apps.
- Benchmark Quickshell overhead; do not add a hot poller to a runtime with prior UI-freeze reports.

## 6 // Safety and authority

No automatic capture on TimeW open, login or reboot. No implicit access to URLs, window titles, terminal contents, secrets or private app documents. No default screenshots or application contents. Never terminate processes, restore shared files, launch apps, move Sway windows or restart Quickshell from this design note. Each later local machine mutation needs separate operator approval. Validate unsaved-work safety and current state immediately before any approved action. A partial result must not be reported as FULLY RESTORED. Always preserve rollback/recovery pointers.

## 7 // Recovery checklist / next worker

- [x] Long-term operator intention recorded in merged vision document.
- [x] Proposed build roadmap documented in this companion record.
- [ ] Operator review and decisions on architecture, design and staged permissions.
- [ ] Technical spike: verify actual Sway/Quickshell and app recovery capabilities.
- [ ] Design durable schema and independent persistent/isolated state model.
- [ ] Create bounded development assignment for M1 and tests, after approval.
- [ ] Implement and test read-only capture preview; seek separate approval for storage writes.
- [ ] Later milestones only under separately verified scope/ownership/acceptance.

**NEXT WORKER:** read this roadmap and the linked vision first, then reacquire *current* repository HEAD, room/assignment/ownership, relevant files and tests. Distinguish user requirements from proposed implementation choices. Continue the same MACHINE job unless explicitly reassigned. Do not merge a draft PR, activate a service, write local state, or claim Hospital registration without evidence/authority.

**Open decisions:** service vs on-demand helper; storage location/security/encryption/retention; source of stable life/branch IDs; file isolation; app adapter priority; which items lazy-load; merge conflict UI; whether the current 432x768 TimeW menu hosts a separate expanded MACHINE surface; failure/rollback boundaries.

**Evidence:** operator discussion plus existing GitHub designs; no live runtime capability tests, security audit or measured memory savings yet.
