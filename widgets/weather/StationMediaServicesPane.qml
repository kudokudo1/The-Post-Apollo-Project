import QtQuick
import "../../components"
import "StationNewsCatalogPolicy.js" as Catalog
import "StationMediaSubjectPanelPolicy.js" as MediaPolicy"

// MEDIA M10 // One canonical SERVICES dashboard with RUNTIME and SOURCE
// DIRECTORY in one scrollable dossier, not two duplicate screens.
// It only displays last-observed NEWS status; never starts NEWS or MPD.
Rectangle {
    id: services
    objectName: "media-m1-services"
    color: Colors.black
    clip: true

    property string viewMode: "runtime"
    property bool embeddedHeader: false
    property bool stationOpen: true
    property double newsObservedMs: 0
    property string newsFeedBadge: "NEWS NOT YET OBSERVED"
    property var newsRuntimeRows: []
    property var newsSourceRows: []

    // The four original service owners and their scope remain separate.
    readonly property var routeRows: [
        {name:"NEWS // GDELT",owner:"StationNewsHub / StationDiscovery",
         state:"NOT MOUNTED ON SERVICES",scope:"REPORTS // EXPLICIT REQUEST"},
        {name:"RADIO // MPD",owner:"StationRadio / HEADLESS MEDIA",
         state:"NOT MOUNTED ON SERVICES",scope:"SELECT // LOAD // PLAY"},
        {name:"WATCH // CATALOG",owner:"StationNewsHub",
         state:Catalog.channels.length+" KNOWN DESTINATIONS",
         scope:"PUBLISHER PAGE // NOT VERIFIED LIVE"},
        {name:"CREATORS // SAVED",owner:"StationNewsHub / CREATOR STORE",
         state:"NOT MOUNTED ON SERVICES",
         scope:"SAVED CHANNELS // ON-DEMAND UPLOADS"}
    ]

    readonly property var details: [
        {label:"NEWS",value:"GDELT",detail:"HEADLINES // SOURCE OWNER IS NEWS"},
        {label:"RADIO",value:"MPD",detail:"NO AUTOPLAY // USER ACTIVATION"},
        {label:"CATALOG",value:String(Catalog.channels.length),
         detail:"DESTINATIONS // NOT LIVE CHANNEL COUNT"},
        {label:"ROUTES",value:String(Object.keys(MediaPolicy.ROUTES).length),
         detail:"MEDIA SUBJECTS // CANONICAL ROUTES"}
    ]
    readonly property var summaryCards: [
        {label:details[0].label,value:details[0].value,
         detail:details[0].detail,color:Colors.cyan},
        {label:details[1].label,value:details[1].value,
         detail:details[1].detail,color:Colors.magenta},
        {label:details[2].label,value:details[2].value,
         detail:details[2].detail,color:Colors.yellow},
        {label:details[3].label,value:details[3].value,
         detail:details[3].detail,color:Colors.blue},
        {label:"OBSERVED",value:newsObservedMs>0 ? "YES" : "NO",
         detail:"LAST OBSERVED RUNTIME // NEWS",color:Colors.orange},
        {label:"SOURCE RACK",value:String(newsSourceRows.length),
         detail:"GDELT // SOURCE RACK // LAST OBSERVED",color:Colors.cyan}
    ]

    readonly property var directoryRows: {
        const out = [];
        for (let i=0; i<routeRows.length; i++) {
            const row=routeRows[i];
            out.push({id:"media-owner-"+i, name:row.name,
                state:row.state, owner:row.owner,detail:row.scope});
        }
        // Preserve every observed diagnostic, but do not report a previous
        // session sample as an active publisher or current live probe.
        for (let i=0; i<newsRuntimeRows.length; i++) {
            const row=newsRuntimeRows[i] || {};
            out.push({id:"media-news-runtime-"+i,
                name:"NEWS // "+String(row.name || "SOURCE"),
                state:"LAST OBSERVED // "+String(row.state || "--"),
                owner:"NEWS → REPORTS",
                detail:newsObservedMs>0 ? newsFeedBadge
                    : "NEWS NOT OBSERVED THIS SESSION"});
        }
        for (let i=0; i<newsSourceRows.length; i++) {
            const row=newsSourceRows[i] || {};
            out.push({id:"media-news-source-"+i,
                name:"GDELT // "+String(row.name || "SOURCE"),
                state:"LAST OBSERVED // "+String(row.state || "--"),
                owner:"NEWS → REPORTS",
                detail:"GDELT // SOURCE RACK // LAST OBSERVED"});
        }
        return out;
    }

    // Existing M2 contextual header buttons remain active. Their actions
    // jump within the combined dossier rather than hiding one data family.
    onViewModeChanged: {
        if (viewMode === "sources") console.focusDirectory();
        else console.focusRuntime();
    }

    StationServicesConsole {
        id: console
        objectName: "media-m10-services-console"
        anchors.fill: parent
        embeddedHeader: services.embeddedHeader
        familyLabel: "MEDIA"
        statusScope: "MEDIA // LAST OBSERVED RUNTIME"
        headerStatus: services.newsObservedMs>0
            ? "OBSERVED // NEWS" : "NEWS NOT OBSERVED"
        runtimeRows: []
        customCards: services.summaryCards
        directoryRows: services.directoryRows
    }
}
