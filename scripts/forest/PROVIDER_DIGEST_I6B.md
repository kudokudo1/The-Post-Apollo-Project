# Forest Heart I6b // Provider-reported digest correlation

PATIENT: The-Post-Apollo-Project · ROOM: Spirit measurement infrastructure
ROLE: external Hospital-compatible Forest Heart DOC · PRODUCTION HOLD.

## IMPLEMENTATION
Continuation of merged I6 #2472 (e843f145). B0 and P0 intentionally
discard digest fields. This additive observer validates an explicit
exact model name and compares its full SHA-256 provider-reported digest
across GET /api/tags, GET /api/ps, GET /api/tags, optionally against a
caller-supplied expected digest reference. Selected installed record
changes, conflicting digests, missing/invalid selected digests, duplicate
records/JSON keys, and resident-without-installed claims refuse. No
fallback to alias, short digest, or other model. Unknown numeric fields
remain null. Public projection omits names, digests and raw responses.

Reuse B0 literal-loopback target and validation and P0 residency
transport and parser. Tags transport uses P0 strict JSON because the
existing B0 JSON decoder does not reject duplicate keys. No existing
adapter changes, new service, polling, retries, process discovery,
inference or privileged access.

## HOW TO USE
Only after review and operator acceptance, from repository root:

    python3 -B scripts/forest/provider_digest_i6b.py observe --model 'example:latest'

Optionally append --expected-digest with a full known SHA-256 reference.
Replace example with an actual exact installed name. No model is loaded.
No real native observation performed by the implementing worker.

## VERIFY
    python3 -B -m unittest discover -s tests/forest -p 'test_provider_digest_i6b.py' -v

Mock transport and parser tests; inherited B0/P0/P2C/I6/I2 regressions.
CI and independent review are separate gates.

## WATCH OUT FOR
Digest equality is equality of unauthenticated provider claims, not
hashing local model files, trusted runtime identity, continuous residency,
atomic snapshot, runner PID association or exclusive cgroup ownership.
Same-name tag ABA or provider replacement between GETs is not ruled out.
Reported resident bytes and VRAM are not measured per-process allocations
or calibrated requirements. No mapping to I6 process membership or I2
binding authority. Service-owned Ollama remains outside I6 same-UID
observer scope. No permission, resource reservation or production action.
No raw diagnostic values are published; operator-selected model input
may be visible to their local process list.

## NEXT / DECISIONS
I6b first slice: compare provider claims only. Protected service identity,
runner-to-digest linkage and evidence freshness need a separate owner
agreement; do not relax I6 UID guard or import C5 authority. Preserve
device-wide versus attributable accelerator measurements. Independent
review outstanding for I6 at succession. No auto-merge or production.
