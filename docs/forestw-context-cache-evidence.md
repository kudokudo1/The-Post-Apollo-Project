# ForestW // Context and cache evidence

**Role:** ForestW UI DOC · **Production:** HOLD

## IMPLEMENTATION
Each existing model row now displays CTX REP from the same exact-name P0 residency record as its existing profile. Unavailable, stale, absent and missing observations remain ?. Row geometry, shared P0 adapter and manual scan paths remain unchanged. Context length is a provider-reported setting, not context occupancy or a model's architectural maximum.

BENCH adds a cold/warm comparison of imported P2B metadata. The reports must agree on exact model label, Ollama version and requested context/output/thinking/concurrency, and comprise one cold and one warm scenario; input order is irrelevant. Show both reported prompt-evaluation time, load time, first-visible-content latency and optional cached-token count, with signed warm-minus-cold deltas only when both counters are available. Missing cache count is unknown, not zero. No cache hit rate, causal speedup, actual retained KV-cache bytes or live context occupancy inferred. Existing A/B report import and clearing behavior unchanged.

## HOW TO USE
Forest → flower → SCAN ALL: read CTX REP on a resident model row. Open BENCH and import one cold and one warm P2B receipt for the same model/version, then scroll to CONTEXT / CACHE. No actual benchmark may be started by this UI.

## VERIFY
Existing profile and BENCH regressions now cover shared P0 context source, and actual P2B fixture-generated receipts with null, zero and nonzero cached counters, reversed report order, mismatched model/version/settings and signed deltas. Native layout acceptance separate.

## WATCH OUT FOR
P2B reports are pasted, unverified historical metadata. Matching labels and request settings do not prove identical hardware, model digest, prompt/cache identity or workload conditions. Warm residency does not prove cache reuse. No changes to runtime context, cache eviction, keep_alive, sessions, inference, authority or persistent preferences.

## NEXT
Forest Core owns actual context accounting and cache lifecycle, including exact execution-context/model identity, token-budget/occupancy semantics, retained cache state, safe reclaim and authorized control. UI will consume the reviewed projection rather than infer occupancy from prompt evaluation counters.