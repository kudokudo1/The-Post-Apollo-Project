import unittest
from copy import deepcopy
from evidence_v2 import classify, PIN, ORDER, VALUES, COUNTERS

BOOT = "12345678-1234-1234-1234-123456789abc"

def fixture():
    events = [{"kind": kind, "time_ns": i+1, "target_pid": 20,
               "target_start_ticks": 30, "emitter_pid": 10 if kind == "SIGNAL_GENERATE" else 20,
               "value": value} for i, (kind, value) in enumerate(zip(ORDER, VALUES))]
    args = dict(candidate_blob=PIN, boot_id=BOOT, observed_boot_id=BOOT,
                actor_verified=True, signal_target_verified=True,
                probe_loss_verified=True, loss=dict.fromkeys(COUNTERS, 0), sender_pid=10)
    return events, args

class Evidence(unittest.TestCase):
    def refused(self, events, args):
        result = classify(events, **args)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertIs(result["can_execute"], False)
    def test_exact_candidate_never_authorizes(self):
        events, args = fixture()
        result = classify(events, **args)
        self.assertEqual(result["state"], "INTERRUPTED_RETURN_OBSERVED")
        self.assertIs(result["can_execute"], False)
    def test_missing_probe_provenance(self):
        events, args = fixture()
        args["probe_loss_verified"] = False
        self.refused(events, args)
    def test_loss_or_malformed_counters(self):
        for key in COUNTERS:
            for value in (1, -1, False, None):
                events, args = fixture()
                args["loss"][key] = value
                self.refused(events, args)
            events, args = fixture()
            del args["loss"][key]
            self.refused(events, args)
    def test_boot_candidate_and_provenance(self):
        for key, value in (("boot_id", "bad"), ("observed_boot_id", "00000000-0000-0000-0000-000000000000"),
                           ("candidate_blob", "legacy"), ("actor_verified", False),
                           ("signal_target_verified", False), ("sender_pid", True)):
            events, args = fixture()
            args[key] = value
            self.refused(events, args)
        events, args = fixture()
        args["boot_id"] = args["observed_boot_id"] = "00000000-0000-0000-0000-000000000000"
        self.refused(events, args)
    def test_sender_target_confusion(self):
        for i, key, value in ((2, "emitter_pid", 20), (5, "emitter_pid", 10),
                              (2, "target_pid", 10), (5, "target_start_ticks", 31)):
            events, args = fixture()
            events[i][key] = value
            self.refused(events, args)
    def test_success_restart_or_other_error(self):
        for i in (3,4):
            for value in (0,-512,-12,False):
                events, args = fixture()
                events[i]["value"] = value
                self.refused(events, args)
    def test_late_missing_repeated_or_tied_events(self):
        events, args = fixture()
        self.refused(events[:-1],args)
        altered = deepcopy(events)
        altered[2], altered[4] = altered[4], altered[2]
        self.refused(altered,args)
        altered = deepcopy(events)
        altered[4]["time_ns"] = altered[3]["time_ns"]
        self.refused(altered,args)
        self.refused(events+events[-1:],args)
    def test_unknown_fields_boolean_identity(self):
        events, args = fixture()
        events[0]["target_pid"] = True
        self.refused(events,args)
        events, args = fixture()
        events[0]["extra"] = 1
        self.refused(events,args)
if __name__ == "__main__":
    unittest.main()
