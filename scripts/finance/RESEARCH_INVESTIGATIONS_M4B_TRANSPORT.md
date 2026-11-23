# FinanceW Research // M4b-T1 One-shot transport lifecycle

## IMPLEMENTATION

This is a **non-executable transport contract**. It is not a live or authorized writer and is not connected to Quickshell.

`scripts/finance/research_investigation_write_attempt.mjs` exposes a single `ResearchWriteAttempt` object. Construction validates an explicit CREATE, ATTACH, or REMOVE intent against the current M1 investigation snapshot and prepares an M2 frame using the approved M4b contract. It performs **no I/O**.

The caller must explicitly invoke `dispatchOnce(callback)`. The class sets `inFlight` **before** calling its externally supplied callback. No second dispatch is possible for the same attempt, even during an unresolved asynchronous operation.

- **Ack received:** Exact M2 response matches expected revision and content. Return `acknowledged`, expose a cloned verified document, and clear the in-memory editor draft.
- **Error or uncertain outcome:** Return `reviewRequired`. Keep the editor draft, expose no unverified document, and disallow retry. A later operator-requested read must reconstruct the current state before any *new* independent intent is prepared.
- **Preflight invalid:** Throw before calling the supplied callback. No submission is attempted.
- **No ambient capabilities:** The module imports neither the M2 writer, filesystem, Quickshell, subprocess nor any network library. The callback interface is **not** a user authorization, consent token or security decision.

## VERIFY

`tests/finance/test_research_investigation_write_attempt.mjs` uses a disposable private temporary directory and injects M2's existing local `run()` function. It exercises:

1. A successful real M2 store write and exact acknowledgement.
2. An injected crash/error *after* M2 commits. The revision can advance even when the caller sees failure; no replay is allowed.
3. Missing/mismatched response, nonzero exit, stderr and extra response fields.
4. Reentrant second dispatch while a first operation remains pending.
5. Copy isolation for editor drafts and verified documents.
6. Invalid intent refuses before any I/O.

Run:
```sh
node tests/finance/test_research_investigation_write_attempt.mjs
```

The dedicated Research workflow also runs M1–M4b regression tests.

## WATCH OUT FOR

This is **not** a production-grade authorization boundary. A future worker could pass any callback that writes files, so the module intentionally provides no executable CLI, QML writer, or dispatch implementation. Actual activation remains blocked on a protected authorization decision, an independent M2 filesystem/crash audit, and approved operator integration.

The current M2 storage is unencrypted; private company, household or bank secrets must not be stored there. The existing `FinanceResearchInvestigationsReadHost.qml` must keep `writeEnabled: false`.

## NEXT / DECISIONS

The next reviewed milestone can add a *separate* protected dispatcher, but only after the M2 security boundary is cleared. Never treat a generic Boolean or a user-supplied callback as authentication. The shared `FinanceW.qml` navigation is untouched, other Finance workers keep their ownership, and no local desktop changes or merges occur in this PR.
