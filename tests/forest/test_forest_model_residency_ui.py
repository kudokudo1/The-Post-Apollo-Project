"""ForestW // One shared, read-only Ollama residency observation for header/popup."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestModelResidencyUITests(unittest.TestCase):
    def test_one_status_source_for_header_and_popup(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        adapter = (ROOT / "services/forest/ForestResidencyAdapter.qml").read_text()
        policy = (ROOT / "services/forest/ForestResidencyPolicy.js").read_text()
        self.assertEqual(view.count("ForestResidencyAdapter {"), 1)
        self.assertIn("id: modelResidency", view)
        self.assertIn("readonly property string selectedModelLoadState:", view)
        self.assertIn("modelResidency.status, modelResidency.models, selectedLocalModel", view)
        self.assertIn("modelResidency.status,", view)
        self.assertIn("modelResidency.models, modelEntry.modelName", view)
        self.assertIn('root.selectedModelLoadState === "LOADED" ? "LOAD"', view)
        self.assertIn('root.selectedModelLoadState === "NOT_LOADED" ? "IDLE" : "?"', view)
        self.assertIn('parent.observedState === "LOADED" ? "LOADED"', view)
        self.assertIn('parent.observedState === "NOT_LOADED" ? "IDLE"', view)
        self.assertIn("localInventory.scanModels()", view)
        self.assertIn("modelResidency.scanResidency()", view)
        self.assertIn("root.refreshLocalModelEvidence();", view)
        self.assertIn("onModelPopupOpenChanged:", view)
        self.assertIn("onReloadRequested:", view)
        self.assertIn("onClicked: root.scanModel(modelEntry.modelName)", view)
        self.assertIn("Quickshell.shellPath(\"scripts/forest/performance_snapshot_p0.py\")", adapter)
        self.assertIn('"snapshot"', adapter)
        self.assertEqual(adapter.count("Process {"), 1)
        self.assertIn('"NOT_CHECKED"', adapter)
        self.assertIn('model_load_requested !== false', policy)
        self.assertIn('generation_requested !== false', policy)
        # No implicit background refresh, external provider, generation or permission.
        for forbidden in ("repeat: true", "onTriggered: residency.scanResidency", "onCompleted: scanResidency", "/api/chat",
                          "ollama_chat_transport", "execDetached", "Hermes"):
            self.assertNotIn(forbidden, adapter)
        for protected in (
            "readonly property bool chatHostTrusted: false",
            "readonly property bool voiceHostTrusted: false",
            "readonly property var activeChatSessions: []",
        ):
            self.assertIn(protected, view)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_snapshot_validation_and_complete_process_barrier(self):
        javascript = textwrap.dedent(r"""
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");
            const ctx = vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
            const p = ctx;
            const observed = () => ({
                schema: "post-apollo.forest.performance-snapshot.readonly-p0",
                status: "OBSERVED", provider: "ollama", version: "0.32.14",
                resident_models: [
                    {model: "qwen3:1.7b", size_bytes_reported: 100,
                     vram_bytes_reported: 80, context_length_reported: 2048}
                ],
                resident_model_count: 1,
                measurement_scope: "LOCAL_PROVIDER_AND_HOST_HINTS_ONLY",
                inference_latency_measured: false,
                generation_requested: false, model_load_requested: false,
                production_authority: false
            });
            const raw = JSON.stringify(observed());
            const valid = p.parseSnapshot(raw);
            assert.strictEqual(valid.valid, true);
            assert.strictEqual(valid.status, "OBSERVED");
            assert.strictEqual(p.modelState(valid.status, valid.models, "qwen3:1.7b"),"LOADED");
            assert.strictEqual(p.modelState(valid.status, valid.models, "granite4:small-h"),"NOT_LOADED");
            assert.strictEqual(p.modelState("NOT_CHECKED",valid.models,"qwen3:1.7b"),"UNKNOWN");
            assert.strictEqual(p.modelState("UNAVAILABLE",valid.models,"qwen3:1.7b"),"UNKNOWN");
            assert.strictEqual(p.modelState("OBSERVED",valid.models,""),"UNKNOWN");
            for(const payload of [
                {...observed(),production_authority:true},
                {...observed(),model_load_requested:true},
                {...observed(),generation_requested:true},
                {...observed(),inference_latency_measured:true},
                {...observed(),provider:"other"},
                {...observed(),status:"UNAVAILABLE"},
                {...observed(),resident_model_count:0},
                {...observed(),resident_models:[observed().resident_models[0],observed().resident_models[0]]},
                {...observed(),resident_models:[{model:"../../bad"}]},
                {...observed(),schema:"not-forest"},
            ]) {
                assert.strictEqual(p.parseSnapshot(JSON.stringify(payload)).valid, false);
            }
            assert.strictEqual(p.parseSnapshot("{broken").valid,false);
            const refused = {...observed(),status:"UNAVAILABLE",reason:"OLLAMA_TIMEOUT",
                              resident_models:[],resident_model_count:0};
            assert.strictEqual(p.parseSnapshot(JSON.stringify(refused)).valid,true);
            const events = [
                s=>p.captureStdout(s,raw),
                s=>p.captureStderr(s,""),
                s=>p.captureExit(s,0,0)
            ];
            for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]) {
                let s=p.beginScan();
                for(let i=0;i<3;i++) {
                    s=events[order[i]](s);
                    if(i<2){
                        assert.strictEqual(s.complete,false);
                        assert.strictEqual(s.models.length,0);
                    }
                }
                assert.strictEqual(s.complete,true);
                assert.strictEqual(s.status,"OBSERVED");
                assert.strictEqual(s.models.length,1);
                assert.strictEqual(s.models[0],"qwen3:1.7b");
            }
            for(const failure of [
                [s=>p.captureStdout(s,raw),s=>p.captureStderr(s,"failure"),s=>p.captureExit(s,0,0)],
                [s=>p.captureStdout(s,raw),s=>p.captureStderr(s,""),s=>p.captureExit(s,0,1)],
                [s=>p.captureStdout(s,raw),s=>p.captureStderr(s,""),s=>p.captureExit(s,1,0)],
                [s=>p.captureStdout(s,"malformed"),s=>p.captureStderr(s,""),s=>p.captureExit(s,0,0)]
            ]) {
                let s=p.beginScan();
                for(const ev of failure)s=ev(s);
                assert.strictEqual(s.complete,true);
                assert.strictEqual(s.status,"UNAVAILABLE");
                assert.strictEqual(s.models.length,0);
            }
            let s=p.beginScan();
            s=p.captureStdout(s,raw);
            s=p.captureStdout(s,raw);
            s=p.captureStderr(s,"");
            s=p.captureExit(s,0,0);
            assert.strictEqual(s.status,"UNAVAILABLE");
            assert.strictEqual(s.models.length,0);
        """)
        source = ROOT / "services/forest/ForestResidencyPolicy.js"
        r = subprocess.run(["node", "-e", javascript, str(source)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
