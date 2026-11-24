"""Actual B6-R2 registry/plan projection; no real identity or execution."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/"scripts/forest/ui_workshop_reference.py"


class WorkshopReferenceTests(unittest.TestCase):
    def invoke(self, args, okay=True):
        p=subprocess.run([sys.executable,"-B",str(HELPER),*args],
                         capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0 if okay else 2,p.stderr)
        if not okay:
            self.assertEqual(p.stdout,"")
            return
        d=json.loads(p.stdout)
        self.assertEqual(d["inputs"],args)
        self.assertEqual(len(d["definitions"]),18)
        self.assertEqual(len(d["workshops"]),4)
        self.assertEqual(d["plan"]["status"],"UNKNOWN_HOLD")
        for flag in ("permission_granted","production_authority","model_execution_permitted"):
            self.assertIs(d[flag],False)
        self.assertEqual(d["safe_actions"],[])
        return d

    def test_core_and_optional_selection(self):
        for name,core in [("research",["web"]),("design",["memory","clarify"]),
                          ("code-debug",["file","terminal"]),("model",["file","terminal"])]:
            self.assertEqual(self.invoke([name,"",""])["plan"]["selected"],core)
        d=self.invoke(["code-debug","todo,leaf","testing"])
        self.assertEqual(d["plan"]["selected"],["file","terminal","todo","leaf","testing"])
        self.assertEqual(d["plan"]["unresolved"],["leaf"])
        self.assertIn("debugging",d["plan"]["dormant"])
        for args in [["research","","testing"],["model","web",""],["unknown","",""],
                     ["research","todo,todo",""],["research","todo,",""],
                     ["research","","","private-context"]]:
            self.invoke(args,False)

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_actual_receipt_projection(self):
        d=self.invoke(["code-debug","todo,leaf","testing"])
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const d=JSON.parse(process.argv[2]),args=d.inputs;
assert(p.parse(JSON.stringify(d),args));
const bad=[
 {...d,permission_granted:true},{...d,production_authority:true},
 {...d,model_execution_permitted:true},{...d,safe_actions:["run"]},
 {...d,plan:{...d.plan,status:"ACTIVE"}},
 {...d,plan:{...d.plan,selected:["file","terminal","todo","leaf","testing","debugging"]}},
 {...d,plan:{...d.plan,unresolved:[]}},
 {...d,definitions:[...d.definitions,d.definitions[0]]},
 {...d,inputs:["research","",""]}
];
for(const x of bad) assert.strictEqual(p.parse(JSON.stringify(x),args),null);
assert.strictEqual(JSON.stringify(p.toggle(["todo","leaf"],"todo")),'["leaf"]');
assert.strictEqual(JSON.stringify(p.toggle(["todo"],"leaf")),'["todo","leaf"]');
"""
        p=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestWorkshopReferencePolicy.js"),json.dumps(d)],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_ui_boundaries(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        pane=(ROOT/"widgets/ForestWorkshopReferenceView.qml").read_text()
        self.assertIn("id: forestWorkshopPopup",view)
        self.assertIn('profileSupported: root.activeTree.sessionKey === "BRISTLECONE_PINE"',view)
        self.assertIn("onDiagnosticsOpenChanged: if (diagnosticsOpen) workshopOpen = false",view)
        self.assertIn("onWorkshopOpenChanged: if (workshopOpen) diagnosticsOpen = false",view)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)
        self.assertIn("if (!visible || !profileSupported || busy || worker.running) return;",pane)
        self.assertIn("!busy || !stdoutSeen || !stderrSeen || !exitSeen",pane)
        self.assertIn("!discard && visible && profileSupported",pane)
        self.assertIn("if (busy) discard = true;",pane)
        self.assertIn("NO RECOVERED WORKSHOP PROFILE FOR THIS TREE",pane)
        self.assertIn("REFERENCE ONLY // NO TOOL EXECUTION OR PERMISSION",pane)
        for forbidden in ("Timer {","XMLHttpRequest","forestPromptInput","saveModelPreferences",
                          "ollama_chat_transport","/api/chat","FileView {"):
            self.assertNotIn(forbidden,pane)


if __name__=="__main__":
    unittest.main()
