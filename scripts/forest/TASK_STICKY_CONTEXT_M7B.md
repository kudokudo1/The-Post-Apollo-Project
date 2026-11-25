# M7b // Original Forest task-sticky context reuse

DOC4F, recovery #7160677299. Dependency M7a #2683 (must land first).
Original read-only Bristlecone learning/context_state.py 98b1447f,
cache/entry.py c3c3ddfb and cache/coordinator.py e5b2107f: meaningful input
invalidates routing, independent knowledge clocks invalidate only affected
pools, policy invalidates both, cached values are disposable derived data.

Current adaptation reuses M7a immutable selected records/route/assembler
and B6 TaskContext. One TaskStickyContext per exact context lifetime;
independent owner observation HotDependencies, monotonic clocks, explicit
new route selection, current selection only lookup and insertion. Execution
steps reuse exact route. Later input may reselect retained immutable records
but cannot read an old route. Missing records are reported, no automatic
retrieval. Domain invalidation does not erase durable knowledge. Same-key
different content in one retained generation refuses, insertions atomic;
at most 32 retained records total, each <=4096 UTF-8 text bytes. Evict only
unselected cached records when capacity reached. Close permanently discards
derived values, not a deletion from a durable store or proof of freed RAM.

This is a narrow task-local fixture, not the original full shared cache,
authoritative snapshot store, concurrent historical retrieval, seasonal
state machine or model-facing context. Independently establish knowledge
provenance, policy and currentness before using it. Old in-flight turns
do not gain a cache write path; immutable results retained externally are
not revoked or granted authority by cache invalidation. No model/IO/DB,
new daemon, automatic approval, or R6 contract changes. Future shared
snapshot caching and actual retrieval require agreed durable authority.
M7c will add explicit selective derived shedding/rehydration semantics,
not host process or model eviction.

## M7f-a // Version-aware sticky context recovery proposal

DOC4F; Nurse2F #7170579213 authorizes architecture development.
M7d-b #2777, M7e-a/a1 #2782/#2795, M7e-b #2803 integrated; M7e-b
ab745866 raw 139409077924 124/124 Python tests, Nurse #7170575913.
Original frozen 28895aaf cache/entry.py c3c3ddfb and coordinator.py
e5b2107f require exact dependency/schema matching before reuse and
allow invalidation of disposable entries. Archived doctrine 533c3c98
sections 7–10 calls for reuse-or-rebuild of affected semantic layers,
separate from provider runtime prompt/prefix caches. Recover semantics,
not the old generic cache or Hermes prompt storage.

### Concrete gap

Current TaskStickyContext 52c1d304 has one lock, two bounded pools and
one route. remember stores SelectedHotRecord keyed by record ID, with
domain snapshot generation, not immutable source revision. lookup
checks IDs and clocks only. assemble projects directly into M7a.
M7d-b explicitly withholds cache insertion; M7e-b independently checks
exact selected public version/commitment and recomposes. Reusing the
existing version-blind route for a retrieved record would discard the
evidence required to compare its exact source and current eligibility.

### Proposed existing-cache evolution (not an API freeze)

Keep one TaskStickyContext, one lock and the existing two pools. A
lifetime is explicitly selected as legacy synthetic or versioned public
fixture at construction; no in-place mode switch, no second controller,
shadow pool or sidecar provenance map. Legacy fixture calls remain
compatible, but never return versioned data or infer provenance.
Versioned mode rejects all legacy route/remember/lookup/assemble calls;
no fallback, stripping provenance, implicit upgrade or importing legacy
entries. Existing count, close and selective shed semantics retained.
Use the current M7a record as a derived projection nested within one
immutable versioned entry, not a second retained text copy.

One retained entry binds exact owner-local TaskContext, source, record
ID, kind, immutable positive revision, record generation, content
commitment, and domain snapshot generation; purpose and intended
recipient fixed for the initial fixture lifetime. Metadata fields are
bounded and typed; version values follow M7d-b semantics. SelectedHotRecord
generation remains the snapshot ceiling, never relabeled revision.
No public private-derived hashes, record IDs, counts or bodies. Retain
no positive grant or authorization token in an entry. A digest is an
integrity comparison, not source authentication. Fixed public fixture
metadata only; production must not import test types.

