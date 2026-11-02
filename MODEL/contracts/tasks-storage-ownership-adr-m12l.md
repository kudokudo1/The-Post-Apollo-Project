# 🏥💜 TASKS // ADR M12l: Prefer a Local-First Single Storage Coordinator; Defer the Privileged Broker

> **DECISION STATUS // ACCEPTED ARCHITECTURAL DIRECTION, NOT IMPLEMENTED**  
> **DATE //** 2026-11-02  
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
> **ROOM //** TASKS JSON writer continuity  
> **PROVIDER //** OPEN AI // CHATGPT (external Hospital-compatible worker; no verified live registration)  
> **OWNER //** TASKS / Post-Apollo local task storage and synchronization architecture  
> **SCOPE //** Local single-user TASKS data consistency, future GitHub and other-format adapters, error recovery and explicit threat-model boundaries  
> **AUTHORITY //** Operator-selected design direction after M12k review; **not** operator authorization to merge, install, migrate, replace the live writer, or activate guarded mode  
> **SUPERSEDES //** Treating the M12k security finding as automatic justification for a privileged broker as the next required implementation  
> **DOES NOT SUPERSEDE //** M12j/M12k evidence; M11t, M12b and other production preflight gates; current live TASKS code  
> **VERIFIED AGAINST //** GitHub main `278d137c6eccb66baa09d4d039c8340b38566398` on 2026-11-02. Re-check before implementation.

## DECISION

**Default:** Preserve **one authoritative local TASKS model and one serialized write-admission path**. Evolve the existing shared TASKS storage seam into a **logical, in-application storage coordinator** that validates changes, controls write ordering, waits for verifiable completion, preserves last-confirmed data and supports explicit recovery. This is a logical responsibility, **not authorization to add a new daemon or second writer**.

Keep future GitHub, file-format import/export, and cross-device synchronization in **separate adapters** around this local authority. Local task edits should not depend on GitHub or another remote being online. Remote conflicts must be detected and reconciled before a remote result is claimed. Whether the canonical local representation remains JSON or evolves to another store is a **separate choice**, not made here.

**Defer** introducing an always-running, independently privileged or OS-isolated storage broker **as a production prerequisite**. A broker remains a conditional option if an explicit threat model, concurrent independent writers, multi-user sharing or reproducible reliability evidence demonstrates sufficient net benefit.

**Explicit limitation:** This direction **does not promise resistance to a malicious, noncooperating process running with the same user's filesystem permissions**. M12k shows that byte equality and advisory locking cannot establish that guarantee. This limitation must remain visible; it is not a certification of hostile-writer safety.

## CONTEXT AND ACTUAL MECHANISM

The current production singleton `services/hub/ApolloHubTodoStore.qml` has **one** Quickshell `FileView`, uses `atomicWrites: true`, funnels mutations through `stage(result)`, and contains `readonly property bool guardedWriterEnabled: false`. Today the legacy callback/path is **not** an independently authenticated or durably stage-attributed guarded OS host. Do not mistake the proposed coordinator for an already installed component.

A local task edit conceptually moves through:

```text
TASKS UI (To-do / Planner / Projects / Hub)
  -> shared task policy and storage coordinator [proposed logical owner]
  -> validate + serialize + reserve/prepare + write
  -> independently confirm acceptable persisted result
  -> publish confirmed UI state, or retain draft and require review

                      [separate future sync boundary]
Confirmed local version -> GitHub / other formats / other devices
                          -> revision checks + conflict handling
                          -> explicit sync state and retry queue
```

A write to JSON and a write to a **separate** SQLite journal are not automatically one atomic transaction. SQLite's transaction guarantee covers the SQLite database transaction, not an unrelated filesystem pathname. A `FileView.onSaved` event is a native completion signal, not proof of an authenticated writer identity or end-to-end source durability. Whichever local implementation is later chosen must state what its acknowledgment means and test crash/restart boundaries.

The **logical coordinator may be implemented within the application** if native I/O supports the required reliability. A small **unprivileged** host may still be justified for specific filesystem primitives, durability guarantees or cross-process coordination. This ADR rejects only the assumption that an **OS-privileged broker is automatically required**. It does not prohibit evidence-driven use of a helper.

## RATIONALE: BENEFITS MUST EXCEED NEW FAILURE MODES

