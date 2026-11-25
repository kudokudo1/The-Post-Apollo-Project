# M7c // Selective seasonal derived shedding

DOC4F; recovery #7160677299 and Nurse2F continuation #7162318447.
Original frozen context_state.py 98b1447f lines 1221–1303 separately
clears route, user context, operational learning and all task-end data.
Original task_session.py a2458c4e lines 4413–4723 separates active season
transitions from Winter retirement and preserves a lightweight activation
snapshot for later review. Historical doctrine 15e4e11a distinguishes
Shedding from durable Pruning. No historical storage or authority copied.

Current M7b c545505c already invalidates dependencies and closes a cache.
M7c adds explicit exact-route domain shedding to that same cache under its
existing lock. Both or either domain may be cleared; selection is always
invalidated. Same-input route reinstallation refuses even after another
dependency changes. A newer independently observed input generation and
explicit selection are required; the owner must supply selected records
again for missing IDs through existing remember validation. Exhausted
generation refuses until a new owner-authorized lifetime; never wrap.
Invalid flags refuse before observation; legitimate newer dependency
observation can still invalidate stale caches even when a request refuses.

This fixture deliberately uses the existing input-generation fence instead
of adding another lifecycle clock. Owner must supply independent currentness
and revalidate record provenance; cache hits are not permission. Retained
other-domain values remain advisory, no implicit selection. No real season
transition, storage read/write, durable deletion, provider, process release,
physical memory guarantee, R6 wire change or restoration plan. External
copies of immutable records are not erased. Runtime owns actual lifecycle,
Security owns permission, Heart owns resource admission. M7d durable
retrieval requires owner agreement; no historical store or approval assumed.
