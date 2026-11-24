"""ForestW P2C same-response model identity cross-check.

This is internal consistency, NOT a host attestation or safe model admission.
Every test uses fake P2C JSON. No native provider or inference is launched.
"""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ForestP2CModelEvidenceCrosscheckTests(unittest.TestCase):
    def test_ui_uses_same_p2c_response_and_preserves_p0_host_source(self):
        view=(ROOT / "widgets/ForestW.qml").read_text()
        ui=(ROOT / "widgets/ForestHardwareCapacityView.qml").read_text()
        policy=(ROOT / "services/forest/ForestCapacityPolicy.js").read_text()
        adapter=(ROOT / "services/forest/ForestCapacityAdapter.qml").read_text()
        self.assertIn("&& capacity.data.model.matched === true",ui)
        self.assertIn("P2C TAGS/PS CROSS-CHECK // MATCH (ONE RESPONSE)",ui)
        self.assertIn("P2C MODEL EVIDENCE // UNCHECKED OR REFUSED",ui)
        self.assertIn("MODEL MEMORY REQUIREMENTS UNCALIBRATED // BENCHMARK HOLD",ui)
        self.assertIn("function _modelLists(installed, resident, requested)",policy)
        self.assertIn("selectedRecord(obj.selected_model, requested, lists)",policy)
        self.assertIn("record.installed_artifact_bytes_reported !== lists.installed",policy)
        self.assertIn("record.resident_vram_bytes_reported",policy)
        self.assertIn("matched:true",policy)
        self.assertIn("CapacityPolicy.beginScan(wanted)",adapter)
        self.assertEqual(adapter.count("Process {"),1)
        self.assertEqual(view.count("ForestResidencyAdapter {"),1)
        self.assertIn("modelResidency.status, modelResidency.models, selectedLocalModel",view)
        self.assertNotIn("modelResidency.status = capacityView",view)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)
        for bad in ("Timer {", "/api/chat", "Component.onCompleted: inspectCapacity",
                    "onVisibleChanged: inspectCapacity", "execDetached"):
            self.assertNotIn(bad,ui+"\n"+adapter)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_list_fields_and_summary_correlate_strictly(self):
        js=textwrap.dedent(r"""
            const fs=require("fs"),vm=require("vm"),assert=require("assert");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx, model="qwen3:1.7b";
            const install=(name=model,size=1048576)=>({name,size_bytes:size});
            const resident=(name=model,size=2097152,vram=1048576)=>({
                model:name,size_bytes_reported:size,
                vram_bytes_reported:vram,context_length_reported:2048
            });
            function snap(){
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
                    installed_models:[install()],installed_model_count:1,
                    resident_models:[resident()],resident_model_count:1,
                    host_visible_cpu_threads:16,process_affinity_cpu_threads:8,
                    host_mem_available_mib:2048,gpu_devices:[],
                    gpu_sysfs_status:"UNAVAILABLE",gpu_sysfs_device_count:0,
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
            const observe=(payload,wanted=model)=>
                p.parseSnapshot(JSON.stringify(payload),wanted);
            let good=observe(snap());
            assert.strictEqual(good.valid,true);
            assert.strictEqual(good.authority,false);
            assert.strictEqual(good.data.model.matched,true);
            assert.strictEqual(good.data.model.name,model);
            assert.strictEqual(good.data.model.installed,true);
            assert.strictEqual(good.data.model.resident,true);
            // Missing selected model is allowed only for generic host CHECK.
            const generic=snap();
            generic.selected_model=null;
            assert.strictEqual(observe(generic,"").valid,true);
            assert.strictEqual(observe(generic,model).valid,false);
            assert.strictEqual(observe(snap(),"").valid,false);
            assert.strictEqual(observe(snap(),"another:model").valid,false);
            function bad(mutator,reason){
                let a=snap();mutator(a);
                const out=observe(a);
                assert.strictEqual(out.valid,false,reason);
                assert.strictEqual(out.data.model.name,"",reason);
                assert.strictEqual(out.authority,false,reason);
            }
            bad(x=>{x.selected_model.installed=false;
                    x.selected_model.installed_artifact_bytes_reported=null;},
                "claimed missing despite tags record");
            bad(x=>{x.selected_model.resident=false;
                    x.selected_model.resident_memory_bytes_reported=null;
                    x.selected_model.resident_vram_bytes_reported=null;},
                "claimed unloaded despite ps record");
            bad(x=>x.selected_model.installed_artifact_bytes_reported=400,
                "wrong artifact size");
            bad(x=>x.selected_model.resident_memory_bytes_reported=400,
                "wrong resident size");
            bad(x=>x.selected_model.resident_vram_bytes_reported=null,
                "wrong null VRAM");
            bad(x=>x.installed_models[0].size_bytes=99,
                "different installed byte count");
            bad(x=>x.resident_models[0].size_bytes_reported=77,
                "different resident byte count");
            bad(x=>x.resident_models[0].vram_bytes_reported=null,
                "different ps nullable VRAM");
            bad(x=>x.installed_models=[install("other:model")],
                "summary present with different tags list");
            bad(x=>x.resident_models=[resident("other:model")],
                "summary resident with different ps list");
            bad(x=>{x.installed_models=[install(),install()];
                    x.installed_model_count=2;},
                "duplicate installed names");
            bad(x=>{x.resident_models=[resident(),resident()];
                    x.resident_model_count=2;},
                "duplicate resident names");
            bad(x=>x.installed_models[0].name="../bad",
                "invalid installed name");
            bad(x=>x.resident_models[0].model="bad model",
                "invalid resident name");
            bad(x=>x.installed_models[0].size_bytes=-1,
                "negative installed file size");
            bad(x=>x.resident_models[0].size_bytes_reported=1.5,
                "fractional resident memory");
            bad(x=>x.resident_models[0].vram_bytes_reported=-1,
                "negative VRAM");
            bad(x=>x.resident_models[0].context_length_reported=0,
                "invalid context length");
            bad(x=>x.resident_models[0].context_length_reported=1.5,
                "fractional context length");
            bad(x=>x.installed_models[0].size_bytes=Number.MAX_SAFE_INTEGER+1,
                "unsafe integer precision");
            // A model may remain resident even if removed from installed
            // inventory between P2C's GET requests. This is observational.
            const residentOnly=snap();
            residentOnly.installed_models=[];
            residentOnly.installed_model_count=0;
            residentOnly.selected_model.installed=false;
            residentOnly.selected_model.installed_artifact_bytes_reported=null;
            const r=observe(residentOnly);
            assert.strictEqual(r.valid,true);
            assert.strictEqual(r.data.model.installed,false);
            assert.strictEqual(r.data.model.resident,true);
            assert.strictEqual(r.data.model.matched,true);
            // Both absent yields explicit negative observation, no fit claim.
            const missing=snap();
            missing.installed_models=[];
            missing.resident_models=[];
            missing.installed_model_count=0;
            missing.resident_model_count=0;
            missing.selected_model.installed=false;
            missing.selected_model.resident=false;
            missing.selected_model.installed_artifact_bytes_reported=null;
            missing.selected_model.resident_memory_bytes_reported=null;
            missing.selected_model.resident_vram_bytes_reported=null;
            const m=observe(missing);
            assert.strictEqual(m.valid,true);
            assert.strictEqual(m.data.model.matched,true);
            assert.strictEqual(m.data.model.installed,false);
            assert.strictEqual(m.data.model.resident,false);
            assert.strictEqual(m.data.model.calibrated,false);
            // Same-response consistency cannot become a benchmark permission.
            assert.strictEqual(m.authority,false);
            const unavailable={
                schema:snap().schema,status:"UNAVAILABLE",
                reason:"LOCAL_OBSERVATION_UNAVAILABLE",
                generation_requested:false,model_load_requested:false,
                benchmark_permitted:false,permission_granted:false,
                production_authority:false
            };
            assert.strictEqual(observe(unavailable).status,"UNAVAILABLE");
            const state=p.beginScan(model);
            assert.strictEqual(state.data.model.matched,false);
        """)
        source=ROOT / "services/forest/ForestCapacityPolicy.js"
        proc=subprocess.run(["node","-e",js,str(source)],capture_output=True,
                            text=True,check=False)
        self.assertEqual(proc.returncode,0,proc.stderr)


if __name__=="__main__":
    unittest.main()
