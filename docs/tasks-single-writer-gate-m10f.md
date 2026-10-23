# 🏥💜 Proxy 1 // M10f Single-Writer Transaction Gate

**Scope:** GitHub CI-only experimental fixture. No production adapter, no live Quickshell write.  
**Owner:** Proxy 1, external development assignment, not registered in live Hospital.  
**Patient:** `kudokudo1/The-Post-Apollo-Project`.

## IMPLEMENTATION

A new disposable Node fixture `tests/tasks/fixtures/single_writer_gate_fixture.cjs` models:

1. An exclusively-created lock directory adjacent to a **test** versioned envelope file. Cooperative competing processes refuse to write while the lock exists.
2. Cryptographic owner token plus process identity, checked before reading/committing/releasing. A lock without valid metadata remains blocked rather than silently stolen.
3. A commit that checks **both** expected revision and SHA-256 of the complete source. It accepts only next revision = previous + 1, encoded through the existing M10b journal policy.
4. Same-directory candidate creation with no overwrite, candidate file fsync, rename over the committed envelope, directory fsync, and byte-hash + revision readback.
5. Explicit inspection after uncertain outcomes. No automatic retry or remote acknowledgement; after rename, actual local state must be re-read before deciding next action.
6. Manual releasing by the same fixture process only while presenting its current owner token. A crashed process's orphan lock is left blocked.

The model and pending GitHub intent remain inside **one test envelope**. It never creates a second actual task writer, service, live lock, or GitHub connector.

## HOW TO USE

CI runs:

```sh
node tests/tasks/test_single_writer_gate.cjs
```

Only OS-generated temporary test folders are used. Two independent Node processes contend for the same synthetic file to prove lock refusal.

## VERIFY

- First process acquires ownership; second independent Node process is denied.
- Wrong owner token cannot inspect or release lock.
- Release allows a new process to acquire.
- Abandoned lock is not auto-stolen or repaired.
- Stale revision, stale source hash, missing hash, and malformed committed data fail closed.
- Simulated interruptions before/after candidate creation, file fsync and rename yield a full old or full new task+journal pair.
- After ambiguous SENDING transition, recovery keeps the pending operation as UNCERTAIN, blocking blind dispatch.
- NORMAL task edits yield no queued GitHub operation.
- A noncooperative external edit keeping the same revision is detected if it happened before the initial hash comparison.

## WATCH OUT FOR

**This is not the production Quickshell storage implementation.** The existing `ApolloHubTodoStore.qml` remains the sole live task writer and does **not** participate in this test lock. Other applications and scripts can ignore the lock, and a hash comparison does not eliminate every time-of-check/time-of-use race with noncooperative writers.

Local filesystem `mkdir` exclusion is appropriate only for cooperative writers on compatible local filesystems. A crashed writer leaves a stale lock requiring explicit operator-controlled recovery. The fixture deliberately does not use PID-liveness checks or automatic lock deletion because process IDs may be reused, remote state may be uncertain, and an incorrect cleanup could allow lost updates.

An injected exception after rename can produce an **uncertain local commit result**. The current running-process file state may be inspectable, but this does not prove power-loss survival before directory fsync. No kernel crash, hardware failure, actual disk-full exhaustion, NFS semantics, adversarial symlink swap, strong cross-process transaction, or real Quickshell `FileView` behavior is verified here.

The fixture uses a single snapshot revision and a cooperative lock, **not** a general SQLite transaction or a final persistent store. M10b's prototype journal still has unresolved migration/time metadata and remote identity semantics. These limitations require explicit resolution before any live migration or synchronization.

## CHECKLIST

- [x] Cooperative exclusive writer gate on disposable file
- [x] Owner token and stale-lock denial
- [x] Revision and content-fingerprint guarded commit
- [x] One-envelope data + journal commit simulation
- [x] Ambiguous write and uncertain-remote recovery tests
- [x] Separate CI workflow
- [ ] Independent source review and CI success confirmation
- [ ] Operator-authorized PR merge
- [ ] Real backend selection, ownership lifecycle and migration protocol
- [ ] Operator-authorized on-device acceptance and activation

## NEXT

Evaluate compatibility and complexity of a single versioned envelope managed by one Quickshell writer versus a transaction-capable service. The live UI must preserve old Apollo Hub, TODAY and PLANNER snapshots until a separately approved migration has passed backup restoration, restart and local runtime tests.

## DECISIONS

Proxy 1 retains storage/journal contract ownership. Proxy 2 owns PLANNER. No `TasksW.qml`, `shell.qml`, `ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`, GitW, local user files or GitHub Project records are modified. This does not register a Hospital session or promote a role.
