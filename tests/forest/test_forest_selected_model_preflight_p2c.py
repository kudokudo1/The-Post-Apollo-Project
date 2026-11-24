"""ForestW P2C selected-model preflight remains exact and read-only."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestSelectedPreflightP2CTests(unittest.TestCase):
    def test_qml_uses_tree_model_only_on_manual_check(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        ui = (ROOT / "widgets/ForestHardwareCapacityView.qml").read_text()
        adapter = (ROOT / "services/forest/ForestCapacityAdapter.qml").read_text()
        policy = (ROOT / "services/forest/ForestCapacityPolicy.js").read_text()
        self.assertIn("selectedModelName: root.selectedLocalModel", view)
        self.assertIn("property string selectedModelName: \"\"", ui)
        self.assertIn("capacity.requestedModel === selectedModelName", ui)
        self.assertIn("capacity.data.model.name === selectedModelName", ui)
        self.assertIn("capacity.inspectCapacity(selectedModelName)", ui)
        self.assertIn("onClicked: hardware.checkNow()", ui)
        self.assertIn('text: "MODEL MEMORY REQUIREMENTS UNCALIBRATED // BENCHMARK HOLD"', ui)
        self.assertIn("MODEL METRICS // UNKNOWN", ui)
        self.assertIn("SELECTED MODEL NOT CHECKED // PRESS CHECK", ui)
        self.assertIn("ARTIFACT", ui)
        self.assertIn("RES MEM", ui)
        self.assertIn("VRAM REP", ui)
        self.assertIn("property string requestedModel: \"\"", adapter)
        self.assertIn("CapacityPolicy.beginScan(wanted)", adapter)
        self.assertIn('argv.push("--model", wanted)', adapter)
        self.assertIn('Quickshell.shellPath("scripts/forest/performance_capacity_p2c.py")', adapter)
        self.assertIn("function validModelName(name)", policy)
        self.assertIn("record.model !== requested", policy)
        self.assertIn("record.runtime_requirement_calibrated !== false", policy)
        self.assertIn("parseSnapshot(raw,n.requestedModel)", policy)
        self.assertEqual(adapter.count("Process {"), 1)
        self.assertEqual(view.count("ForestResidencyAdapter {"), 1)
        self.assertIn("modelResidency.status, modelResidency.models, selectedLocalModel", view)
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertIn("readonly property bool voiceHostTrusted: false", view)
        for forbidden in ("Timer {", "onVisibleChanged: inspectCapacity",
                          "Component.onCompleted: inspectCapacity",
                          "/api/chat", "generation", "execDetached"):
            self.assertNotIn(forbidden, ui + adapter)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_exact_model_match_and_fail_closed_in_all_process_orders(self):
        js = textwrap.dedent(r"""
            const fs=require("fs"),vm=require("vm"),assert=require("assert");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx, model="qwen3:1.7b";
            function payload() {
                return {
                    schema:"post-apollo.forest.performance-capacity.readonly-p2c",
                    status:"OBSERVED",provider:"ollama",ollama_version:"0.32.14",
                    selected_model:{
                        model,installed:true,resident:true,
                        installed_artifact_bytes_reported:1048576,
                        resident_memory_bytes_reported:2097152,
                        resident_vram_bytes_reported:1048576,
                        runtime_requirement_calibrated:false
                    },
                    installed_models:[{name:model,size_bytes:1048576}],
                    installed_model_count:1,
                    resident_models:[{model,size_bytes_reported:2097152,
                                     vram_bytes_reported:1048576,
                                     context_length_reported:2048}],
                    resident_model_count:1,
                    host_visible_cpu_threads:16,
                    process_affinity_cpu_threads:8,
                    host_mem_available_mib:2048,
                    gpu_devices:[],gpu_sysfs_status:"UNAVAILABLE",
                    gpu_sysfs_device_count:0,
                    gpu_metrics_are_free_allocatable_vram:false,
                    ollama_device_mapping_verified:false,
                    resource_budget_established:false,
                    model_requirements_established:false,
                    exclusive_capacity_reserved:false,
                    generation_requested:false,model_load_requested:false,
                    benchmark_permitted:false,c5_authority:"NOT_EVALUATED",
                    permission_granted:false,production_authority:false
                };
            }
            const raw=JSON.stringify(payload());
            const accepted=p.parseSnapshot(raw,model);
            assert.strictEqual(accepted.valid,true);
            assert.strictEqual(accepted.status,"OBSERVED");
            assert.strictEqual(accepted.authority,false);
            assert.strictEqual(accepted.data.model.name,model);
            assert.strictEqual(accepted.data.model.installed,true);
            assert.strictEqual(accepted.data.model.resident,true);
            assert.strictEqual(accepted.data.model.artifactMiB,"1");
            assert.strictEqual(accepted.data.model.residentMiB,"2");
            assert.strictEqual(accepted.data.model.vramMiB,"1");
            assert.strictEqual(accepted.data.model.calibrated,false);
            assert.strictEqual(p.parseSnapshot(raw).valid,false);
            assert.strictEqual(p.parseSnapshot(raw,"granite4:small-h").valid,false);
            assert.strictEqual(p.parseSnapshot(raw,"../../etc").valid,false);
            assert.strictEqual(p.parseSnapshot(raw,23).valid,false);
            assert.strictEqual(p.beginScan("../bad"),null);
            assert.strictEqual(p.beginScan("bad model"),null);
            assert.strictEqual(p.beginScan(model).requestedModel,model);
            assert.strictEqual(p.validModelName(model),true);
            for (const patch of [
                {model:"granite4:small-h"},
                {model:"../bad"},
                {installed:1},
                {resident:"true"},
                {runtime_requirement_calibrated:true},
                {installed_artifact_bytes_reported:null},
                {installed_artifact_bytes_reported:-1},
                {installed_artifact_bytes_reported:1.5},
                {installed_artifact_bytes_reported:Number.MAX_SAFE_INTEGER+1},
                {resident_memory_bytes_reported:null},
                {resident_vram_bytes_reported:-3},
            ]) {
                const r=payload();
                r.selected_model={...r.selected_model,...patch};
                const result=p.parseSnapshot(JSON.stringify(r),model);
                assert.strictEqual(result.valid,false,JSON.stringify(patch));
                assert.strictEqual(result.data.model.name,"");
                assert.strictEqual(result.authority,false);
            }
            const unloaded=payload();
            unloaded.selected_model={
                model,installed:false,resident:false,
                installed_artifact_bytes_reported:null,
                resident_memory_bytes_reported:null,
                resident_vram_bytes_reported:null,
                runtime_requirement_calibrated:false
            };
            unloaded.installed_models=[];
            unloaded.installed_model_count=0;
            unloaded.resident_models=[];
            unloaded.resident_model_count=0;
            const absent=p.parseSnapshot(JSON.stringify(unloaded),model);
            assert.strictEqual(absent.valid,true);
            assert.strictEqual(absent.data.model.installed,false);
            assert.strictEqual(absent.data.model.resident,false);
            assert.strictEqual(absent.data.model.artifactMiB,"?");
            assert.strictEqual(absent.data.model.residentMiB,"?");
            assert.strictEqual(absent.data.model.vramMiB,"?");
            const partial=payload();
            partial.selected_model.resident_vram_bytes_reported=null;
            // P2C's selected summary comes from this SAME residency record.
            partial.resident_models[0].vram_bytes_reported=null;
            const unknown=p.parseSnapshot(JSON.stringify(partial),model);
            assert.strictEqual(unknown.valid,true);
            assert.strictEqual(unknown.data.model.vramMiB,"?");
            const badAbsent=payload();
            badAbsent.selected_model.resident=false;
            assert.strictEqual(p.parseSnapshot(JSON.stringify(badAbsent),model).valid,false);
            const noModel=payload();
            noModel.selected_model=null;
            const generic=p.parseSnapshot(JSON.stringify(noModel));
            assert.strictEqual(generic.valid,true);
            assert.strictEqual(generic.data.model.name,"");
            for (const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]) {
                const callbacks=[
                    s=>p.captureStdout(s,raw),
                    s=>p.captureStderr(s,""),
                    s=>p.captureExit(s,0,0)
                ];
                let state=p.beginScan(model);
                for(let i=0;i<3;i++) {
                    state=callbacks[order[i]](state);
                    assert.strictEqual(state.requestedModel,model);
                    if(i<2) {
                        assert.strictEqual(state.complete,false);
                        assert.strictEqual(state.data.model.name,"");
                    }
                }
                assert.strictEqual(state.complete,true);
                assert.strictEqual(state.status,"OBSERVED");
                assert.strictEqual(state.data.model.name,model);
                assert.strictEqual(state.data.model.calibrated,false);
            }
            for (const triplet of [
                [raw,"oops",0,0],[raw,"",1,0],[raw,"",0,1],
                [raw,"",2,0],[JSON.stringify(noModel),"",0,0]
            ]) {
                let state=p.beginScan(model);
                state=p.captureStdout(state,triplet[0]);
                state=p.captureStderr(state,triplet[1]);
                state=p.captureExit(state,triplet[2],triplet[3]);
                assert.strictEqual(state.status,"UNAVAILABLE");
                assert.strictEqual(state.data.model.name,"");
                assert.strictEqual(state.data.gpuCards.length,0);
            }
            let duplicate=p.beginScan(model);
            duplicate=p.captureStdout(duplicate,raw);
            duplicate=p.captureStdout(duplicate,raw);
            duplicate=p.captureStderr(duplicate,"");
            duplicate=p.captureExit(duplicate,0,0);
            assert.strictEqual(duplicate.status,"UNAVAILABLE");
            assert.strictEqual(duplicate.data.model.name,"");
        """)
        source=ROOT / "services/forest/ForestCapacityPolicy.js"
        p=subprocess.run(["node","-e",js,str(source)],
                         capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
