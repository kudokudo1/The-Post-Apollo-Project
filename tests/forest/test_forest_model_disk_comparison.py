"""ForestW model disk bars: B0 reported artifact size, not intelligence."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ForestModelDiskComparisonTests(unittest.TestCase):
    def test_rows_reuse_b0_without_new_process_or_controls(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        self.assertIn("InventoryPolicy.diskComparison(localInventory.status, localInventory.models)",view)
        self.assertIn("InventoryPolicy.diskProfile(root.modelDiskComparison, modelName)",view)
        self.assertIn('text: "DISK REP // " + modelEntry.diskProfile.label',view)
        self.assertIn("modelEntry.diskProfile.ratio",view)
        self.assertIn("visible: modelEntry.diskProfile.comparable",view)
        self.assertIn("relative to largest listed model, not intelligence",view)
        self.assertEqual(view.count("ForestInventoryAdapter {"),1)
        self.assertEqual(view.count("ForestResidencyAdapter {"),1)
        self.assertEqual(view.count("ForestHardwareCapacityView {"),1)
        self.assertIn("id: forestDiagnosticsPopup",view)
        self.assertIn('onClicked: root.equipLocalModel("small", modelEntry.modelName)',view)
        self.assertIn('onClicked: root.equipLocalModel("big", modelEntry.modelName)',view)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)
        # Existing 82px row: controls end y=27, text y=29..41,
        # track y=43..48, status bar starts at y=52.
        self.assertIn("height: 82",view)
        self.assertIn("anchors.topMargin: 29",view)
        self.assertLessEqual(29+12+2+5,82-8-22)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_exact_snapshot_sizes_ratios_and_unknown_states(self):
        js=textwrap.dedent(r"""
            const fs=require("fs"),vm=require("vm"),assert=require("assert");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx;
            const small={name:"small:model",size_bytes:1073741824};
            const big={name:"big:model",size_bytes:4294967296};
            const zero={name:"zero:model",size_bytes:0};
            let c=p.diskComparison("REACHABLE",[big,zero,small]);
            assert.strictEqual(c.observed,true);
            assert.strictEqual(c.largest,big.size_bytes);
            let s=p.diskProfile(c,small.name), b=p.diskProfile(c,big.name);
            assert.strictEqual(s.observed,true);
            assert.strictEqual(s.label,"1.00 GiB");
            assert.strictEqual(s.ratio,0.25);
            assert.strictEqual(b.label,"4.00 GiB");
            assert.strictEqual(b.ratio,1);
            assert.strictEqual(p.diskProfile(c,zero.name).label,"0 B");
            assert.strictEqual(p.diskProfile(c,zero.name).ratio,0);
            assert.strictEqual(p.diskProfile(c,"SMALL:model").observed,false);
            assert.strictEqual(p.diskProfile(c,"constructor").observed,false);
            const c0=p.diskComparison("REACHABLE",[zero]);
            assert.strictEqual(p.diskProfile(c0,zero.name).comparable,false);
            assert.strictEqual(p.diskProfile(c0,zero.name).label,"0 B");
            for(const status of ["CHECKING","UNAVAILABLE","NOT_CHECKED","STALE"])
                assert.strictEqual(p.diskProfile(p.diskComparison(status,[small]),small.name).observed,false);
            for(const bad of [-1,1.5,NaN,Infinity,"100",null,Number.MAX_SAFE_INTEGER+1])
                assert.strictEqual(p.diskComparison("REACHABLE",[small,{name:"bad",size_bytes:bad}]).observed,false);
            assert.strictEqual(p.diskComparison("REACHABLE",[small,small]).observed,false);
            assert.strictEqual(p.diskComparison("REACHABLE",[{name:"../bad",size_bytes:1}]).observed,false);
            assert.strictEqual(p.diskComparison("REACHABLE",Array(257).fill(small)).observed,false);
            assert.strictEqual(p.diskProfile(p.diskComparison("REACHABLE",[]),small.name).label,"?");
            assert.strictEqual(p.artifactSizeLabel(512),"512 B");
            assert.strictEqual(p.artifactSizeLabel(1024),"1.0 KiB");
            assert.strictEqual(p.artifactSizeLabel(1048576),"1.0 MiB");
            assert.strictEqual(p.artifactSizeLabel(-1),"?");
            // Recalculate against a changed successful inventory, no cached maximum.
            c=p.diskComparison("REACHABLE",[small]);
            assert.strictEqual(p.diskProfile(c,small.name).ratio,1);
            assert.strictEqual(p.diskProfile(c,big.name).observed,false);
            // Actual B0 parser and complete process barrier precede comparison.
            const raw=JSON.stringify({schema_version:1,provider:"ollama",status:"REACHABLE",
                model_count:2,models:[small,big],capabilities:["list_models"],
                generation_enabled:false,tools_enabled:false,sessions_enabled:false});
            let state=p.beginScan();
            state=p.captureStdoutScan(state,raw);
            assert.strictEqual(p.diskComparison(state.status,state.models).observed,false);
            state=p.captureStderrScan(state,"");
            assert.strictEqual(p.diskComparison(state.status,state.models).observed,false);
            state=p.captureExitScan(state,0,0);
            assert.strictEqual(p.diskProfile(p.diskComparison(state.status,state.models),small.name).ratio,0.25);
        """)
        p=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestInventoryPolicy.js")],
                         capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
