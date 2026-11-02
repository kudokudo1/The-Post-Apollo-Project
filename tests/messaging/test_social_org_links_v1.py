"""Synthetic local organization/branch to Social identity/account nickname links."""
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
import SocialOrganizationDirectory as orgdir  # noqa: E402
import SocialOrganizationLinks as links  # noqa: E402

SECTIONS = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
EDITOR = (ROOT / "widgets/messanger/IdentityCenterLocalSocialLinksEditor.qml").read_text()
STORE = (ROOT / "services/social/SocialOrganizationLinksStore.qml").read_text()
QMLDIR = (ROOT / "services/social/qmldir").read_text()


def apply(doc, action, **kwargs):
    return links.apply(doc, {"action":action, "expectedRevision":doc["revision"],
                             **kwargs})


def identity(org_id, branch_id=None, identity_id="identity-1"):
    return {"orgId":org_id, "branchId":branch_id, "identityId":identity_id,
            "serviceId":None, "accountId":None}


class ManualAssociationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="social-links-tests-")
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"XDG_DATA_HOME":self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        doc = orgdir.initial()
        doc = orgdir.apply(doc, {"action":"add_org", "expectedRevision":0,
                                "name":"SYNTHETIC LLC", "kind":"llc"})
        doc = orgdir.apply(doc, {"action":"add_branch", "expectedRevision":1,
                                "orgId":"org-1", "name":"SYNTHETIC BRANCH"})
        doc = orgdir.apply(doc, {"action":"add_org", "expectedRevision":2,
                                "name":"SYNTHETIC NONPROFIT", "kind":"nonprofit"})
        orgdir.save(doc)
        self.service = sorted(links.ITEM_BY_ID)[0]

    def test_missing_file_read_is_non_mutating(self):
        self.assertEqual(links.load(), links.initial())
        self.assertFalse(links.storage_path().exists())

    def test_org_branch_and_account_nickname_link_and_unlink(self):
        doc = apply(links.initial(), "add_link", **identity("org-1"))
        doc = apply(doc, "add_link", **identity("org-1", "branch-2"))
        doc = apply(doc, "add_link", orgId="org-3", branchId=None,
                    identityId="identity-2", serviceId=self.service,
                    accountId="account-1")
        self.assertEqual(doc["revision"], 3)
        self.assertEqual(doc["nextId"], 4)
        self.assertEqual([r["id"] for r in doc["links"]],
                         ["link-1", "link-2", "link-3"])
        links.save(doc)
        self.assertEqual(links.load(), doc)
        self.assertEqual(links.storage_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(links.root_path().stat().st_mode & 0o777, 0o700)
        self.assertNotIn("scopeGrants", links.storage_path().read_text())
        self.assertNotIn("accessToken", links.storage_path().read_text())
        doc = apply(doc, "remove_link", linkId="link-2")
        self.assertEqual(doc["revision"], 4)
        self.assertEqual(len(doc["links"]), 2)

    def test_duplicate_invalid_id_service_and_revision_refused(self):
        doc = apply(links.initial(), "add_link", **identity("org-1"))
        with self.assertRaisesRegex(links.LinkError, "DUPLICATE_LINK"):
            apply(doc, "add_link", **identity("org-1"))
        with self.assertRaisesRegex(links.LinkError, "INVALID_ID"):
            apply(doc, "add_link", **identity("org-1", "identity-1"))
        with self.assertRaisesRegex(links.LinkError, "INVALID_SERVICE"):
            apply(doc, "add_link", orgId="org-1", branchId=None,
                  identityId="identity-1", serviceId="fake-app",
                  accountId="account-1")
        with self.assertRaisesRegex(links.LinkError, "INVALID_REQUEST"):
            apply(doc, "add_link", orgId="org-1", branchId=None,
                  identityId="identity-1", serviceId=self.service, accountId=None)
        with self.assertRaisesRegex(links.LinkError, "INVALID_REQUEST"):
            links.apply(doc, {"action":"remove_link", "expectedRevision":1,
                              "linkId":"link-1", "permission":"records.write"})
        with self.assertRaisesRegex(links.LinkError, "REVISION_CONFLICT"):
            links.apply(doc, {"action":"remove_link", "expectedRevision":0,
                              "linkId":"link-1"})

    def test_archived_missing_and_cross_org_target_refused(self):
        with self.assertRaisesRegex(links.LinkError, "ORGANIZATION_UNAVAILABLE"):
            apply(links.initial(), "add_link", **identity("org-99"))
        with self.assertRaisesRegex(links.LinkError, "BRANCH_UNAVAILABLE"):
            apply(links.initial(), "add_link", **identity("org-3", "branch-2"))
        base = orgdir.load()
        orgdir.save(orgdir.apply(base, {"action":"archive_branch",
                                       "expectedRevision":base["revision"],
                                       "orgId":"org-1", "branchId":"branch-2"}))
        with self.assertRaisesRegex(links.LinkError, "BRANCH_UNAVAILABLE"):
            apply(links.initial(), "add_link", **identity("org-1", "branch-2"))
        base = orgdir.load()
        orgdir.save(orgdir.apply(base, {"action":"archive_org",
                                       "expectedRevision":base["revision"],
                                       "orgId":"org-3"}))
        with self.assertRaisesRegex(links.LinkError, "ORGANIZATION_UNAVAILABLE"):
            apply(links.initial(), "add_link", **identity("org-3"))

    def test_archived_link_remains_readable_and_removable(self):
        doc = apply(links.initial(), "add_link", **identity("org-1"))
        links.save(doc)
        base = orgdir.load()
        orgdir.save(orgdir.apply(base, {"action":"archive_org",
                                       "expectedRevision":base["revision"],
                                       "orgId":"org-1"}))
        self.assertEqual(links.load(), doc)
        doc = apply(doc, "remove_link", linkId="link-1")
        links.save(doc)
        self.assertEqual(links.load()["links"], [])

    def test_bad_json_version_symlink_corrupt_file_fail_closed(self):
        with self.assertRaisesRegex(links.LinkError, "INVALID_JSON"):
            links.decode(b'{"revision":1,"revision":2}')
        with self.assertRaisesRegex(links.LinkError, "INVALID_JSON"):
            links.decode(b'{"value":NaN}')
        future = links.initial()
        future["schema"] = "post-apollo.social-local-associations.v99"
        with self.assertRaisesRegex(links.LinkError, "UNSUPPORTED_VERSION"):
            links.validate(future)
        path = links.storage_path()
        path.write_text("BAD JSON")
        path.chmod(0o600)
        with self.assertRaisesRegex(links.LinkError, "INVALID_JSON"):
            links.load()
        self.assertEqual(path.read_text(), "BAD JSON")
        path.chmod(0o644)
        with self.assertRaises(Exception):
            links.load()
        path.unlink()
        path.symlink_to(links.root_path() / "target")
        with self.assertRaises(Exception):
            links.load()

    def test_cli_fixed_stdin_update_and_revision_conflict(self):
        cli = ROOT / "services/social/SocialOrganizationLinks.py"
        env = dict(os.environ)
        req = {"action":"add_link", "expectedRevision":0, **identity("org-1")}
        first = subprocess.run([sys.executable, str(cli), "update"],
                               input=json.dumps(req) + "\n", text=True,
                               capture_output=True, env=env, check=False)
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertTrue(json.loads(first.stdout)["ok"])
        second = subprocess.run([sys.executable, str(cli), "update"],
                                input=json.dumps(req) + "\n", text=True,
                                capture_output=True, env=env, check=False)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["error"], "REVISION_CONFLICT")
        self.assertNotIn("identity-1", second.stdout)
        read = subprocess.run([sys.executable, str(cli), "read"],
                              capture_output=True, text=True, env=env, check=False)
        self.assertEqual(read.returncode, 0)
        self.assertEqual(len(json.loads(read.stdout)["document"]["links"]), 1)


