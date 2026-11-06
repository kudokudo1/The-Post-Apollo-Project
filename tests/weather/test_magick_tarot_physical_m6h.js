"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const read=p=>fs.readFileSync(path.join(__dirname,"../..",p),"utf8");
const deckSource=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const physicalSource=read("widgets/weather/StationMagickTarotPhysicalPolicy.js");
const qml=read("widgets/weather/StationMagickTarotPane.qml");
const cardQml=read("widgets/weather/StationMagickTarotCard.qml");
const subjects=read("widgets/weather/StationMagickSubjectPane.qml");
const d=vm.createContext({}),m=vm.createContext({});
vm.runInContext(deckSource.replace(/^\.pragma library\s*/m,""),d);
vm.runInContext(physicalSource.replace(/^\.pragma library\s*/m,""),m);
const plain=v=>JSON.parse(JSON.stringify(v));
const start=id=>m.start(d.SPREADS,d.DECK.id,id);
const add=(s,id,r)=>m.add(d.SPREADS,d.CARDS,s,id,r);
const undo=s=>m.undo(d.SPREADS,d.CARDS,s);

test("M6h begins authentic one/three/five position spreads with no guessed cards",()=>{
 for(const s of d.SPREADS){
   const x=start(s.id);
   assert.equal(x.ready,true);
   assert.equal(x.method,"PHYSICAL CARD ENTRY");
   assert.equal(x.deckId,d.DECK.id);
   assert.equal(x.count,0);
   assert.equal(x.total,s.slots.length);
   assert.equal(x.nextPosition,s.slots[0]);
   assert.equal(m.validate(d.SPREADS,d.CARDS,x),true);
 }
 assert.equal(start("not-a-spread").ready,false);
 assert.equal(m.start(d.SPREADS,"","three").ready,false);
});

test("M6h manual physical cards preserve identities, orientation, order and no mutation",()=>{
 let state=start("three"),original=JSON.stringify(state);
 let v=add(state,"wands-daughter",false);
 assert.equal(v.ok,true,v.reason);
 assert.equal(JSON.stringify(state),original);
 state=v.state;
 assert.equal(state.cards[0].title,"Daughter of Wands");
 assert.equal(state.cards[0].position,"PAST");
 assert.equal(state.nextPosition,"PRESENT");
 v=add(state,"major-the-star",true);
 assert.equal(v.ok,true,v.reason);state=v.state;
 assert.equal(state.cards[1].position,"PRESENT");
 assert.equal(state.cards[1].reversed,true);
 v=add(state,"cups-mother",false);
 assert.equal(v.ok,true,v.reason);state=v.state;
 assert.equal(state.count,3);
 assert.equal(state.complete,true);
 assert.equal(state.nextPosition,"");
 assert.deepEqual(plain(state.cards.map(c=>c.position)),
   ["PAST","PRESENT","FUTURE"]);
 assert.equal(new Set(state.cards.map(c=>c.id)).size,3);
 assert.equal(add(state,"swords-ace",false).ok,false);
 assert.equal(m.validate(d.SPREADS,d.CARDS,state),true);
});

test("M6h refuses duplicate cards, unknown IDs and implicit reversed states",()=>{
 const s=add(start("five"),"major-the-fool",false).state;
 for(const [id,reversed] of [
   ["major-the-fool",true],["unknown-card",false],["../other",false],
   ["cups-ace",null],["cups-ace",0],["cups-ace",undefined]]){
   const original=JSON.stringify(s),v=add(s,id,reversed);
   assert.equal(v.ok,false);
   assert.equal(v.state,s);
   assert.equal(JSON.stringify(s),original);
 }
 assert.equal(m.contains(s,"major-the-fool"),true);
 assert.equal(m.contains(s,"swords-ace"),false);
 assert.equal(m.contains(null,"swords-ace"),false);
});

test("M6h undo removes just the last card and restores next physical slot",()=>{
 let state=start("five");
 for(const [id,r] of [
   ["major-the-world",false],["wands-son",true],["cups-father",false],
   ["swords-7",true],["pentacles-daughter",false]]){
   const x=add(state,id,r);
   assert.equal(x.ok,true,x.reason);
   state=x.state;
 }
 assert.equal(state.complete,true);
 assert.equal(state.count,5);
 const before=JSON.stringify(state),first=undo(state);
 assert.equal(first.ok,true,first.reason);
 assert.equal(JSON.stringify(state),before);
 state=first.state;
 assert.equal(state.count,4);
 assert.equal(state.complete,false);
 assert.equal(state.nextPosition,"REFLECTION");
 assert.equal(m.contains(state,"pentacles-daughter"),false);
 assert.equal(m.validate(d.SPREADS,d.CARDS,state),true);
 while(state.count>0)state=undo(state).state;
 assert.equal(state.nextPosition,"CONTEXT");
 assert.equal(undo(state).ok,false);
});

test("M6h rejects manually corrupted deck, slot or source shape",()=>{
 const mutations=[
  s=>{s.count=2;},s=>{s.method="RANDOM";},
  s=>{s.complete=true;},s=>{s.nextPosition="WRONG";},
  s=>{s.total=9;},s=>{s.deckId="";},s=>{s.spread="not-spread";}
 ];
 for(const edit of mutations){
   const s=plain(start("three"));edit(s);
   assert.equal(m.validate(d.SPREADS,d.CARDS,s),false);
   assert.equal(add(s,"cups-ace",false).ok,false);
 }
 assert.equal(m.validate(d.SPREADS,d.CARDS.slice(0,77),start("three")),false);
 assert.equal(m.validate(d.SPREADS,d.CARDS,null),false);
});

test("M6h integrates physical picker with existing Wild Unknown draw and INDEX",()=>{
 for(const re of [
 /import "StationMagickTarotPhysicalPolicy\.js" as Physical/,
 /property string drawMethod: "digital"/,
 /property bool manualReversed: false/,
 /Physical\.start\(Deck\.SPREADS,Deck\.DECK\.id,spreadId\)/,
 /Physical\.add\(Deck\.SPREADS,Deck\.CARDS,reading,/,
 /Physical\.undo\(Deck\.SPREADS,Deck\.CARDS,reading\)/,
 /label: "DIGITAL SHUFFLE"/,
 /label: "MY PHYSICAL CARDS"/,
 /\? "CHOOSE CARD" : "SHUFFLE \+ DRAW"/,
 /label: "UNDO LAST"/,
 /"ADD TO SPREAD"/,
 /tarot\.previewId!==""/,
 /Physical\.contains\(tarot\.reading,/,
 /tarot\.addPhysicalCard\(\)/,
 /tarot\.manualReversed=false/,
 /HOLD YOUR REAL DECK \/\/ CHOOSE CARDS IN INDEX/,
 /NO STORAGE \/\/ CARDS ENTERED BY YOU/,
 /Deck\.draw\(spreadId,Math\.random,reversals\)/,
 /StationMagickTarotCard\s*\{/
 ])assert.match(qml,re);
 assert.match(subject,/id: tarotReference\s*StationMagickTarotPane/);
 assert.match(cardQml,/APOLLO ORIGINAL/);
 for(const src of [physicalSource,qml]){
   for(const forbidden of ["Process {","Timer {","FileView {",
       "XMLHttpRequest","WebEngineView","Qt.openUrlExternally",
       "new WebSocket","fetch(","curl ","writeFile","localStorage"])
     assert.ok(!src.includes(forbidden),forbidden);
 }
});
