"""ForestW P0/P2C freshness presentation is one-shot, not polling.

Only source contracts and pure JS states are tested. GitHub cannot certify
that native Quickshell timers fire when a session is suspended or hidden.
"""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[2]


class ForestObservationFreshnessTests(unittest.TestCase):
    def test_observation_expiry_timers_are_one_shot_and_fail_closed(self):
        p0=(ROOT/"services/forest/ForestResidencyAdapter.qml").read_text()
        p2c=(ROOT/"services/forest/ForestCapacityAdapter.qml").read_text()
        for adapter,scope in ((p0,"residency"),(p2c,"capacity")):
            self.assertIn('property string lastObservedLocalTime: ""',adapter)
            self.assertEqual(adapter.count("Timer {"),1)
            self.assertIn("interval: 300000",adapter)
            self.assertIn("repeat: false",adapter)
            self.assertIn("running: false",adapter)
            self.assertIn("expiryTimer.stop();",adapter)
            self.assertIn("expiryTimer.restart();",adapter)
            self.assertIn('lastObservedLocalTime = Qt.formatTime(new Date(), "HH:mm:ss");',adapter)
            self.assertIn('if (next.status === "OBSERVED") {',adapter)
            self.assertIn('status = "STALE";',adapter)
            self.assertIn('reason = "SNAPSHOT_EXPIRED";',adapter)
            self.assertIn(f"onTriggered: {scope}.expireObserved()",adapter)
            self.assertIn("if (scanning || status !== \"OBSERVED\")",adapter)
            self.assertNotIn("repeat: true",adapter)
            self.assertNotIn(f"onTriggered: {scope}.scan",adapter)
            self.assertNotIn(f"onTriggered: {scope}.inspect",adapter)
            self.assertNotIn("onTriggered: inspectProcess.exec",adapter)
            self.assertNotIn("onTriggered: residencyProcess.exec",adapter)
            self.assertNotIn('"/api/chat"',adapter)
            self.assertNotIn("execDetached",adapter)
        self.assertIn('models = [];',p0)
        self.assertIn('records = [];',p0)
        self.assertIn('data = CapacityPolicy.beginScan().data; // clear old resource hints',p2c)
        self.assertIn("status = next.status;",p0)
        self.assertIn("status = next.status;",p2c)

    def test_model_and_hardware_views_expose_staleness_not_live_grant(self):
        view=(ROOT/"widgets/ForestW.qml").read_text()
        hardware=(ROOT/"widgets/ForestHardwareCapacityView.qml").read_text()
        self.assertIn('modelResidency.lastObservedLocalTime',view)
        self.assertIn('capacityView.lastObservedLocalTime',view)
        self.assertIn('modelResidency.status === "STALE"',view)
        self.assertIn('capacityView.snapshotStatus === "STALE"',view)
        self.assertIn('P0 STALE // SCAN AGAIN',view)
        self.assertIn('P2C STALE // CHECK AGAIN',view)
        self.assertIn('P0 CHECKED ',view)
        self.assertIn('P2C CHECKED ',view)
        self.assertIn('readonly property string lastObservedLocalTime: capacity.lastObservedLocalTime',hardware)
        self.assertIn('capacity.status === "STALE" ? "P2C SNAPSHOT EXPIRED"',hardware)
        self.assertEqual(view.count("ForestResidencyAdapter {"),1)
        self.assertEqual(hardware.count("ForestCapacityAdapter {"),1)
        self.assertIn('readonly property bool chatHostTrusted: false',view)
        self.assertIn('readonly property bool voiceHostTrusted: false',view)
        self.assertIn('readonly property var activeChatSessions: []',view)
        # LOAD uses P0 source only. P2C never becomes another LOAD source.
        self.assertIn("modelResidency.status, modelResidency.models, selectedLocalModel",view)
        self.assertNotIn("selectedModelLoadState: capacityView",view)
        self.assertIn("onClicked: hardware.checkNow()",hardware)
        self.assertIn("onReloadRequested:",view)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_expired_p0_model_projection_is_unknown(self):
        js=textwrap.dedent(r"""
            const fs=require("fs"),vm=require("vm"),assert=require("assert");
            const ctx=vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
            const p=ctx,names=["qwen3:1.7b"];
            assert.strictEqual(p.modelState("OBSERVED",names,"qwen3:1.7b"),"LOADED");
            assert.strictEqual(p.modelState("OBSERVED",names,"other:model"),"NOT_LOADED");
            assert.strictEqual(p.modelState("STALE",names,"qwen3:1.7b"),"UNKNOWN");
            assert.strictEqual(p.modelState("STALE",[],"qwen3:1.7b"),"UNKNOWN");
            assert.strictEqual(p.modelState("UNAVAILABLE",names,"qwen3:1.7b"),"UNKNOWN");
            assert.strictEqual(p.modelProfile("STALE",[{model:"qwen3:1.7b",
                size_bytes_reported:123,vram_bytes_reported:42,
                context_length_reported:2048}],"qwen3:1.7b").state,"UNKNOWN");
        """)
        src=ROOT/"services/forest/ForestResidencyPolicy.js"
        p=subprocess.run(["node","-e",js,str(src)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
