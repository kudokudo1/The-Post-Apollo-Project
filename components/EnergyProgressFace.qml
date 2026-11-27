import QtQuick
import "EnergyProgressMotion.js" as Motion
import "EnergyVariantProfile.js" as Profiles
import "EnergyFireMaterial.js" as Material
import "EnergyBeamFlow.js" as Flow
import "EnergyPixelFire.js" as PixelFire

// Opt-in presentation only. No input handling or service calls.
// The owner supplies phase and, for measured/timed modes, actual progress.
Item {
    id: root
    property string variant: "omnitrix" // default | omnitrix | tron | ki-blast | flamethrower
    // Three retained fire treatments; existing hosts default to standard.
    property string fireMode: "standard" // standard | ash-trail | burn-away
    property bool remainingAsh: false // opt-in staged combustion material
    readonly property bool materialExperiment: variant === "flamethrower"
        && (fireMode === "ash-trail" || fireMode === "burn-away")
    property real materialPeak: 0
    property string phase: "idle" // idle | queued | running | ready | success | failure
    property string progressMode: "indeterminate" // indeterminate | measured | timed
    property real progress: 0
    property string caption: ""
    property bool reducedMotion: false
    // Opt-in suspension when the owner has no fresh process evidence.
    // Preserve elapsed visual position; a quiet child is not a failed child.
    property bool activityMotionEnabled: true
    property color energyColor: (variant === "omnitrix" || variant === "default") ? Colors.omnitrix
        : variant === "tron" ? Colors.cyan
        : variant === "flamethrower" ? Colors.orange : "#55CFFF"
    property color chassisColor: phase === "failure" ? Colors.red : energyColor
    property color foregroundColor: Colors.white
    readonly property var personality: Profiles.profile(variant)
    readonly property var localVibration: Profiles.barMotion(variant, elapsed, visualFrame.intensity,
        reducedMotion || !visible || !activityMotionEnabled || phase !== "running")
    readonly property real displayedFraction: materialExperiment && progressMode === "indeterminate"
        ? Math.max(materialPeak, visualFrame.fraction) : visualFrame.fraction
    readonly property var track: Flow.trackGeometry(width,height,displayedFraction)
    readonly property real fillGap: track.gap
    readonly property real headCenterX: track.front
    readonly property real headCenterY: height / 2
    readonly property var fireState: PixelFire.extinguish(phase,elapsed,reducedMotion,fireMode)
    readonly property bool animationActive: visible && !reducedMotion && activityMotionEnabled
        && (phase === "running" || (phase === "success" && (variant==="flamethrower"?(fireState.active || fireState.repairing):elapsed<.84))
            || (variant==="flamethrower" && phase==="failure" && finishFrom>0 && fireState.active)
            || (variant==="ki-blast" && phase==="failure" && elapsed<1.08))
    property real speedLevel: 0
    property real speedFraction: 0
    property real speedTime: 0
    property real flameSpeed: 0
    readonly property var flameMotion: PixelFire.lightMotion(elapsed,flameSpeed,reducedMotion)
    readonly property var flamePixels: variant==="flamethrower" && fireState.active
        ? PixelFire.fire(height,elapsed,reducedMotion,fireMode,flameSpeed) : null
    readonly property real flameTipOffset: flamePixels && flamePixels.cells.length
        ? (Math.max(...flamePixels.cells.map(cell=>cell.x))+1)*flamePixels.unit*fireState.scale : 0
    readonly property real flameRearOffset: flamePixels && flamePixels.cells.length
        ? Math.max(0,-Math.min(...flamePixels.cells.map(cell=>cell.x)))*flamePixels.unit*fireState.scale : 0
    property real elapsed: 0
    property double startedAt: 0
    property real finishFrom: 0
    property bool initialized: false
    readonly property var visualFrame: Motion.frame(phase, progressMode, progress,
        elapsed, finishFrom, reducedMotion, variant)
    implicitWidth: 150
    implicitHeight: 34

    function beginPhase() {
        // Capture the last rendered fraction, never a guessed success.
        finishFrom = lastFraction;
        if (phase === "running" || phase === "idle" || phase === "queued") materialPeak = 0;
        elapsed = 0;
        startedAt = Date.now();
        lastFraction = Motion.frame(phase, progressMode, progress, elapsed, finishFrom, reducedMotion, variant).fraction;
        if (materialExperiment && phase==="running" && progressMode==="indeterminate") materialPeak=lastFraction;
        speedLevel=0;
        if(phase!=="success") flameSpeed=0;
        speedFraction=lastFraction;
        speedTime=elapsed;
        surface.requestPaint();
    }
    property real lastFraction: 0
    Component.onCompleted: {
        initialized = true;
        beginPhase();
    }
    onPhaseChanged: if (initialized) beginPhase()
    onVisibleChanged: {
        if (initialized && visible) {
            if (animationActive) elapsed = Math.max(0, (Date.now()-startedAt)/1000);
            speedLevel=0;
            flameSpeed=0;
            speedFraction=displayedFraction;
            speedTime=elapsed;
            surface.requestPaint();
        }
    }
    onVisualFrameChanged: {
        if (initialized) {
            // Phase changes may reevaluate bindings before the handler.
            // Only capture running frames on explicit ticks/progress changes.
            surface.requestPaint();
        }
    }
    onProgressChanged: if (initialized && phase === "running") {
        const next=Motion.frame(phase, progressMode, progress, elapsed, finishFrom, reducedMotion, variant).fraction;
        if (materialExperiment && progressMode === "indeterminate") {
            materialPeak=Math.max(materialPeak,next);
            lastFraction=materialPeak;
        } else lastFraction=next;
    }
    onActivityMotionEnabledChanged: if (initialized) {
        if (activityMotionEnabled) startedAt = Date.now() - elapsed * 1000;
        surface.requestPaint();
    }
    onReducedMotionChanged: if (initialized && variant==="flamethrower") {
        flameSpeed=0;
        speedFraction=displayedFraction;
        speedTime=elapsed;
        surface.requestPaint();
    }
    onEnergyColorChanged: if (initialized) surface.requestPaint()
    onChassisColorChanged: if (initialized) surface.requestPaint()
    onVariantChanged: if (initialized) surface.requestPaint()
    onFireModeChanged: {
        materialPeak = 0;
        if (initialized) surface.requestPaint();
    }
    Timer {
        interval: 33
        repeat: true
        running: root.animationActive
        onTriggered: {
            root.elapsed = Math.max(0, (Date.now()-root.startedAt)/1000);
            if (root.phase === "running") {
                const next=Motion.frame(root.phase, root.progressMode, root.progress,
                    root.elapsed, root.finishFrom, root.reducedMotion, root.variant).fraction;
                if(root.variant==="tron") {
                    root.speedLevel=Flow.speedSample(root.speedFraction,next,
                        root.elapsed-root.speedTime,root.speedLevel);
                    root.speedFraction=next;
                    root.speedTime=root.elapsed;
                    surface.requestPaint();
                }
                if (root.materialExperiment && root.progressMode === "indeterminate")
                    root.materialPeak=Math.max(root.materialPeak,next);
                root.lastFraction=root.materialExperiment && root.progressMode === "indeterminate"
                    ? root.materialPeak : next;
            }
            // Sample the rendered front (including retained material extent),
            // not a synthetic time curve. Completion movement uses it too.
            if(root.variant==="flamethrower") {
                const front=root.displayedFraction;
                root.flameSpeed=PixelFire.velocity(root.speedFraction,front,
                    root.elapsed-root.speedTime,root.track.width,root.height,root.flameSpeed);
                root.speedFraction=front;
                root.speedTime=root.elapsed;
                surface.requestPaint();
            }
        }
    }

    // Only the painted chassis moves. Host hit targets and layout stay fixed.
    Item {
        id: visual
        anchors.fill: parent
        transform: Translate {
            x: !root.activityMotionEnabled ? 0 : root.variant==="tron" ? root.localVibration.dx : root.visualFrame.dx * root.personality.x
            y: !root.activityMotionEnabled ? 0 : root.variant==="tron" ? root.localVibration.dy : root.visualFrame.dy * root.personality.y
        }
        Canvas {
            id: surface
            objectName: "energyProgressCanvas"
            anchors.fill: parent
            readonly property real spill: root.variant==="default" ? 0 : Math.max(10, root.height * (root.variant==="flamethrower"?2.1:root.variant==="ki-blast"?2.0:root.variant==="omnitrix"?1.45:1.1))
            anchors.margins: -spill
            renderTarget: Canvas.Image
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const c = getContext("2d");
                c.reset();
                c.clearRect(0,0,width,height);
                const x=spill, y=spill, w=Math.max(0,root.width), h=Math.max(0,root.height);
                if (w<4 || h<4) return;
                const f=root.visualFrame, p=root.displayedFraction, mid=y+h/2;
                const inset=root.track.inset, fx=x+inset, fy=y+inset;
                const inner=root.track.width, fillHeight=root.track.height, edge=x+root.headCenterX;
                const ink=root.phase==="failure" && root.variant!=="ki-blast" ? Colors.red : root.energyColor;
                // Quiet baseline: only a tiny fill-local leading highlight.
                if(root.variant==="default") {
                    c.fillStyle=Colors.dark;
                    c.fillRect(x,y,w,h);
                    c.strokeStyle=root.chassisColor;
                    c.lineWidth=1;
                    c.strokeRect(x+.5,y+.5,w-1,h-1);
                    if(p>0) {
                        const fill=c.createLinearGradient(0,fy,0,fy+fillHeight);
                        fill.addColorStop(0,Qt.rgba(ink.r*.70,ink.g*.70,ink.b*.70,1));
                        fill.addColorStop(.5,Qt.rgba(ink.r*.38,ink.g*.38,ink.b*.38,1));
                        fill.addColorStop(1,Qt.rgba(ink.r*.60,ink.g*.60,ink.b*.60,1));
                        c.fillStyle=fill;
                        c.fillRect(fx,fy,inner*p,fillHeight);
                        if(root.phase==="running" || (root.phase==="success" && root.elapsed<.42)) {
                            const span=Math.min(inner*p,h*1.25);
                            if(span>0) {
                                const active=c.createLinearGradient(edge-span,mid,edge,mid);
                                active.addColorStop(0,Qt.rgba(ink.r,ink.g,ink.b,0));
                                active.addColorStop(.65,Qt.rgba(ink.r,ink.g,ink.b,.07));
                                active.addColorStop(1,Qt.rgba(ink.r,ink.g,ink.b,.19));
                                c.fillStyle=active; c.fillRect(edge-span,fy,span,fillHeight);
                                // Narrow vertical light, not a solid cap or a
                                // second Omnitrix sphere. Keep the dark gap clear.
                                const rx=Math.min(inner*.25,Math.max(1.2,h*.16));
                                const ry=Math.min(fillHeight*.5,Math.max(2.2,h*.42));
                                c.save();
                                c.beginPath(); c.rect(fx,fy,inner,fillHeight); c.clip();
                                c.translate(edge,mid); c.scale(rx,ry);
                                const eye=c.createRadialGradient(0,0,0,0,0,1);
                                eye.addColorStop(0,Qt.rgba(1,1,1,.20));
                                eye.addColorStop(.20,Qt.rgba(ink.r*.72+.28,ink.g*.72+.28,ink.b*.72+.28,.16));
                                eye.addColorStop(.52,Qt.rgba(ink.r,ink.g,ink.b,.08));
                                eye.addColorStop(1,Qt.rgba(ink.r,ink.g,ink.b,0));
                                c.fillStyle=eye;
                                c.beginPath(); c.arc(0,0,1,0,2*Math.PI); c.fill();
                                c.restore();
                            }
                        }
                    }
                    return;
                }
                const hot=root.variant==="flamethrower";
                const ki=root.variant==="ki-blast";
                const tron=root.variant==="tron";
                const omni=root.variant==="omnitrix";
                const bright=f.brightness*root.personality.brightness;
                function tint(col,a) { return Qt.rgba(col.r,col.g,col.b,a); }
                function mix(a,b,k) {
                    return Qt.rgba(a.r+(b.r-a.r)*k,a.g+(b.g-a.g)*k,
                        a.b+(b.b-a.b)*k,1);
                }
                const material=Material.geometry(root.materialExperiment ? root.fireMode : "standard",
                    p,inner,fillHeight);
                // Emitted light, behind the opaque track. Cooled material remains dark.
                const flame=root.flameMotion, fireState=root.fireState;
                if(hot && fireState.repair>=1) {
                    Material.drawRepair(c,x,y,w,h,1,Colors.dark,root.chassisColor);
                    return;
                }
                function radiate(start,span,color,amount) {
                    if(span<=0 || amount<=0) return;
                    if(!hot && !omni) {
                        // Preserve the accepted TRON and Ki Blast body light.
                        const spread=h*.70;
                        const g=c.createLinearGradient(0,y-spread,0,y+h+spread);
                        g.addColorStop(0,tint(color,0));
                        g.addColorStop(.19,tint(color,amount*.28));
                        g.addColorStop(.36,tint(color,amount));
                        g.addColorStop(.64,tint(color,amount));
                        g.addColorStop(.81,tint(color,amount*.28));
                        g.addColorStop(1,tint(color,0));
                        c.fillStyle=g; c.fillRect(start,y-spread,span,h+2*spread);
                        return;
                    }
                    const spread=h*1.18;
                    const g=c.createLinearGradient(0,mid-spread,0,mid+spread);
                    for(let i=0;i<=16;i++)
                        g.addColorStop(i/16,tint(color,amount*PixelFire.falloff(Math.abs(i/8-1))));
                    c.fillStyle=g; c.fillRect(start,mid-spread,span,2*spread);
                    // Rounded, transparent endpoints replace the abrupt
                    // rectangular cut at the advancing edge.
                    for(const side of [-1,1]) {
                        const cx=side<0?start:start+span;
                        const rx=Math.min(h*.80,side<0?cx:width-cx);
                        if(rx<=0) continue;
                        c.save(); c.translate(cx,mid); c.scale(rx,spread);
                        const cap=c.createRadialGradient(0,0,0,0,0,1);
                        for(let i=0;i<=12;i++)
                            cap.addColorStop(i/12,tint(color,amount*PixelFire.falloff(i/12)));
                        c.fillStyle=cap;
                        c.fillRect(side<0?-1:0,-1,1,2); c.restore();
                    }
                }
                if((hot?fireState.active:f.headVisible) && !material.experimental) radiate(fx,inner*p,ink,ki?.47:hot?.34*fireState.heat:tron?.25:.38);
                // Shared flame-attached optical field: smooth orange falloff
                // and a short velocity-dependent backward stretch.
                function fireHalo(cx,cy,rx,ry,amount) {
                    rx=Math.min(rx,cx,width-cx);
                    ry=Math.min(ry,cy,height-cy);
                    if(rx<=0 || ry<=0) return;
                    c.save(); c.translate(cx,cy); c.scale(rx,ry);
                    const halo=c.createRadialGradient(0,0,0,0,0,1);
                    for(let i=0;i<=12;i++) {
                        const r=i/12, color=mix(Colors.yellow,Colors.red,r*.9);
                        halo.addColorStop(r,tint(color,amount*PixelFire.falloff(r)));
                    }
                    c.fillStyle=halo; c.fillRect(-1,-1,2,2); c.restore();
                }
                if(hot && fireState.active && p>0) {
                    const tip=edge+root.flameTipOffset;
                    const center=tip-h*(.38+flame.drag);
                    fireHalo(center,mid+h*(.12+flame.sway),
                        h*1.55*flame.stretch,h*1.46*flame.breath,.60*flame.pulse*fireState.heat);
                }
                if(ki && f.clash) radiate(edge,inner*f.enemyFraction,
                    mix(Qt.rgba(.65,1,1,1),Qt.rgba(1,.10,.16,1),f.enemyHeat),.34*f.enemyOpacity);
                // In Burn Away, the traversed chassis is gone, not covered
                // by a differently colored progress fill.
                if (material.erosion && p>0) {
                    if(p<1) Material.drawRemaining(c,x+.5,y+.5,w-1,h-1,edge,
                        fireState.heat,root.chassisColor,inset-.5,root.remainingAsh);
                } else {
                // Low-cost perimeter: three nested outlines, no full-face shadow.
                for (let i=3;i>=1;i--) {
                    c.strokeStyle=tint(root.chassisColor,Math.min(.35,(.035+f.intensity*.025)*(4-i)*root.personality.brightness));
                    c.lineWidth=i*2;
                    c.strokeRect(x,y,w,h);
                }
                c.fillStyle=Colors.dark;
                c.fillRect(x,y,w,h);
                c.strokeStyle=root.chassisColor;
                c.lineWidth=1;
                c.strokeRect(x+.5,y+.5,w-1,h-1);
                }
                if (material.erosion && root.remainingAsh && p===0) {
                    Material.drawAsh(c,fx,fy,inner,fillHeight,fx+inner,0);
                }
                if (material.ash && p>0) {
                    Material.drawAsh(c,fx,fy,inner,fillHeight,edge,fireState.heat);
                } else if (!material.erosion && p>0) {
                    const g=c.createLinearGradient(0,fy,0,fy+fillHeight);
                    g.addColorStop(0,ink);
                    g.addColorStop(.18,mix(Colors.dark,ink,tron?.22:.42));
                    g.addColorStop(.50,mix(Colors.dark,ink,ki?.92:hot?.72:omni?.80:.43));
                    g.addColorStop(.82,mix(Colors.dark,ink,tron?.22:.42));
                    g.addColorStop(1,ink);
                    c.fillStyle=g;
                    c.fillRect(fx,fy,inner*p,fillHeight);
                    c.fillStyle=tint(Colors.white,.075);
                    for (let yy=fy+3;yy<fy+fillHeight-1;yy+=4)
                        c.fillRect(fx,yy,inner*p,1);
                }
                // A successful fire rebuilds the empty shell after all
                // combustion has cooled. Actual progress remains at 100%.
                if(hot && fireState.repairing) {
                    Material.drawRepair(c,x,y,w,h,fireState.repair,Colors.dark,root.chassisColor);
                    return;
                }
                // Two contiguous beams share a single collision plane.
                // The opposing blast occupies the right side until pushed off
                // the track; on defeat it drives the plane all the way left.
                if (ki && f.clash && f.enemyFraction>0) {
                    const heat=f.enemyHeat;
                    const red=Qt.rgba(1,.10,.16,1);
                    const crimson=Qt.rgba(.53,.015,.05,1);
                    const cyan=Qt.rgba(.88,.88,.66,1);
                    const cool=Qt.rgba(.77,.48,.34,1);
                    const warm=Qt.rgba(1,.79,.39,1);
                    const hotWhite=Qt.rgba(1,.94,.74,1);
                    c.save();
                    c.globalAlpha=f.enemyOpacity;
                    const g=c.createLinearGradient(0,fy,0,fy+fillHeight);
                    g.addColorStop(0,mix(cyan,red,heat));
                    g.addColorStop(.18,mix(cool,crimson,heat));
                    g.addColorStop(.38,mix(warm,red,heat));
                    g.addColorStop(.50,mix(hotWhite,red,heat*.82));
                    g.addColorStop(.62,mix(warm,red,heat));
                    g.addColorStop(.82,mix(cool,crimson,heat));
                    g.addColorStop(1,mix(cyan,red,heat));
                    c.fillStyle=g; c.fillRect(edge,fy,inner*f.enemyFraction,fillHeight);
                    // Red pressure concentrates at the advancing collision
                    // front first, then progressively consumes the enemy core.
                    const rush=c.createLinearGradient(edge,mid,fx+inner,mid);
                    rush.addColorStop(0,tint(red,.18+.48*heat));
                    rush.addColorStop(.35,tint(red,.06+.22*heat));
                    rush.addColorStop(1,tint(red,0));
                    c.fillStyle=rush; c.fillRect(edge,fy,inner*f.enemyFraction,fillHeight);
                    c.restore();
                }
                // Paint the current over the material but under the head.
                // Reduced motion retains a stationary, legible pattern.
                function current(start,span,side,color,alpha) {
                    if(span<1 || alpha<=0) return;
                    const rows=Flow.flow(root.variant,root.fireMode,side,span,fillHeight,
                        root.elapsed,root.reducedMotion,root.speedLevel);
                    c.save();
                    c.beginPath(); c.rect(start,fy,span,fillHeight); c.clip();
                    for(const line of rows) {
                        const left=start+line.x, right=left+line.length;
                        const yy=fy+line.y;
                        const g=c.createLinearGradient(left,yy,right,yy);
                        const a=line.alpha*alpha;
                        g.addColorStop(0,tint(color,side==="enemy"?a:0));
                        g.addColorStop(.32,tint(color,a*.8));
                        g.addColorStop(.72,tint(Colors.white,a));
                        g.addColorStop(1,tint(color,side==="enemy"?0:a*.62));
                        c.fillStyle=g;
                        c.fillRect(left,yy,line.length,line.wake?Math.max(1,h*.055):Math.max(1,h*.036));
                    }
                    c.restore();
                }
                if((hot?fireState.active:f.headVisible) && p>0) current(fx,inner*p,"player",
                    hot?Colors.yellow:ink,hot?fireState.flame:1);
                if(ki && f.clash && f.enemyFraction>0) {
                    const enemyInk=mix(Colors.white,Qt.rgba(1,.10,.16,1),f.enemyHeat);
                    current(edge,inner*f.enemyFraction,"enemy",enemyInk,f.enemyOpacity);
                }
                // Exterior air currents are attached to the TRON front.
                if(tron && f.headVisible) {
                    const air=Flow.airFlow(inner*p,h,root.elapsed,root.reducedMotion,root.speedLevel);
                    for(const line of air) {
                        const left=edge+line.x, right=left+line.length, yy=mid+line.y;
                        const g=c.createLinearGradient(left,yy,right,yy);
                        g.addColorStop(0,tint(ink,0));
                        g.addColorStop(.65,tint(ink,line.alpha*.75));
                        g.addColorStop(1,tint(Colors.white,line.alpha));
                        c.fillStyle=g; c.fillRect(left,yy,line.length,Math.max(1,h*.04));
                    }
                }
                if (!f.headVisible && !(ki && f.clash && f.enemyOpacity>0) && !(hot && fireState.active)) return;
                // All core and aura layers share the exact centerline.
                function orb(rx,ry,stops,centerX) {
                    if(rx<=0 || ry<=0) return;
                    c.save();
                    c.translate(centerX===undefined?edge:centerX,mid);
                    c.scale(rx,ry);
                    const g=c.createRadialGradient(0,0,0,0,0,1);
                    for (const stop of stops) g.addColorStop(stop[0],stop[1]);
                    c.fillStyle=g;
                    c.beginPath(); c.arc(0,0,1,0,2*Math.PI); c.fill();
                    c.restore();
                }
                // Crisp, animated pixel-fire underneath a translucent
                // optical glow. Detached embers rise from the moving front.
                if(hot && p>0 && fireState.active) {
                    const pixel=root.flamePixels;
                    // Heat penetrates the material ahead of the flame.
                    // Keep the already eroded/ashed region unchanged.
                    const bed=Material.heatBed(root.elapsed,root.flameSpeed,root.reducedMotion);
                    const footprint=Material.heatFootprint(h,root.flameTipOffset,bed.reach,flame.speed);
                    const contactWidth=Math.min(fx+inner-edge,footprint.ahead*fireState.heat);
                    if(contactWidth>0) {
                        c.save(); c.globalAlpha=fireState.heat; c.beginPath(); c.rect(edge,fy,contactWidth,fillHeight); c.clip();
                        const heated=c.createLinearGradient(edge,mid,edge+contactWidth,mid);
                        heated.addColorStop(0,tint(Colors.yellow,.94*bed.pulse));
                        heated.addColorStop(.23,tint(Colors.orange,.77*bed.pulse));
                        heated.addColorStop(.64,tint(Colors.red,.36*bed.pulse));
                        heated.addColorStop(1,tint(Colors.red,0));
                        c.fillStyle=heated; c.fillRect(edge,fy,contactWidth,fillHeight);
                        for(const row of bed.rows) {
                            const yy=fy+row.y*fillHeight;
                            const start=edge+contactWidth*row.shift;
                            const length=contactWidth*row.reach;
                            const wave=c.createLinearGradient(start,yy,start+length,yy);
                            wave.addColorStop(0,tint(Colors.yellow,row.alpha*bed.pulse));
                            wave.addColorStop(.40,tint(Colors.orange,row.alpha*.82));
                            wave.addColorStop(1,tint(Colors.red,0));
                            c.fillStyle=wave; c.fillRect(start,yy,length,Math.max(1,fillHeight*.065));
                        }
                        c.restore();
                    }
                    // Visible heat reflection above the opaque ash/material.
                    // Anchor its hot end at the actual leading pixel, not
                    // the midpoint of the elongated flame.
                    const tip=edge+root.flameTipOffset;
                    fireHalo(tip-h*(.36+flame.drag),mid+h*(.20+flame.sway),
                        h*1.02*(1+.35*(flame.stretch-1)),h*1.08*flame.breath,.28*flame.pulse*fireState.heat);
                    // Mirrored contact heat follows the actual trailing
                    // flame silhouette. Burn Away emits light here without
                    // restoring solid material or its destroyed border.
                    const rearSpan=Material.rearHeatSpan(h,root.flameRearOffset,bed.reach,
                        footprint.behind,fireState.heat,inner*p);
                    if(rearSpan>0) {
                        c.save(); c.globalAlpha=fireState.heat;
                        c.beginPath(); c.rect(edge-rearSpan,fy,rearSpan,fillHeight); c.clip();
                        const back=c.createLinearGradient(edge,mid,edge-rearSpan,mid);
                        back.addColorStop(0,tint(Colors.yellow,.66*bed.pulse));
                        back.addColorStop(.23,tint(Colors.orange,.59*bed.pulse));
                        back.addColorStop(.64,tint(Colors.red,.28*bed.pulse));
                        back.addColorStop(1,tint(Colors.red,0));
                        c.fillStyle=back; c.fillRect(edge-rearSpan,fy,rearSpan,fillHeight);
                        for(const row of bed.rows) {
                            const yy=fy+row.y*fillHeight;
                            const start=edge-rearSpan*row.shift;
                            const length=rearSpan*row.reach;
                            const wave=c.createLinearGradient(start,yy,start-length,yy);
                            wave.addColorStop(0,tint(Colors.yellow,row.alpha*bed.pulse*.80));
                            wave.addColorStop(.40,tint(Colors.orange,row.alpha*.70));
                            wave.addColorStop(1,tint(Colors.red,0));
                            c.fillStyle=wave; c.fillRect(start-length,yy,length,Math.max(1,fillHeight*.065));
                        }
                        c.restore();
                    }
                    // Rocket exhaust: tapered back from the round head, hot
                    // inner core and softer outer plume. The material modes
                    // keep a shorter, localized combustion wake.
                    const plume=Math.min(inner*p,h*(root.fireMode==="standard"?3.8:root.fireMode==="ash-trail"?1.85:1.35)*flame.stretch)*fireState.scale;
                    if(plume>0 && fireState.flame>0) {
                        c.save(); c.globalAlpha=fireState.flame;
                        for(let layer=0;layer<3;layer++){
                            const breadth=h*(.55-layer*.12)*flame.breath*fireState.scale;
                            const end=edge-plume*(1-layer*.16);
                            const g=c.createLinearGradient(end,mid,edge+h*.22,mid);
                            g.addColorStop(0,tint(Colors.red,0));
                            g.addColorStop(.25,tint(Colors.red,.26+layer*.08));
                            g.addColorStop(.68,tint(Colors.orange,.42+layer*.12));
                            g.addColorStop(1,tint(Colors.yellow,.65+layer*.10));
                            c.fillStyle=g;
                            c.beginPath(); c.moveTo(end,mid);
                            c.bezierCurveTo(end+plume*.35,mid-breadth*.18,
                                edge-plume*.24,mid-breadth,edge+h*.22,mid-breadth*.50);
                            c.lineTo(edge+h*.22,mid+breadth*.50);
                            c.bezierCurveTo(edge-plume*.24,mid+breadth,
                                end+plume*.35,mid+breadth*.18,end,mid);
                            c.closePath(); c.fill();
                        }
                        c.restore();
                    }
                    const heat=root.fireMode==="burn-away"?1:root.fireMode==="ash-trail"?.83:.90;
                    const u=pixel.unit;
                    // The flame itself emits light. The hot leading cap
                    // grades into orange along its actual pixel silhouette.
                    const fireOrange=[Qt.rgba(.79,.19,.04,1),Qt.rgba(.96,.35,.05,1),
                        Qt.rgba(1,.57,.10,1),Qt.rgba(1,.72,.24,1)];
                    const fireTip=[Qt.rgba(.95,.36,.06,1),Qt.rgba(1,.65,.16,1),
                        Qt.rgba(1,.87,.39,1),Qt.rgba(1,.97,.72,1)];
                    const front=(root.flameTipOffset/u)/Math.max(.001,fireState.scale);
                    const palette=["#D34A18","#F48B1B","#FFD05A","#FFF3B0"];
                    if(fireState.flame>0) {
                        c.save(); c.globalAlpha=fireState.flame;
                        c.translate(edge,mid); c.scale(fireState.scale,fireState.scale);
                        for(const cell of pixel.cells) {
                            const k=Math.max(0,Math.min(1,1-(front-cell.x)/8));
                            const hotColor=mix(fireOrange[cell.heat],fireTip[cell.heat],k*heat);
                            c.fillStyle=fireState.cooling?mix(hotColor,fireOrange[0],fireState.cool):hotColor;
                            c.fillRect(cell.x*u,cell.y*u,u,u);
                        }
                        c.restore();
                    }
                    const sparks=fireState.cooling?PixelFire.releasedEmbers(fireState.cool):pixel.embers;
                    for(const ember of sparks) {
                        c.save(); c.globalAlpha=ember.alpha*fireState.embers;
                        c.fillStyle=palette[ember.heat];
                        c.fillRect(Math.round(edge)+ember.x*u,Math.round(mid)+ember.y*u,u,u);
                        c.restore();
                    }
                }
                // Consuming fire: asymmetric curved tongues curl
                // around the advancing ember, not down the entire beam.
                // Soft flame lobes can spill beyond the beam vertically;
                // the plasma core remains independently centered.
                if (hot && p>0 && fireState.flame>0) {
                    const t=root.reducedMotion ? 0 : root.elapsed;
                    const length=Math.min(h*1.5,inner*p)*fireState.scale;
                    const reach=h*(.78+.12*f.intensity)*flame.breath*fireState.scale;
                    c.save();
                    c.globalAlpha=.35*fireState.flame;
                    // Constrain the fire to the terminal region, while
                    // letting it consume the full height of the beam tip.
                    c.beginPath();
                    c.rect(edge-length,mid-h*1.1,length+h*.46,h*2.2);
                    c.clip();

                    for (let i=0;i<10;i++) {
                        const q=i/10;
                        const wave=.72*Math.sin(t*(7.1+i*.63)+i*2.1)+.28*Math.sin(t*11.1+i*.93);
                        // The upper curls rise more than the lower curls.
                        const sign=i%3===1 ? 1 : -1;
                        const tail=edge-length*(.25+q*.75);
                        const crest=mid+sign*reach*(.55+.28*wave+.12*q);
                        const base=mid-sign*h*.30;
                        const g=c.createRadialGradient(edge-length*.12,mid,0,
                            edge-length*.12,mid,Math.max(h*.95,length));
                        g.addColorStop(0,tint(Colors.yellow,.38));
                        g.addColorStop(.26,tint(Colors.orange,.32));
                        g.addColorStop(.52,tint(Colors.orange,.16));
                        g.addColorStop(.78,tint(Colors.red,.065));
                        g.addColorStop(1,tint(Colors.red,0));
                        c.fillStyle=g;
                        c.beginPath();
                        c.moveTo(edge+h*.22,base);
                        c.bezierCurveTo(tail+length*.22,base,tail-h*.08,mid,tail,crest);
                        c.bezierCurveTo(tail+length*.18,crest+sign*h*.12,
                            tail+length*.35,crest-sign*h*.32,tail+length*.45,crest-sign*h*.08);
                        c.bezierCurveTo(edge-length*.10,crest+sign*h*.24,
                            edge+h*.44,mid+sign*h*.48,edge+h*.22,base);
                        c.closePath(); c.fill();
                    }
                    c.restore();
                }
                const scale=f.power*root.personality.head;
                const enlarged=Flow.head(root.variant,h,f.power,w);
                const rx=enlarged?enlarged.rx:Math.min(h*.78*scale*root.personality.headConsume,w*.48);
                const ry=enlarged?enlarged.ry:Math.min(h*(hot?.66:.84),h*(hot?.47:.58)*(1+(scale-1)*.22));
                if (ki && (f.clash || (root.phase==="success" && f.headVisible))) {
                    // Two overlapping cores. The stronger rounded sphere
                    // overdraws the weaker contact cap, never an empty plane.
                    const red=Qt.rgba(1,.10,.16,1);
                    const enemyInk=mix(Qt.rgba(1,.70,.32,1),red,f.enemyHeat);
                    const enemyCore=mix(Qt.rgba(1,.91,.66,1),red,f.enemyHeat*.82);
                    const contact=Flow.contact(p,f.enemyHeat,h,w);
                    const touching=p>0 && f.enemyFraction>0;
                    function compressed(side,color,core,alpha) {
                        const shape=side<0?contact.left:contact.right;
                        const lobe=shape.rx, tall=shape.ry;
                        if(alpha<=0 || lobe<=0) return;
                        const center=edge+side*(touching?shape.offset*.72:lobe*.12);
                        c.save(); c.globalAlpha=alpha;
                        orb(lobe*1.60,tall*1.48,[[0,tint(color,.67)],
                            [.53,tint(color,.30)],[1,tint(color,0)]],center);
                        orb(lobe,tall,[[0,core],[.20,core],[.49,color],
                            [.77,tint(color,.86)],[1,tint(color,0)]],center);
                        c.restore();
                    }
                    const playerAlpha=Math.min(1,p*12);
                    const enemyAlpha=Math.min(1,f.enemyFraction*12)*f.enemyOpacity;
                    const playerWins=contact.left.rx>=contact.right.rx;
                    if(touching) {
                        const tall=contact.chord;
                        const winner=playerWins?ink:enemyInk;
                        const dominance=Math.min(1,Math.abs(p-.5)*2);
                        const penetration=Math.min(playerWins?inner*f.enemyFraction:inner*p,
                            h*(.65+dominance*2.3));
                        // The winner penetrates the losing beam, fading back
                        // into its original color rather than recoloring it.
                        if(penetration>0) {
                            const end=edge+(playerWins?1:-1)*penetration;
                            const g=c.createLinearGradient(edge,mid,end,mid);
                            g.addColorStop(0,tint(winner,.60*dominance));
                            g.addColorStop(.4,tint(winner,.30*dominance));
                            g.addColorStop(1,tint(winner,0));
                            c.fillStyle=g;
                            c.fillRect(Math.min(edge,end),fy,penetration,fillHeight);
                        }
                    }
                    if(playerWins) {
                        compressed(1,enemyInk,enemyCore,enemyAlpha);
                        compressed(-1,ink,Qt.rgba(.70,.91,1,1),playerAlpha);
                    } else {
                        compressed(-1,ink,Qt.rgba(.70,.91,1,1),playerAlpha);
                        compressed(1,enemyInk,enemyCore,enemyAlpha);
                    }
                    if(touching) {
                        const tall=contact.chord;
                        const winner=playerWins?ink:enemyInk;
                        orb(h*1.75,h*1.7,[[0,tint(winner,.57)],
                            [.34,tint(winner,.32)],[1,tint(winner,0)]]);
                        orb(Math.max(h*.14,tall*.55),tall*1.1,[
                            [0,tint(Colors.white,.92)],[.35,tint(winner,.66)],
                            [.72,tint(winner,.22)],[1,tint(winner,0)]]);
                    }
                    return;
                }
                if(enlarged) {
                    // Long light wake directly behind the substantial core.
                    // Its bright shoulders cover the full chamber height.
                    const tail=Math.min(inner*p,h*(tron?3.2:3));
                    if(tail>0) {
                        const g=c.createLinearGradient(edge-tail,mid,edge,mid);
                        g.addColorStop(0,tint(ink,0));
                        g.addColorStop(.45,tint(ink,.13));
                        g.addColorStop(.78,tint(ink,.48));
                        g.addColorStop(1,tint(ink,.95));
                        c.fillStyle=g;
                        c.fillRect(edge-tail,mid-h*.16,tail,h*.32);
                        if(tron) {
                            orb(tail*.64,h*.65,[[0,tint(ink,.44)],[.45,tint(ink,.24)],[1,tint(ink,0)]],edge-tail*.40);
                        }
                    }
                    orb(rx*(tron?1.82:1.65),ry*(omni?1.66:1.48),[[0,tint(ink,tron?.92:.75)],
                        [.22,tint(ink,tron?.77:.62)],[.48,tint(ink,tron?.53:.37)],
                        [.64,tint(ink,.22)],[.78,tint(ink,.09)],[.90,tint(ink,.025)],[1,tint(ink,0)]]);
                    orb(rx,ry,[[0,Colors.white],[.16,Colors.white],
                        [enlarged.solid,mix(ink,Colors.white,.32)],
                        [.68,tint(ink,.58)],[1,tint(ink,0)]]);
                } else if(hot) {
                    // No foreground sphere: the brightest pixels are the
                    // leading cap itself. Surrounding heat is drawn below it.
                } else {
                    orb(rx*1.6,Math.min(h*(hot?.91:1.12),ry*1.55),[
                        [0,tint(ink,Math.min(.98,.35*bright))],
                        [.55,tint(ink,.22)],[1,tint(ink,0)]]);
                    orb(rx,ry,[[0,Colors.white],[Math.min(.36,.12*bright),Colors.white],
                        [.38,mix(ink,Colors.white,Math.min(.98,.4*bright))],[.57,tint(ink,.84)],
                        [1,tint(ink,0)]]);
                }
                if (!hot && f.intensity>.08) {
                    const flare=c.createLinearGradient(edge-rx*1.4,mid,edge+rx*1.4,mid);
                    flare.addColorStop(0,tint(ink,0));
                    flare.addColorStop(.5,tint(Colors.white,f.intensity*.8));
                    flare.addColorStop(1,tint(ink,0));
                    c.fillStyle=flare; c.fillRect(edge-rx*1.4,mid-1,rx*2.8,2);
                }
            }
        }
        GohuText {
            anchors.fill: parent
            anchors.margins: 4
            text: root.caption
            color: root.foregroundColor
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            style: root.variant==="default" ? Text.Normal : Text.Outline
            styleColor: Colors.dark
        }
    }
}
