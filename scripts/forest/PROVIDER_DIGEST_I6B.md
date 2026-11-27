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


## H17c // Actual thinking metadata acquisition boundary (design only)

H17 #2993 and H17b #3004 are integrated. The latter parses supplied
version/show JSON, not an observed provider identity. Nurse scoped
retrospective source ACCEPT #7215888498; #2161 7215900871 retains actual
native/protected/production HOLD. No second capability registry.

### Upstream source investigation

Ollama v0.32.14 exact release d67ad83426633195089509347ffd4fe795120198,
server/routes.go 3a027a9e, ShowHandler/GetModelInfo and
internal/modelref/modelref.go e58fa22e, establish a concrete limitation:
a POST to /api/show can be forwarded to cloud when a model reference
selects cloud, including the legacy -cloud tag suffix. A loopback
destination does not prove that the server stays local. Explicit
:local is a source selector, not part of the base artifact tag.
ShowHandler rejects a remote-host model for that selector, but the
local metadata path can still inspect its configuration first. This
is evidence about that exact upstream build, not an attestation of the
installed daemon or an independently enforced egress boundary.

The same release's ShowResponse has no thinking values/default
descriptor. Upstream 8ae8acb81afba9c3c67adf08190964eb7d1207ef has one;
its ShowHandler still has a cloud proxy branch, supports runner
selection and may report multiple manifest summaries. Version alone
does not identify the selected runner/artifact. Do not infer a supported
mapping from a model's name, a generic thinking capability or an older
provider response.

GetModelInfo returns much more than the desired descriptor: system
instructions, template, stored messages, model information, modelfile
and possible remote host/model details. Discarding those fields after
receipt is not authorization to receive them. No protected body or
remote metadata acquisition is approved by H17b's pure parser.

### Candidate acquisition sequence and gates

The next source-backed step requires the actual authorized provider
owner to establish an eligible local metadata source before any
request, rather than adding an unguarded /api/show CLI.

- Identify the exact runtime release, instance/endpoint and allowed
  local artifact and metadata scope independently. Require actual local
  routing/egress constraints and independently qualified selected
  manifest/runner identity; a string suffix, localhost, tags digest or
  caller boolean is not sufficient. If the actual source cannot ensure
  those prerequisites, hold without contacting it.
- Prefer a qualified minimal descriptor-only projection if one exists.
  Otherwise full ShowResponse acquisition itself requires independently
  authorized access and processing of its possible extra fields.
  No raw response logging, persistence, UI disclosure or cross-Tree
  transfer; restrict output to the independently allowed fields.
- For a specifically reviewed upstream-compatible local source,
  investigate exact base artifact plus explicit local selection and a
  fixed minimal non-verbose request, no arbitrary option map, remote
  model, fallback, load, inference, credentials, pull or retry. Reject
  remote indicators and ambiguous or changed manifest/runner coverage.
  This is a candidate request shape, not executable authorization.
- Reuse B0 target validation, P0 version/strict bounded decoding, I6b
  selected tag/digest comparisons and H17b descriptor parser only where
  their limits are satisfied. Bracket a prospective observation with
  independent version/artifact/currentness observations; retain exact
  source/clock and selected original lineage. Equality is not atomic
  identity, continuity, independent authentication or ABA prevention.
  A byte cap alone is not an aggregate time/work bound; use a reviewed
  finite whole-operation deadline and no hidden network progression.
- Preserve explicit false versus absent/unknown and exact advertised
  values/default. Missing descriptor on a qualified older build does
  not authorize invented levels. Before actual model dispatch, Runtime
  must bind supported effective options to original versioned serialized
  settings and Mind's eligible payload; Heart recalibrates resources.
  No silent default, alternate model or retry of uncertain effects.

No actual endpoint called, no chosen native collector, no provider
upgrade, no live option or credential, no new permission source.
Do not expand existing I6b observe CLI or H1/B2 settings in this slice.
Runtime/Spirit/Connections must identify a real qualified source and
recipient boundary; Heart owns descriptor interpretation and resource
qualification. Retain HOLD for actual acquisition until these are
established. Ordinary safe development and disposable CI remain active.
