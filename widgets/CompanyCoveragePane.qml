import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/company"
import "CompanyCoveragePolicy.js" as Geo
import "weather/StationNaturalEarthLand110.js" as Land
import "weather/StationNaturalEarthContext110.js" as Context
import "CompanyNaturalEarthLakes110.js" as Lakes
import "CompanyCities50.js" as CityData

// Company Network Coverage M1: real geographic *reference* map.
// Natural Earth is public domain and already pinned by Weather Station.
// Neither Natural Earth boundaries nor capital markers imply service coverage.
// All company coverage, partner, workforce and client data remains absent.
Item {
    id: root

    property string regionKey: "lower48"
    property string selectedCode: ""
    property string selectedCountryCode: ""
    property bool serviceMenuOpen: false
    property bool hubPlacementArmed: false
    property bool hubEditorOpen: false
    property bool showCities: true
    property var selectedCity: null
    property bool streetConsentOpen: false
    property bool streetMode: false
    property bool vectorConsentOpen: false
    property string vectorStatus: "NOT INSTALLED / UNVERIFIED"
    property bool vectorRequestedStop: false
    property string vectorOutput: ""
    property string selectedHubId: ""
    readonly property var hubRows: hubStore.saved && Array.isArray(hubStore.saved.hubs)
        ? hubStore.saved.hubs : []
    readonly property var selectedHub: {
        for (var i=0;i<hubRows.length;i++)
            if(hubRows[i].id===selectedHubId && !hubRows[i].archived)
                return hubRows[i];
        return null;
    }
    property string serviceFamily: "ALL SERVICES"
    property string statusFilter: "ALL STATUS"
    property bool showReferencePoints: true
    property real zoom: 1
    property real centerLon: -96
    property real centerLat: 37

    readonly property bool compactLayout: width < 640
    readonly property var selectedState: Geo.stateForCode(selectedCode)
    readonly property var selectedCountry: Geo.countryForCode(selectedCountryCode)
    readonly property var bounds: Geo.regions[Geo.regionKey(regionKey)]
    onVisibleChanged: if (!visible) {
        serviceMenuOpen=false;
        hubPlacementArmed=false;
        vectorConsentOpen=false;
        // Closing Company Coverage stops the attached sidecar, not a
        // detached background application or persistent Company service.
        if (vectorRunner.running) {
            vectorRequestedStop=true;
            vectorRunner.running=false;
        }
    }

    function openVectorChoice() {
        if (vectorRunner.running) {
            vectorRequestedStop=true;
            vectorRunner.running=false;
            vectorStatus="CLOSING";
        } else {
            vectorConsentOpen=true;
        }
    }

    function launchVector(online) {
        if (vectorRunner.running) return;
        vectorConsentOpen=false;
        vectorOutput="";
        vectorRequestedStop=false;
        vectorStatus="LAUNCHING";
        vectorRunner.command = ["/usr/bin/python3",
            Quickshell.shellPath("services/company/CompanyVectorSidecarLaunch.py"),
            online ? "online" : "offline"];
        vectorRunner.running=true;
    }

    Process {
        id: vectorRunner
        running: false
        stdout: StdioCollector {
            onStreamFinished: root.vectorOutput = String(text || "")
        }
        onStarted: root.vectorStatus="STARTED / NATIVE WINDOW UNVERIFIED"
        onExited: function(code, status) {
            if (root.vectorRequestedStop) {
                root.vectorStatus="CLOSED";
                root.vectorRequestedStop=false;
                return;
            }
            var parsed=null;
            try { parsed=JSON.parse(root.vectorOutput); } catch(e) {}
            if (parsed && parsed.status==="NOT_INSTALLED")
                root.vectorStatus="NOT INSTALLED";
            else if (parsed && parsed.status==="LAUNCH_FAILED")
                root.vectorStatus="LAUNCH FAILED";
            else
                root.vectorStatus="EXITED / CHECK NATIVE INSTALL";
        }
    }

    CompanyHubStore {
        id: hubStore
        visible: false
        onSavedChanged: mapCanvas.requestPaint()
        onSavedSuccessfully: {
            root.selectedHubId = "hub-" + (saved.nextId - 1);
            root.hubEditorOpen = false;
            root.hubPlacementArmed = false;
            mapCanvas.requestPaint();
        }
    }

    function beginHubEntry() {
        hubEditor.begin(root.selectedState ? root.selectedState[0] : "");
        root.hubEditorOpen = true;
        root.hubPlacementArmed = false;
        root.serviceMenuOpen = false;
    }

    function openHubEditor(lon,lat) {
        // Returning from PICK LOCATION must not reset typed form values.
        if (!hubEditor.setCoordinates(lon,lat)) return;
        root.hubEditorOpen=true;
        root.hubPlacementArmed=false;
        root.serviceMenuOpen=false;
    }

    function chooseCity(city) {
        if (!city) return;
        selectedCity = city;
        selectedHubId = "";
        selectedCode = "";
        selectedCountryCode = "";
        var next = Geo.view(regionKey,Math.max(zoom,3.5),city[1],city[2]);
        applyView(next);
        if(streetMode) streetMap.focusAt(city[1],city[2],12);
    }

    function startStreetView() {
        var lon=centerLon,lat=centerLat,z=5;
        if(selectedCity) {
            lon=selectedCity[1];lat=selectedCity[2];z=12;
        } else if(selectedHub) {
            lon=selectedHub.longitude;lat=selectedHub.latitude;z=12;
        } else if(selectedState) {
            lon=selectedState[3];lat=selectedState[4];z=11;
        } else if(selectedCountry) {
            lon=selectedCountry[3];lat=selectedCountry[4];z=9;
        }
        streetMode=true;
        streetConsentOpen=false;
        streetMap.focusAt(lon,lat,z);
    }

    function visibleCities() {
        var q = String(stateSearch.text || "").trim().toLowerCase();
        if (!q) return [];
        var box=root.bounds;
        return CityData.cities.filter(function(city) {
            return city[1]>=box.west && city[1]<=box.east
                && city[2]>=box.south && city[2]<=box.north
                && city[0].toLowerCase().indexOf(q)>=0;
        }).slice(0,25);
    }

    function applyView(next) {
        zoom = next.zoom;
        centerLon = next.centerLon;
        centerLat = next.centerLat;
    }

    function setRegion(key) {
        regionKey = Geo.regionKey(key);
        applyView(Geo.defaultView(regionKey));
        selectedCode = "";
        selectedCountryCode = "";
        selectedHubId = "";
        selectedCity = null;
        serviceMenuOpen = false;
        stateSearch.text = "";
        if(streetMode) {
            var next=Geo.defaultView(regionKey);
            streetMap.focusAt(next.centerLon,next.centerLat,5);
        }
    }

    function chooseState(state) {
        if (!state) return;
        if (regionKey !== state[5] && regionKey !== "northAmerica"
                && regionKey !== "global")
            setRegion(state[5]);
        selectedCode = state[0];
        selectedCountryCode = "";
        selectedHubId = "";
        serviceMenuOpen = false;
    }

    function chooseCountry(country) {
        if (!country) return;
        if (regionKey === "alaska" || regionKey === "hawaii")
            setRegion("northAmerica");
        selectedCountryCode = country[0];
        selectedCode = "";
        selectedHubId = "";
        serviceMenuOpen = false;
    }

    function selectService(family) {
        if (Geo.serviceFamilies.indexOf(family) < 0) return;
        serviceFamily = family;
        serviceMenuOpen = false;
    }

    function cycleStatus() {
        var i=Geo.statusFilters.indexOf(statusFilter);
        statusFilter=Geo.statusFilters[(i+1)%Geo.statusFilters.length];
    }

    function zoomBy(direction,x,y) {
        applyView(Geo.zoomAt(regionKey, zoom, centerLon, centerLat,
                             x, y, mapCanvas.width, mapCanvas.height, direction));
    }

    onRegionKeyChanged: mapCanvas.requestPaint()
    onSelectedCodeChanged: mapCanvas.requestPaint()
    onSelectedCountryCodeChanged: mapCanvas.requestPaint()
    onSelectedHubIdChanged: mapCanvas.requestPaint()
    onSelectedCityChanged: mapCanvas.requestPaint()
    onShowCitiesChanged: mapCanvas.requestPaint()
    onZoomChanged: mapCanvas.requestPaint()
    onCenterLonChanged: mapCanvas.requestPaint()
    onCenterLatChanged: mapCanvas.requestPaint()
    onShowReferencePointsChanged: mapCanvas.requestPaint()

    Column {
        id: column
        anchors.fill: parent
        spacing: 8

        Row {
            id: headingRow
            width: parent.width
            height: 27
            spacing: 10

            GohuText {
                text: root.regionKey === "global" ? "COVERAGE // WORLD"
                    : root.regionKey === "northAmerica" ? "COVERAGE // NORTH AMERICA"
                    : root.regionKey === "lower48" ? "COVERAGE // USA + NEIGHBORS"
                    : root.regionKey === "alaska" ? "COVERAGE // ALASKA"
                    : "COVERAGE // HAWAII"
                font.pixelSize: root.compactLayout ? 13 : 18
                font.bold: true
                color: Colors.yellow
                anchors.verticalCenter: parent.verticalCenter
            }

            GohuText {
                text: "REFERENCE ONLY"
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.7
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Flow {
            id: regionsRow
            width: parent.width
            height: childrenRect.height
            spacing: 6

            Repeater {
                model: [
                    { id:"lower48",name:"USA + NEIGHBORS",width:144 },
                    { id:"northAmerica",name:"N. AMERICA",width:112 },
                    { id:"global",name:"GLOBAL",width:80 },
                    { id:"alaska",name:"ALASKA",width:78 },
                    { id:"hawaii",name:"HAWAII",width:78 }
                ]
                ModeButton {
                    required property var modelData
                    width: modelData.width
                    height: 33
                    textOnly: true
                    labelText: modelData.name
                    labelFontSize: 10
                    selected: root.regionKey === modelData.id
                    idlePrimaryColor: Colors.white
                    hoverPrimaryColor: Colors.blue
                    selectedPrimaryColor: Colors.blue
                    perimeterGlowColor: Colors.blue
                    bordered: false
                    onTriggered: root.setRegion(modelData.id)
                }
            }
        }

        Flow {
            id: filtersRow
            width: parent.width
            height: childrenRect.height
            spacing: 8
            z: 20

            Item {
                id: serviceSelector
                width: root.compactLayout ? 152 : 190
                height: 31

                ModeButton {
                    id: serviceButton
                    width: parent.width
                    height: parent.height
                    textOnly: true
                    labelText: "SERVICE: " + root.serviceFamily + " ▾"
                    labelFontSize: 10
                    bordered: false
                    selected: root.serviceMenuOpen
                    idlePrimaryColor: Colors.white
                    hoverPrimaryColor: Colors.yellow
                    selectedPrimaryColor: Colors.blue
                    perimeterGlowColor: Colors.blue
                    onTriggered: root.serviceMenuOpen = !root.serviceMenuOpen
                }

                Rectangle {
                    id: serviceDropdown
                    visible: root.serviceMenuOpen
                    anchors.top: serviceButton.bottom
                    anchors.topMargin: 4
                    width: serviceSelector.width
                    height: Geo.serviceFamilies.length * 31 + 8
                    color: Colors.dark
                    border.color: Colors.blue
                    border.width: 1
                    z: 30

                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 0

                        Repeater {
                            model: Geo.serviceFamilies
                            ModeButton {
                                required property string modelData
                                width: serviceSelector.width - 8
                                height: 31
                                textOnly: true
                                labelText: modelData
                                labelFontSize: 10
                                bordered: false
                                selected: root.serviceFamily === modelData
                                idlePrimaryColor: Colors.white
                                hoverPrimaryColor: Colors.blue
                                selectedPrimaryColor: Colors.yellow
                                perimeterGlowColor: Colors.blue
                                onTriggered: root.selectService(modelData)
                            }
                        }
                    }
                }
            }

            ModeButton {
                width: root.compactLayout ? 134 : 174
                height: 31
                textOnly: true
                labelText: "STATUS: " + root.statusFilter
                labelFontSize: 10
                bordered: false
                idlePrimaryColor: Colors.white
                hoverPrimaryColor: Colors.yellow
                selectedPrimaryColor: Colors.yellow
                perimeterGlowColor: Colors.blue
                onTriggered: root.cycleStatus()
            }

            ModeButton {
                width: root.compactLayout ? 94 : 108
                height: 31
                textOnly: true
                labelText: root.hubPlacementArmed ? "PICK MAP" : "+ HUB"
                labelFontSize: 10
                bordered: false
                selected: root.hubPlacementArmed
                idlePrimaryColor: Colors.white
                hoverPrimaryColor: Colors.yellow
                selectedPrimaryColor: Colors.magenta
                perimeterGlowColor: Colors.blue
                onTriggered: {
                    if (root.hubPlacementArmed) {
                        root.hubPlacementArmed = false;
                        root.hubEditorOpen = true;
                    } else root.beginHubEntry();
                }
            }

            ModeButton {
                width: 83
                height: 31
                textOnly: true
                labelText: root.showCities ? "CITIES ON" : "CITIES OFF"
                labelFontSize: 10
                bordered: false
                selected: root.showCities
                idlePrimaryColor: Colors.white
                selectedPrimaryColor: Colors.cyan
                hoverPrimaryColor: Colors.yellow
                perimeterGlowColor: Colors.blue
                onTriggered: root.showCities = !root.showCities
            }

            ModeButton {
                width: 104
                height: 31
                textOnly: true
                labelText: root.streetMode ? "STREETS ON" : "STREETS ▾"
                labelFontSize: 10
                bordered: false
                selected: root.streetMode
                idlePrimaryColor: Colors.white
                selectedPrimaryColor: Colors.cyan
                hoverPrimaryColor: Colors.yellow
                perimeterGlowColor: Colors.blue
                onTriggered: {
                    if(root.streetMode) root.streetMode=false;
                    else root.streetConsentOpen=true;
                }
            }

            // Separate-process vector atlas, never a silent map replacement.
            // The running state is owned by Quickshell Process, not by a PID
            // written to disk. No native binary is installed by this control.
            ModeButton {
                width: root.compactLayout ? 105 : 124
                height: 31
                textOnly: true
                labelText: vectorRunner.running ? "CLOSE VECTOR" : "VECTOR VIEW ▸"
                labelFontSize: 10
                bordered: false
                selected: vectorRunner.running
                idlePrimaryColor: Colors.yellow
                hoverPrimaryColor: Colors.blue
                selectedPrimaryColor: Colors.magenta
                perimeterGlowColor: Colors.blue
                onTriggered: root.openVectorChoice()
            }
        }

        Row {
            id: mapRow
            width: parent.width
            spacing: 10
            z: 0
            height: Math.max(130, column.height - headingRow.height
                - regionsRow.height - filtersRow.height - infoRow.height
                - column.spacing * 4)

            Rectangle {
                id: mapSurface
                width: parent.width - (detailPanel.visible ? detailPanel.width + mapRow.spacing : 0)
                height: mapRow.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue
                clip: true

                Canvas {
                    id: mapCanvas
                    anchors.fill: parent
                    anchors.margins: 1

                    function intersects(points, limits) {
                        var lowLon=Infinity, highLon=-Infinity;
                        var lowLat=Infinity, highLat=-Infinity;
                        for (var k=0;k<points.length;k++) {
                            var point=points[k];
                            if (point[0]<lowLon) lowLon=point[0];
                            if (point[0]>highLon) highLon=point[0];
                            if (point[1]<lowLat) lowLat=point[1];
                            if (point[1]>highLat) highLat=point[1];
                        }
                        return !(highLon<limits.west || lowLon>limits.east
                            || highLat<limits.south || lowLat>limits.north);
                    }

                    function drawLine(ctx, points, closeLine) {
                        if (!points || points.length<2) return;
                        var start=Geo.project(points[0][0],points[0][1],width,height,
                            root.regionKey,root.zoom,root.centerLon,root.centerLat);
                        ctx.beginPath();
                        ctx.moveTo(start.x,start.y);
                        for (var j=1;j<points.length;j++) {
                            var p=Geo.project(points[j][0],points[j][1],width,height,
                                root.regionKey,root.zoom,root.centerLon,root.centerLat);
                            ctx.lineTo(p.x,p.y);
                        }
                        if (closeLine) ctx.closePath();
                    }

                    onPaint: {
                        var ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        ctx.fillStyle="#16051F";
                        ctx.fillRect(0,0,width,height);

                        // Real Natural Earth geography, deliberately neutral.
                        // Only recorded company service polygons may receive
                        // active/partner/planned coverage fills in later phases.
                        var polygons=Land.polygons || [];
                        ctx.fillStyle="#251530";
                        ctx.strokeStyle="#536185";
                        ctx.lineWidth=1;
                        for (var i=0;i<polygons.length;i++) {
                            var rings=polygons[i];
                            for (var j=0;j<rings.length;j++) {
                                if (!intersects(rings[j],root.bounds)) continue;
                                drawLine(ctx,rings[j],true);
                                ctx.fill();
                                ctx.stroke();
                            }
                        }

                        ctx.strokeStyle="#467D92";
                        ctx.globalAlpha=0.65;
                        ctx.lineWidth=0.75;
                        var internal=Context.admin1Lines || [];
                        for (var a=0;a<internal.length;a++) {
                            if (!intersects(internal[a].line,root.bounds)) continue;
                            drawLine(ctx,internal[a].line,false);
                            ctx.stroke();
                        }
                        ctx.globalAlpha=1;

                        // 1:110m admin-1 lines are context, not service edges.
                        // Repaint actual lake *water* after internal borders
                        // so Michigan/Huron/Superior/Erie/Ontario do not
                        // appear as land or fill with state boundary strokes.
                        var lakes=Lakes.lakes || [];
                        ctx.fillStyle="#16051F";
                        ctx.strokeStyle="#6989AD";
                        ctx.lineWidth=1.0;
                        ctx.globalAlpha=1.0;
                        for (var lakeIndex=0;lakeIndex<lakes.length;lakeIndex++) {
                            var lake=lakes[lakeIndex];
                            for (var lakeRing=0;lakeRing<lake.rings.length;lakeRing++) {
                                if (!intersects(lake.rings[lakeRing],root.bounds)) continue;
                                drawLine(ctx,lake.rings[lakeRing],true);
                                ctx.fill();
                                ctx.stroke();
                            }
                        }

                        // Draw international boundaries over land/lake shapes,
                        // including the US/Canada and US/Mexico borders.
                        // Natural Earth admin-0 context is generalized and may
                        // include disputed borders; never an eligibility gate.
                        var borders=Context.admin0Lines || [];
                        ctx.strokeStyle="#A3BBD8";
                        ctx.lineWidth=1.1;
                        ctx.globalAlpha=0.82;
                        for (var borderIndex=0;borderIndex<borders.length;borderIndex++) {
                            if (!intersects(borders[borderIndex].line,root.bounds)) continue;
                            drawLine(ctx,borders[borderIndex].line,false);
                            ctx.stroke();
                        }
                        ctx.globalAlpha=1.0;

                        // Capital markers are *navigation anchors*, not hubs.
                        if (root.showReferencePoints) {
                            var points=Geo.visibleStates(root.regionKey,"");
                            // National perspective: show country landmarks
                            // before crowded individual state capitals.
                            if (root.regionKey==="global" && root.zoom<2)
                                points=[];
                            for (var n=0;n<points.length;n++) {
                                var row=points[n];
                                var xy=Geo.project(row[3],row[4],width,height,
                                    root.regionKey,root.zoom,root.centerLon,root.centerLat);
                                if (!xy.visible) continue;
                                var active=row[0]===root.selectedCode;
                                ctx.beginPath();
                                ctx.arc(xy.x,xy.y,active?6:2.9,0,2*Math.PI);
                                ctx.fillStyle=active?"#F2BE4E":"#DCF3FA";
                                ctx.fill();
                                ctx.strokeStyle=active?"#C74EC7":"#5B5FD4";
                                ctx.lineWidth=active?2:1;
                                ctx.stroke();
                            }

                            var countries=Geo.visibleCountries(root.regionKey,"");
                            for(var m=0;m<countries.length;m++) {
                                var country=countries[m];
                                var loc=Geo.project(country[3],country[4],width,height,
                                    root.regionKey,root.zoom,root.centerLon,root.centerLat);
                                if(!loc.visible) continue;
                                var chosen=country[0]===root.selectedCountryCode;
                                ctx.beginPath();
                                ctx.arc(loc.x,loc.y,chosen?7:4,0,2*Math.PI);
                                ctx.fillStyle=chosen?"#F2BE4E":"#55CFCA";
                                ctx.fill();
                                ctx.lineWidth=1.3;
                                ctx.strokeStyle=chosen?"#C74EC7":"#16051F";
                                ctx.stroke();
                                ctx.font="11px monospace";
                                ctx.fillStyle="#DCF3FA";
                                ctx.fillText(country[1],loc.x+8,loc.y-7);
                            }
                        }

                        // Cities are neutral public reference labels, not
                        // confirmed company locations. Budget text labels by
                        // display cell so 1,251 records do not crowd a viewport.
                        if (root.showCities) {
                            var minPopulation = root.regionKey==="global"
                                ? (root.zoom<2 ? 3200000 : 750000)
                                : root.zoom<1.8 ? 240000
                                : root.zoom<3.8 ? 85000 : 25000;
                            var cityRows=CityData.cities.slice().sort(function(a,b) {
                                return b[4]-a[4];
                            });
                            var occupied={};
                            var labelCount=0;
                            ctx.font="10px monospace";
                            for(var ci=0;ci<cityRows.length && labelCount<95;ci++) {
                                var city=cityRows[ci];
                                if(city[4]<minPopulation) continue;
                                if(city[1]<root.bounds.west || city[1]>root.bounds.east
                                    ||city[2]<root.bounds.south ||city[2]>root.bounds.north) continue;
                                var cp=Geo.project(city[1],city[2],width,height,
                                    root.regionKey,root.zoom,root.centerLon,root.centerLat);
                                if(!cp.visible) continue;
                                var cell=Math.floor(cp.x/76)+":"+Math.floor(cp.y/25);
                                if(occupied[cell]) continue;
                                occupied[cell]=true;
                                ctx.fillStyle="#8CA8B8";
                                ctx.fillRect(cp.x-1,cp.y-1,2,2);
                                ctx.fillStyle="#C7D9E6";
                                ctx.fillText(city[0],cp.x+5,cp.y-3);
                                labelCount++;
                            }
                        }

                        // Owner-entered hub claims: hollow orange map pins,
                        // explicitly distinct from geographic reference dots.
                        for(var z=0;z<root.hubRows.length;z++) {
                            var hub=root.hubRows[z];
                            if(hub.archived) continue;
                            var hp=Geo.project(hub.longitude,hub.latitude,
                                width,height,root.regionKey,root.zoom,
                                root.centerLon,root.centerLat);
                            if(!hp.visible) continue;
                            var chosenHub=hub.id===root.selectedHubId;
                            ctx.beginPath();
                            ctx.arc(hp.x,hp.y,chosenHub?8:5,0,2*Math.PI);
                            ctx.fillStyle="#16051F";
                            ctx.fill();
                            ctx.lineWidth=chosenHub?3:2;
                            ctx.strokeStyle=chosenHub?"#C74EC7":"#ED981A";
                            ctx.stroke();
                            if(chosenHub) {
                                ctx.font="11px monospace";
                                ctx.fillStyle="#F2BE4E";
                                ctx.fillText(hub.label,hp.x+10,hp.y-9);
                            }
                        }
                    }

                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    Component.onCompleted: requestPaint()
                }

                MouseArea {
                    id: mapMouse
                    anchors.fill: mapCanvas
                    z: 1
                    acceptedButtons: Qt.LeftButton
                    hoverEnabled: true
                    property real lastX: 0
                    property real lastY: 0
                    property bool dragged: false

                    onPressed: function(mouse) {
                        root.serviceMenuOpen = false;
                        lastX=mouse.x;
                        lastY=mouse.y;
                        dragged=false;
                    }

                    onPositionChanged: function(mouse) {
                        if (!(mouse.buttons & Qt.LeftButton)) return;
                        var dx=mouse.x-lastX, dy=mouse.y-lastY;
                        if (Math.abs(dx)+Math.abs(dy)>1.5) dragged=true;
                        if (dragged)
                            root.applyView(Geo.pan(root.regionKey,root.zoom,
                                root.centerLon,root.centerLat,dx,dy,
                                mapCanvas.width,mapCanvas.height));
                        lastX=mouse.x;
                        lastY=mouse.y;
                    }

                    onReleased: function(mouse) {
                        if (dragged) return;
                        if (root.hubPlacementArmed) {
                            var placed=Geo.unproject(mouse.x,mouse.y,
                                mapCanvas.width,mapCanvas.height,
                                root.regionKey,root.zoom,root.centerLon,root.centerLat);
                            if (placed) root.openHubEditor(placed.lon,placed.lat);
                            return;
                        }

                        var closestHub=null;
                        var bestHubDistance=13*13;
                        for(var h=0;h<root.hubRows.length;h++) {
                            var candidate=root.hubRows[h];
                            if(candidate.archived) continue;
                            var point=Geo.project(candidate.longitude,candidate.latitude,
                                mapCanvas.width,mapCanvas.height,root.regionKey,
                                root.zoom,root.centerLon,root.centerLat);
                            if(!point.visible) continue;
                            var dist=(point.x-mouse.x)*(point.x-mouse.x)
                                +(point.y-mouse.y)*(point.y-mouse.y);
                            if(dist<=bestHubDistance) {
                                bestHubDistance=dist;
                                closestHub=candidate;
                            }
                        }
                        if(closestHub) {
                            root.selectedHubId=closestHub.id;
                            root.selectedCode="";
                            root.selectedCountryCode="";
                            return;
                        }
                        var nearestState=Geo.nearestState(root.regionKey,mouse.x,mouse.y,
                            mapCanvas.width,mapCanvas.height,root.zoom,
                            root.centerLon,root.centerLat,13);
                        var nearestCountry=Geo.nearestCountry(root.regionKey,mouse.x,mouse.y,
                            mapCanvas.width,mapCanvas.height,root.zoom,
                            root.centerLon,root.centerLat,13);
                        if (nearestCountry && nearestState) {
                            var sp=Geo.project(nearestState[3],nearestState[4],
                                mapCanvas.width,mapCanvas.height,root.regionKey,
                                root.zoom,root.centerLon,root.centerLat);
                            var cp=Geo.project(nearestCountry[3],nearestCountry[4],
                                mapCanvas.width,mapCanvas.height,root.regionKey,
                                root.zoom,root.centerLon,root.centerLat);
                            var sd=(sp.x-mouse.x)*(sp.x-mouse.x)
                                +(sp.y-mouse.y)*(sp.y-mouse.y);
                            var cd=(cp.x-mouse.x)*(cp.x-mouse.x)
                                +(cp.y-mouse.y)*(cp.y-mouse.y);
                            if(cd<sd) root.chooseCountry(nearestCountry);
                            else root.chooseState(nearestState);
                        } else if (nearestCountry) {
                            root.chooseCountry(nearestCountry);
                        } else if (nearestState) {
                            root.chooseState(nearestState);
                        }
                    }

                    onWheel: function(wheel) {
                        if (!wheel.angleDelta.y) return;
                        root.zoomBy(wheel.angleDelta.y>0?1:-1,wheel.x,wheel.y);
                        wheel.accepted=true;
                    }
                }

                CompanyStreetMap {
                    id: streetMap
                    anchors.fill: mapCanvas
                    visible: root.streetMode
                    active: root.streetMode && root.visible
                    hubRows: root.hubRows
                    selectedHubId: root.selectedHubId
                    pickingLocation: root.hubPlacementArmed
                    z: 5
                    onLocationPicked: function(lon,lat) {
                        root.openHubEditor(lon,lat);
                    }
                    onHubPicked: function(id) {
                        root.selectedHubId=id;
                        root.selectedCode="";
                        root.selectedCountryCode="";
                        root.selectedCity=null;
                    }
                }

                Column {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 10
                    spacing: 5
                    visible: !root.streetMode
                    z: 2

                    ActionButton {
                        width: 30
                        height: 30
                        label: "+"
                        labelPixelSize: 16
                        accentColor: Colors.blue
                        onLeftClicked: root.zoomBy(1,mapCanvas.width/2,mapCanvas.height/2)
                    }
                    ActionButton {
                        width: 30
                        height: 30
                        label: "−"
                        labelPixelSize: 16
                        accentColor: Colors.blue
                        onLeftClicked: root.zoomBy(-1,mapCanvas.width/2,mapCanvas.height/2)
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    visible: !root.streetMode
                    text: root.bounds.label + "  //  " + Math.round(root.zoom*100) + "%"
                    color: Colors.white
                    font.pixelSize: 10
                }
            }

            Rectangle {
                id: detailPanel
                visible: !root.compactLayout
                width: 218
                height: mapRow.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue

                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    GohuText {
                        width: parent.width
                        text: "REFERENCE DIRECTORY"
                        font.bold: true
                        font.pixelSize: 13
                        color: Colors.yellow
                    }

                    Rectangle {
                        width: parent.width
                        height: 31
                        color: Colors.black
                        border.color: Colors.cyan
                        border.width: 1

                        TextInput {
                            id: stateSearch
                            anchors.fill: parent
                            anchors.leftMargin: 7
                            anchors.rightMargin: 5
                            verticalAlignment: TextInput.AlignVCenter
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 12
                            color: Colors.white
                            selectByMouse: true
                            clip: true
                            Keys.onEscapePressed: function(event) {
                                if (text.length) {
                                    text="";
                                    event.accepted=true;
                                }
                            }
                        }

                        GohuText {
                            visible: !stateSearch.text.length && !stateSearch.activeFocus
                            text: "FIND COUNTRY / STATE"
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.45
                        }
                    }

                    GohuText {
                        text: root.selectedHub
                              ? root.selectedHub.label
                              : root.selectedCity
                              ? root.selectedCity[0] + " // CITY REFERENCE"
                              : root.selectedCountry
                              ? root.selectedCountry[1] + " // " + root.selectedCountry[0]
                              : root.selectedState
                              ? root.selectedState[1] + " // " + root.selectedState[0]
                              : "SELECT PLACE"
                        font.bold: true
                        font.pixelSize: 12
                        color: Colors.magenta
                        width: parent.width
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text: root.selectedHub
                              ? root.selectedHub.organizationLabel + " / "
                                + root.selectedHub.city + " / "
                                + root.selectedHub.serviceFamily
                              : root.selectedCity
                              ? "PUBLIC GEOGRAPHIC REFERENCE, NOT A HUB"
                              : root.selectedCountry
                              ? "NATIONAL CAPITAL: " + root.selectedCountry[2]
                              : root.selectedState
                              ? "STATE CAPITAL: " + root.selectedState[2]
                              : "Select a marker or directory row."
                        font.pixelSize: 10
                        color: Colors.white
                        wrapMode: Text.WordWrap
                    }

                    GohuText {
                        width: parent.width
                        text: root.selectedHub
                              ? "HUB CLAIM // REPORTED, NOT VERIFIED"
                              : "SERVICE COVERAGE: UNVERIFIED"
                        font.pixelSize: 10
                        color: Colors.yellow
                        wrapMode: Text.WordWrap
                    }

                    Flickable {
                        width: parent.width
                        height: Math.max(20, detailPanel.height - 156)
                        clip: true
                        contentWidth: width
                        contentHeight: stateRows.height
                        flickableDirection: Flickable.VerticalFlick
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: stateRows
                            width: parent.width
                            spacing: 3

                            Repeater {
                                model: root.hubRows.filter(function(hub) {
                                    var q=String(stateSearch.text||"").toLowerCase();
                                    return !hub.archived && (!q
                                        || hub.label.toLowerCase().indexOf(q)>=0
                                        || hub.city.toLowerCase().indexOf(q)>=0
                                        || hub.organizationLabel.toLowerCase().indexOf(q)>=0);
                                })
                                Rectangle {
                                    id: hubRow
                                    required property var modelData
                                    width: stateRows.width
                                    height: 26
                                    color: root.selectedHubId===modelData.id
                                        ? Colors.yellow : Colors.black
                                    border.width: 1
                                    border.color: Colors.orange

                                    GohuText {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        verticalAlignment: Text.AlignVCenter
                                        text: "⌂ " + hubRow.modelData.label
                                        color: root.selectedHubId===hubRow.modelData.id
                                            ? Colors.black : Colors.orange
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            root.selectedHubId=hubRow.modelData.id;
                                            root.selectedCode="";
                                            root.selectedCountryCode="";
                                        }
                                    }
                                }
                            }

                            Repeater {
                                model: root.visibleCities()
                                Rectangle {
                                    id: cityRow
                                    required property var modelData
                                    width: stateRows.width
                                    height: 25
                                    color: root.selectedCity
                                        && root.selectedCity[0]===modelData[0]
                                        ? Colors.yellow : Colors.black
                                    border.width: 1
                                    border.color: Colors.cyan

                                    GohuText {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 10
                                        text: "• " + cityRow.modelData[0]
                                        color: root.selectedCity
                                            && root.selectedCity[0]===cityRow.modelData[0]
                                            ? Colors.black : Colors.white
                                        elide: Text.ElideRight
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.chooseCity(cityRow.modelData)
                                    }
                                }
                            }

                            Repeater {
                                model: Geo.visibleCountries(root.regionKey,stateSearch.text)
                                Rectangle {
                                    id: countryRow
                                    required property var modelData
                                    width: stateRows.width
                                    height: 25
                                    color: root.selectedCountryCode===modelData[0]
                                        ? Colors.yellow : Colors.black
                                    border.width: 1
                                    border.color: root.selectedCountryCode===modelData[0]
                                        ? Colors.magenta : Colors.blue

                                    GohuText {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 10
                                        text: modelData[0] + "  " + modelData[1]
                                        color: root.selectedCountryCode===countryRow.modelData[0]
                                            ? Colors.black : Colors.white
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.chooseCountry(countryRow.modelData)
                                    }
                                }
                            }

                            Repeater {
                                model: Geo.visibleStates(root.regionKey,stateSearch.text)
                                Rectangle {
                                    id: stateRow
                                    required property var modelData
                                    width: stateRows.width
                                    height: 25
                                    color: root.selectedCode===modelData[0]
                                        ? Colors.yellow : Colors.black
                                    border.width: 1
                                    border.color: root.selectedCode===modelData[0]
                                        ? Colors.magenta : Colors.blue

                                    GohuText {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 10
                                        text: modelData[0] + "  " + modelData[1]
                                        color: root.selectedCode===stateRow.modelData[0]
                                            ? Colors.black : Colors.white
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.chooseState(stateRow.modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Row {
            id: infoRow
            width: parent.width
            height: 50
            spacing: 10

            GohuText {
                width: parent.width
                text: root.hubPlacementArmed
                    ? "CLICK MAP TO SET HUB COORDINATES. THE FORM WILL RETURN "
                    + "WITH THE FIELDS YOU ALREADY ENTERED."
                    : (root.selectedHub ? root.selectedHub.label + " // "
                    : root.selectedCountry ? root.selectedCountry[1] + " // "
                    : root.selectedState ? root.selectedState[1] + " // "
                    : "NO PLACE SELECTED // ")
                    + root.hubRows.filter(function(h){return !h.archived;}).length
                    + " operator-reported hub(s). NO COMPANY COVERAGE VERIFIED. "
                    + "Orange pins are local claims, not confirmed operations."
                font.pixelSize: 11
                color: Colors.white
                wrapMode: Text.WordWrap
            }
        }

    }

    // Requires a separate deliberate click before requesting remote tiles.
    Rectangle {
        id: streetConsent
        anchors.centerIn: parent
        z: 65
        visible: root.streetConsentOpen
        width: Math.min(parent.width-20,500)
        height: 225
        color: Colors.black
        border.color: Colors.magenta
        border.width: 2

        Column {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 12
            GohuText {
                text: "ENABLE ONLINE STREET DETAIL?"
                font.pixelSize: 16
                font.bold: true
                color: Colors.yellow
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.white
                font.pixelSize: 12
                text: "Street tiles come from OpenStreetMap. The viewed map "
                    + "tile coordinates are sent to the provider. No hub names, "
                    + "employees, clients or organization records are sent. "
                    + "Tiles are cached locally. Internet required; no business SLA."
            }
            GohuText {
                text: "© OpenStreetMap contributors"
                color: Colors.cyan
                font.pixelSize: 11
            }
            Row {
                spacing: 10
                ModeButton {
                    width: 175
                    height: 38
                    textOnly: true
                    labelText: "ENABLE STREETS"
                    bordered: false
                    selected: true
                    onTriggered: root.startStreetView()
                }
                ModeButton {
                    width: 90
                    height: 38
                    textOnly: true
                    labelText: "CANCEL"
                    bordered: false
                    onTriggered: root.streetConsentOpen=false
                }
            }
        }
    }

    // Vector preview is a separate Qt process. Its online mode explicitly
    // discloses public viewport tile coordinates, not business hub records.
    Rectangle {
        id: vectorConsent
        anchors.centerIn: parent
        z: 66
        visible: root.vectorConsentOpen
        width: Math.min(parent.width - 20, 520)
        height: 245
        color: Colors.black
        border.color: Colors.magenta
        border.width: 2

        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10
            GohuText {
                text: "OPEN SEPARATE VECTOR MAP?"
                color: Colors.yellow
                font.bold: true
                font.pixelSize: 15
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.white
                font.pixelSize: 11
                text: "The vector renderer is a separate Qt window, not the "
                    + "Company Coverage map. It must be installed separately. "
                    + "Offline preview uses synthetic geography; Online Streets "
                    + "requests real tiles from OpenFreeMap, disclosing the viewed "
                    + "map area and IP. No Company hub, worker, or client data "
                    + "is passed to either preview."
            }
            GohuText {
                width: parent.width
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
                text: "STATUS: " + root.vectorStatus
            }
            Row {
                spacing: 7
                ModeButton {
                    width: 136
                    height: 34
                    textOnly: true
                    labelText: "OFFLINE TEST"
                    bordered: false
                    selected: false
                    onTriggered: root.launchVector(false)
                }
                ModeButton {
                    width: 148
                    height: 34
                    textOnly: true
                    labelText: "ONLINE STREETS"
                    bordered: false
                    selected: true
                    onTriggered: root.launchVector(true)
                }
                ModeButton {
                    width: 82
                    height: 34
                    textOnly: true
                    labelText: "CANCEL"
                    bordered: false
                    onTriggered: root.vectorConsentOpen=false
                }
            }
        }
    }

    // Map-picked hub editor is confined to Company Coverage; it never
    // accesses verified Identity Center membership or personal client data.
    CompanyHubEditor {
        id: hubEditor
        anchors.fill: parent
        z: 50
        visible: root.hubEditorOpen
        focus: root.hubEditorOpen
        saving: hubStore.state === "saving"
        storeState: hubStore.state
        storeError: hubStore.errorCode
        saveError: hubStore.state === "error" ? hubStore.errorCode : ""
        onPickLocationRequested: {
            root.hubEditorOpen = false;
            root.hubPlacementArmed = true;
            root.serviceMenuOpen = false;
        }
        onRetryStoreRequested: hubStore.refresh()
        onCancelRequested: {
            if (hubStore.state !== "saving")
                root.hubEditorOpen = false;
        }
        onSaveRequested: function(hub) {
            if (!hubStore.createHub(
                    hub.label, hub.organizationLabel, hub.city,
                    hub.regionCode, hub.countryCode, hub.longitude,
                    hub.latitude, hub.serviceFamily)) {
                hubEditor.localError = "DIRECTORY BUSY OR UNAVAILABLE. RELOAD REQUIRED.";
            }
        }
    }
}
