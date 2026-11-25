"""R6b: CI-only fixed public CHERRY child. No installed host or authority."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import select
import stat
import sys
import time

# -I removes the script directory. Bind only this reviewed source directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_public_conversation_r5 import PublicConversationHost, _OWNER, _TURNS, _ref
from runtime_public_delivery_r4b import PresentationCorrelation
from history_public_fixture_m4 import FixtureHistoryAliases
from recovery_inspect_b4d import ForestLocalRecoveryInspector
from shared_context_b6r1 import TaskContext, BarkAttachment

CONTROL = 512
RESPONSE = 16384
TOTAL = 131072
ACTIONS = 64
FRAMES = 160
PHASE = 5
TRIAL = 120
TOKEN = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
LEX = re.compile(r'"(?:[^"\\\x00-\x1f]|\\["\\])*"|0|[1-9][0-9]*|true|false|null|[{}\[\],:]', re.ASCII)
FORBIDDEN = {"__proto__", "constructor", "prototype"}
MAXINT = 2**53 - 1


class WireError(Exception):
    pass


class Refused(Exception):
    pass


def require(ok):
    if not ok:
        raise Refused()


def token(x):
    return type(x) is str and TOKEN.fullmatch(x) is not None


def integer(x, lo=0, hi=MAXINT):
    return type(x) is int and lo <= x <= hi


def exact(x, keys):
    return type(x) is dict and set(x) == set(keys.split())


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result or key in FORBIDDEN:
            raise WireError()
        result[key] = value
    return result


def decode(raw, cap):
    """Bound before recursive parse. Canonical equality rejects alternate encodings."""
    if (type(raw) is not bytes or not 1 < len(raw) <= cap or raw[-1:] != b"\n"
            or any(not 32 <= c <= 126 for c in raw[:-1])):
        raise WireError()
    text = raw[:-1].decode("ascii")
    i = nodes = tokens = 0
    stack = []
    while i < len(text):
        m = LEX.match(text, i)
        if m is None:
            raise WireError()
        value = m.group()
        i = m.end()
        tokens += 1
        if value in ("{", "["):
            stack.append(value)
            nodes += 1
        elif value in ("}", "]"):
            if not stack or stack.pop() != ("{" if value == "}" else "["):
                raise WireError()
        elif value not in (",", ":"):
            nodes += 1
            if value[0].isdigit() and (len(value) > 16 or int(value) > MAXINT):
                raise WireError()
        if len(stack) > 8 or nodes > 256 or tokens > 512:
            raise WireError()
    if stack:
        raise WireError()
    try:
        obj = json.loads(text, object_pairs_hook=_pairs)
        if canonical(obj) != raw:
            raise WireError()
    except (ValueError, TypeError, RecursionError) as exc:
        raise WireError() from None
    if (not exact(obj, "v trial action kind data")
            or not integer(obj["v"], 1, 1) or not token(obj["trial"])
            or not integer(obj["action"], 1, ACTIONS)
            or type(obj["kind"]) is not str or type(obj["data"]) is not dict):
        raise WireError()
    return obj


class Wire:
    """One owner-thread stdin/stdout pair; no buffered IO or unbounded flush."""
    def __init__(self, infd=0, outfd=1):
        self.infd, self.outfd = infd, outfd
        os.set_blocking(infd, False)
        os.set_blocking(outfd, False)
        self.end = time.monotonic() + TRIAL
        self.deadline = self.end
        self.bytes = self.frames = self.last_read = 0

    def phase(self):
        self.deadline = min(self.end, time.monotonic() + PHASE)

    def check(self):
        remaining = min(self.end, self.deadline) - time.monotonic()
        if remaining <= 0:
            raise WireError()
        return remaining

    def charge(self, n, frames=0):
        if self.bytes + n > TOTAL or self.frames + frames > FRAMES:
            raise WireError()
        self.bytes += n
        self.frames += frames

    def read(self):
        buf = bytearray()
        self.charge(0, 1)
        while len(buf) < CONTROL:
            if not select.select([self.infd], [], [], self.check())[0]:
                raise WireError()
            try:
                part = os.read(self.infd, 1)
            except BlockingIOError:
                continue
            if not part:
                raise WireError()
            self.charge(len(part))
            self.check()
            buf.extend(part)
            if part == b"\n":
                self.last_read = len(buf)
                return decode(bytes(buf), CONTROL)
            if not 32 <= part[0] <= 126:
                raise WireError()
        raise WireError()

    def reserve(self, offered):
        frames = 4 if offered else 2
        size = (2 if offered else 1) * (CONTROL + RESPONSE)
        if (self.bytes - self.last_read + size > TOTAL
                or self.frames - 1 + frames > FRAMES):
            raise WireError()
        self.check()

    def room(self, bytes_needed, frames_needed=1):
        self.check()
        if self.bytes + bytes_needed > TOTAL or self.frames + frames_needed > FRAMES:
            raise WireError()

    def send(self, obj):
        raw = canonical(obj)
        # Same lexical/schema limits on both ends, including actual LF.
        decode(raw, RESPONSE)
        self.charge(len(raw), 1)
        pending = memoryview(raw)
        while pending:
            if not select.select([], [self.outfd], [], self.check())[1]:
                raise WireError()
            try:
                n = os.write(self.outfd, pending)
            except BlockingIOError:
                continue
            if n <= 0:
                raise WireError()
            pending = pending[n:]
            self.check()


def correlation(ref):
    require(exact(ref, "requestId viewKey generation"))
    require(token(ref["requestId"]) and token(ref["viewKey"])
            and ref["requestId"] != ref["viewKey"] and integer(ref["generation"], 1))
    return PresentationCorrelation(ref["requestId"], ref["viewKey"], ref["generation"])


def same(a, b):
    # Python True == 1 is not exact wire equality.
    return canonical(a) == canonical(b)


class Child:
    """R6 adapter owns one R5 fixture, not a second journal or runtime."""
    def __init__(self, wire):
        self.wire = wire
        self.trial = None
        self.action = 0
        self.phase = "NEW"
        self.current = None
        self.history = None
        self.history_attachment = None
        self.history_generation = 0
        self.history_after = 0
        self.history_complete = False
        self.used = set()
        self.units = []
        self.host = None
        self.aliases = None
        self.identity = None
        self.revision = 0
        self.reopen_ready = False
        self.steps = 0
        self.stopped = False
        self.effect_possible = False
        self.open_wire_failed = False
        self.turn_aliases = set()

    def send(self, kind, data):
        self.wire.send(dict(v=1, trial=self.trial, action=self.action,
                            kind=kind, data=data))

    def result(self, code):
        units, self.units = self.units, []
        self.send("RESULT", dict(code=code, units=units))

    def _remember(self, value):
        require(token(value) and value not in self.used and value != self.trial
                and value not in self.turn_aliases and len(self.used) < 256)
        self.used.add(value)

    def _new_token(self):
        value = secrets.token_hex(16)
        self._remember(value)
        return value

    def _offer(self, kind, ack_kind, key, value):
        self.send(kind, {key: value})
        ack = self.wire.read()
        if (ack["trial"] != self.trial or ack["action"] != self.action
                or ack["kind"] != ack_kind or not exact(ack["data"], key+" accepted")
                or not same(ack["data"][key], value)
                or type(ack["data"]["accepted"]) is not bool):
            raise WireError()
        self.wire.check()
        if not ack["data"]["accepted"]:
            return False
        self.wire.room(RESPONSE)
        return True

    def _open(self, ref):
        c = correlation(ref)
        self._remember(c.request_id)
        self._remember(c.view_key)
        try:
            if not self._offer("OPEN_OFFER", "OPEN_ACK", "ref", ref):
                return False
        except WireError:
            # R5's callback wrapper translates exceptions to fixture refusal.
            # Preserve the wire failure locally; never reply to a bad ACK.
            self.open_wire_failed = True
            raise
        # Matching timely true ACK consumed. This is only a local observation,
        # not authenticated QML state. Any failure from here can have an effect.
        self.effect_possible = True
        self.current = c
        return True

    def _receive(self, unit):
        require(self.current is not None and len(self.units) < 2)
        require(exact(unit, "requestId viewKey generation sequence kind statusPacket"))
        require(same({k: unit[k] for k in ("requestId","viewKey","generation")},
                     _ref(self.current)))
        # R4b owns exact public status schema. No raw events or obsolete
        # withdrawals can become a result for another operation.
        require(unit["kind"] == "STATUS")
        self.units.append(unit)

    def _invalidate(self, ref):
        if self.current is not None and same(ref, _ref(self.current)):
            self.current = None

    def _retire(self):
        self.history = self.history_attachment = None
        self.current = None
        if self.host is not None:
            # Existing R5 owner lifecycle: loses currentness before old
            # withdrawal, closes delivery locally with no old unit submitted.
            self.host.observe_view()
        require(not self.units)

    def _db_identity(self):
        h = self.host
        path = h._path
        directory = path.parent.stat(follow_symlinks=False)
        require(stat.S_ISDIR(directory.st_mode)
                and directory.st_uid == os.getuid()
                and not directory.st_mode & 0o077)
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1)
        dbs = h._db.execute("PRAGMA database_list").fetchall()
        require(len(dbs) == 1 and dbs[0][1] == "main"
                and Path(dbs[0][2]) == path)
        # Pathname evidence only; SQLite does not expose its actual FD here.
        return (path, directory.st_dev, directory.st_ino,
                info.st_dev, info.st_ino)

    def _verify(self, revision, aborted=False):
        """Owner-local transaction check; no raw identifiers returned to wire."""
        h = self.host
        db = h._db
        require(db.in_transaction and h._stream is None and self._db_identity() == self.identity)
        require(integer(revision, 0, 5))
        session = db.execute("SELECT session_id,owner_key,tree_key,state,revision "
                             "FROM forest_sessions").fetchall()
        require(session == [(h._session, _OWNER, "cherry", "OPEN", revision)])
        rows = db.execute("SELECT turn_id,ordinal,role,body FROM forest_turns "
                          "WHERE session_id=? ORDER BY ordinal", (h._session,)).fetchall()
        expected = []
        for i in range(revision):
            expected.append((i+1, "user" if i%2 == 0 else "assistant", _TURNS[i//2][i%2]))
        require([x[1:] for x in rows] == expected)
        attempts = db.execute("SELECT attempt_id,user_turn_id,expected_revision,model_key,"
                              "status,reply_turn_id FROM forest_attempts_b3 "
                              "WHERE owner_key=? AND session_id=? ORDER BY expected_revision",
                              (_OWNER, h._session)).fetchall()
        require(len(attempts) == (revision+1)//2)
        inspector = ForestLocalRecoveryInspector(h._journal)
        for i, a in enumerate(attempts):
            stopped = aborted and i == len(attempts)-1
            wanted = "ABORTED" if stopped else "COMMITTED"
            require(a[1:] == (rows[2*i][0], 2*i+1, "fixture-model", wanted,
                              None if stopped else rows[2*i+1][0]))
            evidence = inspector.inspect(owner=_OWNER, session_id=h._session, attempt_id=a[0])
            require(evidence["forestWriteState"] == "FOREST_"+wanted)
        return rows, attempts

    def _outcome(self):
        h = self.host
        try:
            require(h._binding is not None and h._attempt is not None)
            ref = h._binding.operation.context_ref
            h._db.execute("BEGIN")
            try:
                row = h._db.execute("SELECT status FROM forest_attempts_b3 WHERE attempt_id=?",
                                    (h._attempt,)).fetchone()
                require(row in (("COMMITTED",), ("ABORTED",)))
                aborted = row == ("ABORTED",)
                revision = ref.expected_revision + (0 if aborted else 1)
                require(ref.context.principal_key == _OWNER and ref.context.tree_key == "cherry"
                        and ref.session_id == h._session)
                rows, attempts = self._verify(revision, aborted)
                require(attempts[-1][0] == h._attempt and attempts[-1][1] == ref.user_turn_id
                        and attempts[-1][2] == ref.expected_revision)
                if aborted:
                    require(h._blocked and rows[-1][0] == ref.user_turn_id)
                    return "ABORTED_LOCAL"
                require(not h._blocked and rows[-2][0] == ref.user_turn_id)
                self.revision = revision
                self.reopen_ready = True
                return "COMMITTED_LOCAL"
            finally:
                h._db.rollback()
        except Exception:
            return "UNKNOWN_HOLD"

    def _idle_snapshot(self):
        require(self.phase == "IDLE" and not self.host._blocked
                and self.revision in (0, 2, 4))
        self._verify(self.revision)

    def _history_offer(self):
        require(self.phase == "IDLE")
        self.history = self.history_attachment = None
        self.history_generation += 1
        generation = self.history_generation
        ctx = TaskContext(_OWNER, "cherry", None, "read-task-"+str(generation),
                          "read-context-"+str(generation), generation, "INTERACTIVE")
        attachment = BarkAttachment(ctx, "fixture-history", "fixture-requester",
                                    "fixture-release", "fixture-seat", "fixture-recipient",
                                    "CHERRY", generation)
        view = self._new_token()
        h = self.host
        h._db.execute("BEGIN")
        try:
            self._idle_snapshot()
            offered = self.aliases.scope_in_transaction(h._journal, attachment,
                        current_attachment=attachment, view_key=view)
        finally:
            h._db.rollback()
        require(self._offer("HISTORY_OFFER", "HISTORY_ACK", "scope", offered.public_fields()))
        h._db.execute("BEGIN")
        try:
            self._idle_snapshot()
            observed = self.aliases.scope_in_transaction(h._journal, attachment,
                        current_attachment=attachment, view_key=view)
            require(observed == offered)
        finally:
            h._db.rollback()
        self.history, self.history_attachment = offered, attachment
        self.history_after, self.history_complete = 0, False

    def _page(self, data):
        require(self.phase == "IDLE" and self.history is not None
                and not self.history_complete and exact(data, "scope request"))
        scope = self.history.public_fields()
        req = data["request"]
        require(same(data["scope"], scope)
                and exact(req, "requestId treeKey generation sessionId revision after limit")
                and all(same(req[k], scope[k]) for k in ("treeKey","generation","sessionId","revision"))
                and integer(req["after"], 0, scope["revision"])
                and req["after"] == self.history_after and integer(req["limit"], 1, 2))
        self._remember(req["requestId"])
        h = self.host
        h._db.execute("BEGIN")
        try:
            self._idle_snapshot()
            current = self.aliases.scope_in_transaction(h._journal, self.history_attachment,
                current_attachment=self.history_attachment, view_key=scope["viewKey"])
            page = self.aliases.page_in_transaction(h._journal, self.history, current=current,
                        request_id=req["requestId"], after=req["after"], limit=req["limit"])
            # Exact fixed public allowlist before serialization, not generic ASCII permission.
            for row in page["messages"]:
                i = row["ordinal"]-1
                require(req["after"] <= i < self.revision and token(row["turn_id"])
                        and row["role"] == ("user" if i%2 == 0 else "assistant")
                        and row["text"] == _TURNS[i//2][i%2])
            public_turns = {row["turn_id"] for row in page["messages"]}
            require(len(public_turns) == len(page["messages"])
                    and not public_turns.intersection(self.used)
                    and not self.trial in public_turns
                    and len(public_turns | self.turn_aliases) <= 5)
            self.turn_aliases.update(public_turns)
            require(page["sessionId"] == scope["sessionId"]
                    and page["revision"] == scope["revision"]
                    and page["requestId"] == req["requestId"])
        finally:
            h._db.rollback()
        self.send("PAGE", {"scope":scope, "page":page})
        self.history_after += len(page["messages"])
        self.history_complete = page["complete"]

    def dispatch(self, kind, data):
        self.effect_possible = False
        if kind == "HELLO":
            require(self.phase == "NEW" and data == {})
            self.host = PublicConversationHost(open_lifetime=self._open,
                current_view=lambda:self.current, receive_unit=self._receive,
                invalidate_lifetime=self._invalidate)
            self.identity = self._db_identity()
            self.aliases = FixtureHistoryAliases(_OWNER, self.host._session)
            self._remember(self.aliases._session_alias)
            self.phase = "IDLE"
            self.result("READY")
        elif kind == "NEXT":
            require(self.phase == "IDLE" and data == {} and self.host._index < 3)
            self.host._db.execute("BEGIN")
            try:
                self._idle_snapshot()
            finally:
                self.host._db.rollback()
            self._retire()
            self.open_wire_failed = False
            try:
                self.host.start_next()
            except Exception:
                if self.open_wire_failed:
                    raise WireError() from None
                raise
            require(self.current is not None)
            self.phase = "ACTIVE"
            self.reopen_ready = False
            self.steps = 0
            self.stopped = False
            self.result("TURN_STARTED")
        elif kind in ("STEP", "STOP"):
            require(self.phase == "ACTIVE" and exact(data, "ref") and self.current is not None
                    and correlation(data["ref"]) == self.current)
            if kind == "STOP":
                require(not self.stopped)
                self.effect_possible = True
                self.host.stop(self.current)
                self.stopped = True
                self.result("STOP_OBSERVED")
            else:
                # Third fixture is STOP-only, never allow a sixth durable row.
                require(self.host._index != 3 or self.steps < 4 or self.stopped)
                self.effect_possible = True
                result = self.host.advance()
                self.steps += 1
                if result == "ACTIVE" and self.current is not None:
                    self.result("ACTIVE")
                else:
                    code = self._outcome()
                    if self.current is None:
                        code = "UNKNOWN_HOLD"
                    self.phase = "IDLE" if code == "COMMITTED_LOCAL" else "BLOCKED"
                    self.result(code)
        elif kind == "REOPEN":
            require(self.phase == "IDLE" and data == {} and self.reopen_ready)
            # Check original path custody and exact idle durable evidence
            # before retiring presentation or calling R5's pathname opener.
            db = self.host._db
            db.execute("BEGIN")
            try:
                self._idle_snapshot()
            finally:
                db.rollback()
            self._retire()
            # Recheck after retirement and immediately before the opener.
            # This narrows but does not close a concurrent same-UID swap race.
            require(self._db_identity() == self.identity)
            self.effect_possible = True
            self.host.reopen_journal()
            self.host._db.execute("BEGIN")
            try:
                self._idle_snapshot()
            finally:
                self.host._db.rollback()
            self.reopen_ready = False
            self.result("JOURNAL_REOPENED")
        elif kind == "HISTORY_ATTACH":
            require(data == {})
            self._history_offer()
            self.result("HISTORY_ATTACHED")
        elif kind == "HISTORY_PAGE":
            self._page(data)
        elif kind == "CLOSE":
            require(self.phase in ("IDLE", "ACTIVE", "BLOCKED") and data == {})
            self._retire()
            self.effect_possible = True
            self.host.close()
            self.phase = "CLOSED"
            self.result("CLOSED")
        else:
            raise Refused()

    def run(self):
        try:
            while self.phase != "CLOSED":
                self.wire.phase()
                obj = self.wire.read()
                if (obj["action"] != self.action + 1
                        or (self.trial is not None and obj["trial"] != self.trial)
                        or (self.phase == "NEW" and obj["kind"] != "HELLO")):
                    raise WireError()
                self.action = obj["action"]
                self.trial = obj["trial"]
                self.wire.reserve(obj["kind"] in ("NEXT","HISTORY_ATTACH"))
                try:
                    self.dispatch(obj["kind"], obj["data"])
                except WireError:
                    raise
                except Exception:
                    self.units = []
                    self.result("UNKNOWN_HOLD" if self.effect_possible else "REFUSED")
                    return 2
            return 0
        except Exception:
            # No raw diagnostics or out-of-budget response.
            return 2
        finally:
            if self.host is not None:
                self.current = None
                try:
                    self.host.close()
                except Exception:
                    pass


def main():
    # Explicit test-only gate, not process attestation or protected authority.
    if (not sys.flags.isolated or len(sys.argv) != 1 or os.getuid() == 0
            or os.getuid() != os.geteuid()
            or os.environ.get("FOREST_R6_CI_ONLY") != "1"):
        return 2
    cwd = Path.cwd()
    if (os.environ.get("HOME") != str(cwd) or os.environ.get("TMPDIR") != str(cwd)
            or cwd.stat().st_uid != os.getuid() or cwd.stat().st_mode & 0o077):
        return 2
    os.umask(0o077)
    return Child(Wire()).run()


if __name__ == "__main__":
    sys.exit(main())
