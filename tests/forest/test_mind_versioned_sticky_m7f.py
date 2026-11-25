"""M7f-b fixed-public cache witness; no real read, permission or provider."""
from dataclasses import replace
from hashlib import sha256
import unittest

from test_mind_final_composition_m7e import Pin, compose
from test_mind_version_resolution_m7d import (
    CONTEXT, SOURCE, PURPOSE, RECIPIENT, CATALOG, Selection, Observation, BODIES,
)
from context_first_tree_m2 import ContextRefusal, SessionContextRef, HistoryTurn
from layered_hot_context_m7a import HotRouteStamp, SelectedHotRecord, MAX_GENERATION
from task_sticky_context_m7b import (
    TaskStickyContext, HotDependencies, PublicVersion, PublicSelection, PublicUse, PublicEntry,
)


def version(v):
    return PublicVersion(v.source, v.record_id, v.kind, v.revision,
                         v.record_generation, bytes.fromhex(v.commitment), v.active)


def entry(v, text, generation):
    return PublicEntry(v, SelectedHotRecord(CONTEXT.principal_key, CONTEXT.tree_key,
        v.record_id, v.kind, generation, True, text))


class VersionedTests(unittest.TestCase):
    def setUp(self):
        self.cache = TaskStickyContext(CONTEXT, mode="public-versioned")
        self.u, self.o = version(CATALOG[1]), version(CATALOG[2])
        self.user = entry(self.u, BODIES[1][2], 3)
        self.op = entry(self.o, BODIES[2][2], 2)
        self.route = HotRouteStamp(CONTEXT, 1, 2, 3, 2, ("preference",), ("lesson",))
        self.sel = PublicSelection(self.route,SOURCE,PURPOSE,RECIPIENT,(self.u,self.o))
        self.install(self.sel)
        self.remember(self.sel,(self.user,self.op))

    def args(self,s,use=None):
        return dict(current=s,dependencies=HotDependencies.from_route(s.route),
                    use=PublicUse(s,s.versions) if use is None else use)

    def install(self,s,use=None):
        self.cache.install_versioned(s,**self.args(s,use))

    def remember(self,s,entries):
        self.cache.remember_versioned(s,entries=entries,**self.args(s))

    def lookup(self,s=None,use=None):
        s=self.sel if s is None else s
        return self.cache.lookup_versioned(s,**self.args(s,use))

    def fresh(self,**clocks):
        return replace(self.sel,route=replace(self.route,**clocks))

    def test_exact_reuse_and_m7e_projection(self):
        fresh=self.fresh(input_generation=2)
        self.install(fresh)
        result, assembled=self.cache.assemble_versioned(fresh,**self.args(fresh),
            final_use=PublicUse(fresh,fresh.versions))
        self.assertEqual(result.entries,(self.user,self.op))
        selection=Selection(fresh.route,SOURCE,PURPOSE,RECIPIENT,(CATALOG[1],CATALOG[2]))
        ref=SessionContextRef(CONTEXT,"fixture-session",1,"fixture-turn")
        row=HistoryTurn("fixture-turn",1,"user","Public fixture: café.","","",1)
        pin=Pin(ref,Observation(selection,True,selection.versions),(row,))
        candidate=compose(pin,current=pin,final=pin,records=tuple(e.record for e in result.entries))
        self.assertEqual(candidate.reference,assembled.reference_text)
        self.assertEqual(candidate.release_status,"RELEASE_HOLD")
        self.assertIsNone(candidate.transport_shape)

    def test_partial_miss_no_body_and_domain_invalidation(self):
        fresh=self.fresh(input_generation=2,user_context_generation=4)
        self.install(fresh)
        result=self.lookup(fresh)
        self.assertEqual(result.entries,())
        self.assertEqual(result.missing,(self.u,))
        self.assertEqual(self.cache.counts(),(0,1))
        self.remember(fresh,(entry(self.u,BODIES[1][2],4),))
        self.assertTrue(self.lookup(fresh).complete)

    def test_revocation_floor_and_explicit_resupply(self):
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.lookup(use=PublicUse(self.sel,(self.o,),(self.u,)))
        self.assertEqual(self.cache.counts(),(0,0))
        for fresh in (self.sel,self.fresh(input_generation=2,user_context_generation=4)):
            with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
                self.install(fresh)
        fresh=self.fresh(input_generation=3,policy_generation=3,user_context_generation=4)
        self.install(fresh)
        self.assertEqual(self.lookup(fresh).entries,())
        self.remember(fresh,(entry(self.u,BODIES[1][2],4),self.op))
        self.assertTrue(self.lookup(fresh).complete)

    def test_stale_revocation_cannot_clear_replacement(self):
        fresh=self.fresh(input_generation=2)
        self.install(fresh)
        with self.assertRaises(ContextRefusal):
            self.install(self.sel,PublicUse(self.sel,(),(self.u,)))
        self.assertEqual(self.cache.counts(),(1,1))
        self.assertTrue(self.lookup(fresh).complete)

    def test_unknown_use_is_not_revocation_and_final_recheck(self):
        with self.assertRaisesRegex(ContextRefusal,"USE"):
            self.lookup(use=PublicUse(self.sel,(self.u,)))
        self.assertEqual(self.cache.counts(),(1,1))
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.cache.assemble_versioned(self.sel,**self.args(self.sel),
                final_use=PublicUse(self.sel,(),(self.o,)))
        self.assertEqual(self.cache.counts(),(0,0))

    def test_same_domain_conflict_floor(self):
        alternate=version(CATALOG[0])
        fresh=replace(self.fresh(input_generation=2),versions=(alternate,self.o))
        with self.assertRaisesRegex(ContextRefusal,"CONFLICT"):
            self.install(fresh)
        self.assertEqual(self.cache.counts(),(0,1))
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(self.fresh(input_generation=3))
        next_s=self.fresh(input_generation=4,user_context_generation=4)
        self.install(next_s)
        self.assertEqual(self.lookup(next_s).missing,(self.u,))

    def test_domain_floor_does_not_mask_current_revocation(self):
        alternate=version(CATALOG[0])
        conflict=replace(self.fresh(input_generation=2),versions=(alternate,self.o))
        with self.assertRaisesRegex(ContextRefusal,"CONFLICT"):
            self.install(conflict)
        self.assertEqual(self.cache.counts(),(0,1))
        blocked=self.fresh(input_generation=3)
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.install(blocked,PublicUse(blocked,(),(self.o,)))
        self.assertEqual(self.cache.counts(),(0,0))
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(self.fresh(input_generation=4,user_context_generation=4))
        fresh=self.fresh(input_generation=5,user_context_generation=4,policy_generation=3)
        self.install(fresh)
        self.assertEqual(self.lookup(fresh).entries,())

    def test_epoch_exhaustion(self):
        fresh=self.fresh(input_generation=2,policy_generation=MAX_GENERATION)
        self.install(fresh)
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.lookup(fresh,PublicUse(fresh,(),(self.u,)))
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(replace(fresh,route=replace(fresh.route,input_generation=3)))
        with self.assertRaises(ContextRefusal):
            replace(fresh.route,policy_generation=MAX_GENERATION+1)

    def test_shed_close_and_legacy_downgrade(self):
        with self.assertRaisesRegex(ContextRefusal,"MODE"):
            self.cache.lookup(self.route,current=self.route,
                              dependencies=HotDependencies.from_route(self.route))
        legacy=TaskStickyContext(CONTEXT)
        with self.assertRaisesRegex(ContextRefusal,"MODE"):
            legacy.install_versioned(self.sel,**self.args(self.sel))
        self.cache.shed_versioned(self.sel,**self.args(self.sel),drop_user=True)
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(self.sel)
        fresh=self.fresh(input_generation=2)
        self.install(fresh)
        self.assertEqual(self.lookup(fresh).missing,(self.u,))
        self.cache.close()
        with self.assertRaisesRegex(ContextRefusal,"CLOSED"):
            self.install(fresh)

    def test_typed_scope_and_atomic_batch(self):
        with self.assertRaises(ContextRefusal):
            replace(self.u,revision=True)
        with self.assertRaises(ContextRefusal):
            replace(self.user,version=replace(self.u,commitment=b"x"*32))
        with self.assertRaises(ContextRefusal):
            self.install(replace(self.sel,recipient="other"))
        fresh=self.fresh(input_generation=2,user_context_generation=4)
        self.install(fresh)
        wrong=entry(self.u,BODIES[1][2],3)
        with self.assertRaises(ContextRefusal):
            self.remember(fresh,(self.op,wrong))
        self.assertEqual(self.cache.counts(),(0,1))
        self.assertEqual(self.lookup(fresh).entries,())

    def test_joint_capacity_and_eviction(self):
        def make(i,operational):
            body="A"*4096
            v=PublicVersion(SOURCE,"fixed-"+str(i),
                "operational-learning" if operational else "current-context",
                1,1,sha256(body.encode()).digest(),True)
            return entry(v,body,2 if operational else 3)
        values=tuple(make(i,i>=16) for i in range(32))
        versions=tuple(e.version for e in values)
        route=replace(self.route,input_generation=2,
            user_record_ids=tuple(v.record_id for v in versions[:16]),
            operational_record_ids=tuple(v.record_id for v in versions[16:]))
        s=replace(self.sel,route=route,versions=versions)
        self.install(s)
        self.remember(s,values)
        self.assertEqual(self.cache.counts(),(16,16))
        self.assertEqual(len(self.lookup(s).entries),32)
        with self.assertRaises(ContextRefusal):
            self.remember(s,values+(values[0],))
        self.assertEqual(self.cache.counts(),(16,16))
        with self.assertRaises(ContextRefusal):
            self.cache.assemble_versioned(s,**self.args(s),final_use=PublicUse(s,versions))
        extra=make(32,False)
        fresh=replace(s,route=replace(route,input_generation=3,
            user_record_ids=(extra.version.record_id,)),versions=(extra.version,)+versions[16:])
        self.install(fresh)
        self.remember(fresh,(extra,))
        self.assertEqual(sum(self.cache.counts()),32)
        self.assertTrue(self.lookup(fresh).complete)

if __name__ == "__main__":
    unittest.main()
