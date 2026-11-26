"""M7f-b fixed-public cache witness; no real read, permission or provider."""
from dataclasses import dataclass, replace
from threading import RLock
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
    PUBLIC_RESTORATION_CONTEXT,
)


def version(v):
    return PublicVersion(v.source, v.record_id, v.kind, v.revision,
                         v.record_generation, bytes.fromhex(v.commitment), v.active)


def entry(v, text, generation):
    return PublicEntry(v, SelectedHotRecord(CONTEXT.principal_key, CONTEXT.tree_key,
        v.record_id, v.kind, generation, True, text))



# Test-local owner observation, not a runtime registry or authority.
@dataclass(frozen=True)
class SeasonalObservation:
    cache: TaskStickyContext
    context: object
    operation: str
    attempt: str
    revision: int
    phase: str


class SeasonalWitness:
    def __init__(self, observed):
        self.lock = RLock()
        self.current = observed

    def observe(self, independently_observed):
        # Fixture owner supplies the current record, never a request notice.
        with self.lock:
            self.current = independently_observed

    def apply(self, notice, action, requested, *, current, dependencies, use,
              final_use=None, entries=(), drop_user=False, drop_operational=False):
        with self.lock:
            pinned = self.current
            if (type(notice) is not SeasonalObservation
                    or notice.cache is not pinned.cache or notice != pinned
                    or type(notice.revision) is not int):
                raise ContextRefusal("SEASON_LIFETIME_CHANGED")
            if (type(requested) is not PublicSelection
                    or type(current) is not PublicSelection
                    or requested != current or current.route.context != pinned.context
                    or type(dependencies) is not HotDependencies
                    or dependencies != HotDependencies.from_route(current.route)
                    or type(use) is not PublicUse or use.selection != current
                    or (final_use is not None and
                        (type(final_use) is not PublicUse or final_use.selection != current))):
                raise ContextRefusal("SEASON_USE_SCOPE")
            cache = pinned.cache
            # Use the original cache's exact revocation path, not a successful
            # initial lookup or an alternate destructive cache operation.
            for observation in (use, final_use):
                if observation is not None and observation.revoked:
                    cache.lookup_versioned(requested, current=current,
                        dependencies=dependencies, use=observation)
                    raise AssertionError("explicit revoke returned")
            if pinned.phase in ("PENDING", "UNKNOWN"):
                raise ContextRefusal("SEASON_HOLD")
            args = dict(current=current, dependencies=dependencies, use=use)
            if action == "close" and pinned.phase == "RETIRED":
                cache.close()
                return None
            if action == "shed" and pinned.phase == "FALL":
                return cache.shed_versioned(requested, **args,
                    drop_user=drop_user, drop_operational=drop_operational)
            if pinned.phase in ("SPRING", "SUMMER"):
                if action == "install":
                    return cache.install_versioned(requested, **args)
                if action == "remember":
                    return cache.remember_versioned(requested, **args, entries=entries)
                if action == "lookup":
                    return cache.lookup_versioned(requested, **args)
                if action == "assemble" and final_use is not None:
                    return cache.assemble_versioned(requested, **args, final_use=final_use)
            raise ContextRefusal("SEASON_ACTION_HOLD")


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

    def test_newer_input_lookup_revocation_fences_without_install(self):
        fresh=self.fresh(input_generation=2)
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.lookup(fresh,PublicUse(fresh,(),(self.u,)))
        self.assertEqual(self.cache.counts(),(0,0))
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(self.fresh(input_generation=3))
        allowed=self.fresh(input_generation=4,policy_generation=3)
        self.install(allowed)
        self.assertEqual(self.lookup(allowed).entries,())
        self.remember(allowed,(self.user,self.op))
        self.assertTrue(self.lookup(allowed).complete)

    def test_newer_input_lookup_without_revocation_requires_install(self):
        fresh=self.fresh(input_generation=2)
        with self.assertRaisesRegex(ContextRefusal,"HOT_ROUTE_CHANGED"):
            self.lookup(fresh)
        self.assertEqual(self.cache.counts(),(1,1))
        self.install(fresh)
        self.assertEqual(self.lookup(fresh).entries,(self.user,self.op))

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


    def test_final_use_revocation_on_partial_miss_fences_both_domains(self):
        for clocks, missing, retained in (
                (dict(user_context_generation=4), self.u, (0,1)),
                (dict(operational_generation=3), self.o, (1,0))):
            with self.subTest(clocks=clocks):
                self.setUp()
                fresh=self.fresh(input_generation=2,**clocks)
                self.install(fresh)
                result=self.lookup(fresh)
                self.assertEqual(result.missing,(missing,))
                self.assertEqual(result.entries,())
                self.assertEqual(self.cache.counts(),retained)
                with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
                    self.cache.assemble_versioned(fresh,**self.args(fresh),
                        final_use=PublicUse(fresh,(),(missing,)))
                self.assertEqual(self.cache.counts(),(0,0))
                with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
                    self.install(replace(fresh,route=replace(fresh.route,input_generation=3)))
                allowed=replace(fresh,route=replace(fresh.route,input_generation=4,
                                                    policy_generation=3))
                self.install(allowed)
                self.assertEqual(self.lookup(allowed).missing,allowed.versions)

    def test_partial_miss_stale_or_mismatched_final_use_preserves_replacement(self):
        fresh=self.fresh(input_generation=2,user_context_generation=4)
        self.install(fresh)
        for wrong in (self.sel,replace(fresh,recipient="other")):
            with self.subTest(selection=wrong):
                with self.assertRaisesRegex(ContextRefusal,"SCOPE"):
                    self.cache.assemble_versioned(fresh,**self.args(fresh),
                        final_use=PublicUse(wrong,(),(self.u,)))
                self.assertEqual(self.cache.counts(),(0,1))
                self.assertEqual(self.lookup(fresh).missing,(self.u,))
                self.assertEqual(self.lookup(fresh).entries,())
        self.remember(fresh,(entry(self.u,BODIES[1][2],4),))
        self.assertEqual(self.lookup(fresh).entries,
                         (entry(self.u,BODIES[1][2],4),self.op))

    def test_partial_miss_nonrevoked_final_use_returns_no_body(self):
        fresh=self.fresh(input_generation=2,user_context_generation=4)
        self.install(fresh)
        with self.assertRaisesRegex(ContextRefusal,"STICKY_RECORDS_MISSING"):
            self.cache.assemble_versioned(fresh,**self.args(fresh),
                final_use=PublicUse(fresh,fresh.versions))
        self.assertEqual(self.cache.counts(),(0,1))
        self.assertEqual(self.lookup(fresh).entries,())
        self.remember(fresh,(entry(self.u,BODIES[1][2],4),))
        self.assertTrue(self.lookup(fresh).complete)

    def test_partial_miss_revocation_clears_two_nonempty_pools(self):
        extra=PublicVersion(SOURCE,"extra","current-context",1,1,
                            sha256(b"Public extra").digest(),True)
        fresh=replace(self.fresh(input_generation=2),versions=(self.u,extra,self.o),
                      route=replace(self.route,input_generation=2,
                                    user_record_ids=("preference","extra")))
        self.install(fresh)
        self.assertEqual(self.cache.counts(),(1,1))
        self.assertEqual(self.lookup(fresh).missing,(extra,))
        self.assertEqual(self.lookup(fresh).entries,())
        with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
            self.cache.assemble_versioned(fresh,**self.args(fresh),
                final_use=PublicUse(fresh,(),(extra,)))
        self.assertEqual(self.cache.counts(),(0,0))
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            self.install(replace(fresh,route=replace(fresh.route,input_generation=3)))


    def seasonal(self, phase="SUMMER"):
        notice=SeasonalObservation(self.cache,CONTEXT,"operation-a","attempt-a",1,phase)
        return SeasonalWitness(notice),notice

    def test_m7g_exact_restoration_allowlist(self):
        restored=PUBLIC_RESTORATION_CONTEXT
        self.assertEqual(restored.generation,2)
        self.assertNotEqual(restored.execution_context_id,CONTEXT.execution_context_id)
        self.assertEqual(TaskStickyContext(restored,mode="public-versioned").counts(),(0,0))
        for wrong in (replace(restored,generation=3),replace(restored,task_id="other"),
                      replace(restored,clone_key="other"),replace(restored,tree_key="maple"),
                      replace(restored,principal_key="other"),replace(restored,origin="BACKGROUND"),
                      replace(restored,execution_context_id=CONTEXT.execution_context_id)):
            with self.subTest(context=wrong):
                with self.assertRaisesRegex(ContextRefusal,"SCOPE"):
                    TaskStickyContext(wrong,mode="public-versioned")
                self.assertEqual(TaskStickyContext(wrong).counts(),(0,0))

    def test_m7g_summer_current_use_and_live_spring_selective_rebuild(self):
        owner,n=self.seasonal()
        result,_=owner.apply(n,"assemble",self.sel,**self.args(self.sel),
            final_use=PublicUse(self.sel,self.sel.versions))
        self.assertEqual(result.entries,(self.user,self.op))
        with self.assertRaisesRegex(ContextRefusal,"USE"):
            owner.apply(n,"lookup",self.sel,**self.args(self.sel,PublicUse(self.sel,())))
        self.assertEqual(self.cache.counts(),(1,1))
        spring=replace(n,phase="SPRING",revision=2)
        owner.observe(spring)
        fresh=self.fresh(input_generation=2,user_context_generation=4)
        owner.apply(spring,"install",fresh,**self.args(fresh))
        result=owner.apply(spring,"lookup",fresh,**self.args(fresh))
        self.assertEqual((result.entries,result.missing),((),(self.u,)))
        self.assertEqual(self.cache.counts(),(0,1))
        owner.apply(spring,"remember",fresh,**self.args(fresh),
                    entries=(entry(self.u,BODIES[1][2],4),))
        self.assertTrue(owner.apply(spring,"lookup",fresh,**self.args(fresh)).complete)

    def test_m7g_fall_selective_shed_and_newer_input(self):
        owner,n=self.seasonal("FALL")
        owner.apply(n,"shed",self.sel,**self.args(self.sel),drop_user=True)
        self.assertEqual(self.cache.counts(),(0,1))
        spring=replace(n,phase="SPRING",revision=2)
        owner.observe(spring)
        with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
            owner.apply(spring,"install",self.sel,**self.args(self.sel))
        fresh=self.fresh(input_generation=2)
        owner.apply(spring,"install",fresh,**self.args(fresh))
        self.assertEqual(owner.apply(spring,"lookup",fresh,**self.args(fresh)).missing,(self.u,))
        self.assertEqual(self.cache.counts(),(0,1))

    def test_m7g_pending_unknown_no_use_or_close(self):
        for phase in ("PENDING","UNKNOWN"):
            with self.subTest(phase=phase):
                owner,n=self.seasonal(phase)
                for action in ("install","remember","lookup","assemble","shed","close"):
                    with self.assertRaisesRegex(ContextRefusal,"SEASON_HOLD"):
                        owner.apply(n,action,self.sel,**self.args(self.sel),
                            final_use=PublicUse(self.sel,self.sel.versions),
                            entries=(self.user,self.op),drop_user=True)
                    self.assertEqual(self.cache.counts(),(1,1))
                self.assertTrue(self.lookup().complete)

    def test_m7g_current_final_revocation_precedes_season_and_lookup_refusal(self):
        for phase in ("PENDING","UNKNOWN","SUMMER"):
            for missing_route in (False,True):
                with self.subTest(phase=phase,missing_route=missing_route):
                    self.setUp()
                    owner,n=self.seasonal(phase)
                    s=self.fresh(input_generation=2) if missing_route else self.sel
                    self.assertEqual(self.cache.counts(),(1,1))
                    # Initial eligibility is unknown. Final observation is an
                    # independently supplied exact current explicit revoke.
                    with self.assertRaisesRegex(ContextRefusal,"REVOKED"):
                        owner.apply(n,"assemble",s,**self.args(s,PublicUse(s,())),
                                    final_use=PublicUse(s,(),(self.u,)))
                    self.assertEqual(self.cache.counts(),(0,0))
                    with self.assertRaisesRegex(ContextRefusal,"FLOOR"):
                        self.install(self.fresh(input_generation=3))

    def test_m7g_winter_old_close_and_new_spring_no_transfer(self):
        owner,n=self.seasonal()
        with self.assertRaisesRegex(ContextRefusal,"ACTION_HOLD"):
            owner.apply(n,"close",self.sel,**self.args(self.sel))
        winter=replace(n,phase="RETIRED",revision=2)
        owner.observe(winter)
        owner.apply(winter,"close",self.sel,**self.args(self.sel))
        self.assertEqual(self.cache.counts(),(0,0))
        with self.assertRaisesRegex(ContextRefusal,"CLOSED"):
            self.install(self.sel)
        replacement=TaskStickyContext(PUBLIC_RESTORATION_CONTEXT,mode="public-versioned")
        spring=SeasonalObservation(replacement,PUBLIC_RESTORATION_CONTEXT,
                                   "operation-b","attempt-b",1,"SPRING")
        owner.observe(spring)
        fresh=self.fresh(context=PUBLIC_RESTORATION_CONTEXT)
        owner.apply(spring,"install",fresh,**self.args(fresh))
        empty=owner.apply(spring,"lookup",fresh,**self.args(fresh))
        self.assertEqual((empty.entries,empty.missing),((),fresh.versions))
        # Explicit fresh owner supply, never copying entries from old cache.
        owner.apply(spring,"remember",fresh,**self.args(fresh),
            entries=(entry(self.u,BODIES[1][2],3),entry(self.o,BODIES[2][2],2)))
        self.assertTrue(owner.apply(spring,"lookup",fresh,**self.args(fresh)).complete)
        impostor=TaskStickyContext(PUBLIC_RESTORATION_CONTEXT,mode="public-versioned")
        for wrong in (winter,replace(spring,cache=impostor),replace(spring,operation="other"),
                      replace(spring,attempt="other"),replace(spring,revision=2),
                      replace(spring,context=CONTEXT)):
            with self.subTest(notice=wrong):
                for action in ("close","assemble"):
                    with self.assertRaisesRegex(ContextRefusal,"LIFETIME_CHANGED"):
                        owner.apply(wrong,action,fresh,**self.args(fresh),
                            final_use=PublicUse(fresh,(),(self.u,)))
                self.assertEqual(replacement.counts(),(1,1))
        with self.assertRaisesRegex(ContextRefusal,"USE_SCOPE"):
            owner.apply(spring,"assemble",fresh,**self.args(fresh),
                        final_use=PublicUse(self.sel,(),(self.u,)))
        self.assertEqual(replacement.counts(),(1,1))
        self.assertTrue(owner.apply(spring,"lookup",fresh,**self.args(fresh)).complete)
        self.assertEqual(impostor.counts(),(0,0))

if __name__ == "__main__":
    unittest.main()
