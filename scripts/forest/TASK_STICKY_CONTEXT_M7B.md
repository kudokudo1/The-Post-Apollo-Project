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
