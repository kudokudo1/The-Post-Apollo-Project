import QtQuick
import "../../components"
import "StationMagickTransitTimelinePolicy.js" as Timeline
import "StationMagickNatalWheelPolicy.js" as Natal
import "StationMagickDateLocationPolicy.js" as Defaults

// M8g // Actual M8f JPL samples and crossing events. Display-only unless
// user explicitly selects a contact, which opens the existing transit chart
// at the NEAREST MINUTE, preserving the original precise event timestamp.
Rectangle {
    id: timeline
    color: Colors.black
    clip: true
    property var natalData: null
    property var finder: null
    property string startDate: ""
    property int spanDays: 7
    property int sampleMinutes: 60
    property int natalIndex: 0
    property int transitIndex: 1
    property real zoom: 1
    property real panX: 0
    property string selectedContactUtc: ""
    signal contactRequested(string exactUtc)
    readonly property bool natalReady: Natal.validate(natalData).ready
    readonly property string natalBody: Timeline.TARGETS[natalIndex]
    readonly property string transitBody: Timeline.TARGETS[transitIndex]
    readonly property bool busy: !!finder&&finder.loading
    readonly property var model:finder&&finder.ready?finder.result:null
    readonly property var geometry:Timeline.plot(model,curve.width,curve.height)
    readonly property bool validSearch: Timeline.request(
        natalData,startDate,spanDays,natalBody,transitBody,sampleMinutes)!==null

    function setTarget(which,direction){
        if(busy)return;
        if(which==="natal")
            natalIndex=(natalIndex+direction+Timeline.TARGETS.length)%
                Timeline.TARGETS.length;
        else transitIndex=(transitIndex+direction+Timeline.TARGETS.length)%
                Timeline.TARGETS.length;
    }
    function search(){
        if(!validSearch||!finder||busy)return;
        selectedContactUtc="";
        finder.search(startDate,spanDays,natalBody,transitBody,sampleMinutes);
    }
    function fit(){zoom=1;panX=0;}
    function zoomAt(factor,x) {
        const next=Math.max(1,Math.min(8,zoom*factor));
        const anchor=Number.isFinite(x)?x:curve.width/2;
        panX=anchor-(anchor-panX-curve.width/2)*(next/zoom)-curve.width/2;
        zoom=next;
        clampPan();
    }
    function clampPan(){
        const limit=Math.max(0,curve.width*(zoom-1)/2);
        panX=Math.max(-limit,Math.min(limit,panX));
    }
    function screenX(value){
        return (value-curve.width/2)*zoom+curve.width/2+panX;
    }
    function chooseEvent(utc){
        if(!model||!model.ready)return;
        const selected=model.contacts.find(function(e){return e.utc===utc;});
        if(!selected)return;
        selectedContactUtc=utc;
        contactRequested(utc);
    }
    onVisibleChanged:{
        if(visible){
            if(!startDate)startDate=Defaults.utcDay();
        }else{
            // The source service remains session-only while TRANSITS is open;
            // this view's selectors can be revisited without losing results.
            startField.releaseFocus();
        }
    }
    onNatalDataChanged:{
        selectedContactUtc="";
        if(visible&&!startDate)startDate=Defaults.utcDay();
    }
    onModelChanged:curve.requestPaint()
    onZoomChanged:curve.requestPaint()
    onPanXChanged:curve.requestPaint()
    onWidthChanged:curve.requestPaint()
    onHeightChanged:curve.requestPaint()

    Row {
        id:header
        anchors.top:parent.top
        anchors.left:parent.left
        anchors.right:parent.right
        height:24
        spacing:3
        QuietText {
            width:Math.max(25,header.width-36-36-38-68-4*header.spacing)
            height:24;color:Colors.magenta
            font.pixelSize:10
            verticalAlignment:Text.AlignVCenter
            elide:Text.ElideRight
            text:"TRANSIT TIMELINE // EXACT CROSSINGS"
        }
        ActionButton {
            width:36;height:23;label:"−";labelPixelSize:11
            accentColor:Colors.cyan;available:timeline.zoom>1
            onClicked:timeline.zoomAt(1/1.25,curve.width/2)
        }
        ActionButton {
            width:36;height:23;label:"+";labelPixelSize:11
            accentColor:Colors.cyan;available:timeline.zoom<8
            onClicked:timeline.zoomAt(1.25,curve.width/2)
        }
        ActionButton {
            width:38;height:23;label:"FIT";labelPixelSize:8
            accentColor:Colors.orange
            onClicked:timeline.fit()
        }
        ActionButton {
            width:68;height:23;label:timeline.busy?"WAIT":"SEARCH"
            labelPixelSize:9
            accentColor:Colors.magenta
            available:timeline.validSearch&&!timeline.busy
            onClicked:timeline.search()
        }
    }
    Row {
        id: pairRow
        anchors.top:header.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.topMargin:2
        height:24
        spacing:3
        ActionButton {
            width:26;height:23;label:"◀";labelPixelSize:9
            accentColor:Colors.yellow;available:!timeline.busy
            onClicked:timeline.setTarget("natal",-1)
        }
        QuietText {
            width:Math.max(26,(pairRow.width-4*26-5*pairRow.spacing)/2)
            height:23;verticalAlignment:Text.AlignVCenter
            color:Colors.yellow;font.pixelSize:9
            elide:Text.ElideRight
            text:"NATAL "+timeline.natalBody.toUpperCase()
        }
        ActionButton {
            width:26;height:23;label:"▶";labelPixelSize:9
            accentColor:Colors.yellow;available:!timeline.busy
            onClicked:timeline.setTarget("natal",1)
        }
        ActionButton {
            width:26;height:23;label:"◀";labelPixelSize:9
            accentColor:Colors.cyan;available:!timeline.busy
            onClicked:timeline.setTarget("transit",-1)
        }
        QuietText {
            width:Math.max(26,(pairRow.width-4*26-5*pairRow.spacing)/2)
            height:23;verticalAlignment:Text.AlignVCenter
            color:Colors.cyan;font.pixelSize:9
            elide:Text.ElideRight
            text:"TRANSIT "+timeline.transitBody.toUpperCase()
        }
        ActionButton {
            width:26;height:23;label:"▶";labelPixelSize:9
            accentColor:Colors.cyan;available:!timeline.busy
            onClicked:timeline.setTarget("transit",1)
        }
    }
    StationMagickUtcDateField {
        id:startField
        anchors.top:pairRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.topMargin:2
        height:26
        dateValue:timeline.startDate
        canEdit:!timeline.busy
        onDateEdited:function(date){timeline.startDate=date;}
    }
    Row {
        id:spanRow
        anchors.top:startField.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.topMargin:2
        height:24;spacing:3
        Repeater {
            model:[1,7,14,31]
            delegate:ActionButton {
                required property var modelData
                width:Math.max(20,(spanRow.width-5*spanRow.spacing-59)/4)
                height:23
                label:modelData+" DAYS"
                labelPixelSize:8
                selected:timeline.spanDays===modelData
                accentColor:selected?Colors.magenta:Colors.cyan
                available:!timeline.busy
                onClicked:timeline.spanDays=modelData
            }
        }
        ActionButton {
            width:59;height:23
            label:timeline.sampleMinutes+" MIN"
            labelPixelSize:8;accentColor:Colors.yellow
            available:!timeline.busy
            onClicked:timeline.sampleMinutes=timeline.sampleMinutes===60?30:60
        }
    }
    QuietText {
        id:stateText
        anchors.top:spanRow.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:17;font.pixelSize:9
        color:timeline.model?Colors.cyan:Colors.orange
        elide:Text.ElideRight
        text:timeline.model
            ?"SOURCE JPL / "+timeline.model.sample_count+" SAMPLES / "+
                timeline.model.contacts.length+" CROSSINGS"
            :timeline.finder?timeline.finder.statusText
            :"CALCULATE NATAL CHART BEFORE SEARCH"
    }
    Canvas {
        id:curve
        anchors.top:stateText.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:contactPanel.top
        anchors.bottomMargin:2
        clip:true
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            const ctx=getContext("2d");
            ctx.clearRect(0,0,width,height);
            const g=timeline.geometry;
            ctx.strokeStyle=String(Colors.blue);
            ctx.lineWidth=1;
            ctx.strokeRect(6,5,Math.max(2,width-12),Math.max(2,height-10));
            ctx.font="9px monospace";ctx.textAlign="center";
            if(!g||!g.points.length){
                ctx.fillStyle=String(Colors.orange);
                ctx.fillText("SELECT NATAL + TRANSIT / SEARCH JPL",width/2,height/2);
                return;
            }
            ctx.beginPath();
            g.points.forEach(function(p,i){
                const x=timeline.screenX(p.x);
                if(i===0)ctx.moveTo(x,p.y);
                else ctx.lineTo(x,p.y);
            });
            ctx.lineWidth=2;ctx.strokeStyle=String(Colors.cyan);
            ctx.stroke();
            g.events.forEach(function(e,i){
                const x=timeline.screenX(e.x);
                if(x<0||x>width)return;
                ctx.beginPath();
                ctx.moveTo(x,6);
                ctx.lineTo(x,height-6);
                ctx.lineWidth=e.utc===timeline.selectedContactUtc?2.5:1;
                ctx.strokeStyle=String(e.utc===timeline.selectedContactUtc
                    ?Colors.magenta:Colors.yellow);
                ctx.stroke();
            });
            ctx.fillStyle=String(Colors.yellow);
            ctx.font="8px monospace";ctx.textAlign="left";
            ctx.fillText(g.max.toFixed(1)+"°",8,12);
            ctx.fillText(g.min.toFixed(1)+"°",8,height-8);
        }
        MouseArea {
            id:graphTouch
            anchors.fill:parent
            hoverEnabled:true
            cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            property real lastX:0
            property real startX:0
            property bool moved:false
            onPressed:function(mouse){startX=lastX=mouse.x;moved=false;}
            onPositionChanged:function(mouse){
                if(!pressed)return;
                if(Math.abs(mouse.x-startX)>5)moved=true;
                if(moved){
                    timeline.panX+=mouse.x-lastX;
                    timeline.clampPan();
                }
                lastX=mouse.x;
            }
            onWheel:function(wheel){
                if(!wheel.angleDelta.y)return;
                timeline.zoomAt(wheel.angleDelta.y>0?1.2:1/1.2,wheel.x);
                wheel.accepted=true;
            }
            onDoubleClicked:timeline.fit()
            onClicked:function(mouse){
                if(moved||!timeline.model||!timeline.geometry)return;
                let nearest="",distance=13;
                timeline.geometry.events.forEach(function(e){
                    const d=Math.abs(timeline.screenX(e.x)-mouse.x);
                    if(d<distance){nearest=e.utc;distance=d;}
                });
                if(nearest)timeline.chooseEvent(nearest);
            }
        }
    }
    Rectangle {
        id:contactPanel
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.bottom:foot.top
        height:Math.max(52,Math.min(116,parent.height*.29))
        color:Colors.black
        border.width:1
        border.color:Colors.blue
        clip:true
        Flickable {
            id:scroll
            anchors.fill:parent
            anchors.margins:2
            contentWidth:width
            contentHeight:items.implicitHeight
            clip:true
            boundsBehavior:Flickable.StopAtBounds
            Column {
                id:items
                width:scroll.width
                spacing:2
                Repeater {
                    model:timeline.model?timeline.model.contacts:[]
                    delegate:Rectangle {
                        required property var modelData
                        width:items.width;height:21
                        color:timeline.selectedContactUtc===modelData.utc?
                            Colors.dark:Colors.black
                        border.width:1
                        border.color:timeline.selectedContactUtc===modelData.utc?
                            Colors.magenta:Colors.blue
                        QuietText {
                            anchors.fill:parent
                            anchors.margins:3
                            font.pixelSize:9
                            color:Colors.yellow
                            elide:Text.ElideRight
                            verticalAlignment:Text.AlignVCenter
                            text:modelData.utc+" / "+modelData.aspect.toUpperCase()+
                                " "+modelData.degrees+"° / "+
                                modelData.direction.toUpperCase()+
                                " / ERR "+modelData.residual_deg.toFixed(5)+"°"
                        }
                        MouseArea {
                            anchors.fill:parent
                            cursorShape:Qt.PointingHandCursor
                            onClicked:timeline.chooseEvent(modelData.utc)
                        }
                    }
                }
                QuietText {
                    visible:!!timeline.model&&timeline.model.contacts.length===0
                    width:items.width;height:22
                    color:Colors.cyan;font.pixelSize:9
                    text:"NO DETECTED CROSSINGS IN SELECTED RANGE"
                }
            }
        }
    }
    QuietText {
        id:foot
        anchors.bottom:parent.bottom
        anchors.left:parent.left
        anchors.right:parent.right
        height:17;font.pixelSize:8
        color:Colors.orange
        elide:Text.ElideRight
        text:timeline.selectedContactUtc
            ?"EXACT "+timeline.selectedContactUtc+" / WHEEL NEAREST UTC MINUTE"
            :"CROSSING SEARCH ONLY / STATIONARY GRAZING EVENTS MAY BE MISSED"
    }
}
