# R6g // Canonical generation checkpoint adapter (unmounted)

Dependency: #2791 exact qualified head `74d8a561`, which must land on main first. Retarget this draft to updated main and rerun CI before merging; do not merge into the dependency branch.

The existing one-shot desktop adapter adds an explicit generation namespace, selected by its trusted caller. Legacy LOAD/SAVE remains the default. GEN_LOAD, GEN_SAVE and GEN_ADVANCE check the request envelope, bounded canonical reply, session generation, operation and ticket; SAVE must echo the exact record, ADVANCE the exact next storage generation and action ID, and LOAD a locked snapshot. The mode is pinned on first accepted request. Failure/timeout retires the adapter. No result grants startup or execution authority. No raw helper API is exposed to DOC 2.

The existing R6f native fixture now uses this actual reusable QML adapter, not a second test-only helper parser. The supervisor's pidfd and database lock checks, independent persisted receipt and original-byte assertions, and three scenarios remain unchanged. Legacy native regression must continue to pass.

Still unmounted: canonical owner process wrapper, child exit gate, Hub, watchdog, visible controls, installed deployment, committed-action retention and operator acceptance. Adapter does not establish backend identity, own the child or authorize an advance. The caller remains responsible for exact retired child exit before GEN_ADVANCE, and fresh validated load before reconstruction. No activation or protected action.
