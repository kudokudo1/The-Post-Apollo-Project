import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/cpuplus"

ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_ADVANCED_POLICY_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int ticks: 0
    property int phase: 0
    property bool done: false
    function check(ok, message) {
        if (!ok) {
            done = true;
            console.error("ADVANCED_POLICY_NATIVE_FAIL // " + message);
            Qt.quit();
        }
        return ok;
    }
    Window {
        visible: smoke.armed
        width: 320
        height: 620
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: CpuPlusAdvancedPolicyPane {}
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 80) { smoke.check(false,"timeout phase="+smoke.phase); return; }
            const pane = scene.item;
            if (!pane || pane.width <= 0) return;
            if (smoke.phase === 0) {
                if (!smoke.check(!pane.busy && pane.status === "NOT CHECKED" && pane.cards.length === 0,
                    "no automatic read")) return;
                pane.refresh();
                smoke.phase++;
                return;
            }
            if (smoke.phase === 1) {
                if (pane.busy) return;
                // Container policy may restrict sysctl reads. Either honest
                // observed or unavailable is permitted; never fabricated.
                if (!smoke.check(pane.status === "OBSERVED // EXPLICIT READ"
                    || pane.status === "UNAVAILABLE // RECHECK","explicit probe terminal state")) return;
                pane.raw = "100\n10\n0\n0\n2097152\n0\n3000\n";
                pane.received = true;
                pane.exited = true;
                pane.exitOk = true;
                pane.finish();
                smoke.phase++;
                return;
            }
            if (smoke.phase === 2) {
                if (!smoke.check(pane.cards.length === 5 && pane.cards[1].value === "10%"
                    && pane.cards[2].value === "2097152 B" && pane.cards[3].value === "DISABLED"
                    && pane.cards[4].value === "30.00 s" && pane.observedAt > 0,
                    "actual rendering model")) return;
                pane.selectPreview("background");
                pane.stagePreview(15);
                if (!smoke.check(pane.stagedValue === 15 && pane.observation.background.ratio === 10,
                    "ratio preview separate from observed")) return;
                pane.stagePreview(101);
                if (!smoke.check(pane.stagedValue === 15,"out of range refusal")) return;
                pane.resetPreview();
                if (!smoke.check(pane.stagedValue === 10,"reset actual")) return;
                pane.selectPreview("writer");
                pane.stagePreview(3145728);
                if (!smoke.check(pane.stagedValue === 3145728 && pane.observation.writer.bytes === 2097152,
                    "byte preview separate from observed")) return;
                pane.raw = "invalid";
                pane.exitOk = true;
                pane.finish();
                smoke.phase++;
                return;
            }
            if (!smoke.check(pane.cards.length === 0 && pane.observedAt === 0
                && pane.status === "UNAVAILABLE // RECHECK" && pane.stagedValue === null && pane.selectedKey === "","invalid result clears values")) return;
            console.log("ADVANCED_POLICY_NATIVE_PASS");
            smoke.done = true;
            Qt.quit();
        }
    }
    Component.onCompleted: if (!armed) Qt.quit()
}
