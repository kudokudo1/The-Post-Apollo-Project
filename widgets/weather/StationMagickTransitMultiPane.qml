import QtQuick
import "../../components"
import "StationMagickTransitMultiPolicy.js" as Multi
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
    property bool descending:false
    property real zoom:1
    property real panX:0
    property string selectedEventKey:""
    signal eventRequested(string exactUtc,string body,string kind)

    readonly property string natalBody:Multi.TARGETS[natalIndex]
    readonly property bool busy:!!finder&&finder.loading
    readonly property var model:finder&&finder.ready?finder.result:null
    readonly property var geometry:Multi.graph(model,plot.width,plot.height)
    readonly property var visibleEvents:Multi.browserEvents(
        model,browserKind,browserPlanet,descending)
    readonly property bool canSearch:Multi.request(natalData,startDate,spanDays,
        natalBody,selectedBodies,selectedAspects,sampleMinutes)!==null&&!busy
    readonly property var palette:[Colors.cyan,Colors.magenta,Colors.orange]

    function invalidated(){
        selectedEventKey="";
        if(finder&&finder.ready)finder.clearState();
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
        browserPlanet="";browserKind="ALL";descending=false;
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
    function eventKey(e){
        return e.utc+"|"+e.transit_body+"|"+e.type+"|"+e.aspect;
    }
    function chooseEvent(e){
        if(!model||!model.ready||!e)return;
        const found=model.events.some(function(row){return eventKey(row)===eventKey(e);});
        if(!found)return;
        selectedEventKey=eventKey(e);
        eventRequested(e.utc,e.transit_body,e.type);
    }
    onModelChanged:plot.requestPaint()
    onGeometryChanged:plot.requestPaint()
    onZoomChanged:plot.requestPaint()
    onPanXChanged:plot.requestPaint()
    onBrowserKindChanged:plot.requestPaint()
    onBrowserPlanetChanged:plot.requestPaint()
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
        anchors.bottom:footer.top
        height:Math.max(52,Math.min(118,parent.height*.26))
        border.width:1;border.color:Colors.blue
        color:Colors.black;clip:true
        Flickable {
            id:eventScroll
            anchors.fill:parent;anchors.margins:2
            contentWidth:width
            contentHeight:eventRows.implicitHeight
            boundsBehavior:Flickable.StopAtBounds;clip:true
            Column {
                id:eventRows
                width:eventScroll.width;spacing:2
                Repeater {
                    model:atlas.visibleEvents
                    delegate:Rectangle {
                        required property var modelData
                        width:eventRows.width;height:22
                        readonly property bool selected:
                            atlas.selectedEventKey===atlas.eventKey(modelData)
                        color:selected?Colors.dark:Colors.black
                        border.width:1
                        border.color:selected?Colors.magenta:Colors.blue
                        QuietText {
                            anchors.fill:parent;anchors.margins:3
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
                            anchors.fill:parent
                            cursorShape:Qt.PointingHandCursor
                            onClicked:atlas.chooseEvent(modelData)
                        }
                    }
                }
                QuietText {
                    visible:!!atlas.model&&atlas.visibleEvents.length===0
                    width:eventRows.width;height:22
                    color:Colors.cyan;font.pixelSize:9
                    text:"NO MATCHING EVENTS IN SELECTED FILTERS"
                }
            }
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