A privileged broker could provide meaningful source isolation **only if** the OS actually makes the authoritative source unwritable by untrusted peer processes and the request boundary is authenticated. A Python service, socket, signed binary or `flock` alone does **not** enforce that isolation when unrelated programs retain the same source write permission.

But an extra mandatory process introduces additional availability and recovery dependencies:

- The coordinator cannot save if its broker fails to launch, crashes, loses its lock, cannot access its credentials or becomes unreachable through IPC.
- Service/version compatibility, activation order, peer identity checks, restart policy, journal migration and permission drift become additional failure paths.
- Out-of-order replies, timeouts, duplicate requests, uncertain commits and UI state divergence must all be handled explicitly.
- Recovery must determine whether a request reached the broker and whether the on-disk change occurred before any retry; an unverified retry risks duplicate or overwritten state.
- A broker with unrestricted same-user source access but no independent OS-enforced boundary **adds complexity without meeting the hostile-peer goal**.

These are engineering risks, **not a claim that privileged brokers are inherently unreliable**. If hostile peers become a required threat, isolation can be worth its costs. For a personal, local-first to-do system with many read/write surfaces, **data integrity, crash recovery, correct UI acknowledgment and synchronization conflicts** have clearer near-term value.

### Explicit alternatives evaluated

| Option | Benefit | Cost or limitation | Decision |
| --- | --- | --- | --- |
| **A. Shared in-application logical coordinator + adapters** | One local authority, no mandatory extra service, works offline, straightforward failure visibility | Does not fence hostile same-UID writers; details of durable I/O still need proof | **Selected direction** |
| B. Unprivileged I/O helper for narrowly needed primitives | Can provide better OS readback, fsync or durable protocol without privilege escalation | Adds IPC/process lifecycle and does **not** create independent filesystem security | **Conditional, test-driven** |
| C. Privileged, OS-isolated source broker | Can enforce an adversarial owner boundary *if* permissions, identities and launch chain are independently trusted | Larger permission, availability, deployment and recovery surface; would change direct `FileView` ownership | **Deferred; not justified as default** |
| D. Multiple UI components or format adapters writing the authoritative source directly | Initially fewer integration steps | Race, overwrite and conflicting state across UI, GitHub and other formats | **Rejected** |
| E. Make GitHub or a remote service mandatory for every edit | Central remote authority | No offline edits; network and remote rate limits become local save failures | **Rejected as default** |

These choices do not freeze a specific on-disk format, signing stack or synchronization library.

## EVIDENCE AND ITS LIMITS

### Project evidence, directly applicable

