"""ForestW local-only preference persistence, using disposable storage."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/forest/ui_model_preferences.py"
KEYS = ("CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH")


class ForestPreferencesTests(unittest.TestCase):
    def invoke(self, base, command, success=True):
        proc = subprocess.run([sys.executable, "-B", str(SCRIPT)],
            input=json.dumps(command)+"\n", text=True, capture_output=True,
            env={**os.environ, "XDG_DATA_HOME": str(base)}, timeout=5)
        self.assertEqual(proc.returncode, 0 if success else 1, proc.stderr)
        if success:
            self.assertEqual(proc.stderr, "")
            return json.loads(proc.stdout)
        self.assertEqual(proc.stdout, "")

    def test_round_trip_conflict_corruption_and_no_startup_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            directory=base/"post-apollo/forest/ui-preferences"
            file=directory/"model-preferences-v1.json"
            initial=self.invoke(base,{"action":"load"})
            self.assertFalse(directory.exists())
            self.assertEqual(initial["revision"],0)
            self.assertFalse(initial["production_authority"])
            trees=initial["trees"]
            self.assertEqual(set(trees),set(KEYS))
            trees["CHERRY"]={"small":"qwen:small","big":"qwen:big","form":"BIG","reasoning":3}
            trees["CEDAR"]["reasoning"]=2
            saved=self.invoke(base,{"action":"save","expectedRevision":0,"trees":trees})
            self.assertEqual(saved["revision"],1)
            self.assertEqual(saved["trees"],trees)
            self.assertEqual(file.stat().st_mode & 0o777,0o600)
            self.assertEqual(directory.stat().st_mode & 0o777,0o700)
            self.assertEqual(self.invoke(base,{"action":"load"}),saved)
            before=file.read_bytes()
            self.invoke(base,{"action":"save","expectedRevision":0,"trees":trees},False)
            self.assertEqual(file.read_bytes(),before)
            invalid=json.loads(json.dumps(trees))
            invalid["CEDAR"]["reasoning"]=True
            self.invoke(base,{"action":"save","expectedRevision":1,"trees":invalid},False)
            self.assertEqual(file.read_bytes(),before)
            file.write_text('{"broken":true}')
            self.invoke(base,{"action":"load"},False)
            self.invoke(base,{"action":"save","expectedRevision":0,"trees":trees},False)
            self.assertEqual(file.read_text(),'{"broken":true}')

    def test_symlink_and_nonprivate_record_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            directory=base/"post-apollo/forest/ui-preferences"
            directory.mkdir(parents=True,mode=0o700)
            file=directory/"model-preferences-v1.json"
            target=base/"unrelated"
            target.write_text("preserve")
            file.symlink_to(target)
            self.invoke(base,{"action":"load"},False)
            self.assertEqual(target.read_text(),"preserve")
            file.unlink()
            file.write_text("{}")
            file.chmod(0o644)
            self.invoke(base,{"action":"load"},False)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_ui_projection_consumes_actual_helper_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=self.invoke(Path(tmp),{"action":"load"})
            data["trees"]["CHERRY"]["small"]="small:model"
            data["trees"]["CHERRY"]["form"]="SMALL"
            data["trees"]["MAPLE"]["reasoning"]=3
            receipt=self.invoke(Path(tmp),{"action":"save","expectedRevision":0,"trees":data["trees"]})
        js=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),p);
const d=p.parse(process.argv[2]);
assert.strictEqual(d.revision,1);
const keys=["MACINTOSH","CEDAR","BRISTLECONE_PINE","MAPLE","CHERRY"];
const out=p.unpack(keys,d.trees);
assert.strictEqual(out.equipment[4].small,"small:model");
assert.strictEqual(out.equipment[4].form,"SMALL");
assert.strictEqual(out.reasoning[3],3);
assert(p.same(p.pack(keys,out.equipment,out.reasoning),d.trees));
assert.strictEqual(p.unpack(["CHERRY","CHERRY","CEDAR","MAPLE","MACINTOSH"],d.trees),null);
let bad=JSON.parse(process.argv[2]);bad.production_authority=true;
assert.strictEqual(p.parse(JSON.stringify(bad)),null);
bad=JSON.parse(process.argv[2]);bad.trees.CHERRY.reasoning=4;
assert.strictEqual(p.parse(JSON.stringify(bad)),null);
bad=JSON.parse(process.argv[2]);bad.revision=0;
assert.strictEqual(p.parse(JSON.stringify(bad)),null);
"""
        run=subprocess.run(["node","-e",js,str(ROOT/"services/forest/ForestPreferencePolicy.js"),json.dumps(receipt)],
                           capture_output=True,text=True,check=False)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_explicit_save_and_existing_locks(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        store=(ROOT/"services/forest/ForestPreferenceStore.qml").read_text()
        self.assertIn("Component.onCompleted: preferenceStore.load()",view)
        self.assertIn("onClicked: root.saveModelPreferences()",view)
        self.assertEqual(view.count("preferenceStore.save(currentPreferences)"),1)
        self.assertIn("if (!preferenceDirty)",view)
        self.assertIn("if (preferenceStore.status !== \"READY\")",view)
        self.assertIn("!stdoutSeen || !stderrSeen || !exitSeen",store)
        self.assertIn("doc.revision === submitted.expectedRevision + 1",store)
        self.assertIn("Preferences.same(doc.trees, submitted.trees)",store)
        self.assertNotIn("Timer {",store)
        self.assertIn("readonly property bool chatHostTrusted: false",view)
        self.assertIn("readonly property bool voiceHostTrusted: false",view)
        self.assertEqual(view.count("ForestInventoryAdapter {"),1)
        self.assertEqual(view.count("ForestResidencyAdapter {"),1)


if __name__ == "__main__":
    unittest.main()
