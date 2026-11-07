import QtQuick
import "../../components"
import "StationMagickTransitMultiPolicy.js" as Multi
import "StationMagickTransitEventBrowserPolicy.js" as Browser
import "StationMagickDateLocationPolicy.js" as Defaults

// M8h // Selected natal reference + up to three moving JPL body trajectories.
// Explicit SEARCH only. Filtered, chronological aspects and sampled stations.
// Sources determine positions and times, never diagrams or random artwork.
Rectangle {
    id: atlas
    color:Colors.black
    clip:true
    property var natalData:null
    property var finder:null
    property string startDate:""
    property int spanDays:7
    property int sampleMinutes:60
    property int natalIndex:0
    property var selectedBodies:["moon","mercury","venus"]
    property var selectedAspects:[0,60,90,120,180]
    property string browserKind:"ALL"
    property string browserPlanet:""
    property string browserAspect:"ALL"
    property string browserMotion:"ALL"
    property int pageIndex:0
    property string inspectedEventKey:""
    property bool descending:false
    property real zoom:1
    property real panX:0
    property string selectedEventKey:""
    signal eventRequested(string exactUtc,string body,string kind)

    readonly property string natalBody:Multi.TARGETS[natalIndex]
    readonly property bool busy:!!finder&&finder.loading
    readonly property var model:finder&&finder.ready?finder.result:null
    readonly property var geometry:Multi.graph(model,plot.width,plot.height)
    readonly property var visibleEvents:Browser.filtered(
        model,browserKind,browserPlanet,descending,browserAspect,browserMotion)
    readonly property var pageData:Browser.page(
        model,browserKind,browserPlanet,descending,
        browserAspect,browserMotion,pageIndex)
    readonly property var inspectedEvent:Browser.inspect(model,inspectedEventKey)
    readonly property bool canSearch:Multi.request(natalData,startDate,spanDays,
        natalBody,selectedBodies,selectedAspects,sampleMinutes)!==null&&!busy
    readonly property var palette:[Colors.cyan,Colors.magenta,Colors.orange]

    function invalidated(){
        selectedEventKey="";
        inspectedEventKey="";
        pageIndex=0;
        if(finder&&finder.ready)finder.clearState();
    }
    function resetBrowse(){
        pageIndex=0;
        eventScroll.contentY=0;
        plot.requestPaint();
    }
    onStartDateChanged:invalidated()
    onSpanDaysChanged:invalidated()
    onSampleMinutesChanged:invalidated()
    onNatalIndexChanged:invalidated()
    onSelectedBodiesChanged:invalidated()
    onSelectedAspectsChanged:invalidated()
    onNatalDataChanged:invalidated()
    onVisibleChanged:{
        if(visible&&startDate==="")startDate=Defaults.utcDay();
        if(!visible)dateField.releaseFocus();
    }
    function selectBody(body){
        if(busy)return;
        var existing=selectedBodies.indexOf(body);
        if(existing>=0) {
            if(selectedBodies.length===1)return;
            selectedBodies=selectedBodies.filter(function(id){return id!==body;});
        } else if(selectedBodies.length<3){
            selectedBodies=selectedBodies.concat([body]);
        }
    }
    function selectAspect(deg){
        if(busy)return;
        var existing=selectedAspects.indexOf(deg);
        if(existing>=0){
            if(selectedAspects.length===1)return;
            selectedAspects=selectedAspects.filter(function(a){return a!==deg;});
        }else selectedAspects=selectedAspects.concat([deg]);
    }
    function cycleBrowserPlanet(){
        if(!model||!model.ready)return;
        const bodies=model.series.map(function(t){return t.id;});
        const index=bodies.indexOf(browserPlanet);
        browserPlanet=index===bodies.length-1?"":bodies[index+1];
    }
    function search(){
        if(!finder||!canSearch)return;
        selectedEventKey="";
        browserPlanet="";browserKind="ALL";browserAspect="ALL";
        browserMotion="ALL";descending=false;pageIndex=0;
        inspectedEventKey="";
        finder.search(startDate,spanDays,natalBody,
            selectedBodies,selectedAspects,sampleMinutes);
    }
    function fit(){zoom=1;panX=0;}
    function clampPan(){
        const limit=Math.max(0,plot.width*(zoom-1)/2);
        panX=Math.max(-limit,Math.min(limit,panX));
    }
    function screenX(x){return (x-plot.width/2)*zoom+plot.width/2+panX;}
    function zoomAt(factor,pointer){
        if(!isFinite(factor)||factor<=0)return;
        const next=Math.max(1,Math.min(8,zoom*factor));
        const x=isFinite(pointer)?pointer:plot.width/2;
        panX=x-(x-panX-plot.width/2)*(next/zoom)-plot.width/2;
        zoom=next;clampPan();
    }
    function eventKey(e){return Browser.eventKey(e);}
    function inspectEvent(e){
        if(!model||!model.ready||!e)return;
        const key=eventKey(e);
        if(!model.events.some(function(row){return eventKey(row)===key;}))return;
        inspectedEventKey=key;
        selectedEventKey=key;
    }
    function goPage(direction){
        const next=pageData.index+direction;
        if(next<0||next>=pageData.pages)return;
        pageIndex=next;
        eventScroll.contentY=0;
    }
    function chooseEvent(e){
        if(!model||!model.ready||!e)return;
        const found=model.events.some(function(row){return eventKey(row)===eventKey(e);});
        if(!found)return;
        selectedEventKey=eventKey(e);
        eventRequested(e.utc,e.transit_body,e.type);
    }
    onModelChanged:{
        inspectedEventKey="";
        selectedEventKey="";
        pageIndex=0;
        plot.requestPaint();
    }
    onGeometryChanged:plot.requestPaint()
    onZoomChanged:plot.requestPaint()
    onPanXChanged:plot.requestPaint()
    onBrowserKindChanged:resetBrowse()
    onBrowserPlanetChanged:resetBrowse()
    onBrowserAspectChanged:resetBrowse()
    onBrowserMotionChanged:resetBrowse()
    onDescendingChanged:resetBrowse()
    onSelectedEventKeyChanged:plot.requestPaint()

    Row {
        id:header
        anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
        height:24;spacing:3
        QuietText {
            width:Math.max(25,header.width-36-36-37-67-4*header.spacing)
            height:23;color:Colors.magenta;font.pixelSize:10
            verticalAlignment:Text.AlignVCenter
            text:"MULTI // JPL EVENT ATLAS";elide:Text.ElideRight
        }
        ActionButton {
            width:36;height:23;label:"−";labelPixelSize:12
            accentColor:Colors.cyan;available:atlas.zoom>1
            onClicked:atlas.zoomAt(1/1.25,plot.width/2)
        }
        ActionButton {
            width:36;height:23;label:"+";labelPixelSize:12
            accentColor:Colors.cyan;available:atlas.zoom<8
            onClicked:atlas.zoomAt(1.25,plot.width/2)
        }
        ActionButton {
            width:37;height:23;label:"FIT";labelPixelSize:8
            accentColor:Colors.orange;onClicked:atlas.fit()
        }
        ActionButton {
            width:67;height:23
            label:atlas.busy?"WAIT":"SEARCH"
            labelPixelSize:9;accentColor:Colors.magenta
            available:atlas.canSearch;onClicked:atlas.search()
        }
    }
    Row {
        id:range
        anchors.top:header.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:26;spacing:3
        StationMagickUtcDateField {
            id:dateField
            width:Math.max(80,(range.width-59-26*2-3*range.spacing)*.62)
            height:26
            canEdit:!atlas.busy
            dateValue:atlas.startDate
            onDateEdited:function(date){atlas.startDate=date;}
        }
        ActionButton {
            width:26;height:25;label:"◀";labelPixelSize:9
            accentColor:Colors.yellow;available:!atlas.busy
            onClicked:atlas.natalIndex=(atlas.natalIndex+9)%10
        }
        QuietText {
            width:Math.max(24,range.width-dateField.width-26*2-59-4*range.spacing)
            height:25;font.pixelSize:9;color:Colors.yellow
            verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
            text:"N:"+Multi.shortLabel(atlas.natalBody)
        }
        ActionButton {
            width:26;height:25;label:"▶";labelPixelSize:9
            accentColor:Colors.yellow;available:!atlas.busy
            onClicked:atlas.natalIndex=(atlas.natalIndex+1)%10
        }
        ActionButton {
            width:59;height:25
            label:atlas.sampleMinutes+" MIN";labelPixelSize:8
            accentColor:Colors.cyan;available:!atlas.busy
            onClicked:atlas.sampleMinutes=atlas.sampleMinutes===60?30:60
        }
    }
    Row {
        id:spanRow
        anchors.top:range.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:23;spacing:3
        Repeater {
            model:[1,7,14,31]
            delegate:ActionButton {
                required property var modelData
                width:Math.max(26,(spanRow.width-3*spanRow.spacing)/4)
                height:23;label:modelData+"D";labelPixelSize:8
                selected:atlas.spanDays===modelData
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!atlas.busy
                onClicked:atlas.spanDays=modelData
            }
        }
    }
    Row {
        id:bodyRow
        anchors.top:spanRow.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:24;spacing:2
        Repeater {
            model:Multi.TARGETS
            delegate:ActionButton {
                required property var modelData
                width:Math.max(22,(bodyRow.width-9*bodyRow.spacing)/10)
                height:23;label:Multi.shortLabel(modelData);labelPixelSize:7
                selected:atlas.selectedBodies.indexOf(modelData)>=0
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!atlas.busy&&(
                    selected||atlas.selectedBodies.length<3)
                onClicked:atlas.selectBody(modelData)
            }
        }
    }
    Row {
        id:aspectRow
        anchors.top:bodyRow.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.topMargin:2;height:23;spacing:3
        Repeater {
            model:[{deg:0,label:"CONJ"},{deg:60,label:"SEXT"},
                {deg:90,label:"SQR"},{deg:120,label:"TRIN"},
                {deg:180,label:"OPP"}]
            delegate:ActionButton {
                required property var modelData
                width:Math.max(24,(aspectRow.width-4*aspectRow.spacing)/5)
                height:23;label:modelData.label;labelPixelSize:8
                selected:atlas.selectedAspects.indexOf(modelData.deg)>=0
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!atlas.busy
                onClicked:atlas.selectAspect(modelData.deg)
            }
        }
    }
    QuietText {
        id:status
        anchors.top:aspectRow.bottom
        anchors.left:parent.left;anchors.right:parent.right
        height:17;font.pixelSize:9
        color:atlas.model?Colors.cyan:Colors.orange
        elide:Text.ElideRight
        text:atlas.model
            ?"JPL "+atlas.model.series.length+" BODIES / "+
              atlas.model.events.length+" EVENTS / "+
              atlas.model.sample_count+" SAMPLES EACH"
            :atlas.finder?atlas.finder.statusText:
              "SOURCE-BOUND CALCULATION REQUIRED"
    }
    Canvas {
        id:plot
        anchors.top:status.bottom
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:eventHeader.top
        anchors.bottomMargin:2
        clip:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            ctx.lineWidth=1;ctx.strokeStyle=String(Colors.blue);
            ctx.strokeRect(6,5,Math.max(2,width-12),Math.max(2,height-10));
            const g=atlas.geometry;
            ctx.textAlign="center";ctx.font="9px monospace";
            if(!g||!g.lines.length){
                ctx.fillStyle=String(Colors.orange);
                ctx.fillText("SELECT PLANETS / FILTERS / SEARCH JPL",
                    width/2,height/2);
                return;
            }
            for(let i=0;i<g.lines.length;i++){
                const line=g.lines[i];
                ctx.beginPath();
                line.points.forEach(function(p,j){
                    const x=atlas.screenX(p.x);
                    if(j===0)ctx.moveTo(x,p.y);else ctx.lineTo(x,p.y);
                });
                ctx.strokeStyle=String(atlas.palette[i%atlas.palette.length]);
                ctx.lineWidth=2;ctx.stroke();
            }
            const selected=atlas.visibleEvents;
            const shown={};
            selected.forEach(function(e){
                shown[atlas.eventKey(e)]=true;
            });
            g.events.forEach(function(e){
                const row=atlas.model.events.find(function(x){
                    return x.utc===e.utc&&x.transit_body===e.body&&x.type===e.type;
                });
                if(!row||!shown[atlas.eventKey(row)])return;
                const x=atlas.screenX(e.x);
                if(x<0||x>width)return;
                const active=atlas.selectedEventKey===atlas.eventKey(row);
                ctx.beginPath();ctx.moveTo(x,6);ctx.lineTo(x,height-6);
                ctx.lineWidth=active?2:1;
                ctx.strokeStyle=String(active?Colors.magenta:
                    e.type==="station"?Colors.orange:Colors.yellow);
                ctx.stroke();
            });
            ctx.font="8px monospace";ctx.textAlign="left";
            ctx.fillStyle=String(Colors.yellow);
            ctx.fillText(g.high.toFixed(1)+"°",9,13);
            ctx.fillText(g.low.toFixed(1)+"°",9,height-8);
        }
        MouseArea {
            id:touch
            anchors.fill:parent;hoverEnabled:true
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real firstX:0
            property real lastX:0
            property bool dragged:false
            onPressed:function(mouse){
                firstX=lastX=mouse.x;dragged=false;
            }
            onPositionChanged:function(mouse){
                if(!pressed)return;
                if(Math.abs(mouse.x-firstX)>5)dragged=true;
                if(dragged){
                    atlas.panX+=mouse.x-lastX;atlas.clampPan();
                }
                lastX=mouse.x;
            }
            onWheel:function(wheel){
                if(!wheel.angleDelta.y)return;
                atlas.zoomAt(wheel.angleDelta.y>0?1.2:1/1.2,wheel.x);
                wheel.accepted=true;
            }
            onDoubleClicked:atlas.fit()
            onClicked:function(mouse){
                if(dragged||!atlas.model||!atlas.geometry)return;
                var nearest=null,dist=12;
                atlas.visibleEvents.forEach(function(e){
                    const point=atlas.geometry.events.find(function(x){
                        return x.utc===e.utc&&x.body===e.transit_body&&
                               x.type===e.type;
                    });
                    if(!point)return;
                    const d=Math.abs(atlas.screenX(point.x)-mouse.x);
                    if(d<dist){dist=d;nearest=e;}
                });
                if(nearest)atlas.chooseEvent(nearest);
            }
        }
    }
    Row {
        id:advancedFilters
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:eventHeader.top
        height:23;spacing:3
        ActionButton {
            width:Math.max(50,(advancedFilters.width-85-2*advancedFilters.spacing)/2)
            height:22;label:"ASPECT "+atlas.browserAspect.toUpperCase()
            labelPixelSize:8;accentColor:Colors.yellow
            available:!!atlas.model
            onClicked:atlas.browserAspect=Browser.nextOption(
                Browser.ASPECTS,atlas.browserAspect)
        }
        ActionButton {
            width:Math.max(50,(advancedFilters.width-85-2*advancedFilters.spacing)/2)
            height:22;label:"MOTION "+atlas.browserMotion.toUpperCase()
            labelPixelSize:8;accentColor:Colors.cyan
            available:!!atlas.model
            onClicked:atlas.browserMotion=Browser.nextOption(
                Browser.MOTIONS,atlas.browserMotion)
        }
        QuietText {
            width:85;height:22;font.pixelSize:8
            color:Colors.magenta
            verticalAlignment:Text.AlignVCenter
            text:atlas.pageData.total+" / "+(atlas.model?atlas.model.events.length:0)
        }
    }
    Row {
        id:eventHeader
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:eventPanel.top
        height:24;spacing:3
        ActionButton {
            width:Math.max(36,(eventHeader.width-132-3*eventHeader.spacing)*.28)
            height:23;label:"ALL";labelPixelSize:8
            accentColor:atlas.browserKind==="ALL"?Colors.magenta:Colors.cyan
            selected:atlas.browserKind==="ALL"
            onClicked:atlas.browserKind="ALL"
        }
        ActionButton {
            width:Math.max(36,(eventHeader.width-132-3*eventHeader.spacing)*.36)
            height:23;label:"ASPECT";labelPixelSize:8
            accentColor:atlas.browserKind==="aspect"?Colors.magenta:Colors.cyan
            selected:atlas.browserKind==="aspect"
            onClicked:atlas.browserKind="aspect"
        }
        ActionButton {
            width:Math.max(36,(eventHeader.width-132-3*eventHeader.spacing)*.36)
            height:23;label:"STATION";labelPixelSize:8
            accentColor:atlas.browserKind==="station"?Colors.magenta:Colors.cyan
            selected:atlas.browserKind==="station"
            onClicked:atlas.browserKind="station"
        }
        ActionButton {
            width:77;height:23
            label:atlas.browserPlanet?Multi.shortLabel(atlas.browserPlanet):"ALL BODIES"
            labelPixelSize:8
            accentColor:Colors.yellow
            available:!!atlas.model
            onClicked:atlas.cycleBrowserPlanet()
        }
        ActionButton {
            width:55;height:23
            label:atlas.descending?"NEW→OLD":"OLD→NEW"
            labelPixelSize:7
            accentColor:Colors.cyan
            onClicked:atlas.descending=!atlas.descending
        }
    }
    Rectangle {
        id:eventPanel
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:inspector.top
        height:Math.max(54,Math.min(138,parent.height*.27))
        border.width:1;border.color:Colors.blue
        color:Colors.black;clip:true
        Row {
            id:pageControls
            anchors.top:parent.top
            anchors.left:parent.left;anchors.right:parent.right
            anchors.margins:2;height:22;spacing:3
            QuietText {
                width:Math.max(50,pageControls.width-94-2*pageControls.spacing)
                height:22;font.pixelSize:9;color:Colors.cyan
                verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight
                text:atlas.pageData.first+"-"+atlas.pageData.last+
                    " / "+atlas.pageData.total+
                    "   PAGE "+(atlas.pageData.index+1)+"/"+atlas.pageData.pages
            }
            ActionButton {
                width:47;height:22;label:"PREV";labelPixelSize:8
                accentColor:Colors.cyan
                available:atlas.pageData.index>0
                onClicked:atlas.goPage(-1)
            }
            ActionButton {
                width:47;height:22;label:"NEXT";labelPixelSize:8
                accentColor:Colors.cyan
                available:atlas.pageData.index+1<atlas.pageData.pages
                onClicked:atlas.goPage(1)
            }
        }
        Flickable {
            id:eventScroll
            anchors.top:pageControls.bottom
            anchors.bottom:parent.bottom
            anchors.left:parent.left;anchors.right:parent.right
            anchors.margins:2
            contentWidth:width
            contentHeight:eventRows.implicitHeight
            boundsBehavior:Flickable.StopAtBounds;clip:true
            Column {
                id:eventRows
                width:eventScroll.width;spacing:2
                Repeater {
                    model:atlas.pageData.items
                    delegate:Rectangle {
                        required property var modelData
                        width:eventRows.width;height:22
                        readonly property bool selected:
                            atlas.selectedEventKey===atlas.eventKey(modelData)
                        color:selected?Colors.dark:Colors.black
                        border.width:1
                        border.color:selected?Colors.magenta:Colors.blue
                        QuietText {
                            anchors.left:parent.left
                            anchors.right:inspectButton.left
                            anchors.top:parent.top;anchors.bottom:parent.bottom
                            anchors.margins:3
                            color:modelData.type==="station"?Colors.orange:Colors.yellow
                            font.pixelSize:9;verticalAlignment:Text.AlignVCenter
                            elide:Text.ElideRight
                            text:modelData.utc+" / "+
                                Multi.shortLabel(modelData.transit_body)+" / "+
                                (modelData.type==="station"
                                  ? "STATION → "+modelData.direction.toUpperCase()
                                  : modelData.aspect.toUpperCase()+" "+
                                     modelData.degrees+"° "+
                                     modelData.direction.toUpperCase()+
                                     " ERR "+modelData.residual_deg.toFixed(5)+"°")
                        }
                        MouseArea {
                            anchors.top:parent.top;anchors.bottom:parent.bottom
                            anchors.left:parent.left;anchors.right:inspectButton.left
                            cursorShape:Qt.PointingHandCursor
                            onClicked:atlas.chooseEvent(modelData)
                        }
                        ActionButton {
                            id:inspectButton
                            anchors.right:parent.right
                            width:42;height:21
                            label:"INFO";labelPixelSize:8
                            accentColor:Colors.magenta
                            selected:atlas.inspectedEventKey===atlas.eventKey(modelData)
                            onClicked:atlas.inspectEvent(modelData)
                        }
                    }
                }
                QuietText {
                    visible:!!atlas.model&&atlas.pageData.total===0
                    width:eventRows.width;height:22
                    color:Colors.cyan;font.pixelSize:9
                    text:"NO MATCHING EVENTS IN SELECTED FILTERS"
                }
            }
        }
    }
    Rectangle {
        id:inspector
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:footer.top
        height:visible?41:0
        visible:!!atlas.inspectedEvent
        color:Colors.dark
        border.width:1;border.color:Colors.magenta
        clip:true
        QuietText {
            anchors.left:parent.left;anchors.right:parent.right
            anchors.top:parent.top;anchors.topMargin:3
            anchors.leftMargin:5;anchors.rightMargin:5
            height:17;font.pixelSize:9;color:Colors.magenta
            elide:Text.ElideRight
            text:!atlas.inspectedEvent?""
                :atlas.inspectedEvent.utc+" / "+
                 Multi.shortLabel(atlas.inspectedEvent.planet)+" / "+
                 (atlas.inspectedEvent.type==="station"
                     ?"STATION "+atlas.inspectedEvent.direction.toUpperCase()
                     :atlas.inspectedEvent.aspect.toUpperCase()+" "+
                        atlas.inspectedEvent.angle_deg+"°")
        }
        QuietText {
            anchors.left:parent.left;anchors.right:parent.right
            anchors.bottom:parent.bottom;anchors.bottomMargin:3
            anchors.leftMargin:5;anchors.rightMargin:5
            height:16;font.pixelSize:8;color:Colors.yellow
            elide:Text.ElideRight
            text:!atlas.inspectedEvent?""
                :atlas.inspectedEvent.type==="station"
                    ?"LONG "+atlas.inspectedEvent.longitude_deg.toFixed(4)+"°"+
                     " / RATE "+atlas.inspectedEvent.velocity_deg_day.toFixed(5)+
                     "°/DAY / NUMERICAL BRACKET ≤60S"
                    :"ANGLE RESIDUAL "+atlas.inspectedEvent.residual_deg.toFixed(6)+
                     "° / NUMERICAL BRACKET ≤1S"
        }
    }
    QuietText {
        id:footer
        anchors.left:parent.left;anchors.right:parent.right
        anchors.bottom:parent.bottom;height:17
        font.pixelSize:8;color:Colors.orange;elide:Text.ElideRight
        text:atlas.selectedEventKey
            ?"SOURCE EVENT TIME RETAINED / WHEEL NEAREST UTC MINUTE"
            :"STATION SPEED ESTIMATED / GRAZING CONTACTS NOT GUARANTEED"
    }
}
