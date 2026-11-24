# Forest Mind M2 // First-Tree context isolation

STATE // disposable public fixture only; production HOLD.
DOC 4F // Mind. Coordination issue #2161, M1 comment 7139569859,
Runtime ACK 7139617637, Security ACK 7139601126.

Additive module: existing B1 journal, B6 TaskContext and B2 prompt bounds.
No new database, schema, host, model call, sender, permission or UI change.
Only base Tree supported; B1 v1 cannot establish durable Clone/task identity.
Host must independently resolve current fixture context, and use only an
isolated public synthetic database. Equality is not authentication.
No actual private data may enter this path.

snapshot_in_transaction compares exact original/current references, checks
owner + Tree + session, OPEN and revision before selecting the latest
durable user and bounded contiguous suffix. Call only within the eventual
B3 reservation transaction (BEGIN IMMEDIATE), never from Bark. An active
transaction alone is not evidence of writer custody. B3 integration and
attempt/commit/recovery rules remain with Runtime. No automatic replay.
History selection does not modify rows, truncate messages or claim token fit.
An unfit latest user refuses; older unfit history ends the suffix and omitted
prefix count is explicit. Capability plan is optional exact-context metadata,
not authorized activation.

list_open_metadata_fixture selects only session ID, revision and updated time
after owner/Tree/OPEN scope, before LIMIT; no title or body selected.
Internal fixture metadata only. UI2 four-field public display and protected
title consent are separate agreements; no actual outbound serializer or
permission check in this module.

VERIFY:
    python3 -B -m unittest discover -s tests/forest -p 'test_context_first_tree_m2.py' -v

NEXT: independent Nurse 2F review and explicit B3 shared seam agreement.
No production, native execution, private storage or UI integration.
