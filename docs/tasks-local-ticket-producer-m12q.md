# 🏥💜 TASKS M12q // Hard-Disabled Local Save Ticket Producer

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Add a production-facing but never-enabled local ticket producer behind the existing single FileView; prove contract behavior without touching live data  
**WORKER //** External Hospital-compatible ChatGPT, not live Hospital-registered  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED MAIN //** `783b95618e31e95353224e1f4040c20ae2ad1e47`, 2026-11-02  
**SCOPE //** GitHub source and isolated tests; no local system/real data writes or activation  
**PREREQUISITES //** M12l ADR accepted, M12m/M12n/M12o test contracts merged, M12p PR #999 merged.

## IMPLEMENTATION

M12q puts a **new disabled-only ticket-producing path within the already-existing `ApolloHubTodoStore.qml` singleton**, rather than launching a new host, FileView, listener, privileged broker, or cloud synchronization process. This is materially closer to the final M12l in-application coordinator architecture than another unmounted file-only demonstration, while still preserving the operator's requirement that the existing To-Do UI remain fully functional.

**Source changes:**

- `services/hub/TaskLocalTicketProducerM12q.js`: pure QML-compatible planner and verifier, using the **actual TASKS v3 policy** for all nine mutation methods. Requires a recognized Hub/Details/Planner/Projects surface, exact argument shape, permitted method, valid document, nonempty change, bounded UTF-8 JSON length, and a session-qualified ticket ID compatible with the M12o/M12p presenter contract. Does **not** write files or authenticate native callbacks.
- `services/hub/ApolloHubTodoStore.qml`: keeps **one FileView**, `guardedWriterEnabled: false`, and the **same nine legacy `stage(TodoPolicy.*)` methods**. Adds `readonly property bool ticketProducerEnabled: false` and a `submit(surface,method,payload)` method that **always refuses writes** in current production. Its inactive code path would stage a planned mutation through the **same existing FileView**, treat `onSaved` as a hint, defer `reload()` until after the native callback unwinds, compare the exact returned JSON to the expected bytes and validated full task view, and emit a single ticket-specific result. A failed/ambiguous write keeps the last-confirmed in-memory document and reports `REVIEW_REQUIRED` rather than replaying automatically. The old FileView handlers still run when the literal flag is false.
- `tests/tasks/test_task_local_ticket_producer_m12q.cjs`: pure policy regression vectors for all nine operations across eleven consumer/method combinations, refusal paths, exact/incorrect/early readback, compatibility with M12p first-consumer presentation, no second writer, and permanently disabled source flags.
- `tests/tasks/test_task_writer_gate_inventory_m11d.py`: explicitly inventories the three new source-only public methods (`submit`, `ticketReview`, `ticketReadback`), verifies the compile-time disabled gate, and still requires exactly one executable `todoFile.setText(...)` call inside the original `stage()` seam. This is **not** a waiver of any production acceptance gate.
- A scoped CI workflow.

### Mechanics and what `CONFIRMED` would mean

```text
Caller submit() [currently always BLOCKED, ticketProducerEnabled:false]
   -> policy validates a change and produces {ticketId,baseline,expected}
   -> one existing FileView setText(expectedRaw)
   -> onSaved [NATIVE CALLBACK HINT, NOT CONFIRMATION]
   -> Qt.callLater(FileView.reload) after saved callback unwinds
   -> onLoaded sees exact expected JSON and parses v3 policy successfully
   -> updates in-memory confirmed document
   -> emits {ticketId,state:CONFIRMED,evidence:SYNTHETIC_READBACK_RECEIPT}
       [test-contract term, NOT authenticated source attribution]
```

The flag is a **QML readonly literal false**, not an operator toggle, runtime preference, environment variable, or automatic feature detection. M12p's Hub `ticketUiEnabled` likewise remains false. No real file is read by this new path or copied to a backup.

**Important:** A direct `FileView.onSaved` callback is not sufficient evidence of persistently committed bytes. M12q demands a deferred source reload before hypothetical UI confirmation, but **native readback in the same QML process is not independently authenticated evidence**. M12k also demonstrated that matching bytes do not identify the process that wrote them, and there is no atomic transaction spanning a JSON pathname and a separate SQLite journal. M12q does not resolve that threat, and `SYNTHETIC_READBACK_RECEIPT` remains an explicitly synthetic classification, never a production authority.

### Why an in-application producer, not another broker?

The M12l accepted ADR requires **one logical storage coordinator** and separate sync/format adapters, with a privileged broker conditional on an actual hostile-same-user or multi-user requirement. The live singleton already serializes nine kinds of task/project mutation and owns one FileView. Adding a disabled ticket stage/reload contract inside that existing owner avoids an independent always-running service and avoids multiple production writers.

## HOW TO USE

There is no new visible control or local command. For repository-only checks:

```sh
node --test tests/tasks/test_task_local_ticket_producer_m12q.cjs
```

The preceding M12m real disposable-filesystem suite, M12n native-ticket model, M12o consumer contract, M12p Hub presenter and M12k outside-writer threat tests also run in CI.

