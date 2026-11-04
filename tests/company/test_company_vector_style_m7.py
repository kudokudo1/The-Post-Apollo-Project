"""M7 nationwide/global Post-Apollo OpenMapTiles style and opt-in source contracts."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"experiments/company-vector-qt"
STYLE=BASE/"style-post-apollo-online.json"

class PostApolloVectorStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.style=json.loads(STYLE.read_text(encoding="utf-8"))
        cls.layers={layer["id"]:layer for layer in cls.style["layers"]}

    def test_schema_world_source_and_no_region_or_provider_credentials(self):
        s=self.style
        self.assertEqual(s["version"],8)
        self.assertEqual(s["sources"]["openmaptiles"]["type"],"vector")
        self.assertEqual(s["sources"]["openmaptiles"]["url"],"https://tiles.openfreemap.org/planet")
        self.assertEqual(s["glyphs"],"https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf")
        self.assertIn("OpenStreetMap",s["sources"]["openmaptiles"]["attribution"])
        self.assertNotIn("bounds",s["sources"]["openmaptiles"])
        self.assertEqual(s["metadata"]["service-coverage"],"none")
        text=STYLE.read_text(encoding="utf-8").lower()
        for forbidden in ("googleapis.com", "mapbox.com", "api_key", "api-key",
                          "clientname", "employeeid", "access_token", "password"):
            self.assertNotIn(forbidden,text)

    def test_motorways_through_minor_and_residential_scale_are_distinct(self):
        for cl in ("motorway","trunk","primary","secondary","tertiary",
                   "minor","service","track","path","pedestrian"):
            with self.subTest(road=cl):
                layer=self.layers["pa-"+cl]
                casing=self.layers["pa-"+cl+"-casing"]
                self.assertEqual(layer["type"],"line")
                self.assertEqual(layer["source-layer"],"transportation")
                self.assertEqual(casing["source-layer"],"transportation")
                self.assertEqual(layer["source"],"openmaptiles")
                self.assertLessEqual(layer["minzoom"],17)
                self.assertIn("line-color",layer["paint"])
                self.assertIn("line-width",layer["paint"])
        self.assertLess(self.layers["pa-motorway"]["minzoom"],self.layers["pa-minor"]["minzoom"])
        self.assertLess(self.layers["pa-minor"]["minzoom"],self.layers["pa-service"]["minzoom"])
        self.assertEqual(self.layers["pa-motorway"]["paint"]["line-color"],"#ED981A")
        self.assertEqual(self.layers["pa-secondary"]["paint"]["line-color"],"#5B5FD4")

    def test_place_labels_include_small_towns_suburbs_and_neighborhoods(self):
        names=("country","state","city","town","village","suburb",
               "quarter","neighbourhood","hamlet","isolated_dwelling")
        for cl in names:
            with self.subTest(place=cl):
                layer=self.layers["pa-place-"+cl]
                self.assertEqual(layer["source-layer"],"place")
                self.assertEqual(layer["type"],"symbol")
                self.assertEqual(layer["layout"]["text-allow-overlap"],False)
                self.assertIn("text-field",layer["layout"])
        self.assertLess(self.layers["pa-place-city"]["minzoom"],
                        self.layers["pa-place-neighbourhood"]["minzoom"])
        self.assertLess(self.layers["pa-place-town"]["minzoom"],
                        self.layers["pa-place-hamlet"]["minzoom"])

    def test_buildings_addresses_water_road_names_and_base_palette(self):
        self.assertEqual(self.layers["pa-background"]["paint"]["background-color"],"#1B0623")
        self.assertEqual(self.layers["pa-water"]["source-layer"],"water")
        self.assertEqual(self.layers["pa-building"]["source-layer"],"building")
        self.assertEqual(self.layers["pa-house-number"]["source-layer"],"housenumber")
        self.assertGreaterEqual(self.layers["pa-building"]["minzoom"],14)
        self.assertGreaterEqual(self.layers["pa-house-number"]["minzoom"],17)
        self.assertEqual(self.layers["pa-road-name"]["source-layer"],"transportation_name")
        self.assertIn("pa-national-border",self.layers)
        self.assertIn("pa-regional-border",self.layers)
        self.assertEqual(len(self.layers),len(self.style["layers"]),"layer IDs must be unique")

    def test_online_style_never_changes_offline_default(self):
        cpp=(BASE/"main.cpp").read_text(encoding="utf-8")
        cmake=(BASE/"CMakeLists.txt").read_text(encoding="utf-8")
        qml=(BASE/"main.qml").read_text(encoding="utf-8")
        self.assertIn('args.contains("--styled-online")',cpp)
        self.assertIn('args.contains("--online")',cpp)
        self.assertIn('const bool anyOnline = online || styledOnline;',cpp)
        self.assertIn("QUrl::fromLocalFile(localPath)",cpp)
        self.assertIn("QUrl::fromLocalFile(styledPath)",cpp)
        self.assertIn('setContextProperty("probeStyledOnline", styledOnline)',cpp)
        self.assertIn("COMPANY_PROBE_ONLINE_STYLE_PATH",cmake)
        self.assertIn("probeOnline ? root.nationwide : root.flint",qml)
        self.assertIn("© OpenStreetMap contributors",qml)
        for example in ("USA","PACIFIC","MIDWEST","NORTHEAST","RURAL",
                        "CANADA","MEXICO","ALASKA","HAWAII"):
            self.assertIn('label:"'+example+'"',qml)

    def test_user_widget_unmodified_by_experimental_style(self):
        shell=(ROOT/"shell.qml").read_text(encoding="utf-8")
        company=(ROOT/"widgets/CompanyCoveragePane.qml").read_text(encoding="utf-8")
        self.assertNotIn("style-post-apollo-online",shell)
        self.assertNotIn("style-post-apollo-online",company)
        self.assertNotIn("MapLibre 3.0",company)


if __name__=="__main__":
    unittest.main()
