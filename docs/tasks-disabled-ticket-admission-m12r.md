# 🏥💜 TASKS M12r // Disabled Admission Repair and Native Recovery Preflight

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** TASKS JSON writer continuity  
**ASSIGNMENT:** Repair M12q's dormant admission and prepare independent native/recovery verification  
**PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible (not live registered)  
**INSPECTED BASE:** GitHub main c05496c0ae637382a091853d6af999dc886bb5b3, 2026-11-02  
**STATUS:** Source-only correction and fixture CI, not native or production acceptance  
**AUTHORITY:** M12l ADR and Syntagma AGENTS / OPERATE. M11t and M12b gates remain open.

## IMPLEMENTATION

### The failure in merged M12q

M12q's inactive submit() reserved a ticket, populated pendingDocument, set storageState to "saving" and then invoked the existing stage(). That stage() starts by refusing any storage state other than "ready" or "empty". Its own call therefore always returned false, and submit() left the storage state stranded at "saving" if the disabled flag were ever enabled. This was a **future enablement blocker**, not a reported live failure: ticketProducerEnabled is a readonly literal false.

M12r leaves admission and pendingDocument ownership exclusively in stage(), which already owns the *one* FileView.setText call. submit() now reserves pendingTicket only before calling stage(). The existing FileView, nine legacy methods, JSON v3 policy and default behavior remain unchanged. No new process, storage path, privileged broker, data writer or runtime setting.

The new tests/tasks/test_task_disabled_admission_m12r.cjs executes the **actual QML JavaScript method bodies** from ApolloHubTodoStore.qml in an isolated Node VM. A memory-only mock FileView and actual task v3 policy exercise: disabled admission refusal; a mock-only enabled path issuing one ticket and one original write; no premature success; exact synthetic readback; early callback; wrong bytes; simulated save failure; no automatic retry; unchanged legacy stage. The VM's flag override does not alter production source or live settings.

## HOW TO USE

No new user-facing control, local commands, installation or data migration. Existing TASKS, TODAY, PLANNER, Projects and Hub behavior is unchanged.

Source test: node --test tests/tasks/test_task_disabled_admission_m12r.cjs

**Separately authorized native no-regression observations, not executed here:**

1. Inspect the actual installed sources. Both guardedWriterEnabled and ticketProducerEnabled must remain literal false. Hub ticketUiEnabled must also remain false.
2. Use an isolated, fresh, disposable Quickshell test configuration and TASKS-format fixture, never the real Quickshell.dataDir/apollo-hub-todo-v1.json file. Do not restart the live Quickshell without fresh operator approval.
3. Verify startup, existing task display, a deliberate disposable create/rename/done cycle, readback, error path and source bytes. Preserve redacted logs and hashes, not task contents.
4. For future native ticket acceptance, separately exercise the real Qt sequence: admission, FileView saved hint, deferred reload, exact loaded readback; also interrupt/failure cases. Never change the production literal false as a shortcut.

See docs/tasks-native-ticket-observer-m12n.md for the existing standalone native fixture lab. That lab is **not** proof that M12r's QML ticket path runs natively.

## VERIFY

- **Observed in source:** pre-setting "saving" in submit() contradicted stage()'s ready/empty guard.
- **Covered by new automated test:** the actual extracted store functions now permit mock-only admission, preserve the last confirmed document during pending/failure and keep exactly one writer.
- **Pending:** GitHub CI on final head; independent review; actual native Quickshell callback behavior; verified source baseline and recovery plan; operator acceptance.

## WATCH OUT FOR

- FileView.watchChanges is false. There is no verified pre-write source revision/byte-hash check. External changes can race a future enabled write. A source-baseline contract is required **before** enabling tickets.
- Tickets are session-local; no durable crash/restart idempotency key or recoverable journal is established by this correction. Never automatically replay an uncertain write.
- Native onSaved and reload events are not authenticated OS-writer evidence. Matching bytes do not prove writer identity against a hostile same-UID process (M12k).
- JSON and an unrelated SQLite journal are not one atomic transaction. A separately approved backup and manual recovery policy must preserve user data and distinguish code rollback from data restoration.
- VM simulation is not Qt/Wayland native acceptance; production ticket mode remains disabled.

## CHECKLIST

- [x] Inspect current GitHub, Syntagma and M12l/M12q source
- [x] Verify no active competing TASKS PR at preflight
- [x] Correct dormant stage admission without adding writers
- [x] Add actual-QML-body memory-only tests and isolated CI
- [ ] CI green / final diff reviewed
- [ ] Operator PR review/merge
- [ ] Separate native no-regression observation
- [ ] Pre-write source baseline, backup/recovery and independent evidence acceptance
- [ ] Separate approval for any ticket activation or UI consumer cutover

## NEXT

After CI and review, undertake an **operator-approved, disposable-native** no-regression check. Then develop a source-baseline + backup/recovery contract before considering enablement. Preserve the M12l in-application single-writer architecture and keep GitHub/format synchronization as a separate adapter milestone.

## DECISIONS

**Implemented:** dormant QML admission correction and synthetic test-only regression evidence.  
**Unchanged:** one FileView, nine legacy mutation routes, false guarded and ticket gates, normal UI semantics.  
**Not authorized:** local Fedora or task-data writes, live Quickshell reload, production activation, new broker, SQLite migration, merge, or final acceptance. Revert the M12r PR to roll back code; never automatically overwrite user task data as a rollback.
