# Forest Mind M4 // Public committed history and reopening reference

STATE // Development only; production HOLD. DOC 4F; #2161 M1/M2/M3
handoffs and UI2.1 #2516. No changes to existing QML, B3 or journal schema.

Uses the original B1 journal, M2 and B6 BarkAttachment. Only a host-owned
isolated public synthetic journal is supported. Caller-created refs, matching
values, a schema name and an open transaction establish no authorization or
public provenance. No live DB opener, provider, sender or permission.
The fixture host owns canonical Tree-to-view mapping; a UI hint is not identity.

ListRef and HistoryPageRef bind an exact attachment (including recipient,
task and view generations), request correlation, and list limit or session,
revision, cursor and page limit. Compare original and independently resolved
current references before reads, in one caller-owned SQLite transaction.
The session list matches UI2.1's five-field envelope and four-field rows;
titles are the fixed synthetic label "Public conversation", never read from
B1. The proposed history envelope contains committed B1 rows only; no
provisional events, model metadata, principal or raw attempt IDs. OPEN scope
and revision checked before reading bodies. Page limit 16, candidate compact
UTF-8 JSON <= 65536 bytes, no partial row or skipped ordinal; next page uses
last ordinal and a new request ID, same revision; stale revision requires a
fresh explicit snapshot, never replay. Control/bidi text refuses the page,
not rewriting stored text. A new host-resolved task can reopen a base Tree
session after restart; this does not restore old active tasks or grant retry
of unresolved attempts. No persistent Clone binding.

The UI2 history consumer and live insertion remain separately owned.
No actual serialization/send gate; size is only a candidate encoding bound.
A host must check currentness before actual delivery and DOC3F owns protected
disclosure; never use this path with private records. No title permission
or protected READ inferred. The existing B3 shared reservation hookup remains
DOC2F-owned and this PR does not change it.

VERIFY:
    python3 -B -m unittest discover -s tests/forest -p 'test_history_public_fixture_m4.py' -v

NEXT: UI2 and Nurse 2F review exact display/page contract; independent
integrated public-only acceptance. No production, native run or deployment.


## R6 read-only alias projection candidate

DOC 4F owns only the additive local M4 seam. FixtureHistoryAliases is
constructed by the owner for its fixed canonical cherry session. The owner
retains it across connection reopen, not process death. An independently
observed B6 read-only attachment (no SessionContextRef or OperationRef)
produces a metadata-only ReadOnlyHistoryScope in a read transaction. Only
public_fields() may be offered to the parent. The exact accepted scope
and independently current scope must agree before page projection. The
parent selects a fresh request ID; the owner validates the complete public
request against the accepted scope and retains its exact cursor/lifetime
before invoking page_in_transaction. The existing M4 projection is reused,
then raw session/turn keys are substituted with stable random 32-hex
aliases. Max five durable rows, two rows per page, printable ASCII only;
collisions refuse, no partial alias allocation on refusal. No title read,
new DB, execution, implicit refresh, or replay.

This is NOT a wire freeze or sender. Host must establish isolated public
provenance, same host-created journal custody across connection reopen,
known idle/committed or independently proven ABORTED state, exact original
and current view, request freshness, and actual send-time currentness.
Alias equality does not establish any of these. Runtime owns complete
canonical ASCII outer envelope and 16KiB including LF limit, trial/action
budget and lifecycle. Never serialize the internal scope/attachment or
raw M4 frame. Existing M4 API unchanged. UI2 owns receiver currentness and
explicit history reattach. DOC3F and Nurse2F review required before wiring.
