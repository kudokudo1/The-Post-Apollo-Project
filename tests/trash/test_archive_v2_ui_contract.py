"""Source-level boundaries for the separate, read-only V2 Archive list."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
INDEX = (ROOT / "scripts/trash/archive_v2_index.py").read_text(encoding="utf-8")


class V2ArchiveUiContractTests(unittest.TestCase):
    def test_archive_navigation_preserves_existing_filters_and_legacy_actions(self):
        for marker in ('id: archiveFilterRow', '{id:"hub", label:"HUB"}',
                       '{id:"copies", label:"COPIES"}',
                       '{id:"bin", label:"BIN"}',
                       'function saveWeatherEventCopy(row)',
                       'function saveDemoCopy(row)',
                       'id: archiveEntriesList'):
            self.assertIn(marker, QML)
        self.assertIn('archiveRows.concat(researchRows)', QML)
        self.assertIn('.concat(archiveV2QueryDirty ? [] : archiveV2Rows)', QML)

    def test_v2_is_page_scoped_and_explicitly_read_only(self):
        for marker in ('property var archiveV2Rows: []',
                       'function refreshArchiveV2(targetPage, cursor, query)',
                       'function pageArchiveV2(direction)',
                       'function consumeArchiveV2(raw)',
                       'id: archiveV2Process',
                       'Quickshell.shellPath("scripts/trash/archive_v2_index.py")',
                       'onStreamFinished: trashLauncher.consumeArchiveV2(this.text)',
                       'id: archiveV2PageRail', 'label: "V2 PREV"',
                       'label: "V2 NEXT"', 'MATCHES ACROSS ALL V2',
                       'item.copyOnly !== true',
                       'item.capabilities.burn !== false',
                       'item.capabilities.restore !== false',
                       'item.capabilities.trash !== false',
                       'function pageArchiveV2(direction)',
                       'archiveV2AppliedQuery',
                       'archiveV2PendingQuery',
                       'archiveV2QueryDirty'):
            self.assertIn(marker, QML)
        self.assertIn('row.kind === "V2 SNAPSHOT"', QML)
        self.assertIn('label: "FIND V2"', QML)
        self.assertIn('V2 SEARCH NOT APPLIED // PRESS FIND V2', QML)
        self.assertIn('reply.query !== archiveV2PendingQuery', QML)
        self.assertIn('String(row.ownerId || "")', QML)
        self.assertIn('String(row.resourceId || "")', QML)
        self.assertIn('onAccepted: trashLauncher.refreshArchiveV2(', QML)
        self.assertIn('!trashLauncher.archiveV2QueryDirty', QML)
        self.assertIn('selected !== "all" && selected !== "copies"', QML)
        # The copy display is only a filtered model. Existing destructive
        # handlers receive the distinct legacy kind and state contracts.
        self.assertNotIn('modelData.kind === "V2 SNAPSHOT"\n                                                     ||', QML)
        self.assertNotIn('trashLauncher.armResearchBurn(trashLauncher.archiveV2Rows', QML)

    def test_reader_is_separate_from_source_writers(self):
        self.assertIn('mode=ro&cache=private', INDEX)
        self.assertIn('PRAGMA query_only=ON', INDEX)
        self.assertIn('READ_ONLY_INDEX_ONLY', INDEX)
        self.assertIn('PAGE_SIZE = 25', INDEX)
        self.assertIn('MAX_QUERY_LENGTH = 80', INDEX)
        self.assertIn('instr(lower(display_label), ?)', INDEX)
        self.assertIn('db.execute("BEGIN")', INDEX)
        self.assertIn('NOT_INSTALLED', INDEX)
        self.assertNotIn('def save(', INDEX)
        self.assertNotIn('def burn(', INDEX)
        self.assertNotIn('from scripts.trash', INDEX)
        # A missing database must not be instantiated as a side effect of
        # opening the Archive UI.
        self.assertNotIn('CREATE TABLE', INDEX)
        self.assertNotIn('os.O_CREAT', INDEX)


if __name__ == "__main__":
    unittest.main()