1. **M12j, operator-observed isolated native experiment:** Two real Quickshell `FileView` saves, two host-reported settled receipts, frozen state, an independent read-only SQLite/source chain check with eight successful checks, and corrected fresh-owner recovery preserving counter 2. Initial wildcard-path recovery attempt was invalid and explicitly excluded. The evidence is **operator-supplied**, synthetic, not a production TASKS activation or cryptographically authenticated callback trace. See [M12k checkpoint](../../docs/tasks-m12j-checkpoint-and-external-writer-boundary-m12k.md) and [redacted fixture summary](../../tests/tasks/fixtures/task_native_receipt_external_writer_m12k.json).
2. **M12k, merged PR [#982](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/982):** A real second same-UID Linux process ignoring the `flock` could overwrite a private synthetic source. Unexpected bytes at pre-admission or readback were detected/refused, **but** an outsider writing the exact expected bytes could cause byte-consistent `SETTLED_UNACKNOWLEDGED` evidence *without FileView writing*. A deliberately injected final-readback-to-SQLite-commit race could leave a stale receipt. Those **passing** tests demonstrate limitations, not mitigation. See [M12k tests](../../tests/tasks/test_task_uncooperative_writer_m12k.py).
3. **Existing source [ApolloHubTodoStore.qml](../../services/hub/ApolloHubTodoStore.qml):** One `FileView`, one shared staged mutation seam and guarded mode hard-disabled. **No** newly authorized production writer is proven by M12j/M12k.
4. **Existing production preflight [M12b](../../tests/tasks/fixtures/task_disabled_integration_preflight_m12b.json):** Ten independent review topics, including source authorization, recovery, release/host identity, native evidence, UI acceptance and activation, remain **OPEN** until separately reviewed and satisfied or explicitly revised by operator-approved architecture. This ADR is **not** an automatic waiver.

### External architecture references, illustrative rather than statistical survey

5. **[Obsidian official storage documentation](https://obsidian.md/help/data-storage):** An established local-first application deliberately uses user-editable Markdown files and detects external file changes. This shows that external editability is a valid product trade-off, **not** evidence that Obsidian has TASKS's exact integrity requirements.
6. **[Joplin synchronization specification](https://joplinapp.org/help/dev/spec/sync/) and [architecture](https://joplinapp.org/help/dev/spec/architecture/):** Joplin persists data locally and synchronizes with selectable remote targets. Offline-first local authority and remote synchronization are separable concerns.
7. **[Taskwarrior TaskChampion sync](https://taskwarrior.org/docs/sync/), [TaskChampion storage overview](https://gothenburgbitfactory.org/taskchampion/taskdb.html), [Taskwarrior 3 upgrade guide](https://taskwarrior.org/docs/upgrade-3/):** A task manager can use a local database with explicit replica synchronization. Its docs also warn against naïve external synchronization of its internal DB files. This supports a dedicated synchronization protocol, **not** copying the database file to GitHub.
8. **[GitHub repository contents REST API](https://docs.github.com/en/rest/repos/contents):** Updating an existing file requires its blob SHA; conflict responses and serialized mutation requests matter. Future GitHub adapters need revision-aware conflict handling rather than blind overwrites.
9. **[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html):** Documents the database transactional boundary. It does **not** make an unrelated editable JSON source part of that transaction.

**Evidence interpretation:** These are implementation examples and primary documentation, **not a statistical claim that most to-do apps choose one architecture**. They are enough to reject "a privileged broker is a default prerequisite," but not enough to prove a particular unimplemented Post-Apollo coordinator is reliable.

## REQUIRED INVARIANTS FOR FUTURE WORK

**Local integrity and recovery**

1. One authoritative local task model and **one serialized mutation-admission path**, regardless of how many Post-Apollo widgets edit tasks.
2. A pending mutation is never displayed as durably saved merely because a request was queued or `onSaved` fired. Last-confirmed data, draft state and recovery state must be distinguishable.
3. Do not silently replace malformed, future-schema, externally changed or missing data with an empty task list.
4. Version/checksum checks before admission and readback where appropriate; no claim of continuous hostile-writer prevention.
5. Crash/restart and ambiguous-settlement scenarios preserve evidence, avoid automatic replay and prevent data loss. Any separate SQLite/file combination must use an explicitly verified recovery protocol rather than assume cross-resource atomicity.
6. Backups must be independently readable, recoverable and validated; automatic data restore remains a separately authorized operation.
7. Keep the existing sole production `FileView` until a separate reviewed migration explicitly preserves single-writer semantics.

**Future synchronization / multiple formats**

8. Local commits and remote sync have **separate statuses**; an offline GitHub endpoint cannot block or falsely confirm an otherwise valid local save.
9. Remote updates use version preconditions, idempotent request identity where feasible, bounded retry/backoff and a recorded conflict state. Do not blindly overwrite a newer revision.
10. Format adapters convert to/from the canonical task model, validating schemas and identities. A new adapter must not become a second authoritative source writer.
11. Track errors explicitly: `LOCAL_SAVE_PENDING`, `LOCAL_CONFIRMED`, `SYNC_PENDING`, `SYNC_CONFLICT`, `REVIEW_REQUIRED` are **illustrative semantic states**, not already selected API identifiers. The async public API, UI callbacks, task identifiers, export formats and concrete retry behavior require separate design.

**Security and authority**

12. This ADR **does not solve** uncooperative same-UID writes, compromised local user sessions, privileged attackers, malicious extension code, supply-chain compromise or power-loss guarantees.
13. Preserve the M12k hostile-writer tests as regression/threat evidence. Do not advertise them as mitigations.
14. Do not turn any synthetic receipt, self-reported digest, `flock`, CI green result or unsigned callback into a trusted native attribution claim.
15. A real production integration, any live TASKS source read, permission change, OS helper installation, trust root, task-data migration, Quickshell restart or guarded-writer activation requires separate explicit authorization.

## REVISIT THE BROKER IF ONE OF THESE TRIGGERS OCCURS

Reopen Option C only if at least one concrete requirement is confirmed:

- **Threat:** The operator requires resistance to malicious/noncooperating programs running with the same Linux user identity, with a specified attacker model and meaningful OS-enforced permission separation.
- **Multiple processes:** Several independently running applications/agents actually need concurrent authoritative mutation rights and cannot reliably share one local coordinator.
- **Multi-user/organization:** TASKS becomes a shared service with distinct human/organization identities and enforceable access permissions; the Identity Center/security owner must participate.
- **Measured reliability:** Reproducible crash, corruption or recovery evidence shows the existing single-process scheme cannot achieve the required guarantees, while a tested helper/broker demonstrably does.
- **Operational feasibility:** Deployment, rollback, offline startup, liveness checks, observability and failure recovery have a measurable cost acceptable to the operator.

Before approval, require a threat model, failure-mode comparison, migration/rollback strategy, identity/permission design, recovery proof, and acceptance tests. A broker alone is not proof of authorization or source fencing.

## IMPLEMENTATION

This ADR is documentation only. It **records a direction**, not a functioning storage coordinator or synchronization adapter. No changes are made to `shell.qml`, `ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`, live JSON, existing disposable fixtures, host service or GitHub writer behavior.

## HOW TO USE

Future TASKS workers should read this ADR before proposing M12l implementation, adding a storage process, integrating GitHub, changing format ownership, or declaring guarded-mode readiness. Cite the concrete requirement and evidence if reopening the deferred broker. No user installation or runtime action is required.

## VERIFY

The design matches the inspected project singleton, M12k merged experimental findings, the M12b blocked-production contract, canonical Syntagma documentation placement and official external references listed above. **Only this documentation and its MODEL navigation link** are proposed in the accompanying PR. CI/runtime proof of a future coordinator or adapter is not claimed.

## WATCH OUT FOR

- **Accepted design direction ≠ accepted implementation ≠ operator production activation.**
- "One coordinator" describes a **logical authority**, not necessarily one OS process, SQLite file, JSON format, cloud endpoint or privileged daemon.
- Source editability and same-UID hostile-writer isolation are incompatible goals unless permission/identity boundaries are redesigned.
- The current M12b preflight's stricter security gates have **not** been silently rewritten or waived. If pragmatic scope changes those gates, reconcile and approve that separately rather than bypassing the gate.
- GitHub syncing task data may create privacy, access-control, credential and accidental-publication risks. Adapter design must decide exact repository visibility and data minimization before any real task upload.

## CHECKLIST

- [x] Operator requested an explicit architecture decision and evidence record
- [x] Recheck current production single-writer/guarded-off code and M12k finding
- [x] Distinguish required reliability/synchronization from optional hostile-writer isolation
- [x] Document benefit, cost, alternatives, failure paths and official primary-source examples
- [x] Preserve unresolved production and security gates
- [ ] Operator reviews/merges the documentation-only PR
- [ ] Separately specify local coordinator acknowledgement and recovery API
- [ ] Design GitHub and multi-format adapters with versioned conflicts
- [ ] Obtain separate approval before runtime implementation or production activation

## NEXT

1. Preserve this direction in the project MODEL contract index.
2. In a **separate** implementation assignment, decide the smallest testable local save/acknowledgment mechanism using the existing single-writer seam. Retain current `guardedWriterEnabled: false` until independently approved integration.
3. Treat future GitHub/multi-format work as adapter contracts, with offline queues and explicit conflicts. Keep the broker parked unless a revisit trigger is met.

## DECISIONS

**Selected:** Local-first, one logical authoritative storage coordinator and isolated format/synchronization adapters. Optimize for correctness, recoverability, offline use and minimized independent failure points.

**Deferred:** Mandatory privileged/OS-isolated storage broker as a prerequisite. It is a contingency for a defined and justified threat or multi-user requirement, not a default feature.

**Not yet selected:** Canonical storage engine/format, coordinator API semantics, native I/O implementation, durable journal wiring in production, asynchronous UI completion contract, GitHub repository/schema credentials, conflict resolution algorithm, backup storage and release/authentication ownership.

**Not authorized:** Local computer changes, code changes to live TASKS runtime, host deployment, trust-root creation, task-data migration, data restore, merge of this PR or activation of the guarded writer.