class LocalLinkUIContracts(unittest.TestCase):
    def test_existing_user_settings_injection_and_disabled_switcher(self):
        self.assertIn("IdentityCenterLocalOrganizationEditor {", SECTIONS)
        self.assertIn("IdentityCenterLocalSocialLinksEditor {", SECTIONS)
        self.assertIn("localLinksStore: SocialOrganizationLinksStore", SELECTOR)
        self.assertIn("socialIdentitiesSnapshot: appSelector.identitySnapshot", SELECTOR)
        self.assertIn("socialAccountDetailsStore: SocialAccountDetailsStore", SELECTOR)
        self.assertIn("singleton SocialOrganizationLinksStore 1.0", QMLDIR)
        self.assertNotIn("FloatingWindow {", EDITOR)
        self.assertNotIn("PanelWindow {", EDITOR)
        self.assertNotIn("Process {", EDITOR)
        self.assertNotIn("FileView {", EDITOR)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', SECTIONS)
        self.assertIn("interactive: false", SECTIONS.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:200])

    def test_link_actions_are_labels_not_provider_login(self):
        for symbol in ("linkIdentity", "linkAccountLabel", "unlink",
                       "accountNamesFor", "identitiesSnapshot",
                       "ORGANIZATION LEVEL", "CONFIRM UNLINK",
                       "STALE OR UNAVAILABLE"):
            self.assertIn(symbol, EDITOR)
        self.assertIn('stdinEnabled: true', STORE)
        self.assertIn('state !== "ready"', STORE)
        for forbidden in ("accessToken", "refreshToken", "scopeGrants",
                          "canSwitchOrganization: true", "Qt.openUrlExternally"):
            self.assertNotIn(forbidden, STORE)
            self.assertNotIn(forbidden, EDITOR)


if __name__ == "__main__":
    unittest.main()
