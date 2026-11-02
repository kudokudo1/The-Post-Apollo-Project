import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

Column {
    id: rack

    property var rows: []
    property string title: "LIVE RUNTIME // CURRENT PAGE"
    readonly property var summary: RuntimePolicy.summarizeRows(rows)

    spacing: 6
    width: parent ? parent.width : implicitWidth

    function statusColor(row) {
        switch (RuntimePolicy.statusToken(row)) {
        case "red": return Colors.red;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "magenta": return Colors.magenta;
        case "blue": return Colors.blue;
        case "green": return Colors.green;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }

    StationSectionDivider {
        width: parent.width
        title: rack.title
    }

    QuietText {
        width: parent.width
        text: "SOURCES " + rack.summary.total
              + " // READY " + rack.summary.ready
              + (rack.summary.loading > 0
                 ? " // READING " + rack.summary.loading : "")
              + (rack.summary.problem > 0
                 ? " // ERROR " + rack.summary.problem : "")
              + (rack.summary.cached > 0
                 ? " // CACHE " + rack.summary.cached : "")
              + (rack.summary.stale > 0
                 ? " // STALE " + rack.summary.stale : "")
              + (rack.summary.expired > 0
                 ? " // EXPIRED " + rack.summary.expired : "")
              + (rack.summary.offline > 0
                 ? " // OFFLINE " + rack.summary.offline : "")
              + (rack.summary.manual > 0
                 ? " // ON REQUEST " + rack.summary.manual : "")
              + (rack.summary.keyed > 0
                 ? " // KEYED " + rack.summary.keyed : "")
              + (rack.summary.local > 0
                 ? " // LOCAL " + rack.summary.local : "")
        font.pixelSize: 8
        color: Colors.orange
        elide: Text.ElideRight
    }

    Repeater {
        model: rack.rows

        delegate: Row {
            required property var modelData
            width: rack.width
            height: 24
            spacing: 10

            GohuText {
                width: 220
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.label
                color: Colors.white
                font.pixelSize: 9
                elide: Text.ElideRight
            }

            GohuText {
                width: 170
                anchors.verticalCenter: parent.verticalCenter
                text: RuntimePolicy.rowStateLabel(modelData)
                color: rack.statusColor(modelData)
                font.pixelSize: 9
                elide: Text.ElideRight
            }

            SecondaryText {
                width: 165
                anchors.verticalCenter: parent.verticalCenter
                text: RuntimePolicy.rowAgeLabel(modelData)
                font.pixelSize: 8
                elide: Text.ElideRight
            }

            QuietText {
                width: Math.max(0, parent.width - 585)
                anchors.verticalCenter: parent.verticalCenter
                text: RuntimePolicy.cadenceLabel(modelData)
                      + " // " + RuntimePolicy.retentionLabel(modelData)
                      + (modelData.detail !== ""
                         ? " // " + modelData.detail : "")
                color: Colors.cyan
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }
    }
}
