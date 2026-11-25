"""UI2 pre-join evidence from the existing disposable child test driver."""
import json
import os
from contextlib import closing
from test_runtime_public_child_r6b import ProcessTrial

assert os.getuid() != 0
with ProcessTrial() as t:
    assert t.result("HELLO", {}, "READY") == []
    def snapshot():
        with closing(t.db()) as db:
            return [db.execute("SELECT revision FROM forest_sessions").fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM forest_turns WHERE role='assistant'").fetchone()[0]]
    def page(scope, after):
        request_id = f"{t.action+1000:032x}"
        frame = t.page(scope, after)
        assert frame["requestId"] == request_id
        return dict(requestId=request_id, after=after, frame=frame)
    a = t.next()
    units_a = t.finish(a)
    h1 = t.history()
    first = page(h1, 0)
    b = t.next()
    units_b = t.finish(b)
    h2 = t.history()
    before = snapshot()
    second = [page(h2, 0), page(h2, 2)]
    assert snapshot() == before == [4, 2]
    assert t.result("REOPEN", {}, "JOURNAL_REOPENED") == []
    h3 = t.history()
    reopened = [page(h3, 0), page(h3, 2)]
    assert snapshot() == before
    c = t.next()
    units_c = []
    for _ in range(4):
        units_c.extend(t.result("STEP", {"ref": c}, "ACTIVE"))
    stop = t.result("STOP", {"ref": c}, "STOP_OBSERVED")
    t.send("STEP", {"ref": c})
    final = t.read()
    assert final["kind"] == "RESULT" and set(final["data"]) == {"code", "units"}
    assert final["data"]["code"] == "ABORTED_LOCAL"
    abort = final["data"]["units"]
    assert snapshot() == [5, 2]
    with closing(t.db()) as db:
        assert db.execute("SELECT status FROM forest_attempts_b3 ORDER BY expected_revision").fetchall() == [
            ("COMMITTED",), ("COMMITTED",), ("ABORTED",)]
        assert db.execute("SELECT reply_turn_id FROM forest_attempts_b3 WHERE status='ABORTED'").fetchone() == (None,)
    assert t.result("CLOSE", {}, "CLOSED") == []
    t.closed(0)
    print(json.dumps(dict(a=a,b=b,c=c,unitsA=units_a,unitsB=units_b,unitsC=units_c,
        stop=stop,abort=abort,abortCode=final["data"]["code"],h1=h1,h2=h2,h3=h3,first=first,second=second,reopened=reopened)))
