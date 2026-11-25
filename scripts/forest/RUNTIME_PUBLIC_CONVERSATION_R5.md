# R5 connected disposable public conversation host

Runtime owner candidate for the first two completed public fixture turns and
one explicit STOP demonstration. Uses the existing B1/B3/M2/R3/R4a/R4b/M4
implementation. Fresh private temporary directory contains only synthetic
public SQLite rows, removed on close; no existing database, supplied path,
prompt, model, tools or network. Actual user/model input and native Ollama
remain HOLD. One explicit owner action at a time; no scheduler or listener.

The host's callbacks implement the reviewed UI2.2b #2624 seam: open a fresh
owner-issued correlation explicitly, independently observe current eligible
view, invoke receiveUnit synchronously and return None, invalidateLifetime
only for that original correlation. A callback refusal must raise locally.
Currentness is sampled before and after the callback, including when a view
switches without throwing. Failure/withdrawal affects the presentation only,
not the execution; no retry or stale status. Owner independently observes
detach and clears the UI without waiting for a callback. No public authority
or authentication follows from a fixture reference. No cross-process bridge.

The host steps the bounded fake streamer explicitly, uses actual operation
specific STOP, and exposes only fixed action results, never raw R3 frames.
M4 history_page is separately invoked at an independently current revision;
no status-created row or implicit refresh. Mind retains history policy.
Tests exercise real reactive QML from the existing UI2 harness, two committed
turns, explicit M4 display and third STOP, independent SQLite read, callback
throws after paint, switch without throwing, and detach. No new QML renderer.
This is a same-process fixture host, not actual installed ForestW/Quickshell
integration. UI1/UI2 own panel mounting and a separately approved actual
process boundary; DOC3F placement/security and Nurse2F independent review
required. No private/protected release or operator acceptance.
