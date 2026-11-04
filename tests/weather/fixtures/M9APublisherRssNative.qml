import QtQuick
import Quickshell
import "widgets/weather"

// M9a: REAL Quickshell publisher buttons, with two synthetic local responses.
// The production Python helper is replaced only in an isolated /tmp config.
ShellRoot {
    id: root
    property string phase: "boot"
    property bool done: false
    property bool bbcInspected: false
    property bool alJazeeraInspected: false
    property int ticks: 0

    FloatingWindow {
        id: window
        visible: true
        title: "M9A-PUBLISHER-RSS"
        implicitWidth: 1000
        implicitHeight: 760

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"

            StationPublisherFeeds {
                id: feeds
                x: 18
                y: 26
                width: parent.width - 36
                stationOpen: true
                onHeadlineSelected: function(row) {
                    if (root.phase === "bbcInspectClick") {
                        if (row.title !== "M9A BBC WORLD SYNTHETIC HEADLINE"
                                || row.source !== "BBC WORLD"
                                || row.url.indexOf("https://www.bbc.com/") !== 0) {
                            root.fail("WRONG_BBC_INSPECTOR_RECORD");
                            return;
                        }
                        root.bbcInspected = true;
                        console.log("M9A_PASS // BBC_INSPECTED_IN_STATION");
                    } else if (root.phase === "alJazeeraInspectClick") {
                        if (row.title !== "M9A AL JAZEERA SYNTHETIC HEADLINE"
                                || row.source !== "AL JAZEERA ENGLISH"
                                || row.url.indexOf("https://www.aljazeera.com/") !== 0) {
                            root.fail("WRONG_AJ_INSPECTOR_RECORD");
                            return;
                        }
                        root.alJazeeraInspected = true;
                        console.log("M9A_PASS // AL_JAZEERA_INSPECTED_IN_STATION");
                    } else {
                        root.fail("UNEXPECTED_INSPECTOR_SIGNAL");
                    }
                }
            }
        }
    }

    function find(item, predicate) {
        if (!item) return null;
        if (predicate(item)) return item;
        const children = item.children || [];
        for (let i = 0; i < children.length; i++) {
            const match = root.find(children[i], predicate);
            if (match) return match;
        }
        return null;
    }
    function button(label) {
        return root.find(window.contentItem, function(item) {
            return item.label === label && item.available !== undefined
                   && item.visible && item.enabled;
        });
    }
    function source(id) {
        return root.find(window.contentItem, function(item) {
            return item.modelData && item.modelData.id === id
                   && item.backend && item.backend.publisher !== undefined;
        });
    }
    function announce(buttonItem, marker) {
        if (!buttonItem || !buttonItem.visible) return false;
        const p = buttonItem.mapToItem(window.contentItem,
                                       buttonItem.width / 2,buttonItem.height / 2);
        if (!isFinite(p.x) || !isFinite(p.y) || p.x < 3 || p.y < 3
                || p.x > window.width - 3 || p.y > window.height - 3)
            return false;
        console.log("M9A_" + marker + "_READY // x=" + Math.round(p.x)
                    + " y=" + Math.round(p.y));
        return true;
    }
    function fail(message) {
        if (root.done) return;
        root.done = true;
        console.error("M9A_FAIL // " + message + " phase=" + root.phase);
    }

    Timer {
        interval: 70
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if (root.ticks % 80 === 0)
                console.log("M9A_TICK // phase=" + root.phase);

            const bbc = root.source("bbc-world");
            const aj = root.source("al-jazeera-english");
            if (root.phase === "boot") {
                if (!bbc || !aj) return;
                if (bbc.backend.ready || aj.backend.ready
                        || feeds.expandedPublisher !== "") {
                    root.fail("UNEXPECTED_INITIAL_FEED_LOAD");
                    return;
                }
                if (!root.announce(root.button("LOAD BBC"),"BBC_BUTTON"))
                    return;
                root.phase = "bbcButtonClick";
            } else if (root.phase === "bbcButtonClick") {
                if (!bbc || !bbc.backend.ready) return;
                if (bbc.backend.loading || bbc.backend.failed
                        || bbc.backend.rows.length !== 1
                        || bbc.backend.publisher !== "BBC WORLD"
                        || bbc.backend.usingCache || aj.backend.ready
                        || feeds.expandedPublisher !== "bbc-world") {
                    root.fail("BBC_REQUEST_PROVENANCE_OR_SOURCE_ISOLATION");
                    return;
                }
                if (!root.announce(root.button("INSPECT"),"BBC_INSPECT"))
                    return;
                root.phase = "bbcInspectClick";
            } else if (root.phase === "bbcInspectClick") {
                if (!root.bbcInspected) return;
                if (!root.announce(root.button("LOAD AL JAZEERA"),"AJ_BUTTON"))
                    return;
                root.phase = "alJazeeraButtonClick";
            } else if (root.phase === "alJazeeraButtonClick") {
                if (!aj || !aj.backend.ready) return;
                if (aj.backend.loading || aj.backend.failed
                        || aj.backend.rows.length !== 1
                        || aj.backend.publisher !== "AL JAZEERA ENGLISH"
                        || aj.backend.usingCache || !bbc.backend.ready
                        || bbc.backend.rows.length !== 1
                        || feeds.expandedPublisher !== "al-jazeera-english") {
                    root.fail("AL_JAZEERA_REQUEST_PROVENANCE_OR_BBC_CACHE_LOSS");
                    return;
                }
                if (!root.announce(root.button("INSPECT"),"AJ_INSPECT"))
                    return;
                root.phase = "alJazeeraInspectClick";
            } else if (root.phase === "alJazeeraInspectClick") {
                if (!root.alJazeeraInspected) return;
                root.done = true;
                console.log("M9A_PASS // BOTH_NATIVE_PUBLISHER_BUTTONS_AND_INSPECTORS");
            }
        }
    }
    Timer {
        interval: 21000
        running: !root.done
        repeat: false
        onTriggered: root.fail("TIMEOUT")
    }
    Timer {
        interval: 350
        running: root.done
        repeat: false
        onTriggered: Qt.quit()
    }
}
