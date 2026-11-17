"""P2.B source integration guard: no shadow broker or queue-publish bypass."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
boundary=(ROOT/"services/publisher/PublisherTransportBoundary.py").read_text()
adapters=(ROOT/"services/publisher/PublisherProviderAdapters.py").read_text()
queue=(ROOT/"services/publisher/PublisherQueueCli.py").read_text()
connection=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
access=(ROOT/"services/publisher/PublisherAccessIntentPolicy.js").read_text()
draft=(ROOT/"services/publisher/PublisherDraftStore.qml").read_text()
messaging=(ROOT/"services/messaging/ADAPTER-CONTRACT.md").read_text()


class P2BSourceContracts(unittest.TestCase):
    def test_existing_broker_and_queue_are_still_deny_only(self):
        self.assertIn("readonly property bool credentialActionsEnabled: false",connection)
        self.assertIn("TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED",access)
        self.assertIn("return {allowed:false",access)
        self.assertIn('"executor":"DISABLED"',queue.replace(" ",""))
        self.assertIn('"posted":0',queue.replace(" ",""))
        self.assertIn("def authorize(",boundary)
        self.assertIn("def deliver(",boundary)
        self.assertIn("return refuse(BROKER_REASON)",boundary)
        self.assertIn("canDispatch",boundary)
        self.assertIn("providerReceipt",boundary)
        self.assertIn("publisher-drafts-v1.json",draft)
        self.assertIn("Adapter Contract",messaging)

    def test_binding_does_not_create_credentials_or_auth_path(self):
        for forbidden in ("Qt.openUrlExternally","QNetworkAccessManager",
                          "import requests","import socket","import urllib",
                          "import subprocess","import http.client",
                          "os.environ","keyring","secretservice",
                          "ssh-agent","webhook_url",
                          "sendMessage(","dispatch("):
            self.assertNotIn(forbidden,boundary)
        self.assertIn("local_candidate(",boundary)
        self.assertIn("fixture_observe(",boundary)
        self.assertIn("retryAutomatically",boundary)
        self.assertIn("hostBrokerConnected",boundary)
        self.assertIn("UNTRUSTED_LOCAL_CANDIDATE",boundary)
        self.assertIn("PREVIEW_PROVIDER_OR_SCOPE_MISMATCH",boundary)
        self.assertIn("STALE_PREVIEW_FINGERPRINT",boundary)
        self.assertIn("FIXTURE_RETRY_OR_ORDER_REFUSED",boundary)
        self.assertIn("def dispatch(",adapters)
        self.assertIn("return deny(REASON_BLOCKED)",adapters)

    def test_rehearsal_is_not_network_or_live_posting(self):
        self.assertIn('phase": "OFFLINE_TEST_ONLY"',boundary)
        self.assertIn('"simulation": True',boundary)
        self.assertIn('"providerReceipt": None',boundary)
        self.assertIn('"realPosted": False',boundary)
        self.assertIn('"sent": False',boundary)
        self.assertIn('"canDispatch": False',boundary)


if __name__=="__main__":
    unittest.main()
