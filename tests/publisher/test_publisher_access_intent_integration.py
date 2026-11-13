"""P1.5 source-boundary tests: local requests do not become active grants."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
policy=(ROOT/"services/publisher/PublisherAccessIntentPolicy.js").read_text()
store=(ROOT/"services/publisher/PublisherAccessIntentStore.qml").read_text()
pane=(ROOT/"widgets/publisher/PublisherAccessPane.qml").read_text()
publisher=(ROOT/"widgets/publisher/PublisherPane.qml").read_text()
social=(ROOT/"widgets/messanger/MessagingW.qml").read_text()
social_identity=(ROOT/"services/social/SocialIdentityStore.qml").read_text()
broker=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
queue=(ROOT/"services/publisher/PublisherQueueCli.py").read_text()
qmldir=(ROOT/"services/publisher/qmldir").read_text()


class PublisherAccessContracts(unittest.TestCase):
    def test_no_new_window_or_social_worker_edit(self):
        self.assertEqual(social.count("FloatingWindow {"),1)
        self.assertIn('id:"access", label:"ACCESS"',publisher)
        self.assertIn("PublisherAccessPane {",publisher)
        self.assertIn('visible: publisher.activeSection === "access"',publisher)
        self.assertIn("SocialIdentityStore.snapshot",pane)
        self.assertIn('identitySnapshot.writable === true',pane)
        self.assertIn('currentIdentityId',pane)
        for forbidden in ("FloatingWindow {","PanelWindow {","PopupWindow {",
                          "Qt.openUrlExternally","sendMessage(","oauthRequest(","Process {"):
            self.assertNotIn(forbidden,pane)
        self.assertIn("single",social_identity.lower())
        self.assertIn("readonly property bool credentialActionsEnabled: false",broker)

    def test_local_requests_are_not_authorization(self):
        self.assertIn("TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED",policy)
        self.assertIn("return {allowed:false",policy)
        self.assertIn('hostConnected:false,canPublish:false,grants:[]',policy)
        self.assertIn("readonly property bool canPublish: false",store)
        self.assertIn("function publishPermission(request,receipt)",store)
        self.assertIn("Policy.evaluate(request,receipt)",store)
        self.assertIn("SAVING",store.upper())
        self.assertIn("onSaveFailed:",store)
        self.assertIn("atomicWrites: true",store)
        self.assertIn("watchChanges: false",store)
        self.assertIn('Quickshell.dataDir + "/publisher-access-intents-v1.json"',store)
        self.assertIn("singleton PublisherAccessIntentStore 1.0 PublisherAccessIntentStore.qml",qmldir)
        self.assertIn("NO AUTHORIZATION",pane)
        self.assertIn("CONFIRM WITHDRAW",pane)
        self.assertIn("ZERO PUBLISHING GRANTS",pane)
        for source in (store,policy):
            for banned in ("QNetworkAccessManager", "Process {", "Qt.openUrlExternally",
                           "requestToken(", "sendMessage(", "access_token",
                           "refresh_token", "secretKey", "password:"):
                self.assertNotIn(banned,source)

    def test_queue_not_connected_to_untrusted_access_intents(self):
        self.assertIn('"executor":"DISABLED"',queue.replace(" ",""))
        self.assertIn('"posted":0',queue.replace(" ",""))
        self.assertNotIn("PublisherAccessIntentStore",queue)
        self.assertNotIn("PublisherAccessIntentStore",social)
        self.assertNotIn("PublisherAccessIntentStore",social_identity)
        self.assertNotIn("PublisherAccessIntentStore",broker)


if __name__=="__main__":
    unittest.main()
