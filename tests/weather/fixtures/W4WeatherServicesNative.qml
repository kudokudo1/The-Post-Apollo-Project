import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W5 // Disposable native visual-layout fixture with synthetic rows.
// The wiring and original source-owner boundaries are covered by source tests.
// No weather service, network collector, or desktop integration is launched.
ShellRoot {
    id: root
    property int ticks: 0
    property bool done: false
    property int phase: 0
    property real originalHeaderY: 0
    property real originalCardsY: 0
    property real originalReportY: 0

    function sampleRows(prefix, count) {
        const rows = [];
        for (let i = 0; i < count; i++)
            rows.push({
                id: prefix + "-" + String(i),
                label: prefix.toUpperCase() + " SERVICE " + (i+1),
                transport: i % 5 === 0 ? "LOADING" : "READY",
                availability: i % 5 === 0 ? "READING"
                    : i % 4 === 0 ? "CACHE_FRESH" : "LIVE",
                receivedAgeMinutes: i+1,
                observationAgeMinutes: i+2,
                ageBand: "FRESH",
                cadenceMs: 900000,
                mode: "NORMAL_POLL",
                retention: "PERSISTENT_LAST_GOOD",
                expireMs: 21600000,
                detail: "SYNTHETIC NATIVE FIXTURE"
            });
        return rows;
    }

    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of (item.children || [])) {
            const found = find(child, name);
            if (found) return found;
        }
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
        Weather.StationWeatherServicesPane {
            id: pane
            anchors.fill: parent
            skyRows: root.sampleRows("sky",8)
            groundRows: root.sampleRows("ground",8)
        }
    }

    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks > 30) return root.fail("TIMEOUT");
            const head = root.find(pane, "weather-w5-fixed-header");
            const cards = root.find(pane, "weather-w5-summary-cards");
            const rows = root.find(pane, "weather-w5-runtime-rows");
            const scroll = root.find(pane, "weather-w5-detail-scroll");
            const report = root.find(pane, "weather-w5-selected-report");
            if (!head || !cards || !rows || !scroll || !report) {
                if (root.ticks > 10) return root.fail("W5_NODES_MISSING");
                return;
            }
            if (root.phase === 0) {
                const background = String(pane.color).toLowerCase();
                if (background === "#ffffff" || background === "white")
                    return root.fail("WHITE_SERVICES_BACKGROUND");
                if (!Array.isArray(pane.runtimeRows) || pane.runtimeRows.length !== 16)
                    return root.fail("SERVICE_RUNTIME_ROWS_NOT_DEDUPED");
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
