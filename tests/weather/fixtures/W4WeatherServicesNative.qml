import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W5 // Disposable 520x300 native check of the original services owner.
// Checks canonical dark screen, pinned header/cards/report and list-only scroll.
ShellRoot {
    id: root
    property int ticks: 0
    property bool done: false
    property int phase: 0
    property real originalHeaderY: 0
    property real originalCardsY: 0
    property real originalReportY: 0

    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of (item.children || [])) {
            const found = find(child, name);
            if (found) return found;
        }
        if (item.item) return find(item.item, name);
        return null;
    }
    function fail(message) {
        if (done) return;
        done = true;
        console.error("W5_NATIVE_FAIL // " + message);
        Qt.quit();
    }

    Window {
        id: window
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationWeatherSubjectPane {
            id: subject
            anchors.fill: parent
            subjectRoute: "weather/services/health"
        }
    }

    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks > 30) return root.fail("TIMEOUT");
            const pane = root.find(subject, "weather-w5-services-pane");
            const head = root.find(subject, "weather-w5-fixed-header");
            const cards = root.find(subject, "weather-w5-summary-cards");
            const rows = root.find(subject, "weather-w5-runtime-rows");
            const scroll = root.find(subject, "weather-w5-detail-scroll");
            const report = root.find(subject, "weather-w5-selected-report");
            if (!pane || !head || !cards || !rows || !scroll || !report) {
                if (root.ticks > 10) return root.fail("W5_NODES_MISSING");
                return;
            }
            if (root.phase === 0) {
                const background = String(pane.color).toLowerCase();
                if (background === "#ffffff" || background === "white")
                    return root.fail("WHITE_SERVICES_BACKGROUND");
                if (!Array.isArray(pane.runtimeRows) || pane.runtimeRows.length < 2)
                    return root.fail("SERVICE_RUNTIME_MISSING");
                if (cards.height !== 65 || scroll.height <= 10)
                    return root.fail("SUMMARY_OR_SCROLL_VIEWPORT");
                if (scroll.contentHeight <= scroll.height)
                    return root.fail("SOURCE_ROWS_NOT_SCROLLABLE");
                root.originalHeaderY = head.y;
                root.originalCardsY = cards.y;
                root.originalReportY = report.y;
                scroll.contentY = Math.min(46, scroll.contentHeight-scroll.height);
                root.phase = 1;
                return;
            }
            if (root.phase === 1) {
                if (head.y !== root.originalHeaderY
                    || cards.y !== root.originalCardsY
                    || report.y !== root.originalReportY
                    || scroll.contentY <= 0)
                    return root.fail("PINNED_CONTENT_MOVED");
                root.done = true;
                console.log("W5_NATIVE_PASS // WEATHER_DARK_PINNED_SERVICES_AND_LIST_SCROLL");
                Qt.quit();
            }
        }
    }
}
