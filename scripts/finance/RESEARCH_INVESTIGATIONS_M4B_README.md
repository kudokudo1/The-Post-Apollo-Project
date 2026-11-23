# FinanceW Research M4b // Write-intent staging contract

**Scope:** FinanceW Research only. **Deployment:** HOLD. **Write execution:** ABSENT.

M1 (investigation model), M2 (local store), M3 (interface) and M4a (read-only controller) already exist on the repository's main branch. M4b isolates the rules that any later write controller must obey. It does **not** connect the M3 pane to M2's writer.

## Implemented boundary

`scripts/finance/research_investigation_write_contract.mjs` is pure request preparation and response validation. It has no process launch, filesystem calls, network calls, or automatic retry.

`prepareResearchWrite(request, current, options)` accepts an **already validated in-memory snapshot** and one of three exact user intents:

- `{action:"create", title, question}`
- `{action:"attach", investigationId, title, summary, url}`
- `{action:"remove", investigationId, evidenceId}`

It generates a fresh random UUID-backed record ID where needed and a UTC timestamp, checks the existing M1 model and revision bounds, calculates the full expected post-write collection, and returns one newline-framed M2 command **without executing it**. A typed URL is always attached as `source:"manual", reviewed:false`; a typed SEC URL is never represented as an authenticated SEC provider snapshot.

`acknowledgeResearchWrite(raw, proposal)` only accepts one `FINANCE_RESEARCH_STORE_RESULT` response whose schema, revision, investigation records and evidence exactly match the expected post-write collection. A process exit code of zero alone must never be treated as a committed write; the future adapter must pass the result through this check.

`writeFailureState()` returns `review-required` and `allowRetry:false`: after an error, timeout, crash or ambiguous result the controller must preserve the unsaved editor text, disable writes, and offer an explicit read-only reload. It must never silently resubmit a possibly committed operation.

## Tests and review boundary

```sh
node tests/finance/test_research_investigation_write_contract.mjs
```

The Research CI workflow runs M1–M4 regression coverage plus these new tests. All tests use invented records and never create or change personal files.

**Unfinished, deliberately not enabled:** the QML->Node writer transport, write-permit decision, recovery from stranded locks, independent M2 security review, actual live save/reopen acceptance, and shared `widgets/FinanceW.qml` navigation. Do not claim any of these were supplied by this contract.

## Security and practical constraints

1. A successful source contract does not establish that M2 filesystem path protection, ownership permissions, process-crash recovery, and concurrent writers have been independently cleared.
2. The present M2 store is local and unencrypted. Company secrets, household financial details, bank credentials and private account records must remain out of this Research store pending Connections/identity and authorization work.
3. New write operations require one deliberately requested action, a current read revision, unique generated IDs, an explicit security-approved writer path, and an exact result acknowledgement.
4. A future writer must not expose a generic `allowWrites` toggle to an untrusted QML caller as a substitute for protected authorization.
5. The M3 pane's save editor must close **only after** verified acknowledgement, not when a request signal fires.

## Next

Nurse 2 independent audit of M2 plus disposable crash-matrix tests. Then, in a **separate** Research-owned PR, implement a guarded transport that stays disabled until a verified authorization decision is available. Shared menu mounting requires coordination and explicit operator approval; production remains HOLD.
