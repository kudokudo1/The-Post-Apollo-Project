import QtQuick
import QtQuick.Window
import Quickshell
import qs.services.memory
import "widgets/cpuplus"

// Unmounted, isolated native test only. Runner copies the actual UI and uses
// a recording operation singleton instead of any privileged backend.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_MEMORY_UI_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int phase: 0
    property int ticks: 0
    property bool done: false

    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child, name);
            if (found) return found;
        }
        return null;
    }
    function check(ok, message) {
        if (!ok) {
            console.error("CPU_MEMORY_UI_NATIVE_FAIL // " + message);
            done = true;
            Qt.quit();
        }
        return ok;
    }
    Window {
        id: win
        visible: smoke.armed
        width: 320
        height: 620
        color: "#1B0623"
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: Item {
            CpuPlusMemoryActuatorPane {
                id: pane
                anchors.fill: parent
            }
            function testStep() {
                const rail = smoke.find(pane, "cpuplusMemoryMenuRail");
                const footer = smoke.find(pane, "cpuplusMemoryFooter");
                const scroll = smoke.find(pane, "cpuplusMemoryScroll");
                const slider = smoke.find(pane, "cpuplusCapacitySelector");
                if (!smoke.check(rail && footer && scroll && slider, "missing pane controls")) return;
                const pinned = smoke.find(pane, "cpuplusMemoryPinned");
                const bottomRail = smoke.find(pane, "cpuplusCapBottomRail");
                if (pane.page === "CAP" && !smoke.check(bottomRail && bottomRail.visible
                    && Math.abs(bottomRail.mapToItem(pane, 0, bottomRail.height).y - pane.height) < 2,
                    "CAP bottom rail not stapled")) return;
                if (pane.width <= 0 || pane.height <= 0 || footer.height <= 0) return;
                if (!smoke.check(rail.height > 0 && scroll.y >= rail.y + rail.height
                        && scroll.y + scroll.height <= footer.y + 1,
                        "rail/footer overlap " + pane.width + "x" + pane.height + " rail=" + rail.height
                            + " scroll=" + scroll.y + "/" + scroll.height + " footer=" + footer.y)) return;
                if (pane.page === "CAP" && !smoke.check(pinned && pinned.y + pinned.height <= footer.y
                        && scroll.y >= pinned.y + pinned.height, "CAP pinned overlap")) return;
                if (smoke.phase === 0) {
                    if (!pane.received || !pane.exited) return;
                    // Supply stable synthetic observations after the real read-only probe exits.
                    pane.sample = {total:33554432, available:8388608, swap:25165820,
                        free:25165820, some:0, full:0, swappiness:60,
                        rows:[{name:"/dev/zram0",size:8388608,used:0,priority:100,kind:"ZRAM"},
                            {name:"/var/lib/post-apollo-memory-swap/swapfile",size:16777212,used:0,priority:10,kind:"OTHER SWAP"}]};
                    pane.stagedGiB = 16;
                    pane.stagedSwappiness = 60;
                    if (!smoke.check(rail.columns === 6 && slider.enabledSlider, "wide CAP geometry/availability")) return;
                    const shared = smoke.find(slider, "cpuplusSharedHorizontalSelector");
                    if (!smoke.check(shared && shared.horizontalStep && shared.rotation === 90
                            && shared.stepDetentCount === 17 && shared.handleTravel() > 0,
                            "shared horizontal STEP geometry")) return;
                    const left = shared.mapToItem(slider, shared.width / 2, shared.height);
                    const right = shared.mapToItem(slider, shared.width / 2, 0);
                    if (!smoke.check(left.x < right.x && Math.abs(left.y - right.y) < 1,
                            "horizontal low-to-high transform")) return;
                    shared.beginStepPreview(shared.handleYForValue(24));
                    if (!smoke.check(shared.pendingStepValue === 24 && pane.stagedGiB === 16,
                            "preview must not stage owner")) return;
                    shared.cancelStepPreview();
                    shared.requestStepDelta(1);
                    shared.requestStepDelta(1);
                    if (!smoke.check(pane.stagedGiB === 24 && pane.capacity.actualKiB === 16777212, "target versus actual")) return;
                    pane.selectCapSection(1);
                    if (!smoke.check(!slider.visible && scroll.visible, "actions section")) return;
                    slider.valueRequested(32);
                    if (!smoke.check(pane.stagedGiB === 24, "hidden slider refusal")) return;
                    pane.selectCapSection(2);
                    if (!smoke.check(scroll.visible, "details section")) return;
                    pane.selectCapSection(0);
                    if (!smoke.check(!scroll.visible && slider.visible, "target section scroll-free")) return;
                    MemoryOperation.busy = true;
                    slider.valueRequested(32);
                    if (!smoke.check(pane.stagedGiB === 24 && !slider.enabledSlider, "busy refusal")) return;
                    pane.selectMenu(1);
                    smoke.phase = 1;
                    return;
                }
                if (smoke.phase === 1) {
                    const dial = smoke.find(pane, "cpuplusSwappinessDial");
                    if (!dial) return;
                    const actions = smoke.find(pane, "cpuplusPolicyActions");
                    const refresh = smoke.find(pane, "cpuplusPolicyRefresh");
                    if (!smoke.check(actions && refresh && actions.width > 60
                        && actions.mapToItem(pane,0,0).x >= dial.mapToItem(pane,dial.width,0).x
                        && !bottomRail.visible, "POL side actions geometry")) return;
                    if (!smoke.check(!dial.interactive && MemoryOperation.busy, "in-flight continuity")) return;
                    MemoryOperation.busy = false;
                    dial.valueRequested(150);
                    if (!smoke.check(pane.stagedSwappiness === 150 && pane.sample.swappiness === 60, "policy target versus actual")) return;
                    win.width = 220;
                    pane.selectMenu(2);
                    smoke.phase = 2;
                    return;
                }
                if (smoke.phase >= 2 && smoke.phase <= 5) {
                    if (!smoke.check(rail.columns === 3 && pane.menuIndex === smoke.phase
                            && !slider.visible && !smoke.find(pane, "cpuplusSwappinessDial"),
                            "narrow menu layout/hidden controls")) return;
                    if (smoke.phase < 5) pane.selectMenu(smoke.phase + 1);
                    else pane.selectMenu(0);
                    smoke.phase++;
                    return;
                }
                if (!smoke.check(pane.page === "CAP" && slider.visible
                        && pane.stagedGiB === 24 && pane.stagedSwappiness === 150
                        && MemoryOperation.requests === 0, "navigation continuity or unexpected dispatch")) return;
                console.log("CPU_MEMORY_UI_NATIVE_PASS");
                smoke.done = true;
                Qt.quit();
            }
            }
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 60) {
                smoke.check(false, "timeout");
                return;
            }
            if (scene.item) scene.item.testStep();
        }
    }
    Component.onCompleted: if (!armed) Qt.quit()
}
