import QtQuick
import "../../components"
import "StationMagickTransitMatrixPolicy.js" as Matrix
import "StationMagickTransitMatrixVisualPolicy.js" as Visual
import "StationMagickDateLocationPolicy.js" as Defaults

// M8k // Source-verified natal x moving-body pair counts and UTC events.
// Uses existing TASKS date spinboxes and Post-Apollo ActionButtons.
// No new provider, saved birth records, station duplication or implied GPS.
Rectangle {
    id:atlas
    color:Colors.black
    clip:true
    property var natalData:null
    property var finder:null
    property string startDate:""
    property int spanDays:7
    property int sampleMinutes:60
    property var natalBodies:["sun","venus"]
    property var transitBodies:["moon","mercury"]
    property var aspectAngles:[0,60,90,120,180]
    property string filterNatal:""
    property string filterTransit:""
    property string filterKind:"ALL"
    property int pageIndex:0
    property string selectedEventKey:""
    property bool inspectorOpen:false
    property string inspectedEventKey:""
    property real detailZoom:1
    signal eventRequested(string exactUtc,string natalBody,
                          string transitBody,string kind)
    readonly property bool busy:!!finder&&finder.loading
    readonly property var model:finder&&finder.ready?finder.result:null
    readonly property var eventPage:Matrix.page(
        model,filterNatal,filterTransit,filterKind,false,pageIndex)
    readonly property var timelineEvents:Matrix.filtered(
        model,filterNatal,filterTransit,filterKind,false)
    readonly property var timelineModel:Visual.timeline(
        model,timelineEvents,eventAxis.width,eventAxis.height)
    readonly property var inspectedEvent:Visual.inspect(model,inspectedEventKey)
    readonly property var detailGeometry:Visual.trajectory(
        model,inspectedEvent,detailCanvas.width,detailCanvas.height,detailZoom)
    readonly property var workload:Matrix.budget(
        spanDays,natalBodies.length,transitBodies.length,sampleMinutes)
    readonly property int suggestedSpan:Matrix.fittingSpan(
        spanDays,natalBodies.length,transitBodies.length,sampleMinutes)
    readonly property bool canSearch:!busy&&Matrix.request(
        natalData,startDate,spanDays,natalBodies,
        transitBodies,aspectAngles,sampleMinutes)!==null

    function invalidate(){
        selectedEventKey="";filterNatal="";filterTransit="";pageIndex=0;
        inspectedEventKey="";inspectorOpen=false;detailZoom=1;
        if(finder&&finder.ready)finder.clearState();
    }
    function resetFilterPage(){
        pageIndex=0;
        resultList.contentY=0;
        if(inspectorOpen)closeInspector();
        eventAxis.requestPaint();
    }
    function cellTier(natal,moving){
        const item=Visual.cell(model,natal,moving);
        return item?item.tier:0;
    }
    function cellFill(natal,moving){
        const tier=cellTier(natal,moving);
        return tier===3?Qt.rgba(Colors.orange.r,Colors.orange.g,Colors.orange.b,.26)
            :tier===2?Qt.rgba(Colors.yellow.r,Colors.yellow.g,Colors.yellow.b,.21)
            :tier===1?Qt.rgba(Colors.cyan.r,Colors.cyan.g,Colors.cyan.b,.15)
            :Colors.black;
    }
    function cellAccent(natal,moving){
        const tier=cellTier(natal,moving);
        return tier===3?Colors.orange:tier===2?Colors.yellow:
            tier===1?Colors.cyan:Colors.blue;
    }
    function inspectEvent(event){
        if(!model||!event)return;
        const key=Visual.eventKey(event);
        if(!model.events.some(function(row){return Visual.eventKey(row)===key;}))
            return;
        inspectedEventKey=key;
        detailZoom=1;
        inspectorOpen=true;
    }
    function closeInspector(){
        inspectorOpen=false;
        detailZoom=1;
    }
    onStartDateChanged:invalidate()
    onSpanDaysChanged:invalidate()
    onSampleMinutesChanged:invalidate()
    onNatalBodiesChanged:invalidate()
    onTransitBodiesChanged:invalidate()
    onAspectAnglesChanged:invalidate()
    onNatalDataChanged:invalidate()
    onFilterNatalChanged:resetFilterPage()
    onFilterTransitChanged:resetFilterPage()
    onFilterKindChanged:resetFilterPage()
    onModelChanged:{
        filterNatal="";filterTransit="";filterKind="ALL";
        pageIndex=0;selectedEventKey="";
        inspectedEventKey="";inspectorOpen=false;detailZoom=1;
        eventAxis.requestPaint();
    }
    onTimelineModelChanged:eventAxis.requestPaint()
    onDetailGeometryChanged:detailCanvas.requestPaint()
    onDetailZoomChanged:detailCanvas.requestPaint()
    onInspectedEventChanged:detailCanvas.requestPaint()
    onVisibleChanged:{
        if(visible&&!startDate)startDate=Defaults.utcDay();
        if(!visible)dateField.releaseFocus();
    }
    function toggleBody(natal,id){
        if(busy)return;
        const current=natal?natalBodies:transitBodies;
        const ix=current.indexOf(id);
        if(ix>=0){
            if(current.length===1)return;
            const updated=current.filter(function(x){return x!==id;});
            if(natal)natalBodies=updated;else transitBodies=updated;
        }else if(current.length<4){
            const updated=current.concat([id]);
            if(natal)natalBodies=updated;else transitBodies=updated;
        }
    }
    function toggleAspect(deg){
        if(busy)return;
        const ix=aspectAngles.indexOf(deg);
        if(ix>=0){
            if(aspectAngles.length===1)return;
            aspectAngles=aspectAngles.filter(function(x){return x!==deg;});
        }else aspectAngles=aspectAngles.concat([deg]);
    }
    function search(){
        if(!finder||!canSearch)return;
        selectedEventKey="";filterNatal="";filterTransit="";
        filterKind="ALL";pageIndex=0;
        inspectedEventKey="";inspectorOpen=false;detailZoom=1;
        finder.search(startDate,spanDays,natalBodies,
                      transitBodies,aspectAngles,sampleMinutes);
    }
    function countFor(natal,moving){
        if(!model)return "--";
        const match=model.matrix.find(function(c){
            return c.natal_body===natal&&c.transit_body===moving;
        });
        return match?String(match.aspect_count):"--";
    }
    function selectPair(natal,moving){
        if(!model)return;
        if(filterNatal===natal&&filterTransit===moving){
            filterNatal="";filterTransit="";
        }else{
            filterNatal=natal;filterTransit=moving;
        }
    }
    function changePage(step){
        const next=eventPage.index+step;
        if(next<0||next>=eventPage.pages)return;
        pageIndex=next;
        resultList.contentY=0;
    }
    function chooseEvent(event){
        if(!model||!event)return;
        const key=Matrix.eventKey(event);
        if(!model.events.some(function(row){return Matrix.eventKey(row)===key;}))
            return;
        const reference=event.natal_body||model.natal_bodies[0];
        if(!reference)return;
        selectedEventKey=key;
        eventRequested(event.utc,reference,event.transit_body,event.type);
    }

    Row {
        id:header
        anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
        height:25;spacing:3
        QuietText {
            width:Math.max(30,header.width-71-header.spacing)
            height:25
            color:Colors.magenta;font.pixelSize:10
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:"NATAL × TRANSIT // JPL PAIR MATRIX"
        }
        ActionButton {
            width:71;height:24
            label:atlas.busy?"WAIT":"SEARCH"
            labelPixelSize:9;accentColor:Colors.magenta
            available:atlas.canSearch
            onClicked:atlas.search()
        }
    }
    Row {
        id:dateRow
        anchors.top:header.bottom;anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:26;spacing:3
        StationMagickUtcDateField {
            id:dateField
            width:Math.max(120,dateRow.width-111-2*dateRow.spacing)
            height:26
            dateValue:atlas.startDate
            canEdit:!atlas.busy
            onDateEdited:function(day){atlas.startDate=day;}
        }
        ActionButton {
            width:54;height:25
            label:atlas.sampleMinutes+" MIN"
            labelPixelSize:8;accentColor:Colors.yellow
            available:!atlas.busy
            onClicked:atlas.sampleMinutes=atlas.sampleMinutes===60?30:60
        }
        ActionButton {
            width:57;height:25
            label:atlas.spanDays+" DAYS"
            labelPixelSize:8;accentColor:Colors.cyan
            available:!atlas.busy
            onClicked:{
                const spans=Matrix.SPANS;
                atlas.spanDays=spans[(spans.indexOf(atlas.spanDays)+1)%spans.length];
            }
        }
    }
    Row {
        id:natalRow
        anchors.top:dateRow.bottom;anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:23;spacing:2
        Repeater {
            model:Matrix.TARGETS
            delegate:ActionButton {
                required property var modelData
                width:Math.max(20,(natalRow.width-9*natalRow.spacing)/10)
                height:23;label:Matrix.shortName(modelData);labelPixelSize:7
                selected:atlas.natalBodies.indexOf(modelData)>=0
                accentColor:selected?Colors.magenta:Colors.yellow
                available:!atlas.busy&&(selected||atlas.natalBodies.length<4)
                onClicked:atlas.toggleBody(true,modelData)
            }
        }
    }
    Row {
        id:movingRow
        anchors.top:natalRow.bottom;anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:23;spacing:2
        Repeater {
            model:Matrix.TARGETS
            delegate:ActionButton {
                required property var modelData
                width:Math.max(20,(movingRow.width-9*movingRow.spacing)/10)
                height:23;label:Matrix.shortName(modelData);labelPixelSize:7
                selected:atlas.transitBodies.indexOf(modelData)>=0
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!atlas.busy&&(selected||atlas.transitBodies.length<4)
                onClicked:atlas.toggleBody(false,modelData)
            }
        }
    }
    Row {
        id:aspectRow
        anchors.top:movingRow.bottom;anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:23;spacing:3
        Repeater {
            model:[{angle:0,label:"CONJ"},{angle:60,label:"SEXT"},
                {angle:90,label:"SQR"},{angle:120,label:"TRIN"},
                {angle:180,label:"OPP"}]
            delegate:ActionButton {
                required property var modelData
                width:Math.max(24,(aspectRow.width-4*aspectRow.spacing)/5)
                height:23;label:modelData.label;labelPixelSize:8
                selected:atlas.aspectAngles.indexOf(modelData.angle)>=0
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!atlas.busy
                onClicked:atlas.toggleAspect(modelData.angle)
            }
        }
    }
    QuietText {
        id:status
        anchors.top:aspectRow.bottom;anchors.left:parent.left;anchors.right:parent.right
        height:17;font.pixelSize:8;elide:Text.ElideRight
        color:atlas.canSearch||atlas.model?Colors.cyan:Colors.orange
        text:atlas.model
            ?atlas.model.natal_bodies.length+" NATAL × "+
             atlas.model.transit_bodies.length+" MOVING / "+
             atlas.model.events.length+" SOURCE EVENTS"
            :atlas.finder&&atlas.finder.loading?atlas.finder.statusText
            :atlas.canSearch?"SOURCE-READY / EXPLICIT SEARCH"
            :atlas.workload.valid?"VERIFY NATAL OR UTC DATE"
            :"EXCEEDS SOURCE BUDGET / SELECT FIT RANGE"
    }
    Row {
        id:budgetRow
        anchors.top:status.bottom
        anchors.left:parent.left;anchors.right:parent.right
        height:23;spacing:3
        QuietText {
            width:Math.max(40,budgetRow.width-87-budgetRow.spacing)
            height:23;font.pixelSize:9
            verticalAlignment:Text.AlignVCenter
            elide:Text.ElideRight
            color:atlas.workload.valid?Colors.cyan:Colors.orange
            text:atlas.workload.pairs+" PAIRS / "+
                atlas.workload.pairSamples+"/"+atlas.workload.pairLimit+
                " SAMPLES / STATIONS "+
                atlas.workload.stationSamples+"/"+atlas.workload.stationLimit
        }
        ActionButton {
            width:87;height:22
            label:atlas.workload.valid?"IN BUDGET":
                atlas.suggestedSpan>0?"FIT "+atlas.suggestedSpan+"D":"TOO MANY"
            labelPixelSize:8
            accentColor:atlas.workload.valid?Colors.cyan:Colors.orange
            available:!atlas.busy&&!atlas.workload.valid&&
                      atlas.suggestedSpan>0
            onClicked:atlas.spanDays=atlas.suggestedSpan
        }
    }
    Rectangle {
        id:cellGrid
        anchors.top:budgetRow.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:browserBar.top
        anchors.bottomMargin:2
        color:Colors.black;border.width:1;border.color:Colors.blue
        clip:true
        Flickable {
            id:matrixScroll
            anchors.fill:parent;anchors.margins:2
            contentWidth:width
            contentHeight:matrixColumn.implicitHeight
            clip:true;boundsBehavior:Flickable.StopAtBounds
            Column {
                id:matrixColumn
                width:matrixScroll.width
                spacing:2
            Row {
                width:parent.width;height:19;spacing:2
                QuietText {
                    width:56;height:19;font.pixelSize:8;color:Colors.yellow
                    text:"NATAL / T"
                    verticalAlignment:Text.AlignVCenter
                }
                Repeater {
                    model:atlas.transitBodies
                    delegate:QuietText {
                        required property var modelData
                        width:Math.max(20,(cellGrid.width-64-
                                2*(atlas.transitBodies.length-1))/
                                atlas.transitBodies.length)
                        height:19;font.pixelSize:9;color:Colors.cyan
                        horizontalAlignment:Text.AlignHCenter
                        verticalAlignment:Text.AlignVCenter
                        text:Matrix.shortName(modelData)
                    }
                }
            }
            Repeater {
                model:atlas.natalBodies
                delegate:Row {
                    required property var modelData
                    width:parent.width;height:25;spacing:2
                    QuietText {
                        width:56;height:25;font.pixelSize:9
                        color:Colors.yellow;verticalAlignment:Text.AlignVCenter
                        text:Matrix.shortName(modelData)
                    }
                    Repeater {
                        model:atlas.transitBodies
                        delegate:ActionButton {
                            required property var modelData
                            width:Math.max(20,(cellGrid.width-64-
                                2*(atlas.transitBodies.length-1))/
                                atlas.transitBodies.length)
                            height:24
                            label:atlas.countFor(parent.modelData,modelData)
                            labelPixelSize:10
                            selected:atlas.filterNatal===parent.modelData &&
                                atlas.filterTransit===modelData
                            accentColor:atlas.cellAccent(parent.modelData,modelData)
                            idleFillColor:atlas.cellFill(parent.modelData,modelData)
                            idleBorderColor:atlas.cellAccent(parent.modelData,modelData)
                            idleForegroundColor:atlas.cellTier(parent.modelData,modelData)
                                >0?Colors.white:Colors.cyan
                            selectedFillColor:Colors.magenta
                            selectedForegroundColor:Colors.black
                            contentGlowEnabled:false
                            softGlowEnabled:false
                            available:!!atlas.model
                            onClicked:atlas.selectPair(parent.modelData,modelData)
                        }
                    }
                }
            }
            QuietText {
                width:parent.width;height:15;font.pixelSize:8
                color:Colors.orange;elide:Text.ElideRight
                text:"COUNT HEAT // 0 NONE · 1-2 CYAN · 3-4 YELLOW · 5+ ORANGE"
            }
            Canvas {
                id:eventAxis
                width:parent.width
                height:80
                clip:true
                onWidthChanged:requestPaint()
                onHeightChanged:requestPaint()
                onPaint:{
                    const ctx=getContext("2d");
                    ctx.clearRect(0,0,width,height);
                    ctx.fillStyle=String(Colors.black);
                    ctx.fillRect(0,0,width,height);
                    ctx.strokeStyle=String(Colors.blue);
                    ctx.lineWidth=1;
                    ctx.strokeRect(1,1,Math.max(2,width-2),Math.max(2,height-2));
                    const g=atlas.timelineModel;
                    ctx.textAlign="center";ctx.font="9px monospace";
                    if(!g){
                        ctx.fillStyle=String(Colors.orange);
                        ctx.fillText("SEARCH JPL TO DRAW UTC EVENTS",width/2,height/2);
                        return;
                    }
                    g.ticks.forEach(function(t){
                        ctx.strokeStyle=String(Colors.blue);
                        ctx.beginPath();ctx.moveTo(t.x,17);
                        ctx.lineTo(t.x,height-3);ctx.stroke();
                        ctx.fillStyle=String(Colors.cyan);
                        ctx.fillText(t.label,t.x,11);
                    });
                    g.markers.forEach(function(mark){
                        const active=atlas.inspectedEventKey===mark.key;
                        ctx.fillStyle=String(active?Colors.magenta:
                            mark.type==="station"?Colors.orange:Colors.yellow);
                        if(mark.type==="station"){
                            ctx.beginPath();ctx.arc(mark.x,mark.y,active?5:3,0,2*Math.PI);
                            ctx.fill();
                        }else{
                            ctx.fillRect(mark.x-(active?3:2),
                                mark.y-(active?7:5),active?6:4,active?14:10);
                        }
                    });
                    if(g.markers.length===0){
                        ctx.fillStyle=String(Colors.orange);
                        ctx.fillText("NO SOURCE EVENTS FOR SELECTED FILTER",
                            width/2,height/2);
                    }
                }
                MouseArea {
                    anchors.fill:parent
                    cursorShape:Qt.PointingHandCursor
                    onClicked:function(mouse){
                        const g=atlas.timelineModel;
                        if(!g||!atlas.model)return;
                        let nearest=null,dist=13;
                        g.markers.forEach(function(mark){
                            const dx=mark.x-mouse.x,dy=mark.y-mouse.y;
                            const d=Math.sqrt(dx*dx+dy*dy);
                            if(d<dist){nearest=mark;dist=d;}
                        });
                        if(!nearest)return;
                        const source=atlas.model.events.find(function(event){
                            return Visual.eventKey(event)===nearest.key;
                        });
                        if(source)atlas.inspectEvent(source);
                    }
                }
            }
            QuietText {
                width:parent.width;height:13
                font.pixelSize:8;color:Colors.cyan;elide:Text.ElideRight
                text:"UTC EVENT LANES // GOLD ASPECT · ORANGE STATION · CLICK TO INSPECT"
            }
            }
        }
    }
    Row {
        id:browserBar
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:resultPanel.top;height:23;spacing:3
        ActionButton {
            width:52;height:22;label:atlas.filterKind;labelPixelSize:8
            accentColor:Colors.yellow
            onClicked:{
                const kinds=["ALL","aspect","station"];
                atlas.filterKind=kinds[(kinds.indexOf(atlas.filterKind)+1)%3];
            }
        }
        ActionButton {
            width:57;height:22;label:"CLEAR";labelPixelSize:8
            accentColor:Colors.cyan
            available:atlas.filterNatal!==""||atlas.filterTransit!==""
            onClicked:{atlas.filterNatal="";atlas.filterTransit="";}
        }
        QuietText {
            width:Math.max(20,browserBar.width-52-57-90-3*browserBar.spacing)
            height:22;font.pixelSize:8;color:Colors.magenta
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:atlas.filterNatal
                ?Matrix.shortName(atlas.filterNatal)+" × "+
                    Matrix.shortName(atlas.filterTransit)
                :"ALL PAIRS + MOVING STATIONS"
        }
        ActionButton {
            width:43;height:22;label:"PREV";labelPixelSize:8
            accentColor:Colors.cyan;available:atlas.eventPage.index>0
            onClicked:atlas.changePage(-1)
        }
        ActionButton {
            width:44;height:22;label:"NEXT";labelPixelSize:8
            accentColor:Colors.cyan
            available:atlas.eventPage.index+1<atlas.eventPage.pages
            onClicked:atlas.changePage(1)
        }
    }
    Rectangle {
        id:resultPanel
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:footer.top
        height:Math.max(53,Math.min(125,parent.height*.27))
        color:Colors.black;border.width:1;border.color:Colors.blue
        clip:true
        QuietText {
            id:rangeText
            anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
            height:17;font.pixelSize:8;color:Colors.cyan
            text:"EVENTS "+atlas.eventPage.first+"-"+atlas.eventPage.last+
                " / "+atlas.eventPage.total+" / PAGE "+
                (atlas.eventPage.index+1)+"/"+atlas.eventPage.pages
        }
        Flickable {
            id:resultList
            anchors.top:rangeText.bottom;anchors.bottom:parent.bottom
            anchors.left:parent.left;anchors.right:parent.right
            contentWidth:width;contentHeight:resultRows.implicitHeight
            boundsBehavior:Flickable.StopAtBounds;clip:true
            Column {
                id:resultRows
                width:resultList.width;spacing:2
                Repeater {
                    model:atlas.eventPage.items
                    delegate:Rectangle {
                        required property var modelData
                        width:resultRows.width;height:22
                        color:atlas.selectedEventKey===Matrix.eventKey(modelData)
                            ?Colors.dark:Colors.black
                        border.width:1
                        border.color:atlas.selectedEventKey===Matrix.eventKey(modelData)
                            ?Colors.magenta:Colors.blue
                        QuietText {
                            anchors.left:parent.left
                            anchors.right:inspectButton.left
                            anchors.top:parent.top;anchors.bottom:parent.bottom
                            anchors.margins:3
                            color:modelData.type==="station"?Colors.orange:Colors.yellow
                            font.pixelSize:9;verticalAlignment:Text.AlignVCenter
                            elide:Text.ElideRight
                            text:modelData.utc+" / "+
                                (modelData.natal_body
                                 ?Matrix.shortName(modelData.natal_body)+" × ":"")+
                                Matrix.shortName(modelData.transit_body)+" / "+
                                (modelData.type==="station"
                                 ?"STATION "+modelData.direction.toUpperCase()
                                 :modelData.aspect.toUpperCase()+
                                    " "+modelData.degrees+"°")
                        }
                        MouseArea {
                            anchors.left:parent.left
                            anchors.right:inspectButton.left
                            anchors.top:parent.top;anchors.bottom:parent.bottom
                            cursorShape:Qt.PointingHandCursor
                            onClicked:atlas.chooseEvent(modelData)
                        }
                        ActionButton {
                            id:inspectButton
                            anchors.right:parent.right
                            width:48;height:21
                            label:"INFO";labelPixelSize:8
                            accentColor:Colors.magenta
                            selected:atlas.inspectedEventKey===
                                Visual.eventKey(modelData)&&atlas.inspectorOpen
                            onClicked:atlas.inspectEvent(modelData)
                        }
                    }
                }
                QuietText {
                    visible:!!atlas.model&&atlas.eventPage.total===0
                    width:resultRows.width;height:22
                    text:"NO SOURCE MATCHES FOR THIS PAIR / FILTER"
                    color:Colors.cyan;font.pixelSize:9
                }
            }
        }
    }
    Rectangle {
        id:inspectorPanel
        visible:atlas.inspectorOpen&&!!atlas.inspectedEvent
        z:12
        anchors.top:cellGrid.top
        anchors.bottom:footer.top
        anchors.left:parent.left;anchors.right:parent.right
        clip:true
        color:Colors.dark
        border.width:2;border.color:Colors.magenta
        Row {
            id:inspectorHeader
            anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
            anchors.margins:5;height:25;spacing:4
            QuietText {
                width:Math.max(40,inspectorHeader.width-150-2*inspectorHeader.spacing)
                height:25
                color:Colors.magenta;font.pixelSize:11
                verticalAlignment:Text.AlignVCenter
                elide:Text.ElideRight
                text:atlas.inspectedEvent?
                    "SOURCE EVENT // "+
                    Matrix.shortName(atlas.inspectedEvent.transit_body):
                    "SOURCE EVENT"
            }
            ActionButton {
                width:72;height:24
                label:"WHEEL";labelPixelSize:9
                accentColor:Colors.yellow
                available:!!atlas.inspectedEvent
                onClicked:{
                    if(!atlas.inspectedEvent||!atlas.model)return;
                    const e=atlas.model.events.find(function(row){
                        return Visual.eventKey(row)===atlas.inspectedEventKey;
                    });
                    if(e)atlas.chooseEvent(e);
                }
            }
            ActionButton {
                width:74;height:24
                label:"CLOSE";labelPixelSize:9
                accentColor:Colors.magenta
                onClicked:atlas.closeInspector()
            }
        }
        QuietText {
            id:inspectorTime
            anchors.left:parent.left;anchors.right:parent.right
            anchors.top:inspectorHeader.bottom
            anchors.leftMargin:7;anchors.rightMargin:7
            height:22;font.pixelSize:11;color:Colors.cyan
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:atlas.inspectedEvent?
                atlas.inspectedEvent.utc+" UTC / "+
                (atlas.inspectedEvent.natal_body?
                    Matrix.shortName(atlas.inspectedEvent.natal_body)+" × ":"")+
                Matrix.shortName(atlas.inspectedEvent.transit_body):
                ""
        }
        QuietText {
            id:inspectorEvidence
            anchors.left:parent.left;anchors.right:parent.right
            anchors.top:inspectorTime.bottom
            anchors.leftMargin:7;anchors.rightMargin:7
            height:23;font.pixelSize:10;color:Colors.yellow
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:!atlas.inspectedEvent?""
                :atlas.inspectedEvent.type==="station"
                    ?"ESTIMATED "+atlas.inspectedEvent.direction.toUpperCase()+
                     " STATION / "+atlas.inspectedEvent.longitude_deg.toFixed(4)+
                     "° / RATE "+atlas.inspectedEvent.velocity_deg_day.toFixed(5)+"°/D"
                    :atlas.inspectedEvent.aspect.toUpperCase()+" "+
                     atlas.inspectedEvent.angle_deg+"° / "+
                     atlas.inspectedEvent.direction.toUpperCase()+
                     " / RESIDUAL "+atlas.inspectedEvent.residual_deg.toFixed(6)+"°"
        }
        Row {
            id:detailControls
            anchors.top:inspectorEvidence.bottom
            anchors.left:parent.left;anchors.right:parent.right
            anchors.leftMargin:6;anchors.rightMargin:6
            height:24;spacing:4
            QuietText {
                width:Math.max(30,detailControls.width-150-2*detailControls.spacing)
                height:24;font.pixelSize:9;color:Colors.orange
                verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
                text:"JPL-SAMPLED ECLIPTIC LONGITUDE"
            }
            ActionButton {
                width:46;height:23;label:"−";labelPixelSize:12
                accentColor:Colors.cyan;available:atlas.detailZoom>1
                onClicked:atlas.detailZoom=Math.max(1,atlas.detailZoom/1.5)
            }
            ActionButton {
                width:46;height:23;label:"+";labelPixelSize:12
                accentColor:Colors.cyan;available:atlas.detailZoom<8
                onClicked:atlas.detailZoom=Math.min(8,atlas.detailZoom*1.5)
            }
            ActionButton {
                width:50;height:23;label:"FIT";labelPixelSize:8
                accentColor:Colors.yellow
                onClicked:atlas.detailZoom=1
            }
        }
        Canvas {
            id:detailCanvas
            anchors.left:parent.left;anchors.right:parent.right
            anchors.top:detailControls.bottom
            anchors.bottom:detailFooter.top
            anchors.margins:7
            clip:true
            onWidthChanged:requestPaint()
            onHeightChanged:requestPaint()
            onPaint:{
                const ctx=getContext("2d");
                ctx.clearRect(0,0,width,height);
                ctx.strokeStyle=String(Colors.blue);ctx.lineWidth=1;
                ctx.strokeRect(1,1,Math.max(2,width-2),Math.max(2,height-2));
                const g=atlas.detailGeometry;
                if(!g){
                    ctx.fillStyle=String(Colors.orange);
                    ctx.font="9px monospace";ctx.textAlign="center";
                    ctx.fillText("NO VERIFIED JPL SAMPLES",width/2,height/2);
                    return;
                }
                if(g.referenceY!==null){
                    ctx.strokeStyle=String(Colors.yellow);
                    ctx.setLineDash([4,4]);
                    ctx.beginPath();ctx.moveTo(0,g.referenceY);
                    ctx.lineTo(width,g.referenceY);ctx.stroke();
                    ctx.setLineDash([]);
                }
                ctx.strokeStyle=String(Colors.cyan);
                ctx.lineWidth=2;
                ctx.beginPath();
                g.points.forEach(function(p,i){
                    if(i===0)ctx.moveTo(p.x,p.y);
                    else ctx.lineTo(p.x,p.y);
                });
                ctx.stroke();
                ctx.strokeStyle=String(Colors.magenta);
                ctx.lineWidth=1;
                ctx.beginPath();ctx.moveTo(g.eventX,3);
                ctx.lineTo(g.eventX,height-3);ctx.stroke();
                ctx.fillStyle=String(Colors.yellow);
                ctx.font="9px monospace";ctx.textAlign="left";
                ctx.fillText(g.max.toFixed(2)+"°",5,12);
                ctx.fillText(g.min.toFixed(2)+"°",5,height-6);
            }
        }
        QuietText {
            id:detailFooter
            anchors.left:parent.left;anchors.right:parent.right
            anchors.bottom:parent.bottom
            anchors.leftMargin:7;anchors.rightMargin:7
            height:25;font.pixelSize:9;color:Colors.orange
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:atlas.inspectedEvent
                ?"NUMERICAL BRACKET ≤"+
                 atlas.inspectedEvent.numerical_bracket_seconds+
                 "S / WHEEL NEAREST UTC MINUTE / NOT OBSERVATIONAL ACCURACY"
                :"SOURCE-VERIFIED EVENT REQUIRED"
        }
    }
    QuietText {
        id:footer
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:parent.bottom;height:17;font.pixelSize:8
        color:Colors.orange;elide:Text.ElideRight
        text:"STATION = MOVING ONLY / WHEEL USES FIRST NATAL REFERENCE"
    }
}
