import unittest
from kernel_evidence import PIN, classify

def sample():
    return [dict(kind=k, time_ns=i+1, pid=123, start_ticks=456, value=v)
            for i,(k,v) in enumerate(zip(
                ("SYSCALL_ENTER","UNUSE_ENTER","SIGNAL_GENERATE","UNUSE_RETURN","SYSCALL_EXIT"),
                (168,0,15,-4,-4)))]

def check(events, **kwargs):
    return classify(events, **dict({"trace_complete":True,"actor_verified":True,
                                   "candidate_blob":PIN}, **kwargs))

class Evidence(unittest.TestCase):
    def test_ordered_shape(self):
        self.assertEqual(check(sample())["state"], "INTERRUPTED_RETURN_OBSERVED")
    def test_no_authority(self):
        self.assertFalse(check(sample())["can_execute"])
    def test_no_native_provenance(self):
        for kw in ({"trace_complete":False},{"actor_verified":False},{"candidate_blob":"old"}):
            self.assertEqual(check(sample(), **kw)["state"],"UNKNOWN")
    def test_missing_or_duplicate(self):
        for events in (sample()[:1],sample()[:-1],sample()+sample()[:1]):
            self.assertEqual(check(events)["state"],"UNKNOWN")
    def test_late_signal(self):
        e=sample(); e[2],e[3]=e[3],e[2]
        self.assertEqual(check(e)["state"],"UNKNOWN")
    def test_clock_tie_or_rollback(self):
        for t in (2,1):
            e=sample(); e[2]["time_ns"]=t
            self.assertEqual(check(e)["state"],"UNKNOWN")
    def test_actor_change(self):
        for key in ("pid","start_ticks"):
            e=sample(); e[2][key]+=1
            self.assertEqual(check(e)["state"],"UNKNOWN")
    def test_signal_or_success_not_interrupt(self):
        for idx,v in ((2,9),(3,0),(4,0),(4,-512),(4,-22),(4,True)):
            e=sample(); e[idx]["value"]=v
            self.assertEqual(check(e)["state"],"UNKNOWN")
    def test_wrong_syscall(self):
        e=sample(); e[0]["value"]=167
        self.assertEqual(check(e)["state"],"UNKNOWN")

if __name__ == "__main__":
    unittest.main()
