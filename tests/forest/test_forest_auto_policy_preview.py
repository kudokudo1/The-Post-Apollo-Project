"""Archived AUTO rules illustrated in UI; no runtime or task classification."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ForestAutoPreviewTests(unittest.TestCase):
    def test_preview_is_opt_in_and_nonactuating(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        preview=(ROOT/"widgets/ForestAutoPolicyPreview.qml").read_text()
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
        for forbidden in ("Process {","Timer {","XMLHttpRequest","forestPromptInput",
                          "equipLocalModel(", "chooseModelForm(", "saveModelPreferences(",
                          "scanModels(", "scanResidency(", "chatHostTrusted"):
            self.assertNotIn(forbidden,preview)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_all_archived_example_combinations(self):
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
let tested=0;
for(const c of ["unset","low","normal","high"])
 for(const f of ["unset","absent","present"])
  for(const s of ["unset","sufficient","insufficient","unknown"]){
    const r=p.preview(c,f,s);
    assert.strictEqual(r.form,c==="high"||f==="present"||s==="insufficient"?"BIG":"SMALL");
    assert.strictEqual(r.authority,false);
    assert.strictEqual(r.reasons.length,Math.max(1,Number(c==="high")+Number(f==="present")+Number(s==="insufficient")));
    tested++;
  }
assert.strictEqual(tested,48);
assert.strictEqual(p.preview("invalid","absent","unknown").form,"UNKNOWN");
assert.strictEqual(p.preview("low",null,"unknown").authority,false);
assert.strictEqual(p.preview("normal","absent","invalid").form,"UNKNOWN");
assert.strictEqual(p.preview("high","present","insufficient").reasons.join("|"),
"HIGH TASK COMPLEXITY|KNOWN SMALL FAILURE|SMALL CAPABILITY INSUFFICIENT");
"""
        p=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestAutoPolicyPreview.js")],
                         capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
