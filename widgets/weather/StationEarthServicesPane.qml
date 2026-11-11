import QtQuick
import "../../components"

// EARTH E9 // The canonical SERVICES console observes existing map runtime
// and source inventory. The original StationDiscovery remains the only owner.
Rectangle {
    id: services
    objectName: "earth-e2-services-pane"
    color: Colors.black
    clip: true

    property var runtimeRows: []
    property var sourceRows: []
    // Historical mode selection is retained for existing callers; both
    // runtime reports and source ownership are visible on one SERVICES page.
    property string viewMode: "runtime"
    property string selectedSourceId: ""

    readonly property var sourceDirectory: {
        const items = [];
        const rows = Array.isArray(sourceRows) ? sourceRows : [];
        for (let i=0; i<rows.length; i++) {
            const row = rows[i] || {};
            items.push({
                id:"earth-directory-"+i,
                name:String(row.name || row.label || row.id || "SOURCE"),
                state:String(row.state || row.status || "SOURCE INVENTORY"),
                owner:String(row.owner || "EARTH MAP"),
                detail:String(row.detail || row.scope || "CURRENT MAP SOURCE DIRECTORY")
            });
        }
        return items;
    }

    StationServicesConsole {
        id: earthServicesConsole
        objectName: "earth-e9-services-console"
        anchors.fill: parent
        familyLabel: "EARTH"
        statusScope: "EARTH // MAP"
        runtimeRows: services.runtimeRows
        directoryRows: services.sourceDirectory
        selectedServiceId: services.selectedSourceId
        onSelectedServiceIdChanged: {
            services.selectedSourceId = selectedServiceId;
        }
    }
}
