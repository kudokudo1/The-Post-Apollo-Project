# 🏥💜 TASKS // M13t Source-Bound Consent Review (Disposable)

**PATIENT //** kudokudo1/The-Post-Apollo-Project
**ROOM //** TASKS opt-in encrypted recovery
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible; live registration unverified
**PERMISSIONS //** Bounded GitHub test/CI/docs only. No local workstation changes, shared Connections edits, actual keyring operations, production activation or automatic merge.

## IMPLEMENTATION

M13s PR #1286 is merged. It observes real TASKS entry/details dirty flags but does not preserve drafts. M13p defined three exact separate scopes: encrypted draft capture, unlocked preview, and encrypted checkpoint deletion. The shared CPU++ Connections credential broker is still deny-all.

M13t adds an **unmounted Node-only disposable test model**, TaskRecoveryConsentSourceM13t.cjs, and regression coverage. Client requests can propose only the three fixed M13p scopes. A distinct syntheticOperator test facade simulates opt-in, approval, denial and revocation. The initial state is OFF; each approval expires, is restricted to its original scope and can be consumed only once. Any forged request shape, replay, expiry or opt-out is refused.

The model independently reads **synthetic saved-source bytes** from a test-harness-held reader, binds the review to the SHA-256 digest, and checks the bytes again before approval and consumption. A private random in-process HMAC binds the test receipt to request ID, scope, source digest, generation and expiration. It exports no proof, source content, draft text or encryption key. All returned production permission flags remain false, including key release, capture, preview, restore, deletion and source writes.

Only the test harness creates/removes a temporary fake JSON source in a newly created private postapollo-m13t-disposable-* directory. No actual TASKS source, OS keyring, credentials, desktop widgets, or service is accessed by this fixture.

**Critical security boundary:** syntheticOperator is an ordinary in-process test facade and does **not** authenticate a human, trusted caller or OS host. A SHA-256 comparison is a point-in-time byte observation, not an independently trusted monotonic revision or an exclusive lock. It does not defend against post-check changes, ABA restoration of identical bytes, a same-user malicious process or actual reboot loss. M13t is **not** production consent or encrypted recovery.

## HOW TO USE

No desktop action. After review, CI runs the Node test from tests/tasks/test_task_recovery_consent_source_m13t.cjs.

The accepted UI remains CPU++ → SETTINGS → CONNECTIONS → TASKS for keyring/status, and TASKS → SYNC → RECOVERY for in-memory editor presence.

## VERIFY

The new tests cover: non-disposable invocation refusal; default-OFF consent; all three fixed scopes; invalid provider/wildcard/extra-field denial; separate synthetic approval; single-use/replay rejection; cross-scope mismatch; source modification before approval and before consumption; expiry, denial, opt-out and unavailable source; absence of keys and task content in public results.

GitHub CI reruns M13p, M13s, C2a and M11d regression guards, including the single existing TASKS writer and deny-all shared broker. No production import or OS keyring actuation is permitted.

## WATCH OUT FOR

Connections C2 host status is observational; same-UID socket evidence does not authenticate an application. Do not use a UI click or provider label as permission to release secrets. The source digest does not validate full source schema, provenance or durable write completion. The actual source revision and key-release host are shared ownership work and have not been implemented here.

## CHECKLIST

- [x] Recover M13s and M13p checkpoints and current code ownership
- [x] Build bounded disposable source/consent state machine
- [x] Test refusal, expiry, revocation, source mismatch and replay
- [x] Add CI regression gates
- [ ] Final-head GitHub CI and independent review
- [ ] Operator PR merge decision
- [ ] Coordinate genuine Connections host authentication with its owner
- [ ] Implement independent saved-source revision/first-create contract with TASKS owner
- [ ] Implement real opt-in key lifecycle, encrypted capture, preview, clear and restart/reboot acceptance

## NEXT

The CPU++ Connections owner must establish a genuinely trusted, revocable operator/host channel for those exact three scopes; the TASKS source owner must independently attest a last-confirmed revision and fence source writes. Only then connect actual editor contents to encrypted capture. Do not import this disposable model into production as a broker.

## DECISIONS

Preserve accepted CPU++ layout, single TASKS saved-JSON writer, status-only C2 broker, default-off recovery flags and no automatic network sync. No keyring or local machine mutation, merge or real recovery activation in M13t.
