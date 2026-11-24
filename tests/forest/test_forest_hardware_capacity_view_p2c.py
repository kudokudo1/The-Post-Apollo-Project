"""ForestW P2C read-only hardware screen, strict source/snapshot tests.

Native P2C and Ollama are NOT invoked. All input is disposable fake JSON;
host memory and GPU values are diagnostic hints, never execution authority.
"""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestHardwareViewP2CTests(unittest.TestCase):
    def test_popup_navigation_does_not_change_live_or_enable_inference(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        ui = (ROOT / "widgets/ForestHardwareCapacityView.qml").read_text()
        adapter = (ROOT / "services/forest/ForestCapacityAdapter.qml").read_text()
        self.assertIn("property bool hardwareViewOpen: false", view)
        self.assertEqual(view.count("ForestHardwareCapacityView {"), 1)
        self.assertIn('id: hardwareViewButton', view)
        self.assertIn('onClicked: root.hardwareViewOpen = !root.hardwareViewOpen', view)
        self.assertIn('text: root.hardwareViewOpen ? "FOREST // HARDWARE" : "FOREST // MODELS"', view)
        self.assertIn('visible: !root.hardwareViewOpen', view)
        self.assertIn('height: !root.hardwareViewOpen && modelPopup.height >= 270 ? 48 : 0', view)
        self.assertIn('anchors.top: popupProviderStatus.bottom', view)
        self.assertIn('anchors.bottom: popupFoot.top', view)
        self.assertIn('hardwareViewOpen = false;', view)
        self.assertIn('id: capacityView', view)
        self.assertEqual(view.count("ForestResidencyAdapter {"), 1)
        self.assertIn('root.selectedModelLoadState === "LOADED" ? "LOAD"', view)
        self.assertIn('modelResidency.models, modelEntry.modelName', view)
        self.assertIn("readonly property bool chatHostTrusted: false", view)
        self.assertIn("readonly property bool voiceHostTrusted: false", view)
        self.assertIn("readonly property var activeChatSessions: []", view)
        self.assertEqual(ui.count("ForestCapacityAdapter {"), 1)
        self.assertIn('onClicked: hardware.checkNow()', ui)
        self.assertIn('capacity.data.gpuCards', ui)
        self.assertIn('HEADROOM EST', ui)
        self.assertIn('NOT ALLOCATABLE PROOF', ui)
        self.assertIn('NO VERIFIED OLLAMA GPU MAPPING OR C5 PERMIT', ui)
        self.assertIn('NO BENCHMARK / NO INFERENCE', ui)
        self.assertIn("contentHeight: reportColumn.height", ui)
        self.assertIn("boundsBehavior: Flickable.StopAtBounds", ui)
        self.assertIn("running: false", adapter)
        self.assertIn('Quickshell.shellPath("scripts/forest/performance_capacity_p2c.py")', adapter)
        self.assertIn('"inspect"', adapter)
        self.assertEqual(adapter.count("Process {"), 1)
        for forbidden in (
            "Timer {", "Component.onCompleted: inspectCapacity",
            "onVisibleChanged: inspectCapacity", "execDetached",
            '"/api/chat"', '"--model"', "modelResidency.scanResidency()",
            "localInventory.scanModels()",
        ):
            self.assertNotIn(forbidden, adapter + "\n" + ui)
        self.assertNotIn("modelResidency.status = capacityView", view)
        self.assertNotIn("chatHostTrusted: true", view)
        self.assertNotIn("voiceHostTrusted: true", view)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_p2c_validation_and_exit_barrier(self):
        js = textwrap.dedent(r"""
            const assert=require("assert"),fs=require("fs"),vm=require("vm");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx;
            const card=()=>({
                card:"card0",vram_total_bytes_reported:4294967296,
                vram_used_bytes_reported:3221225472,
                vram_headroom_bytes_estimated:1073741824,
                measurement_scope:"DRM_SYSFS_DIAGNOSTIC_ONLY",
                ollama_device_mapping_verified:false
            });
            const payload=()=>({
                schema:"post-apollo.forest.performance-capacity.readonly-p2c",
                status:"OBSERVED",provider:"ollama",ollama_version:"0.32.14",
                selected_model:null,installed_models:[{name:"qwen3:1.7b",size_bytes:50000}],
                installed_model_count:1,resident_models:[],resident_model_count:0,
                host_visible_cpu_threads:16,process_affinity_cpu_threads:8,
                host_mem_available_mib:2280,gpu_devices:[card()],
                gpu_sysfs_status:"COUNTERS_OBSERVED",gpu_sysfs_device_count:1,
                gpu_metrics_are_free_allocatable_vram:false,
                ollama_device_mapping_verified:false,resource_budget_established:false,
                model_requirements_established:false,exclusive_capacity_reserved:false,
                generation_requested:false,model_load_requested:false,
                benchmark_permitted:false,c5_authority:"NOT_EVALUATED",
                permission_granted:false,production_authority:false
            });
            const raw=JSON.stringify(payload());
            const okay=p.parseSnapshot(raw);
            assert.strictEqual(okay.valid,true);
            assert.strictEqual(okay.status,"OBSERVED");
            assert.strictEqual(okay.authority,false);
            assert.strictEqual(okay.data.hostRam,"2280");
            assert.strictEqual(okay.data.cpuVisible,"16");
            assert.strictEqual(okay.data.cpuAffinity,"8");
            assert.strictEqual(okay.data.gpuCount,1);
            assert.strictEqual(okay.data.gpuCards[0].card,"card0");
            assert.strictEqual(okay.data.gpuCards[0].totalMiB,"4096");
            assert.strictEqual(okay.data.gpuCards[0].usedMiB,"3072");
            assert.strictEqual(okay.data.gpuCards[0].headroomMiB,"1024");
            const unknown=payload();
            unknown.host_mem_available_mib=null;
            unknown.process_affinity_cpu_threads=null;
            unknown.gpu_devices=[];
            unknown.gpu_sysfs_device_count=0;
            unknown.gpu_sysfs_status="UNAVAILABLE";
            const missing=p.parseSnapshot(JSON.stringify(unknown));
            assert.strictEqual(missing.valid,true);
            assert.strictEqual(missing.data.gpuCount,0);
            assert.strictEqual(missing.data.hostRam,"?");
            assert.strictEqual(missing.data.cpuAffinity,"?");
            const partial=payload();
            partial.gpu_devices[0].vram_used_bytes_reported=null;
            partial.gpu_devices[0].vram_headroom_bytes_estimated=null;
            const nullable=p.parseSnapshot(JSON.stringify(partial));
            assert.strictEqual(nullable.valid,true);
            assert.strictEqual(nullable.data.gpuCards[0].usedMiB,"?");
            assert.strictEqual(nullable.data.gpuCards[0].headroomMiB,"?");
            const broken=[
                {production_authority:true}, {permission_granted:true},
                {benchmark_permitted:true}, {generation_requested:true},
                {model_load_requested:true}, {resource_budget_established:true},
                {exclusive_capacity_reserved:true},{ollama_device_mapping_verified:true},
                {gpu_metrics_are_free_allocatable_vram:true},
                {c5_authority:"PERMITTED"},{selected_model:{model:"x"}},
                {host_mem_available_mib:-2},{host_mem_available_mib:1.5},
                {host_mem_available_mib:Number.MAX_SAFE_INTEGER+1},
                {process_affinity_cpu_threads:0},{process_affinity_cpu_threads:65537},
                {gpu_sysfs_device_count:0},{gpu_sysfs_status:"UNAVAILABLE"},
                {installed_model_count:0},{resident_model_count:1},
                {provider:"other"},{schema:"invalid"},
            ];
            for(const patch of broken) {
                const r=p.parseSnapshot(JSON.stringify({...payload(),...patch}));
                assert.strictEqual(r.valid,false,JSON.stringify(patch));
                assert.strictEqual(r.data.gpuCards.length,0);
                assert.strictEqual(r.authority,false);
            }
            const badGpu=[
                {card:"card8"},{card:"../../sys"},{vram_total_bytes_reported:-1},
                {vram_used_bytes_reported:1.25},{vram_headroom_bytes_estimated:99},
                {measurement_scope:"REAL_FREE_VRAM"},
                {ollama_device_mapping_verified:true}
            ];
            for(const patch of badGpu) {
                const r=payload();
                r.gpu_devices=[{...card(),...patch}];
                assert.strictEqual(p.parseSnapshot(JSON.stringify(r)).valid,false,
                                   JSON.stringify(patch));
            }
            const dup=payload();
            dup.gpu_devices=[card(),card()];
            dup.gpu_sysfs_device_count=2;
            assert.strictEqual(p.parseSnapshot(JSON.stringify(dup)).valid,false);
            assert.strictEqual(p.parseSnapshot("x").valid,false);
            assert.strictEqual(p.parseSnapshot("[").valid,false);
            assert.strictEqual(p.parseSnapshot(" ".repeat(1048577)).valid,false);
            const err={
                schema:payload().schema,status:"UNAVAILABLE",
                reason:"LOCAL_OBSERVATION_UNAVAILABLE",
                generation_requested:false,model_load_requested:false,
                benchmark_permitted:false,permission_granted:false,
                production_authority:false
            };
            assert.strictEqual(p.parseSnapshot(JSON.stringify(err)).valid,true);
            assert.strictEqual(p.parseSnapshot(JSON.stringify(err)).status,"UNAVAILABLE");
            const streams=[
                s=>p.captureStdout(s,raw),
                s=>p.captureStderr(s,""),
                s=>p.captureExit(s,0,0)
            ];
            for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]) {
                let state=p.beginScan();
                for(let i=0;i<3;i++){
                    state=streams[order[i]](state);
                    if(i<2){
                        assert.strictEqual(state.complete,false);
                        assert.strictEqual(state.data.gpuCards.length,0);
                    }
                }
                assert.strictEqual(state.complete,true);
                assert.strictEqual(state.status,"OBSERVED");
                assert.strictEqual(state.data.gpuCount,1);
            }
            const failed=[
                [raw,"error",0,0],[raw,"",1,0],[raw,"",0,1],
                ["invalid","",0,0],[JSON.stringify(err),"",0,0]
            ];
            for(const [out,stderr,code,exit] of failed) {
                let state=p.beginScan();
                state=p.captureStdout(state,out);
                state=p.captureStderr(state,stderr);
                state=p.captureExit(state,code,exit);
                assert.strictEqual(state.status,"UNAVAILABLE");
                assert.strictEqual(state.data.gpuCards.length,0);
            }
            let stale=p.beginScan();
            stale=p.captureStdout(stale,raw);
            stale=p.captureStdout(stale,raw);
            stale=p.captureStderr(stale,"");
            stale=p.captureExit(stale,0,0);
            assert.strictEqual(stale.status,"UNAVAILABLE");
            assert.strictEqual(stale.data.gpuCards.length,0);
        """)
        policy = ROOT / "services/forest/ForestCapacityPolicy.js"
        r = subprocess.run(["node","-e",js,str(policy)],capture_output=True,
                           text=True,check=False)
        self.assertEqual(r.returncode,0,r.stderr)


if __name__=="__main__":
    unittest.main()
