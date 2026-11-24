# Forest I6 // Runtime membership diagnostic

PATIENT: The-Post-Apollo-Project · ROOM: Spirit measurement infrastructure
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator continued from I5 #2466 merged 08fa1aeb. I1–I5 independent
reviews outstanding at base inspection. Four additive Core-only paths.
Reuse I4 bounded stat parsing and I5 anchored cgroup selection/counter
reader. No duplicate resource accounting, process discovery or service.

Correlate explicit existing same-effective-UID process selections with
one non-root cgroup-v2 hierarchy. Up to sixteen distinct numeric PIDs.
All four kernel UID fields must equal the observer effective UID.
Read fixed stat/status/cgroup files, retain process and group directory
descriptors, inspect only kernel executable device/inode metadata
(no executable content or link-text read). Compare start ticks, owner,
component-wise membership, executable and directory references within
and across observations; re-open selected paths at end; compare boot
and mount references. Refuse changed observed references; close all
handles on failure. Public projection includes only counts of selected,
direct/descendant members and distinct executable inode references.
No raw PID, UID, boot ID, path, executable reference or private content.

This is observational membership consistency, NOT a release digest,
authenticated runtime instance, actual model identity, complete group
roster or continuous custody proof. A process could exec the same inode,
move out and back, or change after checks. No proof against ABA or
namespace differences. Processes not selected may still contribute to
cgroup charges. Never divide group memory by model count or attribute all
bytes to a selected process. Provider claims from B0/P0/P2C remain
separate; exact artifact digest and runner-to-model linkage are not
established. I2 references and I3 calibration requirements stay HOLD.

## HOW TO USE
After independent review, merge and operator acceptance, select actual
existing group and same-owner PID(s). From repository root:

    python3 -B scripts/forest/runtime_membership_i6.py correlate --cgroup "$group" --pid "$PID"

Repeat --pid for another known process. No sudo; if Ollama is a
system service under a separate account, this diagnostic refuses that
process. Do not weaken access or move processes to make a report.
Do not launch a model to collect measurements. This is no authority
for any native inference or private operation.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_runtime_membership_i6.py' -v

Tests include real Linux self metadata and disposable child membership
read, plus fixture correlation, path/owner/migration/identity refusal,
bounded selection, fixed read allowlist, handle cleanup and privacy.
Native tests do not claim whole public correlation on actual Ollama.
I5/I4/I3/I2/P1 regressions included.

## WATCH OUT FOR
No new privilege, executable authentication, provider calls, process
enumeration, network, mutation, storage, actual model attribution or
resource allocation. Observer cannot prove complete membership or
exclusive workloads. Same-user-only rule is intentionally conservative
and may block service-owned Ollama; genuine service identity mapping
requires a separate approved method. No dependency on C4b producer
authority or changes to its implementation. Hardware deferral respected.

## NEXT / DECISIONS
Independent review. Before further native trial work, agree a bounded
read-only exact provider model digest observation and service/runner
mapping method (including separate-service UID accessibility); keep
GPU/device-wide counters distinct from attributable allocations.
No new service or trial approval. Production HOLD.
