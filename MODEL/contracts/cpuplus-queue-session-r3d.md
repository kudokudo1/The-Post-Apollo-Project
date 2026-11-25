# DOC 2 R3d // Session coordinator reference

Pure host-side transitions for DOC 4 #2577 (659321a3) and #2579
(5d0553dc, actual corrected UI 7982ff18 pinned). Uses merged consumer and
projector and pinned #2591 reduced DETAIL parser for tests. No QML mounting,
Process, launch, storage, provider, timer or live transport. Caller must commit
returned state before sending a frame and stop the exact child when requested.
One explicit connection generation per child; no auto reconnect/replay.
Generation is host-controlled, HELLO binds only that already-started child.
All sequenced replies share one watermark. Preserve atomic pending/unresolved
context while projection is null. Scheduled INVALIDATE during action pending
does not imply action timeout. History is one explicit outstanding read,
correlated to owner and request; no history read during a mutation.

The ASCII compact JSON round-trip guard rejects duplicate keys and unsafe
integers after framing; it does not bound bytes accumulated by a real parser.
A reviewed byte-bounded receive path, independent watchdog, secure action UUID
source, child entrypoint, native provider, deployment configuration, and
durable startup reconciliation are still required. Default startupHold prevents
submissions; the explicit fixture-only flag is for disposable tests, never a
production bypass. There is no unlock or history acknowledgment method.
Owner/child loss preserves unresolved in-memory action; full process restart
cannot recover that state. No protected operation or completion authority.
