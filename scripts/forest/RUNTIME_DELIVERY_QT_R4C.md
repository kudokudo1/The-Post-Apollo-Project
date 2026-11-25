# R4c synchronous local Qt consumer witness

Test-only Runtime lane, stacked on the exact UI2.2a candidate #2608.
Do not merge into UI2's branch. Reconcile after reviewed UI2 merge.
This test exercises existing R3/B3/R4a/R4b producer and the actual UI2
JavaScript consumer inside one QJSEngine, on one owner thread. No
production sender, QML insertion, duplicate consumer, socket, scheduler,
private storage, or Ollama service. The host fixture independently selects
its current binding; it is not an authenticated provenance witness.

The callback takes only the already allowlisted six-field status unit,
calls the existing consumer synchronously with the separately observed
current correlation, and returns None. The test host explicitly handles
INVALIDATED via scoped consumer.invalidate; no old clear can affect a new
lifetime. Independently observed detach clears without callback. Tests
cover ordered statuses and withdrawal, 100 fragments, change between
projection and callback, failure after painting, stale withdrawal and
scope invalidation, callback view switch, terminal loss, and actual
fixture STOP/ABORTED. All flags remain false. The Qt JS engine is a real
cross-language execution witness, not physical rendering or installed
ForestW, and no M4 fetch or history row is synthesized. Mind owns M6c
history continuity; UI2 owns presentation and actual QML integration.
Independent Nurse2F and DOC3F/UI2 compatibility review required.
