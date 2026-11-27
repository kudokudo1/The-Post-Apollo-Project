# Post-Apollo test contract strength · V1 proposal

Status: proposed, opt-in, source-only. This does not supersede Syntagma,
Hospital OPERATE, existing protected approvals or current test ownership.

## Purpose

Tests should protect the operator's actual requirement, not accidental source
spelling. Some source spelling **is** the requirement. Preserve it explicitly.

## Four enforcement classes

| Level | What is locked | Appropriate evidence |
| --- | --- | --- |
| EXACT | Operator-approved literal declaration or implementation form | Exact source assertion; intentionally fails on formatting/refactor |
| STRUCTURAL | Required ownership, dependency graph, count or forbidden path | Structural parser/import/binding checks; no duplicate owner |
| BEHAVIOR | Observable input/output, state transition and failure modes | Executed function or component cases including negative cases |
| NATIVE | Real QML layout, pointer, keyboard and lifecycle integration | Disposable Quickshell fixture with actual runtime assertions |

Use multiple contracts when several requirements apply. An exact lock does not
replace behavior and native checks. A passing source test is **not** proof that
pixels, gestures, process safety or host authority work.

## Requirement declaration

Every newly classified requirement must record:
- Stable requirement ID and owner; owner approval for EXACT lock changes
- Rationale describing what must remain true
- Enforcement level and actual test entry point
- Positive witness and a negative/regression witness
- Scope, fixture type and evidence limitations

Default to BEHAVIOR for functionality and STRUCTURAL for ownership/integration
rules. Choose EXACT deliberately for approved source forms or protected
declarations. NATIVE is required when actual rendered/interactive operation
matters; do not replace native tests with string checks.

## New helper

`tests/contract_levels/contract_levels.py` provides opt-in declaration and
assertions. `exact_source` pins a literal. `structural_invariants` checks named
boolean conditions (callers must show how those were derived).
`behavior_cases` executes real callables. `native_fixture_required` may
consume a **real external fixture's result**; it does not run QML or produce
native evidence by itself.

Example, operator-locked declaration:

```python
locked = Contract("H1-WRITES", "Hospital owner",
    "Protected writes must remain source-disabled until admission", "EXACT")
exact_source(locked, doctor_qml,
    "readonly property bool protectedDoctorWritesReady: false")
```

Example, equivalent implementations:

```python
behavior = Contract("KILL-FILTER", "KILL owner",
    "Stable results for same identity and filter", "BEHAVIOR")
behavior_cases(behavior, filter_fn, [((rows, query), expected_rows)])
```

These examples are illustrative, not registered requirements.

## Change protocol

1. Locate original requirement and current owner; do not silently downgrade.
2. Classify strength with evidence. An explicit operator lock stays EXACT
   until operator/owner authorization changes it.
3. Add a regression witness that fails for the actual defect, plus positive
   evidence for the approved behavior or structure.
4. For native behaviors, preserve a disposable runtime fixture and its
   isolated/no-write boundary.
5. Review on a separate branch and show exact-head CI results. No automatic
   merge, protected writes, host installation, or bulk test rewrite.

## CI feedback

A failure should identify a requirement ID, enforcement level, actual evidence
and owner in the review report. Existing workflow names need not change in V1.
One red check can contain unrelated failures; do not infer causality from a
PR title or a stale run.

## Scope and non-goals

V1 provides the shared vocabulary, an opt-in helper and self-tests. It **does
not** automatically reclassify pre-existing tests, replace Native QML
integration, or waive security gates. Incrementally migrate brittle tests by
owner-reviewed PRs. Keep current safety protections even if a string test is
replaced with stronger behavior or structural evidence.
