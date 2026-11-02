# 🏥💜 TASKS M12u // One-command Native Self-Reporting Smoke

**PATIENT //** kudokudo1/The-Post-Apollo-Project  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Replace manual M12s panel-message recollection with one operator-launched native PASS/FAIL test  
**WORKER //** External Hospital-compatible ChatGPT doctor, OPEN AI // CHATGPT; not verified Hospital-registered  
**GITHUB BASE //** main at 0b7f37b0bdf77439aabdb3e488c044f2a7fd85c6, 2026-11-02  
**TYPE //** Unmounted test-only root and disposable runner; no live task changes, native acceptance pending

## IMPLEMENTATION

M12s was operator-run: Quickshell reported "Configuration Loaded" and after exit a disposable v3 file contained one task. That established a valuable disk persistence checkpoint **but no captured report of the isolation indicator, disabled-ticket refusal, or onReload response**. Repeating a series of panel observations from memory is not a good acceptance mechanism.

M12u preserves M12s intact and adds a *second, unmounted* standalone test root at **TaskNativeSelfReportM12u.qml**. This imports the actual singleton **ApolloHubTodoStore** without creating another FileView or a second writer. It is never imported by shell.qml. An operator must deliberately start its own separate Quickshell process through **tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py**.

The Python runner creates a fresh, private temporary root. It starts **only** that new test process with XDG_DATA_HOME and XDG_STATE_HOME pointing into the private root and POST_APOLLO_M12U_DISPOSABLE=1. QML independently validates that its actual Quickshell.dataDir ends in /post-apollo-m12u-fixture, that its resolved singleton storage path is *exactly* that path plus /apollo-hub-todo-v1.json, and that guardedWriterEnabled, ticketProducerEnabled and independentlyAuthenticatedTicketReceipt all remain false. If any guard fails, the test **does not write**.

Once the *fresh* initial store reaches "empty", the native QML state machine:

1. Confirms the fixture starts empty (refuses an existing one).
2. Calls the disabled ticket submit and requires exact refusal, with store still empty.
3. Invokes the **single existing** legacy addTask route with the fixed synthetic title M12U_SYNTHETIC_TASK (never using the disabled producer).
4. Waits for actual singleton storageState to become ready and validates the observed UI snapshot's sole task and title.
5. Calls the existing reloadFromDisk route, waits for ready again, and confirms the one-task UI snapshot survives reload.

Each stage emits a specific machine-readable M12U_STAGE marker in the **test process** log. Errors, invalid transitions or a 20-second test deadline emit M12U_RESULT|FAIL; a complete sequence emits M12U_RESULT|PASS. A terminal marker alone does **not** establish success.

The Python runner collects markers (up to a bounded log size), stops **only the subprocess it started**, independently reads the disposable v3 JSON after test completion, rejects a missing/invalid/duplicate-key source, bad version, extra tasks, wrong title, linked/symlinked source, or absent/out-of-order/duplicate native markers, and prints one final human-readable PASS/FAIL with the synthetic file SHA-256 when successful. The temporary root is then discarded. No task titles other than the fixed synthetic one are logged. The runner neither starts nor stops the user's ordinary Quickshell process.

The M11d writer inventory explicitly counts this additional test-only root separately from four live TASKS consumers, and verifies its hard-disabled ticket flags and private environment/path safeguards. No production data, store source, Hub, Planner or Projects code changes.

## HOW TO USE

After operator review/merge and source update, the operator can opt in to **one synthetic native run**, in the already installed repository directory:

~~~sh
cd "$HOME/.config/quickshell"
python3 tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py
~~~

The checkout path above is an example from the earlier operator's terminal, **not a verified filesystem location**. No need to manually click buttons or copy intermediate status lines. The command itself is the operator's intentional authorization for temporary test-only filesystem changes. It should leave the live Quickshell session running.

A complete successful run should print approximately:

