import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W4 // Disposable offscreen SERVICES smoke; no providers or host writes.
ShellRoot {
    id: root
    property int ticks: 0
    property bool done: false
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
        console.error("W4_NATIVE_FAIL // " + message);
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
            const sky = root.find(subject, "weather-w4-sky-rack");
            const ground = root.find(subject, "weather-w4-ground-rack");
            if (!sky || !ground) {
                if (root.ticks > 8) return root.fail("SERVICES_RACKS_MISSING");
                return;
            }
            if (!Array.isArray(sky.rows) || !Array.isArray(ground.rows)
                || sky.rows.length < 1 || ground.rows.length < 1)
                return root.fail("SERVICES_RUNTIME_ROWS_MISSING");
            root.done = true;
            console.log("W4_NATIVE_PASS // WEATHER_SERVICE_RACKS_MOUNTED");
            Qt.quit();
        }
    }
}
