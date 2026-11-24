"""ForestW P0 selected-model read-only profile and compact popup tests."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestSelectedProfileTests(unittest.TestCase):
    def test_ui_reuses_existing_p0_and_hides_compact_profile(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        adapter = (ROOT / "services/forest/ForestResidencyAdapter.qml").read_text()
        self.assertEqual(view.count("ForestResidencyAdapter {"), 1)
        self.assertIn("readonly property var selectedModelProfile:", view)
        self.assertIn("modelResidency.status, modelResidency.records, selectedLocalModel", view)
        self.assertIn("id: selectedModelProfilePanel", view)
        self.assertIn("height: modelPopup.height >= 340 ? 48 : 0", view)
        self.assertIn("anchors.top: selectedModelProfilePanel.bottom", view)
        self.assertIn("root.selectedModelProfile.sizeMiB", view)
        self.assertIn("root.selectedModelProfile.vramMiB", view)
        self.assertIn("root.selectedModelProfile.context", view)
        self.assertIn("not verified GPU execution or permission", view)
        self.assertIn("property var records: []", adapter)
        self.assertIn("records = next.records", adapter)
        self.assertEqual(adapter.count("Process {"), 1)
        self.assertIn("Timer {", adapter)
        self.assertIn("repeat: false", adapter)
        self.assertNotIn("repeat: true", adapter)
        self.assertNotIn("onTriggered: residency.scanResidency", adapter)
        self.assertNotIn("ollama_chat_transport", adapter)
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertIn("readonly property bool voiceHostTrusted: false", view)
        # Every stage must retain room for its clipped model list + header/footer.
        for popup_height in (120, 180, 190, 240, 270, 340, 360):
            profile = 48 if popup_height >= 340 else 0
            equipment = 62 if popup_height >= 190 else 24
            remaining = popup_height - 33 - 19 - 17 - equipment - profile - 10
            self.assertGreaterEqual(remaining, 140 if profile else 15)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_selected_profile_keeps_unknown_and_refuses_bad_numbers(self):
        js = textwrap.dedent(r"""
            const fs=require("fs"),vm=require("vm"),assert=require("assert");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx;
            const sample=()=>({
                schema:"post-apollo.forest.performance-snapshot.readonly-p0",
                status:"OBSERVED",provider:"ollama",version:"0.32.14",
                resident_models:[{model:"qwen3:1.7b",size_bytes_reported:3145728,
                   vram_bytes_reported:2097152,context_length_reported:2048}],
                resident_model_count:1,
                measurement_scope:"LOCAL_PROVIDER_AND_HOST_HINTS_ONLY",
                inference_latency_measured:false,generation_requested:false,
                model_load_requested:false,production_authority:false
            });
            const raw=JSON.stringify(sample());
            const parsed=p.parseSnapshot(raw);
            assert.strictEqual(parsed.valid,true);
            assert.strictEqual(parsed.records.length,1);
            assert.strictEqual(parsed.models.length,1);
            assert.strictEqual(parsed.models[0],parsed.records[0].model);
            const profile=p.modelProfile(parsed.status,parsed.records,"qwen3:1.7b");
            assert.strictEqual(profile.state,"LOADED");
            assert.strictEqual(profile.sizeMiB,"3.0");
            assert.strictEqual(profile.vramMiB,"2.0");
            assert.strictEqual(profile.context,"2048");
            assert.strictEqual(p.modelState(parsed.status,parsed.models,"qwen3:1.7b"),"LOADED");
            assert.strictEqual(p.modelProfile(parsed.status,parsed.records,"not-installed").state,"NOT_LOADED");
            assert.strictEqual(p.modelProfile("UNAVAILABLE",parsed.records,"qwen3:1.7b").state,"UNKNOWN");
            assert.strictEqual(p.modelProfile("NOT_CHECKED",parsed.records,"qwen3:1.7b").sizeMiB,"?");
            const u=sample();
            u.resident_models[0].vram_bytes_reported=null;
            u.resident_models[0].context_length_reported=null;
            const nullable=p.parseSnapshot(JSON.stringify(u));
            assert.strictEqual(nullable.valid,true);
            assert.strictEqual(p.modelProfile(nullable.status,nullable.records,"qwen3:1.7b").vramMiB,"?");
            assert.strictEqual(p.modelProfile(nullable.status,nullable.records,"qwen3:1.7b").context,"?");
            const badValues=[
                ["size_bytes_reported",-1],["size_bytes_reported",1.5],
                ["size_bytes_reported",Number.MAX_SAFE_INTEGER+1],
                ["vram_bytes_reported",-1],["vram_bytes_reported",1.1],
                ["context_length_reported",0],["context_length_reported",-2],
                ["context_length_reported",Number.MAX_SAFE_INTEGER+1],
            ];
            for(const [k,v] of badValues){
                const invalid=sample();
                invalid.resident_models[0][k]=v;
                const checked=p.parseSnapshot(JSON.stringify(invalid));
                assert.strictEqual(checked.valid,false,k);
                assert.strictEqual(checked.records.length,0,k);
            }
            const events=[
                s=>p.captureStdout(s,raw),
                s=>p.captureStderr(s,""),
                s=>p.captureExit(s,0,0)
            ];
            for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]){
                let s=p.beginScan();
                for(let j=0;j<3;j++){
                    s=events[order[j]](s);
                    if(j<2){assert.strictEqual(s.models.length,0);
                            assert.strictEqual(s.records.length,0);}
                }
                assert.strictEqual(s.status,"OBSERVED");
                assert.strictEqual(s.records.length,1);
                assert.strictEqual(s.records[0].size_bytes_reported,3145728);
            }
            for(const bad of [
                [raw,"failure",0,0],[raw,"",1,0],
                [raw,"",0,1],["garbage","",0,0]
            ]){
                let s=p.beginScan();
                s=p.captureStdout(s,bad[0]);
                s=p.captureStderr(s,bad[1]);
                s=p.captureExit(s,bad[2],bad[3]);
                assert.strictEqual(s.status,"UNAVAILABLE");
                assert.strictEqual(s.models.length,0);
                assert.strictEqual(s.records.length,0);
            }
        """)
        policy=ROOT / "services/forest/ForestResidencyPolicy.js"
        p=subprocess.run(["node","-e",js,str(policy)],text=True,
                         capture_output=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
