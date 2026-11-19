# TimeW MACHINE // Paired V2 window + one-use consent fixture admission

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Desktop & Brave Recovery
STAFF ROLE // External Hospital-compatible DOC, no live Hospital registration verified
ASSIGNMENT // Coordinated pairing/consent verifier and durable one-use burn before two-command floating geometry
SCOPE // TimeW-only, no changes to Connections C3e/C5 or installed Brave host
STATE // DRAFT · EXPERIMENTAL · PRODUCTION HOLD

## IMPLEMENTATION

Existing merged milestones: #2058 (CI-only floating rectangle placement), #2059's durable SQLite geometry journal, and #2063 (journal mainline ancestry repair). All are reachable from the base main. They prove the test compositor can move an explicitly selected floating container and permanently record incomplete operations. They **do not prove the current Brave window matches a saved historical window**, nor that a real operator approved the change.

This milestone builds one **disposable admission coordinator**, not another independent recovery engine:

1. **External pairing assertion**: \`MachineV2PairConsent.py\` accepts a strictly structured, short-lived, Ed25519-signed binding containing an opaque browser window reference, checkpoint UUID, saved window key, current Sway con_id, app ID, monitor, workspace, and native session ID. It verifies the signature under an independently supplied pinned pairing public key. It does *not* produce such a signature, check a real Brave process, authenticate an extension origin or discover a real browser/OS mapping.
2. **Independent operator approval**: A distinct, independently supplied Ed25519 public key verifies a separate signed consent assertion referencing the **digest of the entire pairing payload** and the **digest of the full exact operation intent**: checkpoint, window key, live con ID, app/output/workspace, before and target rectangles and session. It binds a single grant UUID, operator seat, fixed action, and strict issuance/expiration window (up to 10 seconds). Same-key pairing and consent is refused, as are stale times, scope changes, replayed signatures, unknown fields and wrong seat/session.
3. **Irrevocable spend before dispatch**: A private \`OneUseSpendLedger\` stores only the signed grant UUID and SHA-256 pair/intent digests in owner-only WAL+FULL SQLite. It atomically refuses repeated grant IDs, reused pairs and reused exact intents across concurrent calls. A process crash after this spend burns the authorization and cannot automatically restore it. The separate V2 geometry operation journal still records \`prepared → dispatching → verified / uncertain\` before any Sway command.
4. **Fresh preflight + guard at BOTH geometry commands**: \`MachineV2PairedRehearsal.py\` first uses existing V2 saved/live matching to construct the exact operation digest. It verifies both independent signed statements and a separately supplied active-seat callback. It spends the grant before calling the existing disposable pilot. The pilot now optionally rechecks the callback before it starts and before each of its two commands. If it expires after resize, the move is not dispatched and the journal stays UNCERTAIN/manual review.
5. **Identical app IDs are not an identity strategy**: Tests show two Brave-like windows with the same app ID. A signed assertion for current ID 110 cannot authorize current ID 111 or any other saved key, checkpoint, output, workspace, before rectangle or target. The policy still labels the *real-world* persistent Brave identity unverified until a separate installed pairing issuer has been independently security-reviewed.

There are no production key files, signing functions, native host installers, TimeW UI controls, real Linux seat queries, C3e/C5 API calls, browser tab APIs, production Sway commands, journal resets, automatic retries or automatic undos in this PR.

## HOW TO USE

**Only** through GitHub Actions CI in a disposable test environment. No user-visible application action exists:

\`\`\`bash
python3 -m pip install cryptography==46.0.4
python3 -B -I tests/timew/test_machine_v2_pair_consent.py
\`\`\`

Fixture test signers are generated in RAM, are distinct for pairing and consent, are never stored or installed, and prove only cryptographic contract consistency. The injected Sway reader and writer are simulated. Existing separate native stock Sway geometry capture/placement CI continues to prove actual compositor syntax, not this fixture's installed signing provenance.

## VERIFY

The test harness runs a private V1+V2 geometry SQLite checkpoint, two same-app live Brave-like floating windows, two independent signed Ed25519 role assertions, a private durable grant-spend DB and the original geometry operation DB. Test cases include signature/role substitution, edited signed payloads, wrong monitor/window/checkpoint, wrong seat/session, expiration, same-key two-role attempt, state preflight, no double dispatch, expiry between two commands, pending journal hold, subprocess restart proof of grant consumption, and concurrent attempts spending the same grant.

The dedicated workflow also reruns merged V2 durable-journal tests, fake two-window geometry placement, read-only planner, and original one-click V1 restoration contracts. **Passing source/CI tests is not installation, authorization or acceptance.**

## WATCH OUT FOR

- **Real trusted pairing is NOT implemented.** Pairing signature verification checks key possession only. An untrusted signer could sign a false Brave-to-Sway mapping. An independently installed pairing issuer must prove native browser/window association with a separate protected process/peer-origin trust chain before granting it authority.
- **Real operator consent is NOT implemented.** Consent signing is simulated with ephemeral CI keys. The actual signing service must enforce interactive, per-operation, unprivileged-to-protected C5 consent, kernel-backed seat/session liveness and established trust provenance. No TimeW source can supply its own "approved" flag as production authority.
- **Two SQLite ledgers are not one atomic transaction.** The signed grant is burned *before* geometry journaling. A crash between them must remain a consumed but unused grant; this is fail-closed and cannot be silently retried. Future operational recovery requires an independently approved reconciliation protocol.
- **Race and same-UID threats remain.** The session can change between Sway's IPC reads and writes. SQLite's owner-only permissions do not protect against a malicious same-UID process. Signed keys and trusted time/seat provenance are the responsibility of an installed native issuer; C3e/C5 ownership remains external.
- **No real multi-window Brave restore yet.** Only existing manually selected floating windows, already on their saved output/workspace, can be moved in the test. No tab restoration, tiling tree reconstruction, cross-output migration, browser profile recovery, process relaunch or native workstation activation.

## CHECKLIST

- [x] Verify #2058, #2059, #2063 GitHub state and actual journal on main
- [x] Inspect existing C3e/C5 issuer and Brave marker limitations
- [x] Bind separate signed pairing and operator-consent assertions to exact geometry
- [x] Add durable one-use grant burn and per-command revocation guard
- [x] Add two-Brave simulated security/regression matrix
- [x] Add dedicated CI workflow and runbook
- [ ] Exact-head GitHub CI verified
- [ ] Independent Nurse 2 security review
- [ ] Independently installed pairing issuer with authenticated native/browser/Sway identity
- [ ] Independently installed C5 one-use human authorization and protected key custody
- [ ] Native SwayPX acceptance and operator merge/production approvals

## NEXT / DECISIONS

**Do not merge or activate as a production restore capability.** Nurse 2 must review signature schemas, role/key separation, strict canonicalization, expiry, exact geometry/seat binding, SQLite spend concurrency and crash/replay failure modes. After verification, coordinate with Connections owners for an installed/native pairing issuer and real C5 human consent. Keep this implementation under TimeW ownership; do not edit or claim authority from Connections' code. User acceptance and production activation remain separate decisions.
