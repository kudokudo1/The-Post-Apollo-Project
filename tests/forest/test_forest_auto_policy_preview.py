"""ForestW uses actual Core I1 policy for disposable examples, not a second router."""
from itertools import product
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/"scripts/forest/ui_routing_example.py"
sys.path.insert(0,str(HELPER.parent))
from ui_routing_example import evaluate


class ForestAutoPreviewTests(unittest.TestCase):
    def test_preview_is_opt_in_and_nonactuating(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        preview=(ROOT/"widgets/ForestAutoPolicyPreview.qml").read_text()
        policy=(ROOT/"services/forest/ForestAutoPolicyPreview.js").read_text()
        self.assertIn("property bool autoPreviewOpen: false",view)
        self.assertIn("onClicked: root.autoPreviewOpen = !root.autoPreviewOpen",view)
        self.assertIn("visible: root.modelPopupOpen && root.autoPreviewOpen",view)
        self.assertIn("visible: !root.autoPreviewOpen",view)
        self.assertIn("autoPreviewOpen = false;",view)
        self.assertIn("EXAMPLE ONLY // NOT ROUTED",view)
        self.assertIn("AUTO // OFFLINE POLICY PREVIEW",preview)
        self.assertIn("EXAMPLE RECOMMENDATION",preview)
        self.assertIn("onVisibleChanged: if (!visible) resetExample()",preview)
        self.assertIn("ModelFormPolicy.slotLabel(pane.equipment,",preview)
        self.assertIn("REASONING INDEPENDENT",preview)
        self.assertIn("selectedEquipment, localInventory.status, localInventory.models",view)
        self.assertIn("onLeftClicked: pane.evaluateExample()",preview)
        self.assertIn("!busy || !stdoutSeen || !stderrSeen || !exitSeen",preview)
        self.assertIn("if (!discard && visible)",preview)
        self.assertIn("if (busy) discard = true;",preview)
        self.assertIn("AutoPreview.parse(output,submitted)",preview)
        self.assertEqual(preview.count("Process {"),1)
        self.assertNotIn("function preview(",policy)
        self.assertIn("result = recommend(RoutingInput(",HELPER.read_text())
        for forbidden in ("Timer {","XMLHttpRequest","forestPromptInput",
                          "equipLocalModel(", "chooseModelForm(", "saveModelPreferences(",
                          "scanModels(", "scanResidency(", "chatHostTrusted"):
            self.assertNotIn(forbidden,preview)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)

    def test_all_example_combinations_use_actual_core(self):
        tested=0
        for form,effort,c,f,s in product(("auto","small","big"),
                ("light","normal","deep"),("unset","low","normal","high"),
                ("unset","absent","present"),("unset","sufficient","insufficient","unknown")):
            args=[form,effort,c,f,s]
            d=evaluate(args)
            r=d["reference"]
            triggers=[reason for active,reason in [
                (c=="high","high_task_complexity"),(f=="present","known_small_failure"),
                (s=="insufficient","small_capability_insufficient")] if active]
            expected=form if form!="auto" else ("big" if triggers else "small")
            reasons=["explicit_form"] if form!="auto" else (triggers or ["no_big_escalation_evidence"])
            self.assertEqual(d["inputs"],args)
            self.assertEqual(r["recommendedForm"],expected)
            self.assertEqual(r["reasoningMode"],effort)
            self.assertEqual(r["reasons"],reasons)
            self.assertEqual(r["status"],"UNKNOWN_HOLD")
            self.assertIsNone(r["resolvedForm"])
            self.assertIsNone(r["resolvedBinding"])
            for flag in ("sourceAuthenticated","permissionGranted","productionAuthority","modelExecutionPermitted"):
                self.assertIs(r[flag],False)
            self.assertEqual(r["safeActions"],[])
            tested+=1
        self.assertEqual(tested,432)

    def test_cli_refuses_invalid_inputs(self):
        for args in (["auto","normal","invalid","absent","unknown"],
                     ["auto","none","low","absent","unknown"],
                     ["other","normal","low","absent","unknown"],
                     ["auto","normal","low","absent","unknown","extra"]):
            p=subprocess.run([sys.executable,"-B",str(HELPER),*args],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,2)
            self.assertEqual(p.stdout,"")

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_receipt_from_actual_helper(self):
        args=["auto","deep","high","present","insufficient"]
        run=subprocess.run([sys.executable,"-B",str(HELPER),*args],
                           capture_output=True,text=True,timeout=5,check=True)
        self.assertEqual(run.stderr,"")
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const d=JSON.parse(process.argv[2]),args=d.inputs;
const r=p.parse(JSON.stringify(d),args);
assert.strictEqual(r.form,"BIG");
assert.strictEqual(r.effort,"DEEP");
assert.strictEqual(r.requested,"AUTO");
assert.strictEqual(r.reasons.join("|"),"HIGH TASK COMPLEXITY|KNOWN SMALL FAILURE|SMALL CAPABILITY INSUFFICIENT");
for(const [k,v] of [["permissionGranted",true],["sourceAuthenticated",true],
 ["productionAuthority",true],["modelExecutionPermitted",true],["resolvedForm","big"],
 ["resolvedBinding","model"],["safeActions",["run"]],["status","ACTIVE"],
 ["reasoningMode","normal"],["reasons",["unrecognized"]]]){
 assert.strictEqual(p.parse(JSON.stringify({...d,reference:{...d.reference,[k]:v}}),args),null);
}
assert.strictEqual(p.parse(JSON.stringify(d),["auto","normal",...args.slice(2)]),null);
assert.strictEqual(p.parse(JSON.stringify({...d,extra:"private"}),args),null);
"""
        p=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestAutoPolicyPreview.js"),run.stdout],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
