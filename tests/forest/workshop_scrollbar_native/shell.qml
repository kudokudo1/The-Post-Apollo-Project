import QtQuick
import QtQuick.Window
import Quickshell
import "./widgets" as Widgets

ShellRoot {
    id: witness
    property int phase: 0
    property int attempts: 0
    property bool failed: false
    function check(ok, why) {
        if (!ok) {
            failed = true;
            console.error("WORKSHOP_SCROLL_FAIL // " + why);
        }
    }
    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        if (item.children) {
            for (let i = 0; i < item.children.length; ++i) {
                const found = find(item.children[i], name);
                if (found) return found;
            }
        }
        return null;
    }
    function near(a,b) { return Math.abs(a-b) < 0.1; }
    function referenceVocabulary(body) {
        const seasons = find(body,"forestSeasonReference");
        const spirit = find(body,"forestSpiritReference");
        check(seasons && spirit, "missing recovered reference vocabulary");
        if (!seasons || !spirit) return;
        check(seasons.text === "SEASONS // STATE UNKNOWN (REFERENCE)\nSUMMER // GROWING\nFALL // SHEDDING\nWINTER // DORMANT\nSPRING // CLEANING"
            && spirit.text === "SPIRIT // DETERMINISTIC GUIDANCE AND CONTROLS\nTOOLS LOCKED // NO LIVE AUTHORITY",
            "reference must not assert active season or authority");
        check(seasons.textFormat === Text.PlainText && spirit.textFormat === Text.PlainText
            && near(seasons.width,body.width) && near(spirit.width,body.width)
            && seasons.height > 0 && spirit.height > 0,
            "reference width/text geometry");
    }
    function geometry(s, body, bar) {
        referenceVocabulary(body);
        check(bar.parent === workshop && s.parent === workshop, "non-scrolling sibling");
        check(near(body.width,s.width) && near(s.contentHeight,body.implicitHeight), "body geometry");
        check(bar.x - bar.effectiveGlowPadding >= s.width, "content/rail overlap");
        check(bar.x + bar.width + bar.effectiveGlowPadding <= workshop.width, "right glow clipped");
        check(bar.y - bar.effectiveGlowPadding >= 0
            && bar.y + bar.height + bar.effectiveGlowPadding <= workshop.height, "endpoint glow clipped");
    }
    Window {
        id: scene
        width: 360; height: 220; visible: true
        Widgets.ForestWorkshopReferenceView {
            id: workshop
            anchors.fill: parent
            profileSupported: true
        }
    }
    Timer {
        id: timer
        interval: 100
        running: true
        repeat: true
        onTriggered: {
            if (witness.failed) { stop(); Qt.quit(); return; }
            const s = witness.find(workshop,"forestWorkshopViewport");
            const body = witness.find(workshop,"forestWorkshopBody");
            const bar = witness.find(workshop,"forestWorkshopScrollBar");
            if (!s || !body || !bar) { witness.check(false,"missing production items"); return; }
            if (witness.phase === 1 && workshop.busy) {
                if (++witness.attempts > 100) witness.check(false,"reference timeout");
                return;
            }
            const n = witness.phase++;
            switch(n) {
            case 0:
                witness.geometry(s,body,bar);
                witness.check(!bar.visible && !bar.scrollable,"short content should hide rail");
                workshop.requestPlan("research",[],[]);
                break;
            case 1:
                witness.check(!!workshop.receipt && workshop.receipt.plan.status === "UNKNOWN_HOLD"
                    && !workshop.receipt.permission_granted && !workshop.receipt.model_execution_permitted
                    && !workshop.receipt.production_authority && workshop.receipt.safe_actions.length === 0,
                    "actual read-only reference");
                witness.geometry(s,body,bar);
                witness.check(bar.visible && bar.scrollable,"long content should show rail");
                const event = {modifiers:0,pixelDelta:Qt.point(0,-42),angleDelta:Qt.point(0,0),accepted:false};
                bar.handleWheel(event);
                witness.check(event.accepted && s.contentY > 0,"wheel mapping");
                break;
            case 2:
                witness.geometry(s,body,bar);
                bar.scrollTo(bar.trackLength,0);
                witness.check(witness.near(s.contentY,bar.maxContentY),"drag bottom");
                bar.scrollTo(0,0);
                witness.check(witness.near(s.contentY,0),"drag top");
                scene.width = 220;
                break;
            case 3:
                witness.geometry(s,body,bar);
                witness.check(bar.visible && bar.scrollable,"narrow viewport");
                bar.scrollTo(bar.trackLength,0);
                witness.check(witness.near(s.contentY,bar.maxContentY),"narrow drag bottom");
                scene.width = 390; scene.height = 1600;
                break;
            case 4:
                witness.geometry(s,body,bar);
                witness.check(!bar.scrollable && !bar.visible,"tall viewport fits actual receipt");
                workshop.visible = false;
                break;
            case 5:
                witness.check(!workshop.receipt && !bar.visible,"close clears reference");
                break;
            default: witness.check(false,"unexpected phase");
            }
            if (witness.failed) { stop(); Qt.quit(); return; }
            console.info("WORKSHOP_SCROLL_PHASE_PASS " + n);
            if (n === 5) {
                console.info("WORKSHOP_SCROLL_NATIVE_PASS");
                stop(); Qt.quit();
            }
        }
    }
}
