"""P1.4 integration guard: ledger is local and incapable of posting."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
host = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
selector = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
pane = (ROOT / "widgets/publisher/PublisherPane.qml").read_text()
queue_ui = (ROOT / "widgets/publisher/PublisherQueuePane.qml").read_text()
engine = (ROOT / "services/publisher/PublisherQueueCli.py").read_text()
draft_store = (ROOT / "services/publisher/PublisherDraftStore.qml").read_text()
template_store = (ROOT / "services/publisher/PublisherTemplateStore.qml").read_text()


class QueueP14Contracts(unittest.TestCase):
    def test_existing_social_host_and_other_stores_unchanged(self):
        self.assertEqual(host.count("FloatingWindow {"), 1)
        self.assertIn('id: publisherFooter', selector)
        self.assertIn('PublisherQueuePane {', pane)
        self.assertIn('id: publisherQueuePane', pane)
        self.assertIn('calendarMode: publisher.activeSection === "calendar"', pane)
        self.assertIn('|| publisher.activeSection === "queue"', pane)
        self.assertIn('visible: publisher.activeSection === "history"', pane)
        self.assertIn("publisher-drafts-v1.json", draft_store)
        self.assertIn("publisher-templates-v1.json", template_store)
        self.assertNotIn("PublisherQueueCli", template_store + draft_store)

    def test_no_network_or_dispatch_or_autostart(self):
        for forbidden in ("requests", "urllib", "http.client", "socket",
                          "subprocess", "asyncio.create_subprocess_exec",
                          "Qt.openUrlExternally", "provider_token",
                          "autopublish", "sendMessage("):
            self.assertNotIn(forbidden, engine)
        self.assertIn("NEEDS_REVIEW", engine)
        self.assertIn('"executor":"DISABLED"', engine.replace(" ", ""))
        self.assertIn('"posted":0', engine.replace(" ", ""))
        self.assertIn("NO PROVIDER DISPATCH", queue_ui)
        self.assertIn("MARK REVIEWED // NOT SENT", queue_ui)
        self.assertIn("SCHEDULER LOCAL // OUTBOUND PUBLISHING DISABLED", queue_ui)
        self.assertNotIn('action === "watch"', queue_ui)
        self.assertNotIn('issue("watch"', queue_ui)
        self.assertNotIn("Qt.openUrlExternally", queue_ui)
        self.assertNotIn("FloatingWindow {", queue_ui)

    def test_sqlite_and_date_guards(self):
        for required in ("PRAGMA journal_mode=WAL",
                         "PRAGMA synchronous=FULL",
                         "BEGIN IMMEDIATE", "UNIQUE", "SCHEDULE_MUST_BE_FUTURE",
                         "NONEXISTENT_LOCAL_TIME", "AMBIGUOUS_LOCAL_TIME",
                         "SOURCE_CHANGED_OR_UNAVAILABLE", "DUE_NO_DISPATCH",
                         "idempotent", "MAX_ACTIVE", "MAX_JOBS",
                         "watch", "rearm"):
            self.assertIn(required, engine)
        self.assertIn("publisher-queue-v1.sqlite3", queue_ui)
        self.assertIn("publisher-drafts-v1.json", queue_ui)
        self.assertIn("CHECK DUE // NO SEND", queue_ui)
        self.assertIn("CONFIRM CANCEL", queue_ui)
        self.assertIn("PublisherDraftStore.snapshot.drafts", queue_ui)
        self.assertIn("PublisherQueuePane {", pane)


if __name__ == "__main__":
    unittest.main()
