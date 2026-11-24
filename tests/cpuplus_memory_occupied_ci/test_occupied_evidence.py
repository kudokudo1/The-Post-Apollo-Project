import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("occupied", Path(__file__).with_name("guest-occupied.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Evidence(unittest.TestCase):
    def receipt(self):
        return {"state": "WAITING", "code": "EXTENSION_OCCUPIED",
                "evidence": {"extensionUsedKiB": 4096, "availableKiB": 5000000,
                             "requiredRamKiB": 4194304, "baseFreeKiB": 4194300,
                             "requiredBaseFreeKiB": 2097152}}
    def test_occupied_evidence(self):
        self.assertEqual(m.occupied_evidence(self.receipt())["extensionUsedKiB"], 4096)
    def test_zero_occupancy_refuses(self):
        for used in (0, -1, True, "4096"):
            with self.subTest(used=used):
                r = self.receipt()
                r["evidence"]["extensionUsedKiB"] = used
                with self.assertRaisesRegex(RuntimeError, "occupancy"):
                    m.occupied_evidence(r)
    def test_wrong_blocker_refuses(self):
        r = self.receipt()
        r["code"] = "RAM_HEADROOM"
        with self.assertRaisesRegex(RuntimeError, "blocker"):
            m.occupied_evidence(r)
    def test_other_headroom_failure_refuses(self):
        for key in ("availableKiB", "baseFreeKiB"):
            with self.subTest(key=key):
                r = self.receipt()
                r["evidence"][key] = 0
                with self.assertRaisesRegex(RuntimeError, "confounds"):
                    m.occupied_evidence(r)

if __name__ == "__main__":
    unittest.main()
