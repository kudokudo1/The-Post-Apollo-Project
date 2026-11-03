"""Local portfolio grouping uses fictional names and never confers access rights."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "social"))
import SocialLocalPortfolios as p  # noqa: E402
import SocialOrganizationDirectory as orgs  # noqa: E402

SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
# The original editors now live in the consolidated local workspace.
SECTIONS += "\n" + (ROOT / "widgets/messanger/IdentityCenterLocalOrganizationsWorkspace.qml").read_text()
APP = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalPortfolioEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialLocalPortfoliosStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def do(doc, action, **fields):
    return p.apply(doc, {"action":action, "expectedRevision":doc["revision"],
                         **fields})


class SyntheticLocalPortfolioTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="social-local-portfolios-test-")
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME":tmp.name})
        env.start()
        self.addCleanup(env.stop)
        doc = orgs.initial()
        for name, kind in [("SYNTHETIC LLC A", "llc"),
                           ("SYNTHETIC LLC B", "llc"),
                           ("SYNTHETIC NONPROFIT", "nonprofit")]:
            doc = orgs.apply(doc, {"action":"add_org",
                                   "expectedRevision":doc["revision"],
                                   "name":name, "kind":kind})
        orgs.save(doc)

    def test_read_missing_file_is_empty_and_non_mutating(self):
        self.assertEqual(p.load(), p.initial())
        self.assertFalse(p.storage_path().exists())

    def test_create_rename_attach_detach_archive_restore_durable(self):
        doc = do(p.initial(), "create", name="SYNTHETIC FAMILY PORTFOLIO")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-2")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-3")
        doc = do(doc, "rename", portfolioId="portfolio-1",
                 name="SYNTHETIC MAIN GROUP")
        doc = do(doc, "detach", portfolioId="portfolio-1", orgId="org-2")
        doc = do(doc, "archive", portfolioId="portfolio-1")
        self.assertTrue(doc["portfolios"][0]["archived"])
        doc = do(doc, "restore", portfolioId="portfolio-1")
        self.assertFalse(doc["portfolios"][0]["archived"])
        self.assertEqual(doc["portfolios"][0]["orgIds"], ["org-1", "org-3"])
        self.assertEqual(doc["revision"], 8)
        self.assertEqual(doc["nextId"], 2)
        p.save(doc)
        self.assertEqual(p.load(), doc)
        self.assertEqual(p.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(p.root_path().stat().st_mode & 0o777, 0o700)
        encoded = p.storage_path().read_text()
        for forbidden in ("scopeGrants", "accessToken", "refreshToken",
                          "legalOwner", "principalId"):
            self.assertNotIn(forbidden, encoded)

    def test_many_to_many_without_copying_organization_data(self):
        doc = do(p.initial(), "create", name="Business group")
        doc = do(doc, "create", name="Personal group")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        doc = do(doc, "attach", portfolioId="portfolio-2", orgId="org-1")
        self.assertEqual(doc["portfolios"][0]["orgIds"], ["org-1"])
        self.assertEqual(doc["portfolios"][1]["orgIds"], ["org-1"])
        self.assertEqual(set(doc["portfolios"][0]), {"id","name","archived","orgIds"})

    def test_duplicated_name_member_revision_and_unknown_fields_refused(self):
        doc = do(p.initial(), "create", name="Example")
        with self.assertRaisesRegex(p.PortfolioError, "DUPLICATE_NAME"):
            do(doc, "create", name="example")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        with self.assertRaisesRegex(p.PortfolioError, "ALREADY_ATTACHED"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_REQUEST"):
            p.apply(doc, {"action":"attach", "expectedRevision":doc["revision"],
                          "portfolioId":"portfolio-1", "orgId":"org-2",
                          "permission":"records.read"})
        with self.assertRaisesRegex(p.PortfolioError, "REVISION_CONFLICT"):
            p.apply(doc, {"action":"detach", "expectedRevision":0,
                          "portfolioId":"portfolio-1", "orgId":"org-1"})
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_ID"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="tenant-3")
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_NAME"):
            do(doc, "rename", portfolioId="portfolio-1", name="Bad\nName")

    def test_invalid_stale_and_archived_orgs_not_attachable(self):
        doc = do(p.initial(), "create", name="Example")
        with self.assertRaisesRegex(p.PortfolioError, "ORGANIZATION_UNAVAILABLE"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="org-99")
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_ID"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="branch-1")
        doc = do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        base = orgs.load()
        orgs.save(orgs.apply(base, {"action":"archive_org",
                                   "expectedRevision":base["revision"],
                                   "orgId":"org-1"}))
        with self.assertRaisesRegex(p.PortfolioError, "ORGANIZATION_UNAVAILABLE"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="org-1")
        # An old reference is retained for display and can still be removed.
        p.save(doc)
        self.assertEqual(p.load()["portfolios"][0]["orgIds"], ["org-1"])
        doc = do(doc, "detach", portfolioId="portfolio-1", orgId="org-1")
        self.assertEqual(doc["portfolios"][0]["orgIds"], [])

    def test_archived_group_rejects_edits_and_restore_name_collision(self):
        doc = do(p.initial(), "create", name="Business")
        doc = do(doc, "archive", portfolioId="portfolio-1")
        with self.assertRaisesRegex(p.PortfolioError, "PORTFOLIO_ARCHIVED"):
            do(doc, "attach", portfolioId="portfolio-1", orgId="org-2")
        doc = do(doc, "create", name="business")
        with self.assertRaisesRegex(p.PortfolioError, "DUPLICATE_NAME"):
            do(doc, "restore", portfolioId="portfolio-1")
        with self.assertRaisesRegex(p.PortfolioError, "NO_CHANGE"):
            do(doc, "archive", portfolioId="portfolio-1")

    def test_invalid_document_corruption_symlink_and_future_schema(self):
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_JSON"):
            p.decode(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_JSON"):
            p.decode(b'{"x":NaN}')
        future = p.initial()
        future["schema"] = "post-apollo.social-local-portfolios.v999"
        with self.assertRaisesRegex(p.PortfolioError, "UNSUPPORTED_VERSION"):
            p.validate(future)
        wrong = p.initial()
        wrong["portfolios"] = [{"id":"portfolio-1","name":"Example",
                               "archived":False,"orgIds":["org-1"]}]
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_DOCUMENT"):
            p.validate(wrong)
        path = p.storage_path()
        path.write_text("CORRUPT")
        path.chmod(0o600)
        with self.assertRaisesRegex(p.PortfolioError, "INVALID_JSON"):
            p.load()
        self.assertEqual(path.read_text(), "CORRUPT")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            p.load()
        path.unlink()
        path.symlink_to(p.root_path() / "not-the-directory")
        with self.assertRaises(Exception):
            p.load()

    def test_cli_read_update_revision_conflict_is_private(self):
        cli = ROOT / "services/social/SocialLocalPortfolios.py"
        req = {"action":"create", "expectedRevision":0, "name":"Synthetic Group"}
        first = subprocess.run([sys.executable, str(cli), "update"],
                               capture_output=True, input=json.dumps(req) + "\n",
                               text=True, env=dict(os.environ), check=False)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertTrue(json.loads(first.stdout)["ok"])
        second = subprocess.run([sys.executable, str(cli), "update"],
                                capture_output=True, input=json.dumps(req) + "\n",
                                text=True, env=dict(os.environ), check=False)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("Synthetic Group", second.stdout)
        reader = subprocess.run([sys.executable, str(cli), "read"],
                                capture_output=True, text=True,
                                env=dict(os.environ), check=False)
        self.assertEqual(reader.returncode, 0)
        self.assertEqual(len(json.loads(reader.stdout)["document"]["portfolios"]), 1)


class UIContractTests(unittest.TestCase):
    def test_existing_organizations_page_and_frozen_switcher(self):
        self.assertIn("IdentityCenterLocalOrganizationEditor {", SECTIONS)
        self.assertIn("IdentityCenterLocalPortfolioEditor {", SECTIONS)
        self.assertIn("IdentityCenterLocalSocialLinksEditor {", SECTIONS)
        self.assertIn("localPortfoliosStore: SocialLocalPortfoliosStore", APP)
        self.assertIn("singleton SocialLocalPortfoliosStore 1.0", QMLDIR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        self.assertIn("interactive: false", SECTIONS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])
        for illegal in ("PanelWindow {", "FloatingWindow {", "Process {",
                        "FileView {", "SocialOrganizationLinksStore"):
            self.assertNotIn(illegal, EDITOR)

    def test_portfolio_ui_creates_only_labels(self):
        for marker in ("MY PORTFOLIOS // LOCAL GROUPS", "+ PORTFOLIO",
                       "REMOVE FROM GROUP", "CONFIRM REMOVE",
                       "SHOW ARCHIVED", "CONFIRM ARCHIVE", "RESTORE",
                       "attachOrganization", "detachOrganization"):
            self.assertIn(marker, EDITOR)
        for forbidden in ("scopeGrants", "accessToken", "roleGrants",
                          "canSwitchOrganization: true", "AccountBroker"):
            self.assertNotIn(forbidden, EDITOR)
            self.assertNotIn(forbidden, STORE)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)


if __name__ == "__main__":
    unittest.main()