~~~text
M12u // Starting a separate disposable Quickshell test
M12u // Live shell and live tasks are not targeted
M12u // PASS // NATIVE_AND_DISK_AGREE
Native: INITIAL_EMPTY, TICKET_DISABLED, NATIVE_SAVE, NATIVE_RELOAD
Fixture: version=3 tasks=1
Fixture SHA-256: <sha256>
Classification: disposable legacy save/reload; no ticket activation
~~~

If QML did not load, an event failed to arrive, the private file is missing or corrupted, the callback order is wrong, or the runner was interrupted, the result is **FAIL**, not an inferred PASS from seeing a one-task file. The runner exits nonzero on failure.

No local install or test has been performed by this PR. Do not change production flags, use the real source path, reset/clean local Git changes, or restart the normal Quickshell instance.

## VERIFY

- **GitHub source/CI only, until a user starts this exact script:** Python evaluator tests full marker+disk success and rejects missing markers, wrong order, duplicate success, native failure, external source changes, bad/duplicate-key JSON, wrong task count/version and linked paths. M11d inventory, M12s source smoke and M12r/M11t production-disable regressions remain intact.
- **Native:** only operator's future actual run proves that the compiled standalone QML root loaded, the real store's onSaved and onLoaded transitions were observed as claimed, and a separate process read the exact fixture after test exit.
- **No stronger claim:** A PASS does not prove source-writer authentication, hardware power-loss durability, code signing, hostile same-user fencing, native ticket *enabled* operation, crash/restart replay, production backup/restore or final release acceptance.

## WATCH OUT FOR

- **Opt-in side effects:** The command creates a temporary test directory, launches a separate Quickshell process, writes one synthetic JSON fixture, then terminates that test process and deletes its temporary directory. It does **not** act on live task files.
- **Separate native test only:** Even a full PASS verifies the *legacy* writer and that tickets are disabled; it is **not** grounds to flip ticketProducerEnabled or activate a UI consumer.
- **No indefinite hang:** QML has a 20-second deadline, Python has a bounded 35-second log-collection deadline and stops only its child process. An OS/GUI runtime failure is reported as FAILURE rather than treated as success.
- **QML source/CI is not Qt execution:** If the installed Quickshell version does not support these callbacks or the guard evaluates incorrectly, the native test will report failure and a follow-up source fix needs independent review.
- **Security limit:** A separate synthetic directory and byte-exact reread do not protect against malicious same-user processes, per M12k. No new OS authority is claimed.

## CHECKLIST

- [x] Verify current main, Syntagma, existing M12s and M12t evidence, no open TASKS PR
- [x] Preserve M12s and the live source while adding standalone synthetic auto-sequencing
- [x] Add independent post-run JSON inspection and FAIL-closed tests
- [x] Update strict M11d fixture-caller inventory, never hide a new call site
- [ ] CI source and simulated-evaluator suite green
- [ ] Operator PR review/merge
- [ ] Operator's *actual native M12u result* printed with full marker and disk checks
- [ ] Final M12s/M12u verification acceptance
- [ ] Separate production-ticket/native-write source recovery review, explicit activation approval

## NEXT

After a green PR and operator merge, run the one-command disposable native test and record its final summary. If PASS, close the narrow M12s manual-status evidence gap. Continue with future ticket/recovery design, but keep real task storage, tickets and any migration unchanged unless separately authorized.

## DECISIONS

**Selected:** A single operator-launched synthetic test instance automatically reports native event sequence and post-run disk integrity; it does not rely on the operator remembering intermediate panel text.

**Reused:** Production ApolloHubTodoStore singleton and existing M12s/M12t architecture; one FileView; one writer route. The test runner is **not** a new service, storage engine or permanent worker.

**Unchanged and unauthorized:** Production tasks, local machine actions by this worker, live Quickshell restart, producer activation, privileged broker, SQLite migration, GitHub task sync, PR merge, or real Hospital connection.
