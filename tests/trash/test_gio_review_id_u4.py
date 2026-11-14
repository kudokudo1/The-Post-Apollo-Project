"""U4: GIO index emits opaque review metadata, never new restore authority."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT / "scripts/trash/trash_cli.py"
spec=importlib.util.spec_from_file_location("trashpp_gio_u4",PATH)
gio=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gio)


class GIOReviewIdU4Tests(unittest.TestCase):
    def setUp(self):
        self.uri="trash:///weather%20report%20copy%20one.txt"
        self.original="/home/user/Documents/weather report copy one.txt"
        self.row=self.uri+"\t"+self.original+"\n"

    def test_row_id_binds_exact_inventory_tuple_and_has_sha_form(self):
        listed=gio.parse_listing(self.row)
        self.assertEqual(len(listed),1)
        row=listed[0]
        self.assertEqual(len(row["reviewId"]),64)
        expected=hashlib.sha256(json.dumps(
            [self.uri,self.original],ensure_ascii=False,
            separators=(",",":")).encode("utf-8")).hexdigest()
        self.assertEqual(row["reviewId"],expected)
        self.assertEqual(row["uri"],self.uri)
        self.assertEqual(row["original"],self.original)

    def test_identity_changes_with_uri_or_original_but_not_listing_order(self):
        other="trash:///file2\t/home/user/file2\n"
        first=gio.parse_listing(self.row+other)
        second=gio.parse_listing(other+self.row)
        self.assertEqual({r["uri"]:r["reviewId"] for r in first},
                         {r["uri"]:r["reviewId"] for r in second})
        changed=gio.parse_listing(
            self.uri+"\t/home/user/Documents/other.txt\n")
        self.assertNotEqual(changed[0]["reviewId"],first[0]["reviewId"])
        moved=gio.parse_listing(
            "trash:///other%20name\t"+self.original+"\n")
        self.assertNotEqual(moved[0]["reviewId"],first[0]["reviewId"])

    def test_index_revision_still_has_same_existing_scope_and_no_action_change(self):
        rows=gio.parse_listing(self.row)
        old_formula=hashlib.sha256(json.dumps(
            [[self.uri,self.original]],ensure_ascii=False,
            separators=(",",":")).encode("utf-8")).hexdigest()
        self.assertEqual(gio._revision(rows),old_formula)
        with patch.object(gio,"_gio",return_value="/usr/bin/gio"), \
             patch.object(gio,"_run",
                          return_value=SimpleNamespace(
                              returncode=0,stdout=self.row,stderr="")) as run:
            result=gio.index()
        self.assertEqual(result["items"][0]["reviewId"],rows[0]["reviewId"])
        self.assertEqual(result["revision"],old_formula)
        self.assertEqual(run.call_args.args[0],
                         ["/usr/bin/gio","trash","--list"])

    def test_no_new_restore_verb_or_backend_authority(self):
        source=PATH.read_text(encoding="utf-8")
        self.assertIn('elif len(argv) == 4 and argv[1] == "restore":',source)
        self.assertNotIn('"restore-reviewed"',source)
        self.assertNotIn('reviewId", confirmation',source)
        self.assertNotIn("os.remove(",source)
        self.assertIn('_selected(rows, uri, original)',source)
        self.assertIn('os.path.lexists(row["original"])',source)


if __name__=="__main__":
    unittest.main()
