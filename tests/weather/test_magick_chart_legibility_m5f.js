"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const source=fs.readFileSync(path.join(root,
    "widgets/weather/StationMagickCelestialVisualPolicy.js"),"utf8");
const qml=fs.readFileSync(path.join(root,
    "widgets/weather/StationMagickCelestialInstrument.qml"),"utf8");
const ctx=vm.createContext({Date,Math,isFinite,JSON});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),ctx);
const plain=x=>JSON.parse(JSON.stringify(x));
const start=Date.UTC(2026,9,15);

function fixture(){
    const times=Array.from({length:5},(_,i)=>start+i*86400000);
    const make=(body,i)=>{
        const isMoon=body==="moon",lon=isMoon?(350+15*i)%360:10+i;
        return {time_utc:new Date(times[i]).toISOString(),
            unix_ms:times[i],longitude_deg:lon,
            unwrapped_longitude_deg:isMoon?350+15*i:10+i,
            latitude_deg:0.3,distance_au:isMoon?0.0026:1,
            longitude_rate_deg_per_day:isMoon?15:1,motion:"direct"};
    };
    const moon=times.map((_,i)=>make("moon",i));
    const sun=times.map((_,i)=>make("sun",i));
    return {
        format:ctx.FORMAT,
        query:{origin:"geocentric",position_model:"apparent",
            frame:"true-ecliptic-of-date",bodies:["moon","sun"]},
        provenance:{engine:"skyfield",engine_version:"1.55",
            ephemeris_id:"de440s.bsp",ephemeris_sha256:"a".repeat(64),
            time_data_id:"skyfield-builtin"},
        sample_count:5,
        series:[{body:"moon",samples:moon},{body:"sun",samples:sun}],
        relationships:[{bodies:["moon","sun"],
            samples:times.map((time,i)=>({
                unix_ms:time,time_utc:moon[i].time_utc,
                longitude_separation_deg:Math.abs(
                    ((moon[i].longitude_deg-sun[i].longitude_deg+540)%360)-180),
                aspects:[],
            }))}],
        event_markers:[{
            type:"exact_longitude_aspect",name:"conjunction",
            time_utc:new Date(times[1]).toISOString(),
            contact_kind:"crossing",bodies:["moon","sun"],
        }],
    };
}

test("plot dimensions reserve readable axis and UTC date gutters",()=>{
    const layout=ctx.chartLayout(380,205);
    assert.ok(layout.left>=36);
    assert.ok(layout.top>=24);
    assert.ok(layout.width<380-35);
    assert.ok(layout.height<205-40);
    assert.ok(layout.bottom<=205);
    assert.ok(layout.right<=380);
    assert.ok(layout.right>layout.left);
    const v={from:1,to:3,count:3};
    assert.equal(ctx.plotX(1,v,layout),layout.left);
    assert.equal(ctx.plotX(3,v,layout),layout.left+layout.width);
    assert.equal(ctx.plotFraction(layout.left,380,205),0);
    assert.equal(ctx.plotFraction(layout.left+layout.width,380,205),1);
    assert.equal(ctx.plotFraction(-100,380,205),0);
    assert.equal(ctx.plotFraction(999,380,205),1);
    assert.equal(ctx.plotFraction(layout.left+layout.width/2,380,205),0.5);
    assert.equal(ctx.plotY(200,{min:100,max:200},layout),layout.top);
    assert.equal(ctx.plotY(100,{min:100,max:200},layout),
                 layout.top+layout.height);
});

test("line hues are stable and legends identify actual JPL body IDs",()=>{
    const m=ctx.model(fixture());
    assert.equal(m.ready,true,m.reason);
    const legend=plain(ctx.legendRows(m,"motion"));
    assert.deepEqual(legend.map(x=>x.text),["MOON","SUN"]);
    assert.deepEqual(legend.map(x=>x.color),["#ED981A","#55CFCA"]);
    assert.equal(ctx.legendRows(m,"aspects").length,1);
    assert.equal(ctx.legendRows(m,"aspects")[0].text,"MOON/SUN");
    assert.equal(ctx.shortBodyName("jupiter_barycenter"),"JUP SYS");
    assert.equal(ctx.shortBodyName("neptune_barycenter"),"NEP SYS");
    assert.equal(ctx.shortBodyName("mars_barycenter"),"MARS SYS");
    assert.equal(ctx.shortBodyName("moon"),"MOON");
    assert.deepEqual(plain(ctx.legendRows(ctx.model(null),"motion")),[]);
});

test("wheel keeps angular markers unchanged while text stays within plot bounds",()=>{
    const m=ctx.model(fixture());
    const markers=ctx.wheelPositions(m,0);
    const labels=ctx.wheelLabels(m,0,330,160);
    assert.equal(markers.length,labels.length);
    for(let i=0;i<labels.length;i++){
        assert.equal(labels[i].body,markers[i].body);
        assert.equal(labels[i].label,ctx.shortBodyName(markers[i].body));
        assert.ok(labels[i].x>=0 && labels[i].x<330);
        assert.ok(labels[i].y>=0 && labels[i].y<160);
        const angle=Math.atan2(labels[i].pointX-165,80-labels[i].pointY);
        const expected=markers[i].longitude_deg*Math.PI/180;
        assert.ok(Math.abs(Math.sin(angle-expected))<1e-12);
    }
    assert.deepEqual(plain(ctx.wheelLabels(ctx.model(null),0,330,160)),[]);
});

test("a two-sample zoom is still clickable at both actual endpoints",()=>{
    const m=ctx.model(fixture()),view={from:2,to:3,count:2};
    const l=ctx.chartLayout(330,160);
    const left=ctx.plotFraction(l.left,330,160);
    const right=ctx.plotFraction(l.left+l.width,330,160);
    assert.equal(ctx.indexAtFraction(m,view,left),2);
    assert.equal(ctx.indexAtFraction(m,view,right),3);
    const middle=ctx.plotFraction(l.left+l.width/2,330,160);
    assert.equal(ctx.indexAtFraction(m,view,middle),3);
});

test("QML plot and mouse gestures share coordinate mapping",()=>{
    assert.match(qml,/Celestial\.chartLayout\(width,height\)/);
    assert.match(qml,/Celestial\.plotX\(index,view,layout\)/);
    assert.match(qml,/Celestial\.plotY\(value,range,layout\)/);
    assert.match(qml,/Celestial\.legendRows\(instrument\.graphModel,instrument\.mode\)/);
    assert.match(qml,/Celestial\.wheelLabels\(instrument\.graphModel/);
    assert.match(qml,/Celestial\.plotFraction\(x,width,height\)/);
    assert.match(qml,/function sampleFraction\(x\)/);
    assert.match(qml,/sampleFraction\(mouse\.x\)/);
    assert.match(qml,/onWheel: function\(wheel\)/);
    assert.match(qml,/onClicked: instrument\.stepToEvent\(-1\)/);
    assert.match(qml,/onClicked: instrument\.stepToEvent\(1\)/);
    assert.match(qml,/ctx\.fillRect\(legendX,16,9,3\)/);
    assert.match(qml,/const focusX=layout\.left/);
    assert.match(qml,/ctx\.arc\(focusX,y,3\.5,0,2\*Math\.PI\)/);
    for(const unwanted of ["Process {","Timer {","FileView {","XMLHttpRequest"])
        assert.equal(qml.includes(unwanted),false);
});