One installed selection binds original route plus ordered exact version
tuple, fixed source/purpose/recipient, independent current eligibility
observation and input/policy/domain clocks. Independently held current
selection and use/revocation facts supplied on every route installation,
admission and reuse; never obtain them from the cache or reconstruct
them from remembered values. Empty selection still validates scope.
No live resolver, callback, external read, provider or lock-held I/O.
For a real custodian, independent authority and atomic read/revoke/use
ordering remain separately required; local lock is not a protection
against external revocation. Synthetic observations are not authority.

### Reuse and invalidation

1. Validate types/bounds and independent current task, purpose,
   recipient, source, policy and complete exact selection metadata
   before exposing any cached content. Observe valid newer dependency
   clocks as existing M7b does; regressions refuse without replacing
   newer state. Unknown currentness blocks return, never falls back.
2. Input change invalidates installed selection but may retain entries.
   Policy change clears both; respective domain clock change clears
   affected pool. Source/purpose/recipient change retires this fixture
   lifetime; no transfer to a new destination. Exact source/version/
   commitment mismatch even with same domain clock is a conflict, not
   an ID hit; discard affected derived entry and refuse selection, require
   fresh independently observed selection. Conflicting same-clock
   metadata must not silently replace an immutable retained value.
   Revoked/unknown selected use blocks whole composition; explicit
   revocation discards that derived entry. A new authorized selection
   does not resurrect previously revoked data; explicit resupply needed.
3. Admission checks every provided entry against exact selected immutable
   versions and separate current use facts, verifies strict UTF8 body
   commitment, domain and projection generation before modifying pools.
   Atomic candidate copy under the existing lock. A refused batch adds
   no entries; independently valid invalidation may still remove old
   entries, as M7b/c. Do not permit unselected admission. Retain at most
   32 entries across both pools, 4096 UTF8 content bytes per record,
   bounded metadata (source/record/purpose/recipient keys <=128 ASCII,
   revision/generation <=2^53-1, raw 32-byte commitment). Evict only
   unselected retained entries as existing M7b; no unbounded tombstones
   or historical cache. No claim of exact Python heap/RAM consumption.
4. Lookup checks the whole selected version tuple and all current use
   observations before returning content. Return exact versions with
   ordered selected projections as one immutable result, never bare
   records on a versioned route. If any selected entry is missing,
   return bounded missing metadata only, no partial body projection;
   explicit owner supply required, no auto-retrieval or latest fallback.
   Recheck currentness before assembly; M7e verifies exact version
   evidence again and accounts combined history/reference budget.
   No cached assembled workload or final provider payload reuse.
5. Shedding clears chosen derived domain(s), invalidates route and
   preserves existing strictly-newer-input reselection fence. Retained
   unaffected entries still require exact fresh selection/use checks;
   explicit resupply for missing versions. close permanently retires
   lifetime. No durable deletion, actual seasonal transition, external
   copies erasure, provider KV reuse or claimed physical RAM release.

### Proposed M7f-b executable scope (requires owner/Nurse agreement)

Extend existing M7b cache in-place, preserving legacy tests and existing
bounds. Only fixed-public, one base-CHERRY task and fixed source/
purpose/recipient; supplied public records and independent fixture
observations, no source access, actual authority, protected data, new
store, matcher, R6 or Runtime/Heart source. Do not import M7d/e test
types into production source; use bounded owner-local fixture value
types in the existing module after interface review, with explicit test
projection to M7d/e. No positive grant or model-facing representation.
Negative/positive matrix:
- exact revision reuse across newer input, partial miss metadata only,
  changed source/commitment/revision/domain with same clock, future and
  stale scope, superseded/revoked/no-current-use version, duplicate/
  reordered selection, mismatched body, empty stale selection;
- legacy/versioned downgrade refusal, policy/domain invalidation,
  wrong task/recipient, capacity and atomic batch refusal, no implicit
  latest fallback, selective shed and close, no resurrection;
- exact version evidence survives selected projection into existing
  M7e public candidate, same joint budget and nonempty RELEASE_HOLD;
  no new serializer, cache admission path for private data, or dispatch.

DOC3F: ACCEPT/REVISE exact version/current-use/revocation ordering and
fixture mode isolation; protected custodian remains separate.
DOC2F: ACCEPT/REVISE owner-local lifetime/shedding/close vs actual Task
retirement and M7e recipient continuity; no R7 writer mutation.
DOC1F: ACCEPT/REVISE bounded derived content/metadata accounting, no
inferred physical release, token/demand or native admission.
Nurse2F: independently review this design and authorize exact M7f-b
fixture scope only after owner agreements. Real durable retrieval,
trigger matcher, authorized absorption, source/recipient custody and
model-facing representation remain separate. Production HOLD.
