# TimeW // MACHINE: branching lives and session recovery vision

**State:** Operator-expressed long-term product intent, recorded 2026-10-23. **Design only: not an approved implementation contract, runtime permission, or completed feature.**
**Patient / owner:** `The-Post-Apollo-Project` / TimeW MACHINE.
**Room:** TimeW development (live Hospital room identity/registration unverified); external ChatGPT handoff.
**Predecessor:** [merged PR #579](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/579) introduced volatile UTC timestamp markers; [merged PR #582](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/582) added a *proposed* metadata-only Sway layout checkpoint contract. PR #582's document still says "not merged"; this is stale document metadata, not runtime evidence.
**Technical truth:** GitHub and actual TimeW code. Do not infer that a ChatGPT discussion has registered a Hospital Room or granted runtime permissions.

## 1 // Purpose: a video-game-style desktop session system

The operator wants MACHINE to behave like game checkpoints, lives, respawning and inventories, not merely a clock marker or window arranger. A saved point should preserve enough *recoverable* desktop-session information to reopen applications, windows, browser tabs and work context after the environment changes, crashes, or is deliberately reconstructed. Examples from the operator: Dark Souls checkpoint/revival and Terraria death preserving items/progression while losing some disposable resources.

**Guiding distinction:** restore the useful working experience, preserve newly earned progress, and discard unwanted temporary runtime baggage. This is not synonymous with rolling back the entire filesystem or capturing/restoring exact RAM.

- **Life:** a live running desktop/work session; identity/scope remain to be designed.
- **Checkpoint:** an immutable saved observation plus recoverable recipes and references, not a promise of exact process memory.
- **Timeline:** a branch of checkpoint history and its independent continuation.
- **Revive (proposed):** reuse existing running applications/windows when safe, recover missing layout/context where possible, and minimize interruption.
- **Respawn (proposed):** safely rebuild selected recoverable application/window/tab context using fresh processes where supported, without erasing newer persistent progress. RAM reduction is a hoped-for effect, not guaranteed.
- **Inventory/progression:** saved files, documents, repositories, settings and other persistent assets; separate from per-process RAM/temporary resources.

Illustrative desired behavior: a browser session containing a specific YouTube video and 50 tabs reappears with tab identities/URLs and useful context but can keep most pages dormant rather than immediately restarting every tab's processes. Exact playback position, form contents, unsaved edits or every application-internal state cannot be presumed recoverable. Confirm capabilities per application.

## 2 // Branches and a child with two parents

The operator explicitly wants Git-like branching *and merging* of desktop lives. Example:

```text
             A  common checkpoint
            / \
 B gaming + Git  C work + documents
            \ /
             D  unified child
            parents: B and C
```

B and C continue independently and remain recoverable after merging; D is a new checkpoint/timeline derived from both. A merge is not "replace current desktop with newer snapshot" or "delete the losing branch." A graph may have shared ancestors, divergent descendants, and multi-parent merge checkpoints. New state acquired on either life should not disappear just because another life is restored.

**Important caveat:** A Git-like timeline graph does not automatically version ordinary mutable files. If branches access the same file path without isolation/snapshots, both see mutations; there is no meaningful independent file history to merge. Worktree/versioned snapshots/application-specific isolation must be designed before promising independent parallel progress.

## 3 // What may and may not merge

Treat these state layers separately:

1. **Desktop layout:** monitors, workspaces, existing window placement and app identity; existing PR #582 addresses an intentionally narrow safe subset.
2. **Recoverable app context:** app launch intent, browser tab sets, document references, recoverable application state, work profiles, settings; requires explicit application-specific integrations and privacy review.
3. **Persistent assets:** files, Git repositories and changes, documents and game saves. Preserve post-checkpoint progress by default; where both branches modify the same artifact, compare to common ancestor when one exists, flag contradictions, and require conflict resolution.
4. **Ephemeral runtime:** processes, memory, sockets, live playback, volatile buffers, GPU/window handles; not generally mergeable. Recreate/delay/omit these with disclosed limits, rather than fabricate a successful RAM merge.

Candidate conflict UI: keep B, keep C, retain both as separate copies, manually combine where supported, defer/skip. Different versions of the same unsaved document are a **conflict**, not grounds to silently choose a newer timestamp. Browser tabs with overlapping identities, app settings, shared files, window locations and output topology may also conflict. No guaranteed automatic merge for arbitrary app state.

**Lazy activation (proposed):** merged inventory includes application/tab intent without eagerly starting everything. A new merged life should not automatically run a game and 50 tabs merely because both appeared in ancestors.

## 4 // Experience and UI concept (not accepted visuals)

MACHINE can remain a TimeW mode while evolving into a substantial internally organized subsystem. Candidate surfaces: TIMELINE (graph and saved lives), CAPTURE (checkpoint inventory), RESTORE (Revive/Respawn preview), MERGE (two-parent comparison/conflict resolution), and HISTORY/DETAIL (lineage, capabilities, exclusions). The operator anticipates later visual design and implementation work; do not freeze these tabs or geometry as canonical.

Preview must distinguish: selected parents; common ancestor; files/app/window additions/removals/edits; compatible items; contradictions; unsupported or unrecoverable items; lazy/dormant choices; resulting child's parent IDs; which action changes the live desktop or disk. Never label a partial result as exact/full restoration.

## 5 // Guardrails and distinctions

- Keep Git repo history/working trees, Hospital Room checkpoints, TimeW's UTC markers, and Apollo Hub uptime distinct; integrate by explicit links/adapters, not by treating them as interchangeable stores.
- Ordinary restoration should not delete files created *after* an old checkpoint. A true file/OS rollback, if ever added, must be an **independent, opt-in, high-risk design** with backups and review.
- No implicit read of sensitive user data, browser contents, command lines, titles or secrets; permission scopes and application opt-in/redaction are not decided.
- No automatic startup/restore, application kill, reboot, shell invocation, Sway mutation, filesystem mutation or process replacement from this document.
- Respawn must address unsaved work and process termination safety before any runtime attempt.
- Existing PR #582 limits (read-only preview, consent stages, metadata-only allowlist, cautious matching and operator-gated selected actions) remain operative *as that proposal's boundaries*. This vision does not quietly supersede or activate them.

## 6 // Work stages for future authorized workers

- [x] Preserve long-term operator intent and gaming/Git analogies in a durable recovery note
- [ ] Operator review/acceptance of the written interpretation
- [ ] Formal session identity, immutable checkpoint/branch DAG schema and lineage rules
- [ ] Distinguish shared vs timeline-isolated persistent data and merge-base/provenance semantics
- [ ] Inventory existing Sway, Quickshell, browser, application, file/versioning and Git capabilities
- [ ] Define app recovery adapters, privacy fields, storage path, permissions, retention, encryption and export
- [ ] Define Revive vs Respawn guarantees, unsaved work safeguards and lazy activation behavior
- [ ] Define three-way conflict detection, manual resolution, merge preview and partial failure reporting
- [ ] Design larger MACHINE UI with operator; do not treat earlier mockups as approved visuals
- [ ] Create independently authorized bounded implementation assignment(s), tests and rollback procedures
- [ ] Live acceptance in disposable sessions, then separately authorized local runtime trials

## 7 // Recovery / handoff instructions

**NEXT WORKER:** inspect current `main`, TimeW QML and services, [PR #579](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/579), [PR #582](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/582), this note, Syntagma `AGENTS.md` and relevant `OPERATE/` protocols. Reacquire active PRs, file ownership and actual Hospital Room/Assignment state if available; never claim registration from this note alone. Preserve operator's distinctions between revive, respawn, branching, child-of-two merge, and progress surviving reset. Do not silently implement from a vision note.

**Open decisions:** definition of a "life"; mutable file isolation; exact restore guarantees per app; what persists between reboots; checkpoint frequency/retention; whether browser tabs merge as sets or per-profile; conflict default; local encryption and access control; graph/editor layout; approval boundaries; runtime resource budget; how progress and game saves remain protected.

**Evidence status:** user-expressed requirements and GitHub baseline, not technical feasibility certification or final operator acceptance.
