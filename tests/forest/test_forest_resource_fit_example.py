"""Exercise actual P1 example bridge with hypothetical data only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/"scripts/forest/ui_resource_fit_example.py"


class ForestResourceFitExampleTests(unittest.TestCase):
    def invoke(self, values, expected):
        p=subprocess.run([sys.executable,"-B",str(HELPER),*values],
                         capture_output=True,text=True,check=False,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stderr,"")
        result=json.loads(p.stdout)
        self.assertEqual(result["outcome"],expected)
        self.assertEqual(result["inputs"],values)
        for key in ("production_authority","permission_granted","safe_to_start_inference"):
            self.assertIs(result[key],False)
        return result

    def test_real_governor_outcomes_and_precedence(self):
        fit=["defer","2048","4096","4096","512","1024","1024","2","4","4"]
        receipt=self.invoke(fit,"approve")
        self.assertIn("Modeled resource requirement fits current inputs",receipt["reasons"])
        for idx,value,outcome in [(2,"1024","deny"),(3,"1024","defer"),
                                  (1,"?","defer"),(3,"?","defer"),
                                  (2,"?","approve"),(1,"0","approve")]:
            example=fit.copy()
            example[idx]=value
            self.invoke(example,outcome)
        self.invoke(["deny"]+["?"]*9,"deny")
        self.invoke(["defer"]+["?"]*9,"defer")
        self.invoke(["defer","2048","1024","?"]+["?"]*6,"deny")
        self.invoke(["defer","0","?","?","0","?","?","0","?","?"],"approve")
        for invalid in ("-1","01","1.5","1000000001","true","nan","--help"):
            example=fit.copy();example[1]=invalid
            p=subprocess.run([sys.executable,"-B",str(HELPER),*example],
                             capture_output=True,text=True,check=False,timeout=5)
            self.assertEqual(p.returncode,2)
            self.assertEqual(p.stdout,"")

    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_ui_consumes_actual_governor_receipt(self):
        inputs=["defer","2048","4096","4096","512","1024","1024","2","4","4"]
        receipt=self.invoke(inputs,"approve")
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const receipt=JSON.parse(process.argv[2]),expected=receipt.inputs;
assert.strictEqual(p.parseReceipt(JSON.stringify(receipt),expected).outcome,"approve");
assert.strictEqual(JSON.stringify(p.commandInputs(["","","","","","","","",""],true)),
JSON.stringify(["defer","?","?","?","?","?","?","?","?","?"]));
assert.strictEqual(p.commandInputs(["-1","","","","","","","",""],true),null);
for(const key of ["production_authority","permission_granted","safe_to_start_inference"])
 assert.strictEqual(p.parseReceipt(JSON.stringify({...receipt,[key]:true}),expected),null);
assert.strictEqual(p.parseReceipt(JSON.stringify({...receipt,inputs:["deny",...expected.slice(1)]}),expected),null);
assert.strictEqual(p.parseReceipt(JSON.stringify({...receipt,outcome:"execute"}),expected),null);
"""
        p=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestResourceFitExamplePolicy.js"),json.dumps(receipt)],
                         capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_presentation_does_not_consume_live_capacity(self):
        pane=(ROOT/"widgets/ForestResourceFitExample.qml").read_text()
        diagnostics=(ROOT/"widgets/ForestHardwareCapacityView.qml").read_text()
        self.assertIn("ForestResourceFitExample {",diagnostics)
        self.assertIn("onClicked: pane.evaluateNow()",pane)
        self.assertIn("!stdoutSeen || !stderrSeen || !exitSeen",pane)
        self.assertIn("Example.parseReceipt(output, submitted)",pane)
        self.assertIn("HYPOTHETICAL VALUES ONLY",pane)
        self.assertIn("NO LEASE / NO PERMISSION / NO MODEL EXECUTION",pane)
        self.assertEqual(pane.count("Process {"),1)
        for forbidden in ("capacity.data","snapshot","selectedModelName","/api/chat","Timer {",
                          "XMLHttpRequest","Component.onCompleted: evaluateNow"):
            self.assertNotIn(forbidden,pane)
        source=HELPER.read_text()
        self.assertIn("result = evaluate_resource_request(req, requirements, budget, available)",source)
        self.assertNotIn("subprocess",source)


if __name__=="__main__":
    unittest.main()
