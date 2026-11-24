import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("fixture", Path(__file__).with_name("guest-headroom.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class HeadroomBounds(unittest.TestCase):
    def run_samples(self, samples, regions):
        values = iter(samples)
        return m.hold_headroom(lambda: next(values), object, regions,
                               now=lambda: 0, pause=lambda _: None)

    def test_real_threshold_target_with_margin(self):
        regions = []
        g = m.GIB_KIB
        available, required = self.run_samples([(6*g, 4*g+1), (6*g, 4*g-m.MARGIN_KIB)], regions)
        self.assertEqual(required, 4*g)
        self.assertEqual(available, 4*g-m.MARGIN_KIB)
        self.assertEqual(len(regions), 1)

    def test_independent_floor_refuses(self):
        regions = []
        with self.assertRaisesRegex(RuntimeError, "floor"):
            self.run_samples([(6*m.GIB_KIB, m.FLOOR_KIB-1)], regions)
        self.assertEqual(regions, [])

    def test_allocation_cap_refuses(self):
        regions = [object()] * (m.MAX_ALLOC//m.STEP)
        with self.assertRaisesRegex(RuntimeError, "cap"):
            self.run_samples([(6*m.GIB_KIB, 5*m.GIB_KIB)], regions)
        self.assertEqual(len(regions), m.MAX_ALLOC//m.STEP)

    def test_time_limit_refuses_before_allocation(self):
        times = iter((0, m.DEADLINE_SECONDS))
        regions = []
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            m.hold_headroom(lambda:(6*m.GIB_KIB,5*m.GIB_KIB),object,regions,
                            now=lambda:next(times),pause=lambda _:None)
        self.assertEqual(regions, [])

if __name__ == "__main__":
    unittest.main()
