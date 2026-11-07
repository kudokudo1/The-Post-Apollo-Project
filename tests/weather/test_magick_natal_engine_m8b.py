"""M8b pure-numerical natal regressions, no BSP/Skyfield download."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "weather"))
import celestial_natal_chart as natal
from celestial_contract import ContractError


def request(**overrides):
    raw = {
        "format": natal.REQUEST_FORMAT,
        "epoch_utc": "2026-11-06T14:20:00Z",
        "latitude_deg": 38.9,
        "longitude_deg": -76.8,
        "zodiac": "tropical",
        "house_system": "whole-sign",
    }
    raw.update(overrides)
    return raw


class NatalCalculatorTest(unittest.TestCase):
    def test_explicit_utc_and_coordinates_only(self):
        self.assertEqual(natal.normalize(request())["epoch_utc"],
                         "2026-11-06T14:20:00Z")
        for bad in (
            {"epoch_utc": "2026-11-06T14:20:00-05:00"},
            {"epoch_utc": "2026-02-29T14:20:00Z"},
            {"epoch_utc": "2026-11-06T24:20:00Z"},
            {"epoch_utc": "2026-11-06"},
            {"epoch_utc": "2100-01-01T00:00:00Z"},
            {"latitude_deg": 91},
            {"latitude_deg": True},
            {"latitude_deg": float("nan")},
            {"longitude_deg": 181},
            {"longitude_deg": "38.9"},
            {"house_system": "placidus"},
            {"zodiac": "sidereal"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ContractError):
                    natal.normalize(request(**bad))
        with self.assertRaises(ContractError):
            natal.normalize({**request(), "extra": "birth-record"})
        with self.assertRaises(ContractError):
            natal.normalize({k: v for k, v in request().items() if k != "latitude_deg"})

    def test_known_ascendant_and_midheaven_against_independent_reference(self):
        # Independently derived Swiss Ephemeris reference for:
        # 2026-11-06 14:20 UTC, 38.9 N, 76.8 W, true obliquity 23.4379242.
        # Upper meridian and East horizon solutions must select correct roots.
        epsilon = math.radians(23.437924203463336)
        eq_to_ecl = (
            (1.0, 0.0, 0.0),
            (0.0, math.cos(epsilon), math.sin(epsilon)),
            (0.0, -math.sin(epsilon), math.cos(epsilon)),
        )
        gast = (184.01656372212443 + 76.8) / 15.0
        asc, mc = natal.angles_from_frame(38.9, -76.8, gast, eq_to_ecl)
        self.assertAlmostEqual(asc, 255.570003845761, places=5)
        self.assertAlmostEqual(mc, 184.376420714428, places=5)
        self.assertNotAlmostEqual(asc, mc)
        self.assertEqual(natal.house_cusps(asc, "whole-sign")[:3],
                         [240, 270, 300])
        equal = natal.house_cusps(asc, "equal")
        self.assertAlmostEqual(equal[0], asc)
        self.assertAlmostEqual(equal[1], (asc + 30) % 360)

    def test_geometry_quadrants_and_invalid_frame(self):
        identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        asc, mc = natal.angles_from_frame(0, 0, 0, identity)
        self.assertAlmostEqual(asc, 90)
        self.assertAlmostEqual(mc, 0)
        asc, mc = natal.angles_from_frame(0, 0, 6, identity)
        self.assertAlmostEqual(asc, 180)
        self.assertAlmostEqual(mc, 90)
        with self.assertRaises(ContractError):
            natal.angles_from_frame(0, 0, 0, ((1, 2),))
        with self.assertRaises(ContractError):
            natal.angles_from_frame(90, 0, 0, identity)

    def test_exact_targets_no_planet_center_barycenter_label_swaps(self):
        expected = ("sun", "moon", "mercury", "venus", "mars_barycenter",
                    "jupiter_barycenter", "saturn_barycenter",
                    "uranus_barycenter", "neptune_barycenter",
                    "pluto_barycenter")
        self.assertEqual(natal.BODY_IDS, expected)
        self.assertEqual(len(natal.BODY_IDS), 10)
        self.assertEqual(natal.NAIF_IDS["mercury"], 199)
        self.assertEqual(natal.NAIF_IDS["venus"], 299)
        self.assertEqual(natal.NAIF_IDS["mars_barycenter"], 4)
        self.assertEqual(natal.NAIF_IDS["jupiter_barycenter"], 5)

    def test_no_private_birth_details_in_argv_or_storage(self):
        script=(ROOT/"scripts/weather/celestial_natal_chart.py").read_text()
        self.assertIn("sys.stdin.readline(2049)", script)
        self.assertIn('args = parser.parse_args(argv)', script)
        self.assertIn("_position(origin, _target(kernel, name), t, \"apparent\")",
                      script)
        self.assertIn("true_equator_and_equinox_of_date.rotation_at(t)", script)
        self.assertIn("float(t.gast)", script)
        self.assertIn("loader.timescale(builtin=True)", script)
        for forbidden in (
            "requests.get(", "urllib.request", "open('/home",
            "sqlite3.connect(", "pickle.dump(", "os.system(", "subprocess.run(",
            "load.download(", "--latitude", "--longitude", "--birth",
        ):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