## VERIFY

### CI evidence and corrective iteration (2026-11-02)

The first CI run found a **genuine writer-seam violation**: the inactive ticket path included a second `todoFile.setText(...)` call inside the same FileView. This was corrected by invoking the original `todo.stage({ok:true,document:stage.expectedDocument})` after ticket planning. Therefore the final source again has **exactly one FileView and one `setText` call**. The follow-up inventory failures exposed M11d's deliberately closed public-method list; its test now recognizes only the three audited, hard-disabled M12q ticket methods, checks their source guard and absence of direct writes, and retains every original nine mutation-route requirement. Its executable-write assertion ignores mere comments mentioning `setText`, while requiring the true write call still occur solely within `stage()`.

**Final verified head `238fb6580b1da8272bed2f4b6fe690b9569606a3`: 27/27 GitHub Actions workflows passed,** including M12q's own nine-operation producer suite, M12p/M12o/M12n/M12m, M12i/M12k, M11t/M11d and all other triggered source checks. This is **source/fixture CI**, not native Quickshell acceptance or real data authorization.

**Expected evidence from this PR:**

1. All nine existing policy operations can produce a ticket plan only from valid data, correct method and recognized surface, without mutating the original document. Both remove and project-delete require an explicit `confirmed:true`.
2. A ticket is not successful on `submit`, `WRITING`, `onSaved` or an unrelated callback. The pure readback verifier requires `VERIFYING`, exact bytes, valid source schema and matching full view.
3. One existing live `FileView`, nine existing `stage(...)` mutation routes, `guardedWriterEnabled:false`, and the old behavior remain. A new literal `ticketProducerEnabled:false` disables all new write admission.
4. No additional QML `Process`, network endpoint, privileged host, storage path, actual TASKS data handling, or Hub ticket activation is introduced.
5. No native Quickshell runtime execution is conducted by GitHub CI. **Green unit/static CI must never be interpreted as local or production native acceptance.**

## WATCH OUT FOR

- **Source integration is not activation.** M12q intentionally edits `ApolloHubTodoStore.qml`, a live QML source file. Even with its gate false, operator-owned native smoke testing and rollback verification are needed before treating the code as accepted on Fedora. This PR does not change the local machine.
- The inactive QML integration has not been shown to execute successfully under a native Quickshell instance; no claim of native callback timing or OS fsync/durability is made. Future review must validate any `onLoaded` reentry, asynchronous event order, and staged-data behavior.
- Its session-qualified ID is **not a durable cross-restart idempotency key**, nor is the `Math.random()` session nonce a cryptographic identity. A restart after rename but before readback is ambiguous; no automatic replay is allowed.
- `FileView.watchChanges:false` means external edits aren't continuously monitored. Admission should gain a real source-baseline precondition or an explicitly reviewed threat model before activation.
- A pure JS test-generated `SYNTHETIC_READBACK_RECEIPT` is forgeable by another JS caller and cannot prove trusted native callback origin. A proper production evidence contract is still required; avoid marking M11t/M12b production authority gates passed on this result.
- M12o's and M12p's consumer code are unchanged in this patch and their features remain disabled. UI draft controls and confirmation events still need actual native tests and final operator approval.
- GitHub/format synchronization adapters are not implemented or activated.

## CHECKLIST

- [x] Confirm M12p merged and no competing open TASKS PR
- [x] Inspect canonical Hospital rules, M12l decision, current singleton and ticket consumer contracts
- [x] Preserve the live single FileView and nine mutation routes
- [x] Add QML-compatible ticket policy across all nine operations
- [x] Add hard-disabled producer code within existing singleton, with deferred readback requirement
- [x] Add pure producer/consumer contract regressions
- [ ] Validate CI, final scoped diff and independence from other workers' changes
- [ ] Operator review and merge
- [ ] Native Quickshell no-regression smoke with local operator permission
- [ ] Approve/test proper source-baseline authority, recovery and durable evidence
- [ ] Only then review enabling real producer and first Hub ticket consumer
- [ ] Subsequent Details, Planner and Projects integration
- [ ] Explicit production acceptance and activation

## NEXT

First resolve CI and review this disabled-source PR. Run a separately approved **read-only/no-regression** native load verification of the updated singleton against a safe test installation, not by restarting the user's live Quickshell without permission. Then reconcile the native receipt, baseline and recovery guarantees with the accepted M12l threat model and M12b security gates. A production ticket flag change requires a different, explicitly approved change; no automatic progression from CI success is authorized.

## DECISIONS

**Implemented in GitHub:** A real QML-facing producer seam in the existing owner, plus explicit policy/after-save readback behavior, hard-disabled, and regression tests.

**Not implemented or authorized:** Trusted native writer provenance, durable transaction across JSON+SQLite, persistent ticket journal, privileged broker, changing real task storage, enabling M12p ticket UI, bypassing existing gates, local machine edits, Quickshell restart, merge, synchronization or final operator acceptance.
