"""M7e-b public fixture, never a production composer or HTTP serializer."""
from dataclasses import dataclass, replace
from hashlib import sha256
import struct
import unittest

# Reuse merged M7d-b fixed-public types/constants, not its reader.
from test_mind_version_resolution_m7d import (
    CONTEXT, SOURCE, PURPOSE, RECIPIENT, CATALOG, Selection, Observation,
    valid_version, digest,
)
from context_first_tree_m2 import (
    ContextRefusal, SessionContextRef, HistoryTurn, select_history, _key,
)
from layered_hot_context_m7a import (
    HotRouteStamp, SelectedHotRecord, assemble_hot_context, MAX_RECORDS,
    MAX_RECORD_BYTES, MAX_ASSEMBLY_BYTES,
)
from ollama_chat_transport import MAX_HISTORY, MAX_MESSAGE_BYTES, MAX_TOTAL_PROMPT_BYTES

PREFIX = b"FOREST-M7E-PUBLIC-WORKLOAD-V1\0"
GOLDEN = "82d5f9c361b48cdca0fc66b3a24bb2959d22620eb5840a11e7481f20d97b28dc"


def refuse(code):
    raise ContextRefusal("M7E_" + code)


def number(value, width, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        refuse("INTEGER")
    return value.to_bytes(width, "big")


def u32(value):
    return number(value, 4, 2**32-1)


def u64(value):
    return number(value, 8, 2**63-1)


def string(value):
    if type(value) is not str or any(0xd800 <= ord(c) <= 0xdfff for c in value):
        refuse("STRING")
    raw = value.encode("utf-8")
    return u32(len(raw)) + raw


def sequence(values, encode):
    if type(values) is not tuple:
        refuse("TUPLE")
    return u32(len(values)) + b"".join(encode(v) for v in values)


def flag(value):
    if type(value) is not bool:
        refuse("BOOL")
    return b"\1" if value else b"\0"


@dataclass(frozen=True, slots=True)
class Pin:
    ref: SessionContextRef
    observation: Observation
    newest_rows: tuple


@dataclass(frozen=True, slots=True)
class Candidate:
    pin: Pin
    history: tuple
    omitted: int
    reference: str
    history_bytes: int
    reference_bytes: int
    combined_bytes: int
    ceiling: int
    workload_commitment: str
    transport_shape: tuple | None
    release_status: str


def encode(pin, snapshot, fragment, history_bytes, reference_bytes, ceiling):
    """Owner-local fixture encoding; all semantic validation precedes this."""
    ref, sel = pin.ref, pin.observation.selection
    ctx, route = ref.context, sel.route
    def ver(v):
        valid_version(v)
        return (string(v.source) + string(v.record_id) + string(v.kind)
                + u64(v.revision) + u64(v.record_generation)
                + bytes.fromhex(v.commitment) + flag(v.active))
    def turn(v):
        return (string(v.turn_id) + u64(v.ordinal) + string(v.role)
                + string(v.content) + string(v.provider) + string(v.model)
                + u64(v.recorded_at_ms))
    return (PREFIX + string(ctx.principal_key) + string(ctx.tree_key)
            + flag(ctx.clone_key is not None)
            + (string(ctx.clone_key) if ctx.clone_key is not None else b"")
            + string(ctx.task_id) + string(ctx.execution_context_id)
            + u64(ctx.generation) + string(ctx.origin)
            + string(ref.session_id) + u64(ref.expected_revision) + string(ref.user_turn_id)
            + u64(route.input_generation) + u64(route.policy_generation)
            + u64(route.user_context_generation) + u64(route.operational_generation)
            + sequence(route.user_record_ids, string)
            + sequence(route.operational_record_ids, string)
            + string(sel.source) + string(sel.purpose) + string(sel.recipient)
            + sequence(sel.versions, ver)
            + u64(snapshot.omitted_prefix_count) + sequence(snapshot.messages, turn)
            + string(fragment) + u64(ceiling) + u64(history_bytes)
            + u64(reference_bytes) + u64(history_bytes + reference_bytes))


def compose(requested, *, current, final, records=(), ceiling=MAX_TOTAL_PROMPT_BYTES):
    """No I/O: independently supplied before/after fixture observations.

    records are already supplied public literals, never fetched. The
    preselected M7d metadata is checked, not expanded or auto-resolved.
    """
    if (type(requested) is not Pin or type(current) is not Pin
            or requested != current):
        refuse("CURRENTNESS")
    ref, obs, rows = requested.ref, requested.observation, requested.newest_rows
    if (type(ref) is not SessionContextRef or ref.context != CONTEXT
            or type(obs) is not Observation or type(obs.selection) is not Selection):
        refuse("SCOPE")
    sel = obs.selection
    route = sel.route
    if (type(route) is not HotRouteStamp or route.context != ref.context
            or any(type(x) is not str for x in (sel.source, sel.purpose, sel.recipient))
            or (sel.source, sel.purpose, sel.recipient) != (SOURCE, PURPOSE, RECIPIENT)):
        refuse("SCOPE")
    if (type(ceiling) is not int or not 1 <= ceiling <= MAX_TOTAL_PROMPT_BYTES):
        refuse("BUDGET")
    ids = route.user_record_ids + route.operational_record_ids
    versions = sel.versions
    if (type(versions) is not tuple or len(versions) != len(ids)
            or len(versions) > MAX_RECORDS
            or type(obs.metadata_visible) is not bool
            or type(obs.use_versions) is not tuple or len(obs.use_versions) > MAX_RECORDS
            or type(obs.revoked) is not tuple or len(obs.revoked) > 64
            or type(records) is not tuple or len(records) != len(ids)):
        refuse("SELECTION")
    for v in versions + obs.use_versions + obs.revoked:
        valid_version(v)
        _key(v.record_id)
    if (tuple(v.record_id for v in versions) != ids
            or len(set(obs.use_versions)) != len(obs.use_versions)
            or len(set(obs.revoked)) != len(obs.revoked)):
        refuse("SELECTION")
    if versions and not obs.metadata_visible:
        refuse("METADATA")
    # Fixed public preselected metadata only, never enumerate a source.
    for i, v in enumerate(versions):
        operational = i >= len(route.user_record_ids)
        generation = route.operational_generation if operational else route.user_context_generation
        if ((v.kind == "operational-learning") != operational or not v.active
                or v.record_generation > generation or v not in obs.use_versions
                or v in obs.revoked or v not in CATALOG):
            refuse("VERSION")
        # The supplied pinned version must be the visible immutable revision
        # in the existing fixed M7d metadata, never fallback to a different one.
        visible = tuple(x for x in CATALOG if x.record_id == v.record_id
                        and x.kind == v.kind and x.record_generation <= generation)
        if not visible or max(visible, key=lambda x: x.record_generation) != v:
            refuse("VERSION")
    if type(rows) is not tuple or not 1 <= len(rows) <= MAX_HISTORY:
        refuse("HISTORY")
    # M2 validates roles, newest user, contiguous history and revision.
    snapshot = select_history(ref, rows)
    # Do not silently accept additional history reduction in this slice.
    if len(snapshot.messages) != len(rows):
        refuse("HISTORY_REDUCTION")
    messages = snapshot.transport_messages()
    history_bytes = sum(len(m["content"].encode("utf-8")) for m in messages)
    for i, (v, record) in enumerate(zip(versions, records)):
        generation = (route.user_context_generation if i < len(route.user_record_ids)
                      else route.operational_generation)
        if (type(record) is not SelectedHotRecord
                or (record.principal_key, record.tree_key, record.record_id, record.kind,
                    record.generation, record.active) !=
                   (ref.context.principal_key, ref.context.tree_key, v.record_id, v.kind,
                    generation, True)
                or digest(record.text) != v.commitment):
            refuse("RECORD")
    split = len(route.user_record_ids)
    assembly = assemble_hot_context(route, current=route, user_records=records[:split],
                                    operational_records=records[split:])
    fragment = assembly.reference_text
    reference_bytes = len(fragment.encode("utf-8"))
    if reference_bytes != assembly.byte_count or history_bytes + reference_bytes > ceiling:
        refuse("BUDGET")
    if type(final) is not Pin or final != current:
        refuse("CURRENTNESS")
    raw = encode(requested, snapshot, fragment, history_bytes, reference_bytes, ceiling)
    # Immutable local shape only. Neither result authorizes dispatch.
    shape = None if fragment else tuple((m["role"], m["content"]) for m in messages)
    return Candidate(requested, snapshot.messages, snapshot.omitted_prefix_count, fragment,
                     history_bytes, reference_bytes, history_bytes+reference_bytes, ceiling,
                     sha256(raw).hexdigest(), shape,
                     "RELEASE_HOLD" if fragment else "SHAPE_ONLY_NO_SEND")


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.route = HotRouteStamp(CONTEXT, 1, 2, 3, 2, (), ())
        self.ref = SessionContextRef(CONTEXT, "fixture-session", 1, "fixture-turn")
        self.row = HistoryTurn("fixture-turn", 1, "user", "Public fixture: café.", "", "", 1)
        self.sel = Selection(self.route, SOURCE, PURPOSE, RECIPIENT, ())
        self.pin = Pin(self.ref, Observation(self.sel, True, ()), (self.row,))
        self.v = CATALOG[1]
        sel = replace(self.sel, route=replace(self.route, user_record_ids=("preference",)),
                      versions=(self.v,))
        self.with_ref = replace(self.pin, observation=Observation(sel, True, (self.v,)))
        self.record = SelectedHotRecord(CONTEXT.principal_key, CONTEXT.tree_key,
            "preference", "user-preference", 3, True, "Public fixture: revised preference.")

    def run_pin(self, pin=None, records=(), **kwargs):
        pin = self.pin if pin is None else pin
        return compose(pin, current=kwargs.pop("current", pin),
                       final=kwargs.pop("final", pin), records=records, **kwargs)

    def test_golden_empty_reference_exact_m2_passthrough(self):
        result = self.run_pin()
        self.assertEqual(result.history_bytes, 22)
        self.assertEqual(result.combined_bytes, 22)
        self.assertEqual(result.workload_commitment, GOLDEN)
        snap = select_history(self.ref, (self.row,))
        self.assertEqual(result.transport_shape,
                         tuple((m["role"], m["content"]) for m in snap.transport_messages()))
        self.assertEqual(result.release_status, "SHAPE_ONLY_NO_SEND")
        self.assertEqual(len(encode(self.pin, snap, "", 22, 0, 16384)), 381)

    def test_independent_nonempty_framing_crosscheck(self):
        result = self.run_pin(self.with_ref, (self.record,))
        # Independent struct-packed explicit field sequence, not encoder helpers.
        def st(s):
            b = s.encode("utf-8")
            return struct.pack(">I", len(b)) + b
        def q(*values):
            return struct.pack(">"+"Q"*len(values), *values)
        raw = (b"FOREST-M7E-PUBLIC-WORKLOAD-V1\x00"
               + st("fixture-owner")+st("cherry")+b"\x00"+st("task-a")+st("ctx-a")
               + q(1)+st("INTERACTIVE")
               + st("fixture-session")+q(1)+st("fixture-turn")+q(1,2,3,2)
               + struct.pack(">I",1)+st("preference")+struct.pack(">I",0)
               + st(SOURCE)+st(PURPOSE)+st(RECIPIENT)+struct.pack(">I",1)
               + st(SOURCE)+st("preference")+st("user-preference")+q(2,3)
               + sha256(b"Public fixture: revised preference.").digest()+b"\x01"
               + q(0)+struct.pack(">I",1)+st("fixture-turn")+q(1)+st("user")
               + st("Public fixture: café.")+st("")+st("")+q(1)
               + st(result.reference)+q(16384,22,result.reference_bytes,result.combined_bytes))
        snap = select_history(self.ref, (self.row,))
        self.assertEqual(encode(self.with_ref, snap, result.reference, 22,
                                result.reference_bytes, 16384), raw)
        self.assertEqual(result.workload_commitment, sha256(raw).hexdigest())
        self.assertEqual(result, self.run_pin(self.with_ref, (self.record,)))
        self.assertIsNone(result.transport_shape)
        self.assertEqual(result.release_status, "RELEASE_HOLD")
        self.assertEqual(result.history, (self.row,))
        self.assertIn(self.record.text, result.reference)

    def test_stale_current_and_final_even_empty(self):
        stale = replace(self.pin, ref=replace(self.ref, expected_revision=2))
        for changes in (dict(current=stale), dict(final=stale)):
            with self.assertRaisesRegex(ContextRefusal, "M7E_CURRENTNESS"):
                self.run_pin(**changes)
        for field in ("input_generation", "policy_generation", "user_context_generation",
                      "operational_generation"):
            selection = replace(self.sel, route=replace(self.route, **{field: 9}))
            stale = replace(self.pin, observation=replace(self.pin.observation,
                                                          selection=selection))
            with self.assertRaisesRegex(ContextRefusal, "M7E_CURRENTNESS"):
                self.run_pin(current=stale)

    def test_wrong_task_source_recipient_and_clone(self):
        for field in ("source", "purpose", "recipient"):
            sel = replace(self.sel, **{field: "other"})
            with self.assertRaisesRegex(ContextRefusal, "M7E_SCOPE"):
                self.run_pin(replace(self.pin, observation=replace(self.pin.observation,
                                                                 selection=sel)))
        for ctx in (replace(CONTEXT, task_id="other"), replace(CONTEXT, tree_key="maple"),
                    replace(CONTEXT, principal_key="other"), replace(CONTEXT, generation=2)):
            sel = replace(self.sel, route=replace(self.route, context=ctx))
            bad = replace(self.pin, ref=replace(self.ref, context=ctx),
                          observation=replace(self.pin.observation, selection=sel))
            with self.assertRaisesRegex(ContextRefusal, "M7E_SCOPE"):
                self.run_pin(bad)
        with self.assertRaises(ContextRefusal):
            replace(self.ref, context=replace(CONTEXT, clone_key="clone-a"))

    def test_version_use_commitment_and_record_refusals(self):
        obs = self.with_ref.observation
        for changes in (dict(metadata_visible=False), dict(use_versions=()),
                        dict(revoked=(self.v,)), dict(use_versions=(self.v,self.v))):
            with self.assertRaises(ContextRefusal):
                self.run_pin(replace(self.with_ref, observation=replace(obs, **changes)),
                             (self.record,))
        for v in (CATALOG[0], replace(self.v, revision=True),
                  replace(self.v, commitment="0"*64), replace(self.v, active=False)):
            sel = replace(obs.selection, versions=(v,))
            with self.assertRaises(ContextRefusal):
                self.run_pin(replace(self.with_ref, observation=Observation(sel,True,(v,))),
                             (self.record,))
        for records in ((), (replace(self.record,text="Substituted public fixture"),),
                        (replace(self.record,generation=2),)):
            with self.assertRaises(ContextRefusal):
                self.run_pin(self.with_ref, records)

    def test_joint_budget_and_message_limits(self):
        result = self.run_pin(self.with_ref, (self.record,))
        with self.assertRaisesRegex(ContextRefusal, "M7E_BUDGET"):
            self.run_pin(self.with_ref, (self.record,), ceiling=result.combined_bytes-1)
        self.assertEqual(self.run_pin(self.with_ref, (self.record,),
                                     ceiling=result.combined_bytes).combined_bytes,
                         result.combined_bytes)
        for ceiling in (True, 0, 16385):
            with self.assertRaises(ContextRefusal):
                self.run_pin(ceiling=ceiling)
        row = replace(self.row, content="🌳"*1024)
        self.assertEqual(self.run_pin(replace(self.pin,newest_rows=(row,))).history_bytes,4096)
        with self.assertRaises(ContextRefusal):
            self.run_pin(replace(self.pin,newest_rows=(replace(row,content="🌳"*1025),)))

    def test_history_role_order_and_no_silent_reduction(self):
        assistant = HistoryTurn("reply",2,"assistant","Public reply","ollama","model",2)
        latest = replace(self.row,ordinal=3,turn_id="latest",recorded_at_ms=3)
        ref = replace(self.ref,expected_revision=3,user_turn_id="latest")
        pin = replace(self.pin,ref=ref,newest_rows=(latest,assistant,self.row))
        self.assertEqual(self.run_pin(pin).history,(self.row,assistant,latest))
        for rows in ((assistant,latest,self.row),(latest,self.row,assistant),
                     (latest,assistant,assistant),(latest,assistant)):
            with self.assertRaises(ContextRefusal):
                self.run_pin(replace(pin,newest_rows=rows))
        oversized = replace(assistant,content="A"*4097)
        with self.assertRaisesRegex(ContextRefusal,"M7E_HISTORY_REDUCTION"):
            self.run_pin(replace(pin,newest_rows=(latest,oversized,self.row)))
        with self.assertRaises(ContextRefusal):
            self.run_pin(replace(pin,newest_rows=(latest,)*17))

    def test_strict_framing_and_field_change(self):
        self.assertNotEqual(string("ab")+string("c"),string("a")+string("bc"))
        self.assertNotEqual(sequence((),string),sequence(("",),string))
        for value in (True,-1,2**63):
            with self.assertRaises(ContextRefusal):
                u64(value)
        with self.assertRaises(ContextRefusal):
            flag(1)
        with self.assertRaises(ContextRefusal):
            string("\ud800")
        base = self.run_pin()
        for pin in (replace(self.pin,ref=replace(self.ref,expected_revision=2)),
                    replace(self.pin,newest_rows=(replace(self.row,content="Public fixture: cafe\u0301."),)),
                    replace(self.pin,newest_rows=(replace(self.row,recorded_at_ms=2),))):
            self.assertNotEqual(base.workload_commitment,self.run_pin(pin).workload_commitment)
        self.assertNotEqual(base.workload_commitment,self.run_pin(ceiling=100).workload_commitment)
        self.assertEqual(self.pin.newest_rows,(self.row,))
        self.assertEqual(self.with_ref.observation.selection.versions,(self.v,))


if __name__ == "__main__":
    unittest.main()
