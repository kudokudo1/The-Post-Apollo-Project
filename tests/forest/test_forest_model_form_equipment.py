"""Local model-form controls do not execute or authorize models."""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestModelFormEquipmentTests(unittest.TestCase):
    def test_local_equipment_form_and_reasoning_are_independent(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn("ModelFormPolicy.emptyEquipment(5)", view)
        self.assertIn("ModelFormPolicy.selectedModel(", view)
        self.assertIn("ModelFormPolicy.equip(selectedTreeEquipment, selectedTreeIndex", view)
        self.assertIn("ModelFormPolicy.clearSlot(selectedTreeEquipment, selectedTreeIndex", view)
        self.assertIn("ModelFormPolicy.chooseForm(selectedTreeEquipment, selectedTreeIndex", view)
        self.assertIn('model: ["SMALL", "AUTO", "BIG"]', view)
        self.assertIn('model: ["small", "big"]', view)
        self.assertIn("id: modelEquipmentPanel", view)
        self.assertIn("id: equipSmallButton", view)
        self.assertIn("id: equipBigButton", view)
        self.assertIn("PROFILE // AUTO ROUTER NOT CONNECTED", view)
        self.assertIn('property var selectedTreeReasoningSteps: [0, 0, 0, 0, 0]', view)
        self.assertIn('readonly property bool chatHostTrusted: false', view)
        self.assertIn('readonly property bool voiceHostTrusted: false', view)
        self.assertIn("InventoryPolicy.diskComparison(localInventory.status, localInventory.models)", view)
        self.assertIn("selectedModelName: root.selectedLocalModel", view)
        self.assertIn("modelResidency.status, modelResidency.models, selectedLocalModel", view)
        self.assertEqual(view.count("ForestInventoryAdapter {"), 1)
        self.assertEqual(view.count("ForestResidencyAdapter {"), 1)
        self.assertEqual(view.count("ForestHardwareCapacityView {"), 1)
        equipment = view[view.index("function equipLocalModel("):view.index("function scanModel(")]
        self.assertNotIn("selectedTreeReasoningSteps", equipment)
        self.assertNotIn("scanModels(", equipment)
        self.assertNotIn("scanResidency(", equipment)
        self.assertNotIn("refreshLocalModelEvidence(", equipment)
        self.assertNotIn("Process", equipment)
        self.assertNotIn("exec", equipment)

    def test_model_form_slider_shares_owner_state_and_keeps_compact_fallback(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        slider = (ROOT / "components/SelectorSlider.qml").read_text()
        rail = view.split("id: modelFormSlider", 1)[1].split(
            "visible: !root.autoPreviewOpen && localInventory.modelCount === 0", 1)[0]
        self.assertEqual(view.count("SelectorSlider {"), 2)
        self.assertIn('indexInteraction: "preview-release"', rail)
        self.assertIn('optionLabels: ["BIG", "AUTO", "SMALL"]', rail)
        self.assertIn('currentIndex: root.selectedModelForm === "BIG" ? 0', rail)
        self.assertIn(': root.selectedModelForm === "SMALL" ? 2 : 1', rail)
        self.assertIn("root.chooseModelForm(optionLabels[index]);", rail)
        self.assertIn("enabledSlider: root.menuOpen && root.modelPopupOpen && visible", rail)
        self.assertIn("if (!visible)", rail)
        self.assertIn("cancelIndexPreview();", rail)
        self.assertIn("root.modelPopupOpen && modelPopup.width >= 320", rail)
        self.assertIn("&& modelPopup.height >= 320", rail)
        self.assertEqual(view.count("anchors.rightMargin: modelFormSlider.visible ? 53 : 7"), 2)
        self.assertIn('model: ["SMALL", "AUTO", "BIG"]', view)
        self.assertIn("root.chooseModelForm(parent.modelData)", view)
        self.assertIn("onSelectedTreeIndexChanged: modelPopupOpen = false", view)
        self.assertNotIn("equipLocalModel(", rail)
        self.assertNotIn("clearLocalModel(", rail)
        self.assertNotIn("selectedTreeReasoningSteps", rail)
        self.assertNotIn("scanResidency(", rail)
        self.assertNotIn("scanModels(", rail)
        # Ensure a usable vertical track with the shared thumb and ruler.
        self.assertIn("topMargin: 38", slider)
        self.assertIn("bottomMargin: 26", slider)
        self.assertIn("height: 52", slider)
        for height in (320, 340, 360):
            rail_height = height - 33 - 19 - 62 - 2 - 2 - 17 - 4 - 3
            self.assertGreaterEqual(rail_height - 38 - 26 - 52, 60)
        # At the width threshold the list still has room for its buttons.
        self.assertGreaterEqual(320 - 53 - 7 - 43 - 32 - 45 - 20, 100)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_equipment_preserves_both_slots_and_tree_isolation(self):
        js = textwrap.dedent(r"""
            const fs = require("fs"), vm = require("vm"), assert = require("assert");
            const ctx = vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
            const p = ctx;
            const models = [
                {name:"small:model",size_bytes:100},
                {name:"big:model",size_bytes:400},
                {name:"alternate:model",size_bytes:200}
            ];
            const ready = "REACHABLE";
            let s = p.emptyEquipment(5);
            assert.strictEqual(s.length,5);
            for(const c of s) {
                assert.strictEqual(c.small,"");
                assert.strictEqual(c.big,"");
                assert.strictEqual(c.form,"AUTO");
                assert.strictEqual(p.selectedModel(c,ready,models),"");
            }
            const initial=s;
            s=p.equip(s,0,"small","small:model",ready,models);
            assert.strictEqual(initial[0].small,"");
            const smallOnly=s;
            s=p.equip(s,0,"big","big:model",ready,models);
            assert.strictEqual(smallOnly[0].big,"");
            assert.strictEqual(s[0].small,"small:model");
            assert.strictEqual(s[0].big,"big:model");
            assert.strictEqual(s[1].small,"");
            assert.strictEqual(s[1].big,"");
            assert.strictEqual(s[0].form,"AUTO");
            assert.strictEqual(p.selectedModel(s[0],ready,models),"");
            s=p.chooseForm(s,0,"SMALL");
            assert.strictEqual(p.selectedModel(s[0],ready,models),"small:model");
            s=p.chooseForm(s,0,"BIG");
            assert.strictEqual(p.selectedModel(s[0],ready,models),"big:model");
            s=p.chooseForm(s,0,"SMALL");
            assert.strictEqual(p.selectedModel(s[0],ready,models),"small:model");
            assert.strictEqual(s[0].big,"big:model");
            s=p.equip(s,0,"small","alternate:model",ready,models);
            assert.strictEqual(s[0].big,"big:model");
            assert.strictEqual(p.selectedModel(s[0],ready,models),"alternate:model");
            assert.strictEqual(p.selectedModel(s[0],"CHECKING",models),"");
            assert.strictEqual(p.selectedModel(s[0],"UNAVAILABLE",models),"");
            assert.strictEqual(p.selectedModel(s[0],ready,models.slice(0,2)),"");
            assert.strictEqual(p.slotLabel(s[0],"small","UNAVAILABLE",models),"alternate:model // UNVERIFIED");
            assert.strictEqual(p.slotLabel(s[0],"small",ready,models.slice(0,2)),"alternate:model // NOT FOUND");
            assert.strictEqual(s[0].small,"alternate:model");
            s=p.chooseForm(s,0,"BIG");
            assert.strictEqual(p.selectedModel(s[0],ready,models.slice(0,2)),"big:model");
            s=p.clearSlot(s,0,"small");
            assert.strictEqual(s[0].small,"");
            assert.strictEqual(s[0].big,"big:model");
            assert.strictEqual(p.slotLabel(s[0],"small",ready,models),"EMPTY");
            s=p.chooseForm(s,0,"SMALL");
            assert.strictEqual(p.selectedModel(s[0],ready,models),""); // no silent fallback
            s=p.chooseForm(s,0,"AUTO");
            assert.strictEqual(p.selectedModel(s[0],ready,models),""); // no fake routing
            s=p.equip(s,4,"big","alternate:model",ready,models);
            assert.strictEqual(s[4].big,"alternate:model");
            assert.strictEqual(s[0].big,"big:model");
            for(const bad of [
                p.equip(s,0,"large","big:model",ready,models),
                p.equip(s,-1,"big","big:model",ready,models),
                p.equip(s,5,"big","big:model",ready,models),
                p.equip(s,0,"big","BIG:model",ready,models),
                p.equip(s,0,"big","big:model","CHECKING",models),
                p.equip(s,0,"big","missing:model",ready,models),
                p.clearSlot(s,5,"small"),
                p.chooseForm(s,0,"DEEP")
            ]) assert.strictEqual(bad,null);
        """)
        result = subprocess.run(
            ["node", "-e", js, str(ROOT / "services/forest/ForestModelFormPolicy.js")],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
