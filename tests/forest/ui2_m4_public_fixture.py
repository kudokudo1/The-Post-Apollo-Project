"""Generate two pages using the actual M4 producer and disposable B1 journal."""
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext, BarkAttachment
from context_first_tree_m2 import ContextRefusal
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from history_public_fixture_m4 import PublicViewRef, HistoryPageRef, history_public_fixture_in_transaction

if sys.argv[1:] not in ([], ["--corrupt-next"]):
    raise SystemExit(2)
corrupt_next = sys.argv[1:] == ["--corrupt-next"]
db = sqlite3.connect(":memory:")
try:
    bootstrap_synthetic(db)
    journal = ForestSessionJournal(db)
    context = TaskContext("fixture-owner", "cherry", None, "task-a", "exec-a", 1, "INTERACTIVE")
    attachment = BarkAttachment(context, "bark-a", "requester-a", "release-a",
                                "seat-a", "recipient-a", "CHERRY", 1)
    sid = journal.create_session("fixture-owner", "cherry", "Unused fixture title",
                                 now_ms=1)["session_id"]
    revision = 0
    for role, body in [("user", "Public question"), ("assistant", "Public reply\nsecond line 🌲")]:
        revision = journal.append_turn("fixture-owner", sid, expected_revision=revision,
            role=role, body=body, provider="ollama" if role == "assistant" else "",
            model="model-a" if role == "assistant" else "", now_ms=revision+2)["revision"]
    if corrupt_next:
        # Public synthetic fixture only; no external database or body disclosure.
        db.execute("UPDATE forest_turns SET body=CAST(X'FF' AS TEXT) "
                   "WHERE session_id=? AND ordinal=2", (sid,))
        db.commit()
    pages = []
    for after, rid in [(0, "fixture_request_001"), (1, "fixture_request_002")]:
        ref = HistoryPageRef(PublicViewRef(attachment,rid),sid,revision,after,1)
        db.execute("BEGIN")
        try:
            frame = history_public_fixture_in_transaction(journal,ref,current=ref)
            pages.append({"frame":frame,"ref":{"requestId":rid,"treeKey":"CHERRY",
                "generation":1,"sessionId":sid,"revision":revision,"after":after,"limit":1}})
        except ContextRefusal as exc:
            if not corrupt_next or after != 1 or str(exc) != "STORAGE_REFUSED":
                raise
            pages.append({"refused": True})  # test marker, not a wire frame
        finally:
            db.rollback()
    print(json.dumps(pages,ensure_ascii=False))
finally:
    db.close()
