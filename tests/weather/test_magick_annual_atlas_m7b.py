"""M7b source-contract tests. Synthetic fixtures test formatting, not ephemerides."""
from datetime import date, datetime, timedelta, timezone
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "weather"))
import celestial_annual_calendar as atlas

SHA = "a" * 64


def fixture(year=2026, zone="UTC"):
    start = date(year, 1, 1)
    length = (date(year+1,1,1)-start).days
    daily = [
        {"date": (start+timedelta(days=i)).isoformat(),
         "phase_angle_deg": (i*12.2)%360,
         "illumination": (i*10)%101}
        for i in range(length)
    ]
    # Chronological synthetic events only; intentionally NOT real 2026 dates.
    moons = [
        {"id": atlas.MAJOR_PHASES[i%4],
         "time_utc": atlas.utc_label(datetime(
             year,1,1,tzinfo=timezone.utc)+timedelta(days=i*7))}
        for i in range(50)
    ]
    sun = [
        {"id": atlas.SOLAR_TERMS[i], "longitude_deg": i*15,
         "time_utc": atlas.utc_label(datetime(
             year,1,1,tzinfo=timezone.utc)+timedelta(days=i*15))}
        for i in range(24)
    ]
    source = {"engine":"skyfield", "ephemeris_sha256":SHA,
              "ephemeris_id":"synthetic-test-only"}
    return daily, moons, sun, source


class AnnualAtlasTest(unittest.TestCase):
    def test_all_days_and_solar_longitudes_are_structured(self):
        data, moon, sun, source = fixture()
        result = atlas.assemble(2026, "UTC", data, moon, sun, source)
        self.assertEqual(result["format"], atlas.FORMAT)
        self.assertEqual(len(result["days"]), 365)
        self.assertEqual(len(result["calendar_markers"]["daily_moon"]), 365)
        self.assertEqual(len(result["solar_terms"]), 24)
        self.assertEqual(len(result["lunar_events"]), 50)
        self.assertEqual(len(result["calendar_markers"]["events"]), 74)
        self.assertEqual(result["days"][0]["phase_id"], "new")
        self.assertEqual(result["solar_terms"][6]["longitude_deg"], 90)
        self.assertTrue(result["solar_terms"][6]["major"])
        self.assertEqual(result["solar_terms"][0]["id"], "spring-equinox")

    def test_leap_year_and_no_year_invention(self):
        data, moon, sun, source = fixture(2024)
        result = atlas.assemble(2024, "UTC", data, moon, sun, source)
        self.assertEqual(len(result["days"]),366)
        self.assertEqual(result["days"][59]["date"],"2024-02-29")
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2024,"UTC",data[:-1],moon,sun,source)
        data[59]["date"]="2024-03-01"
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2024,"UTC",data,moon,sun,source)

    def test_phase_band_boundaries(self):
        self.assertEqual(atlas.phase_band(0),"new")
        self.assertEqual(atlas.phase_band(22.49),"new")
        self.assertEqual(atlas.phase_band(22.5),"waxing-crescent")
        self.assertEqual(atlas.phase_band(90),"first-quarter")
        self.assertEqual(atlas.phase_band(180),"full")
        self.assertEqual(atlas.phase_band(270),"last-quarter")
        self.assertEqual(atlas.phase_band(359.9),"new")
        for angle in (-1,360,float("nan"),float("inf")):
            with self.assertRaises(atlas.ContractError):
                atlas.phase_band(angle)

    def test_year_zone_and_source_require_provenance(self):
        for year,zone in ((1899,"UTC"),(2100,"UTC"),(True,"UTC"),
                          (2026,"not/a-valid-zone"),(2026,"../UTC"),
                          (2026,"UTC\n/attack")):
            with self.assertRaises(atlas.ContractError):
                atlas.year_zone(year,zone)
        self.assertIsNotNone(atlas.year_zone(2026,"America/New_York"))
        data, moon, sun, source = fixture()
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"UTC",data,moon,sun,{})
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"UTC",data,moon,sun[:23],source)
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"UTC",data,moon[:44],sun,source)

    def test_invalid_solar_term_angle_and_event_boundaries(self):
        data, moon, sun, source = fixture()
        sun[0]["longitude_deg"]=3
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"UTC",data,moon,sun,source)
        sun[0]["longitude_deg"]=0
        moon[0]["time_utc"]="2025-12-31T23:59:59Z"
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"UTC",data,moon,sun,source)

    def test_dst_local_calendar_dates_use_explicit_iana_zone(self):
        data, moon, sun, source = fixture()
        # Synthetic 2026-11-01 01:00 UTC is still October 31 in New York.
        moon[43]["time_utc"]="2026-11-01T01:00:00Z"
        # This deliberately makes events nonmonotonic and must fail.
        with self.assertRaises(atlas.ContractError):
            atlas.assemble(2026,"America/New_York",data,moon,sun,source)
        self.assertEqual(
            datetime.fromisoformat("2026-11-01T01:00:00+00:00")
            .astimezone(atlas.year_zone(2026,"America/New_York"))
            .date().isoformat(),"2026-10-31")

    def test_no_local_side_effects_or_synthetic_numerical_fallback(self):
        text=(ROOT/"scripts/weather/celestial_annual_calendar.py").read_text()
        self.assertIn("almanac.moon_phases(kernel)", text)
        self.assertIn("almanac.find_discrete(left, right, solar_index)", text)
        self.assertIn("frame_latlon(ecliptic_frame)", text)
        self.assertIn("builtin=True", text)
        for forbidden in ("urlopen(", "requests.get(", "load.download(",
                          "open(\\\"/home", "pip install", "os.system("):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
