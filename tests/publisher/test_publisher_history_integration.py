"""P1.6 static boundaries: local receipts and explicit recovery, no publication."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
engine=(ROOT/"services/publisher/PublisherQueueCli.py").read_text()
ui=(ROOT/"widgets/publisher/PublisherHistoryPane.qml").read_text()
publisher=(ROOT/"widgets/publisher/PublisherPane.qml").read_text()
social=(ROOT/"widgets/messanger/MessagingW.qml").read_text()
access=(ROOT/"services/publisher/PublisherAccessIntentPolicy.js").read_text()
media=(ROOT/"services/publisher/PublisherMediaStore.qml").read_text()
draft=(ROOT/"services/publisher/PublisherDraftStore.qml").read_text()


class P16HistoryContracts(unittest.TestCase):
    def test_local_event_ledger_is_atomic_with_state_transitions(self):
        for required in ("CREATE TABLE IF NOT EXISTS queue_events",
                         "BEGIN IMMEDIATE", "PRAGMA user_version=2",
                         "LEGACY_BASELINE_UNVERIFIED", "append_event(",
                         "history_problems(", "HISTORY_DIVERGENCE",
                         "QUEUE_INTEGRITY_FAILED", "PRAGMA integrity_check",
                         "def audit(", "def reconcile(", "def history(",
                         "repairPerformed", "sourceProblems", "providerReceipt"):
            self.assertIn(required, engine)
        self.assertIn('"canPublish":False', engine)
        self.assertIn('"posted":0', engine)
        self.assertNotIn("webhook", engine.lower())
        for forbidden in ("QNetworkAccessManager", "requests", "urllib", "socket",
                          "http.client", "sendMessage(", "token_cache",
                          "access_token", "refresh_token", "remote_post("):
            self.assertNotIn(forbidden, engine)

    def test_history_ui_is_not_provider_history(self):
        self.assertIn('id: publisherHistoryPane', publisher)
        self.assertIn('visible: publisher.activeSection === "history"', publisher)
        self.assertIn("PublisherHistoryPane {", publisher)
        self.assertNotIn("P1 FUTURE STEP // NOT ENABLED.", publisher)
        self.assertIn("LOCAL QUEUE HISTORY // NO EXTERNAL POSTS", ui)
        self.assertIn("NO SOCIAL POSTS, PROVIDER CONFIRMATIONS", ui)
        self.assertIn("AUDIT STORAGE & SOURCES", ui)
        self.assertIn("CONFIRM BLOCK STALE JOBS", ui)
        self.assertIn("reconcileArmed", ui)
        self.assertIn('historyPane.command("audit")', ui)
        self.assertIn("result.ledgerConsistent", ui)
        self.assertIn('result.canPublish !== false', ui)
        self.assertIn("result.posted !== 0", ui)
        self.assertNotIn("FloatingWindow {", ui)
        self.assertNotIn("Qt.openUrlExternally", ui)
        # The existing host has provider processes; don't change the host.
        self.assertIn("FloatingWindow {", social)

    def test_prior_writers_and_publish_grant_stay_separate(self):
        self.assertIn("publisher-drafts-v1.json", draft)
        self.assertIn("publisher-media-v1.json", media)
        self.assertIn("TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED", access)
        self.assertIn("return {allowed:false", access)
        self.assertNotIn("PublisherHistoryPane", access)
        self.assertNotIn("PublisherQueueCli", access)


if __name__ == "__main__":
    unittest.main()
