"""M1: offline guardrails and JPL-backed numerical integration checks.

Integration tests run with MAGICK_M1_KERNEL pointing at a local DE440s BSP.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_solver as solver


def request(*bodies, origin="geocentric", mode="apparent", observer=None,
            moment="2019-09-02T10:42:26Z"):
    data = {
        "format": contract.REQUEST_FORMAT,
        "instant_utc": moment,
        "origin": origin,
        "position_model": mode,
        "frame": contract.FRAME,
        "bodies": list(bodies),
    }
    if observer is not None:
        data["observer"] = observer
    return data


class OfflineGuards(unittest.TestCase):
    def test_explicit_local_kernel_required_before_skyfield(self):
        with self.assertRaisesRegex(contract.ContractError, "existing local"):
            solver.compute_snapshot(request("moon"), "/no/such/file/de440s.bsp")

    def test_never_accept_wrong_kernel_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            wrong = Path(directory) / "data.txt"
            wrong.write_text("this is not SPK")
            with self.assertRaisesRegex(contract.ContractError, "local .bsp"):
                solver.compute_snapshot(request("moon"), wrong)

    def test_no_implicit_time_or_location(self):
        data = request("moon", origin="topocentric")
        with self.assertRaises(contract.ContractError):
            solver.compute_snapshot(data, "not-a-kernel.bsp")
        data = request("moon")
        data["instant_utc"] = "2019-09-02T06:42:26-04:00"
        with self.assertRaises(contract.ContractError):
            solver.compute_snapshot(data, "not-a-kernel.bsp")

    def test_center_vs_barycenter_are_distinct(self):
        self.assertEqual(solver.NAIF_IDS["mars"], 499)
        self.assertEqual(solver.NAIF_IDS["mars_barycenter"], 4)
        self.assertNotEqual(solver.NAIF_IDS["earth"], solver.NAIF_IDS["moon"])
        self.assertIn("mars_barycenter", contract.BODIES)

    def test_digest_is_real_file_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.bsp"
            path.write_bytes(b"abc")
            self.assertEqual(solver._digest(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"), "requires explicit JPL BSP for integration")
class JplDe440sIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = os.environ["MAGICK_M1_KERNEL"]

    def test_geocentric_actual_sun_moon_and_mars_barycenter(self):
        actual = solver.compute_snapshot(request("sun", "moon", "mars_barycenter"), self.kernel)
        self.assertEqual(contract.validate_snapshot(actual)["body_count"], 3)
        self.assertEqual(actual["provenance"]["ephemeris_id"], "de440s.bsp")
        self.assertEqual(len(actual["provenance"]["ephemeris_sha256"]), 64)
        positions = {r["body"]: r for r in actual["positions"]}
        for body in positions.values():
            self.assertGreaterEqual(body["longitude_deg"], 0)
            self.assertLess(body["longitude_deg"], 360)
            self.assertGreater(body["distance_au"], 0)
        # Skyfield published example: 2019-09-02 10:42:26 UTC Sun ~159.68641°.
        # DE440s vs example DE421 differences are much smaller than 0.02°.
        self.assertAlmostEqual(positions["sun"]["longitude_deg"], 159.68641, delta=0.02)
        self.assertLess(abs(positions["mars_barycenter"]["longitude_deg"] -
                            positions["sun"]["longitude_deg"]), 0.03)

    def test_geometric_earth_sun_reverse_vector(self):
        moment = "2026-11-03T12:00:00Z"
        geo = solver.compute_snapshot(request("sun", mode="geometric", moment=moment), self.kernel)
        helio = solver.compute_snapshot(request("earth", origin="heliocentric",
            mode="geometric", moment=moment), self.kernel)
        a, b = geo["positions"][0], helio["positions"][0]
        self.assertAlmostEqual((b["longitude_deg"] - a["longitude_deg"]) % 360, 180, delta=1e-8)
        self.assertAlmostEqual(a["latitude_deg"], -b["latitude_deg"], delta=1e-8)
        self.assertAlmostEqual(a["distance_au"], b["distance_au"], delta=1e-12)

    def test_local_moon_parallax_changes_coordinates(self):
        moment = "2026-11-03T12:00:00Z"
        geo = solver.compute_snapshot(request("moon", moment=moment), self.kernel)
        topo = solver.compute_snapshot(request("moon", origin="topocentric", moment=moment,
            observer={"latitude_deg": 38.9, "longitude_deg": -76.7,
                      "elevation_m": 20}), self.kernel)
        a, b = geo["positions"][0], topo["positions"][0]
        self.assertGreater(abs(a["latitude_deg"] - b["latitude_deg"]) +
                           abs(a["longitude_deg"] - b["longitude_deg"]), 0.001)

    def test_mars_mass_center_unavailable_does_not_relabel(self):
        with self.assertRaisesRegex(contract.ContractError, "exact target for mars"):
            solver.compute_snapshot(request("mars"), self.kernel)

    def test_kernel_coverage_not_extrapolated(self):
        with self.assertRaisesRegex(contract.ContractError, "coverage"):
            solver.compute_snapshot(request("sun", moment="1800-01-01T00:00:00Z"), self.kernel)


if __name__ == "__main__":
    unittest.main()
