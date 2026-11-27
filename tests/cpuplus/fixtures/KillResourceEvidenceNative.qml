import QtQuick
import Quickshell
import "services/kill" as KillBackend

// Real read-only helper path, with a disposable child supplied by the CI runner.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_CPU_KILL_SMOKE") === "CI_DISPOSABLE_ONLY"
    readonly property string childKey: Quickshell.env("POST_APOLLO_KILL_INSPECTION_CHILD")
    property int phase: 0
    property int ticks: 0
    property bool done: false

    function check(ok, label) {
        if (ok) return true;
        console.error("KILL_INSPECTION_NATIVE_FAIL " + label + " // " + reader.status);
        done = true;
        Qt.quit();
        return false;
    }

    KillBackend.KillResourceEvidence {
        id: reader
    }

    Timer {
        interval: 50
        running: smoke.armed && !smoke.done
        repeat: true
        onTriggered: {
            if (++smoke.ticks > 300) {
                smoke.check(false, "bounded lifecycle");
                return;
            }
            if (smoke.phase === 0) {
                if (!smoke.check(!!smoke.childKey && !reader.inspect(), "ineligible refusal")) return;
                reader.targetKey = smoke.childKey;
                reader.eligible = true;
                if (!smoke.check(!reader.busy && reader.result === null, "no automatic dispatch")) return;
                if (!smoke.check(reader.inspect() && reader.busy && !reader.inspect(), "one explicit request")) return;
                smoke.phase = 1;
            } else if (smoke.phase === 1 && !reader.busy) {
                if (!smoke.check(reader.result && reader.result.key === smoke.childKey
                    && reader.status === "OBSERVED // READ ONLY", "real helper correlated success")) return;
                let stale = JSON.parse(smoke.childKey);
                stale[1] += 1;
                reader.targetKey = JSON.stringify(stale);
                if (!smoke.check(reader.result === null && reader.inspect(), "changed identity clears evidence")) return;
                smoke.phase = 2;
            } else if (smoke.phase === 2 && !reader.busy) {
                if (!smoke.check(reader.result === null
                    && reader.status === "EVIDENCE UNAVAILABLE // NOT VERIFIED", "real stale identity refusal")) return;
                reader.targetKey = smoke.childKey;
                if (!smoke.check(reader.inspect(), "start cancellable read")) return;
                reader.eligible = false;
                if (!smoke.check(reader.result === null && !reader.inspect(), "selection loss refuses new request")) return;
                reader.eligible = true;
                smoke.phase = 3;
            } else if (smoke.phase === 3 && !reader.busy) {
                if (!smoke.check(reader.result === null && reader.status === "NOT INSPECTED",
                    "cancelled result suppressed after drain")) return;
                if (!smoke.check(reader.inspect(), "reinspect after drain")) return;
                smoke.phase = 4;
            } else if (smoke.phase === 4 && !reader.busy) {
                if (!smoke.check(reader.result && reader.result.key === smoke.childKey,
                    "fresh real read succeeds after cancellation")) return;
                console.log("KILL_INSPECTION_NATIVE_PASS");
                smoke.done = true;
                Qt.quit();
            }
        }
    }

    Component.onCompleted: if (!armed) Qt.quit()
}
