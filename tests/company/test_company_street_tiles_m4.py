"""M4 street tile provider safety contract. All HTTP calls are faked."""
from __future__ import annotations
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "services/company/CompanyStreetTiles.py"
spec = importlib.util.spec_from_file_location("company_street_tiles", SOURCE)
tile = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(tile)


class StreetTileSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"XDG_CACHE_HOME":self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def request(self, **overrides):
        data={"enable":True,"lon":-76.61,"lat":39.29,
              "zoom":11,"width":800,"height":500}
        data.update(overrides)
        return data

    def test_opt_in_and_only_view_coordinates_accepted(self):
        tile.validate_request(self.request())
        for bad in (self.request(enable=False),
                    self.request(clientName="private"),
                    self.request(organizationLabel="company"),
                    self.request(zoom=19),
                    self.request(width=99999),
                    self.request(lat=100),
                    self.request(lon=float("nan"))):
            with self.subTest(bad=bad),self.assertRaises(tile.TileError):
                tile.validate_request(bad)

    def test_only_visible_viewport_tiles_are_selected(self):
        lng,lat,z,w,h=tile.validate_request(self.request())
        tiles=tile.visible_tiles(lng,lat,z,w,h)
        self.assertTrue(tiles)
        self.assertLessEqual(len(tiles),tile.MAX_TILES)
        cx,cy=tile.world(lng,lat,z)
        for zz,x,y in tiles:
            self.assertEqual(zz,z)
            self.assertLess(x*256,cx+w/2)
            self.assertGreater((x+1)*256,cx-w/2)
            self.assertLess(y*256,cy+h/2)
            self.assertGreater((y+1)*256,cy-h/2)

    def test_owner_private_cache_and_no_implicit_directory_on_error(self):
        with self.assertRaises(tile.TileError):
            tile.validate_request(self.request(enable=False))
        self.assertEqual(os.listdir(self.tmp.name),[])
        root=tile.safe_cache_root(create=True)
        self.assertEqual(root.stat().st_mode & 0o777,0o700)
        self.assertEqual(root.parent,Path(self.tmp.name))

    def test_cache_is_reused_without_http(self):
        root=tile.safe_cache_root(create=True)
        path,meta=tile.tile_paths(root,11,602,781)
        tile.atomic_bytes(path,tile.PNG_SIGNATURE+b"FAKE")
        tile.atomic_bytes(meta,json.dumps({"expires":time.time()+86400}).encode())
        with patch.object(tile,"urlopen",side_effect=AssertionError("HTTP forbidden")):
            result=tile.fetch_one(root,(11,602,781))
        self.assertEqual(result["path"],str(path))
        self.assertTrue(tile.cached(path,meta))

    def test_cache_symlink_and_world_writable_file_refused(self):
        root=tile.safe_cache_root(create=True)
        outside=Path(self.tmp.name)/"outside"
        outside.write_bytes(b"private")
        a,_=tile.tile_paths(root,11,602,781)
        a.symlink_to(outside)
        with self.assertRaises(tile.TileError):
            tile.require_file(a)
        a.unlink()
        tile.atomic_bytes(a,b"fake")
        a.chmod(0o644)
        with self.assertRaises(tile.TileError):
            tile.require_file(a)

    def test_valid_tile_cache_headers_and_user_agent(self):
        self.assertIn("Post-Apollo-CompanyNetwork",tile.USER_AGENT)
        self.assertEqual(tile.BASE,"https://tile.openstreetmap.org")
        self.assertEqual(tile.DEFAULT_TTL,7*86400)
        self.assertLessEqual(tile.MAX_NETWORK,32)
        class FakeResponse:
            headers = {"Content-Type":"image/png",
                       "Cache-Control":"max-age=600",
                       "ETag":"fixture"}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return tile.PNG_SIGNATURE+b"DATA"
        root=tile.safe_cache_root(create=True)
        calls=[]
        def fake_http(req,timeout=None):
            calls.append(req)
            return FakeResponse()
        with patch.object(tile,"urlopen",side_effect=fake_http):
            result=tile.fetch_one(root,(11,602,781))
        self.assertTrue(result)
        self.assertEqual(len(calls),1)
        self.assertTrue(calls[0].full_url.startswith(tile.BASE+"/"))
        self.assertIn("Post-Apollo-CompanyNetwork",calls[0].get_header("User-agent"))
        p,m=tile.tile_paths(root,11,602,781)
        self.assertEqual(p.stat().st_mode & 0o777,0o600)
        self.assertTrue(tile.cached(p,m))
        self.assertEqual(json.loads(m.read_text())["etag"],"fixture")


if __name__=="__main__":
    unittest.main()
