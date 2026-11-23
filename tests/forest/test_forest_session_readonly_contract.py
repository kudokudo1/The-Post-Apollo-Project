"""ForestW read-only B1 session projection. No native host or inference."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestSessionReadonlyContract(unittest.TestCase):
    def test_ui_preserves_locked_chat_and_real_inventory_signal(self):
        window = (ROOT / "widgets/ForestW.qml").read_text()
        rail = (ROOT / "widgets/ForestChatList.qml").read_text()
        self.assertIn("readonly property bool chatHostTrusted: false", window)
        self.assertIn("readonly property var activeChatSessions: []", window)
        self.assertIn("sessions: root.activeChatSessions", window)
        self.assertIn("treeKey: root.activeTree.sessionKey", window)
        self.assertIn('sessionKey: "BRISTLECONE_PINE"', window)
        self.assertIn("inventoryStatus: localInventory.status", window)
        self.assertIn("selectedModel: root.selectedLocalModel", window)
        self.assertIn("discoveredModels: localInventory.modelCount", window)
        self.assertIn("SessionPolicy.openSessions(sessions, treeKey)", rail)
        self.assertIn("chatListRoot.hostConnected ? chatListRoot.visibleSessions : []", rail)
        self.assertIn("modelData.title", rail)
        self.assertNotIn("modelData.lastMessage", rail)
        self.assertIn("textFormat: Text.PlainText", rail)
        self.assertIn("CHAT HOST OFFLINE", rail)
        self.assertIn("OLLAMA // ", rail)
        for prohibited in ("Process {", "MouseArea {", "onClicked:"):
            self.assertNotIn(prohibited, rail)
        self.assertNotIn("onPrimaryRequested:", window)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_policy_filters_open_sessions_and_refuses_bad_snapshots(self):
        js = textwrap.dedent(r"""
            const fs = require('fs');
            const vm = require('vm');
            const assert = require('assert');
            const ctx = vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
            const open = ctx.openSessions;
            const row = (id, tree, state='OPEN', when=200) => ({
              session_id:id, tree_key:tree, title:'Session '+id, state,
              revision:2, created_at_ms:100, updated_at_ms:when
            });
            const feed = [row('s_1','CHERRY'), row('s_2','MAPLE'),
                          row('s_3','CHERRY','PAUSED'),
                          row('s_4','CHERRY','OPEN',300)];
            let found = open(feed, 'CHERRY');
            assert.strictEqual(found.length, 2);
            assert.strictEqual(found[0].session_id, 's_4');
            assert.strictEqual(found[1].title, 'Session s_1');
            assert.strictEqual(Object.keys(found[0]).includes('tree_key'), false);
            assert.strictEqual(open(feed,'MAPLE').length, 1);
            assert.strictEqual(open(feed,'CEDAR').length, 0);
            assert.strictEqual(open(feed,'').length, 0);
            assert.strictEqual(open([row('s_1','CHERRY'), row('s_1','MAPLE')], 'CHERRY').length, 0);
            assert.strictEqual(open([row('s_1','CHERRY'), {...row('s_2','MAPLE'), body:'SECRET'}], 'CHERRY').length, 0);
            assert.strictEqual(open([{...row('s_1','CHERRY'), state:'ACTIVE'}], 'CHERRY').length, 0);
            assert.strictEqual(open([{...row('s_1','CHERRY'), updated_at_ms:Infinity}], 'CHERRY').length, 0);
            assert.strictEqual(open([{...row('s_1','CHERRY'), title:'bad\nname'}], 'CHERRY').length, 0);
            assert.strictEqual(open('untrusted','CHERRY').length, 0);
            assert.strictEqual(open(Array(101).fill(row('s_1','CHERRY')),'CHERRY').length, 0);
        """)
        source = ROOT / "widgets/ForestChatSessionPolicy.js"
        result = subprocess.run(
            ["node", "-e", js, str(source)], text=True, capture_output=True,
            check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
