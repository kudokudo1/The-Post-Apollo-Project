# MACHINE // Offline Transfer Plan & Recovery Evidence Contract

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
ROLE // External Hospital-compatible DOC; live Hospital registration unverified
ASSIGNMENT // Metadata-only, deny-only future-transfer planning and synthetic recovery-state classification
SCOPE // New isolated contract module, in-memory tests, dedicated GitHub CI, this runbook only

## IMPLEMENTATION

This PR builds an **offline, non-executable planning contract** for a *possible future* ciphertext-only transfer from the ordinary-user Brave sealed vault to separate service-owned storage. No migration, service, privilege grant, archive deletion, browser restore, native host, ledger file or operational CLI is added.

The two prerequisites are independently open draft PRs:

- #1898 source inventory: `offline_migration_inventory_preflight` and SHA-256 inventory.
- #1906 protected target observation: `ci_only_protected_destination_observed` and SHA-256 inventory.
- #1900 protected destination isolation and synthetic rollback: separate independent CI tests.

This module targets their **documented response schemas only**, without importing a draft branch. It imports only the existing merged strict vault UUID/hash/size constants. All three remain independent review gates; this PR must not presume they are on `main`.

**`build_plan(source, target)`** checks exact shape, absent positive authorization flags, sorted UUID records, strict timestamps, sizes, SHA-256 fingerprints, no source/destination UUID collision and combined record capacity. It returns only encrypted record IDs, creation timestamps, sealed file sizes, hashes and observation fingerprints. The output always says `migration_authorized:false`, `restore_allowed:false`, `read_only:true` and `safe_actions:[]`. A matching digest is NOT a transfer approval.

**`append_fixture_receipt(plan, history, record_id, phase)`** adds a deterministic SHA-256-chained *synthetic* event to an in-memory array. It validates plan binding, sequence, previous hash, record SHA-256 and strict phase transitions (`staged`, `published`, `observed`, `rolled_back`, `uncertain`). These records are **unsigned, non-durable and actor-untrusted**. Any actor can forge an entire hash chain; its validity only checks structural integrity.

**`reconcile(plan, before_source, before_target, after_source, after_target, receipts)`** compares new sampled metadata against the original plan, refuses malformed or stale plan inputs, and detects source drift, altered existing destination records, unexpected target IDs, mismatching new record hashes and contradictory receipt claims. Returns only observed states: `no_new_records_observed`, `partial_records_observed`, `all_records_observed`, or `manual_reconciliation_required`. Even `all_records_observed` is **NOT proof of a successful authorized migration**. Every output keeps `requires_independent_human_review:true`, `fixture_receipts_authenticated:false` and all permission flags FALSE.

## HOW TO USE

**No desktop button, local command, live migration or service activation.** The module's `__main__` exits with code 1 and has no executable production entrypoint. GitHub CI exercises the pure functions with synthetic dictionaries only:

```bash
python3 -B -I tests/timew/test_machine_offline_transfer_recovery_contract.py
```

This test is safe only as repository verification, not an instruction to handle real archives. Do not interpret or use a generated plan as authorization to copy, delete or restore user files.

## VERIFY

The in-memory regression checks valid exact source/target schemas, baseline/partial/full observations, deterministic hashes, conflicting IDs, UUID/capacity constraints, empty/absent vault, forged positive authorization, malformed timestamps/metadata, duplicate/unsorted files, changed fingerprints, source drift, sentinel overwrite, unexpected target records, out-of-order/replayed/modified hash-chain events and inconsistent publication/rollback statements. Existing sealed vault and deny-only request/deadline tests also run.

Actual kernel identity, SELinux, service deployment, power loss, transactional crash recovery, independently authenticated release witness, backup integrity and C5 human consent are **not** tested here. The prior #1900 and #1906 CI tests remain distinct.

## WATCH OUT FOR

- **Source #1898 and target #1906 remain draft**, so this schema-level contract may need integration reconciliation when their reviewed code lands.
- The SHA-256 snapshot and hash chain are **not signed by an authority**, not durable, not protected against malicious same-UID modification, and not a chain-of-custody proof.
- This code has no filesystem access. A future persistent ledger requires an independently authenticated protected writer, fsync/atomic ordering and recovery from crash/power loss. A fixture event such as `published` must never be trusted just because a checksum matches.
- An absent/uncertain record requires manual investigation, not blind retry, deletion, or rollback.
- Real migration requires operator-approved destination, separate UID, full path/SELinux custody, independent backup, trust witnesses, one-use C5 intent and independent review. No production archive broker permission is opened.
- No local desktop, Brave profile, Quickshell, running service, Unix account or user archive is touched by this PR.

## CHECKLIST

- [x] Reconcile Syntagma and current MACHINE branch/PR ownership
- [x] Write exact-schema metadata-only plan with fail-closed conflicts
- [x] Create unsigned in-memory event chain and strictly negative recovery classifications
- [x] Add independent test and workflow without editing other workers' open branches
- [ ] Exact-head CI and security review of this branch
- [ ] Independent Nurse 2 reviews of #1898/#1900/#1906 and this contract
- [ ] Operator review and explicit merge/host-deployment decisions
- [ ] Full protected service custody, signed evidence, C5 consent and crash-safe migration design
- [ ] Authorized Brave restore and multi-monitor layout integration

## NEXT / DECISIONS

Stage this PR as an independent **draft for review**. Do not merge or deploy automatically. The future MACHINE implementation milestone may plan an authenticated persistent receipt journal and crash tests, but only after the owning #1898/#1900/#1906 contracts are reconciled and reviewed. Connections C3e and C5 keep their separate authority and ownership. Operator acceptance alone controls final DONE.
