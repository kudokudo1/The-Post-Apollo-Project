# 🏥💜 Trash++ U2 // Universal Lifecycle Preflight, DENY-ONLY

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
STAFF ROLE // External DOC-compatible; live Hospital registration not verified
ASSIGNMENT // Define a universal permission/recovery/retention/dependency *review* seam before any cross-owner Delete button migration.
SCOPE // \`scripts/trash/universal_lifecycle_review_u2.py\`, tests, documentation only. No U1 component modification, no protected V3b overlap.

## IMPLEMENTATION

U1 (#1936, merged) introduced review-only \`TrashLifecycleActionDeck.qml\` and a source-code deletion candidate scanner. V3a (#1941, merged) introduced an entirely separate, deny-only protected Archive migration readiness review. U2 complements these with a common **metadata-only** evaluation of a proposed Trash, Restore, or Burn action.

The U2 Python \`review(request)\` function:

- Accepts an exact versioned request envelope with action, *review-family* owner ID, opaque resource ID, 64-hex expected revision, storage scope, current state, retention, dependencies, recovery, writer stability, destination conflict, confirmation and an untrusted source-grant report.
- Never accepts a free-form path, payload, account, note body, task description, medical report, private key, user identity, arbitrary owner policy, positive \`approved\` flag or extra field.
- Pins conservative **review-only** classifications for existing GIO/managed-copy, Weather/research/Hub and illustrative future Hospital/company/social/Finance/Identity/MACHINE family labels. These labels do **not** establish real owner registrations, permissions, data classification, legal compliance, grant provenance or retention requirements.
- Returns sorted fixed blocker codes. Even a supposedly green \`reported_stable\` writer, \`restore_test_reported\` recovery, \`eligible\` retention, \`second_click_reported\` Burn confirmation or \`reported\` owner grant is untrusted. The output *always* sets \`trashAllowed=false\`, \`restoreAllowed=false\`, \`burnAllowed=false\`, \`productionAllowed=false\`, \`deleteOriginalAllowed=false\`, \`safeActions=[]\`.
- Holds unregistered owners, mismatched source scopes, all original source-owned writes, immutable protected Archive copies, sensitive/regulated owner classes, unresolved retention/hold and record dependencies, unstable source revisions or writers, unverified recovery, occupied Restore destinations, and every unverified irreversible Burn.
- Reads no source file/DB; never calls GIO, ArchiveStore, source-owner service, signer, Hospital or company API; has no CLI for acting on production.

\`ownerId\` labels such as \`hospital\`, \`company\` or \`social\` are future **review profile names**, *not actual trusted source or API identities*. Real owner identity must be verified by the owner-specific service before any future integration. The U2 reviewer never grants authority based on a name or a frontend Boolean.

### Request envelope

| Field | Scope |
| --- | --- |
| \`schema\` | Exactly \`post-apollo.trashpp.universal-lifecycle-review.u2\` |
| \`operation\` | \`trash\`, \`restore\`, \`burn\`; no generic \`delete\` |
| \`ownerId\`, \`resourceId\`, \`expectedRevision\` | Bounded opaque tokens and an exact lowercase 64-hex witness *format*; authenticity NOT established |
| \`resourceScope\` | \`gio-file\`, \`managed-copy\`, \`source-owned\`, \`protected-archive\` |
| \`resourceState\` | \`active\`, \`trashed\`, \`unknown\` |
| \`revisionWitnessState\` | \`unverified\` or \`reported_stable\` |
| \`retentionState\` | \`unknown\`, \`eligible\`, \`hold\`, \`mandatory\` |
| \`dependencyState\` | \`unknown\`, \`none_reported\`, \`linked\` |
| \`recoveryState\` | \`unknown\`, \`copy_reported\`, \`restore_test_reported\` |
| \`writerState\` | \`unknown\`, \`stable_reported\`, \`concurrent\` |
| \`destinationState\` | \`unknown\`, \`empty_reported\`, \`occupied\` |
| \`confirmationState\` | \`none\`, \`first_click\`, \`second_click_reported\` |
| \`ownerGrantState\` | \`absent\`, \`reported\`; **reported is NOT verified** |

### Actual authorization must remain external

Future source-owner adapters need all of the following, each independently verified *at commit time*, before any live action:

1. Source owner identity, isolated process/host trust and per-operation scope.
2. Exact record ID/generation/revision authenticated against the owner source and checked again under its writer lock/transaction.
3. Applicable retention rule, legal hold, privacy restrictions and dependencies. A request saying \`eligible\` is not proof.
4. For Trash, a durable recoverable snapshot or owner-supported reversible record lifecycle, with a tested Restore path and storage quota.
5. For Restore, an atomic collision/destination check, full record schema and relationship restoration, and safe failure recovery.
6. For Burn, a separate one-use human decision, eligible retention, independently protected receipt/custody, crash-safe purge semantics, and the correct disposal boundary (including derived copies/backups only where separately authorized).
7. Durable receipts proving what was performed without leaking protected content.
8. Source-specific failure/crash/concurrency and native host tests.

**Never** generalize a file \`rm\` command to an original SQLite/JSON source; do not invent a universal cross-owner \`BURN ALL\`. Hospital, Finance, company, identity, and evidence originals are protected by default. V3a/V3b are independent Archive security lanes and do not authorize general deletion.

## HOW TO USE

CI / developer unit test only:

\`python3 -B -m unittest discover -s tests/trash -p 'test_universal_lifecycle_review_u2.py' -v\`

The pure API can be exercised *in tests* with in-memory synthetic request metadata. There is no new Quickshell button or desktop workflow. U1 button handlers are unchanged, and neither U1 nor U2 can execute a lifecycle mutation.

## VERIFY

- Tests cover all three actions, every listed sensitive family, unknown/mismatched identities, wrong state, retention holds, linked dependencies, concurrent writers, incomplete recovery, occupied Restore targets, Burn without separate receipt, malformed booleans, privileged schema injection, path-injection strings and information minimization.
- The existing Trash Bottom-Left Launcher Contracts workflow runs the complete \`tests/trash/test_*.py\` suite on this module/test change, plus current JavaScript regressions.
- Meta Apollo Grammar and any affected existing workflows must pass at exact PR HEAD. Native Quickshell was not modified.

## WATCH OUT FOR

1. **This is not an authorization engine.** Even every input field claiming the most favorable state returns \`DENY_ONLY_OWNER_REVIEW\`. A source owner could *use* the risk checklist after an independently authorized workflow exists, but must never turn \`holdReasons\` absence into a grant.
2. The source-code inventory is heuristic and cannot prove all application Delete sites. U2 is about semantics, not an exhaustive UI migration.
3. Future source owners may use different IDs. Unregistered values deny until a separately approved source adapter is designed.
4. These conservative review classes are not legally definitive classifications. Actual statutory/policy retention needs owner/legal review based on real data type and jurisdiction.
5. Reading the review metadata does not inspect or protect the underlying user's information; there is no migration, backup, trusted key, protected receipt, permission service or state change.
6. V3b active ownership is respected; do not modify its protected witness, tests, workflow or source-owner keys.
7. No local host writes, no Quickshell reload, no real user record mutation and no PR merge/production activation under this assignment.

## CHECKLIST

- [x] Recheck latest main; U1 merged; V3a merged; V3b active in separate PR.
- [x] Add isolated U2 review-only module with strict envelope and no allow path.
- [x] Add cross-owner and malicious metadata tests.
- [ ] Exact-head CI and independent owner security review.
- [ ] U3: classify specific Delete buttons and migrate **one** already-recoverable owner action without changing protected sources.
- [ ] Future: protected source authority, robust owner-side recovery and independently authorized Burn.

## NEXT

U3 // First functional owner-approved integration, beginning with an existing recoverable Trash++ or GIO item. Use U1's new action deck only after owner review and revision/scope mapping. Preserve old behavior and never activate protected-system Burn by UI wiring.

## DECISIONS

This U2 contract is safety instrumentation for universal Trash++ development, not evidence of end-to-end protection for Hospital, company, social or other sensitive records. Browser session is Hospital-compatible but not verified registered. Operator retains merge/activation/final acceptance.
