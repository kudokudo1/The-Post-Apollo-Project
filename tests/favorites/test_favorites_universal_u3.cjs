"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const clean=s=>s.replace(/^\.pragma library\s*$/m,"")
  .replace(/^\.import ".+" as \w+\s*$/gm,"");
function load(file,context) {
    vm.runInNewContext(clean(read(file)),context,{filename:file});
}
const Resource={};
load("services/favorites/FavoritesResourcePolicy.js",Resource);
const Default={Resource};
load("services/favorites/FavoritesDefaultPolicy.js",Default);
const C={Resource,Default};
load("services/favorites/FavoritesCollectionsPolicy.js",C);
const clone=x=>JSON.parse(JSON.stringify(x));
const key=(provider,kind,id)=>Resource.identityKey(provider,kind,id);
const clock=key("time","timezone","America/New_York");
const place=key("places","saved-place","12");
const newWidget=key("finance","instrument","NASDAQ:EXM");

test("versioned local collection file retains only names and canonical refs",()=>{
  assert.deepEqual(clone(C.empty()),{
    schema:"post-apollo.favorites.collections.v1",
    version:1,revision:0,nextId:1,collections:[]
  });
  const created=C.change(C.empty(),{type:"create",name:"Work"});
  assert.equal(created.ok,true);
  assert.equal(created.collectionId,"c1");
  assert.equal(created.document.revision,1);
  assert.deepEqual(clone(created.document.collections),[
    {id:"c1",name:"Work",members:[]}
  ]);
  const save=C.change(created.document,{type:"set-member",
    collectionId:"c1",key:clock,enabled:true});
  assert.equal(save.ok,true);
  assert.deepEqual(clone(save.document.collections[0].members),[clock]);
  assert.equal(C.memberOf(save.document,"c1",clock),true);
  assert.equal(C.memberOf(save.document,"c2",clock),false);
  assert.deepEqual(clone(C.parse(JSON.stringify(save.document)).document),
                   clone(save.document));
});

test("existing legacy owners remain protected; safe time and places IDs allowed",()=>{
  for(const good of [clock,place,newWidget,
      key("time","timezone","UTC"),key("places","saved-place","1")]) {
    assert.equal(C.checkMemberKey(good).ok,true,good);
  }
  const denied=[
    key("appcontrol","item","run|secret-command"),
    key("hospital","activity","room-24"),
    key("radio","station","123e4567-e89b-42d3-a456-000000000001"),
    key("notifications","source","org.mozilla.firefox"),
    key("weather-home","card","space|geomagnetic"),
    key("time","timezone","Not A Zone"),
    key("time","timezone","a/b/../x"),
    key("places","saved-place","-2"),
    key("places","saved-place","01"),
    key("finance","instrument","https://secret.example/key"),
    key("finance","instrument","secret=one two"),
    "fav1:local:finance:instrument:%GG",
    "fav1:local:finance:instrument:a%2Fb",
    "", null, {}
  ];
  for(const raw of denied)
    assert.equal(C.checkMemberKey(raw).ok,false,String(raw));
});

test("rename, delete and order are independent of provider favorite membership",()=>{
  const a=C.change(C.empty(),{type:"create",name:"Morning"});
  const b=C.change(a.document,{type:"create",name:"Travel"});
  assert.equal(b.collectionId,"c2");
  const c=C.change(b.document,{type:"set-member",
    collectionId:"c1",key:clock,enabled:true});
  const d=C.change(c.document,{type:"set-member",
    collectionId:"c1",key:place,enabled:true});
  const e=C.change(d.document,{type:"set-member",
    collectionId:"c1",key:newWidget,enabled:true});
  assert.deepEqual(clone(e.document.collections[0].members),[
    clock,place,newWidget
  ]);
  const moved=C.change(e.document,{type:"move-member",
    collectionId:"c1",key:newWidget,direction:-1});
  assert.deepEqual(clone(moved.document.collections[0].members),[
    clock,newWidget,place
  ]);
  assert.deepEqual(clone(e.document.collections[0].members),[
    clock,place,newWidget
  ]);
  assert.equal(C.change(moved.document,{type:"move-member",
    collectionId:"c1",key:clock,direction:-1}).changed,false);
  const renamed=C.change(moved.document,{type:"rename",
    collectionId:"c1",name:"Daily"});
  assert.equal(renamed.document.collections[0].name,"Daily");
  const deleted=C.change(renamed.document,{type:"delete",collectionId:"c2"});
  assert.equal(deleted.document.collections.length,1);
  assert.equal(deleted.document.nextId,3);
  assert.equal(deleted.document.collections[0].members.length,3);
  // Local grouping never removes the Clock favorite from TimeSettings.
  assert.equal(C.checkMemberKey(clock).ok,true);
});

test("invalid names, duplicate names and invalid actions fail closed",()=>{
  const doc=C.change(C.empty(),{type:"create",name:"Alpha"}).document;
  for(const name of [""," "," Alpha","Alpha ","a\nb","x".repeat(49)]) {
    assert.equal(C.change(doc,{type:"create",name}).ok,false,
                 JSON.stringify(name));
  }
  assert.equal(C.change(doc,{type:"create",name:"alpha"}).reason,
               "DUPLICATE_NAME");
  assert.equal(C.change(doc,{type:"rename",collectionId:"c1",name:"Alpha"})
               .changed,false);
  assert.equal(C.change(doc,{type:"delete",collectionId:"c9"}).reason,
               "UNKNOWN_COLLECTION");
  assert.equal(C.change(doc,{type:"set-member",collectionId:"c1",
      key:clock,enabled:1}).reason,"INVALID_ACTION");
  assert.equal(C.change(doc,{type:"set-member",collectionId:"c1",
      key:key("appcontrol","item","app-1"),enabled:true}).ok,false);
  assert.equal(C.change(doc,{type:"move-member",collectionId:"c1",
      key:clock,direction:0}).reason,"INVALID_DIRECTION");
  assert.equal(C.change(doc,{type:"share"}).reason,"INVALID_ACTION");
  assert.equal(C.change(doc,null).reason,"INVALID_ACTION");
});

test("duplicate members, unsupported fields and corrupt bytes preserve old document",()=>{
  const a=C.change(C.empty(),{type:"create",name:"Daily"}).document;
  const b=C.change(a,{type:"set-member",collectionId:"c1",
                      key:clock,enabled:true}).document;
  const valid=JSON.stringify(b);
  const bad=[
    "", "{bad", "null","[]",JSON.stringify({...b,version:2}),
    JSON.stringify({...b,schema:"other"}),
    JSON.stringify({...b,revision:-1}),
    JSON.stringify({...b,nextId:1}),
    JSON.stringify({...b,otherField:"SHOULD_NOT_PERSIST"}),
    JSON.stringify({...b,collections:[{...b.collections[0],
      members:[clock,clock]}]}),
    JSON.stringify({...b,collections:[{...b.collections[0],name:"bad\nname"}]}),
    JSON.stringify({...b,collections:[{...b.collections[0],id:"c0"}]}),
    "x".repeat(C.MAX_DOCUMENT_CHARS+1)
  ];
  for(const raw of bad)
    assert.equal(C.parse(raw).ok,false,raw.slice(0,65));
  assert.equal(C.parse(JSON.stringify({...b,version:2})).reason,
               "UNSUPPORTED_VERSION");
  assert.equal(C.parse(valid).ok,true);
  assert.deepEqual(clone(C.parse(valid).document),clone(b));
});

test("collection and member limits refuse rather than silently evict",()=>{
  let doc=C.empty();
  for(let i=1;i<=C.MAX_COLLECTIONS;i++)
    doc=C.change(doc,{type:"create",name:"Group "+i}).document;
  assert.equal(doc.collections.length,C.MAX_COLLECTIONS);
  assert.equal(C.change(doc,{type:"create",name:"overflow"}).reason,
               "COLLECTION_LIMIT");
  let count=C.change(C.empty(),{type:"create",name:"Watch"}).document;
  for(let i=0;i<C.MAX_MEMBERS;i++)
    count=C.change(count,{type:"set-member",collectionId:"c1",
      key:key("finance","instrument","ID"+i),enabled:true}).document;
  assert.equal(count.collections[0].members.length,C.MAX_MEMBERS);
  assert.equal(C.change(count,{type:"set-member",collectionId:"c1",
      key:newWidget,enabled:true}).reason,"MEMBERSHIP_LIMIT");
  assert.equal(C.change(count,{type:"set-member",collectionId:"c1",
      key:count.collections[0].members[0],enabled:false}).ok,true);
  assert.equal(C.change({...count,revision:Number.MAX_SAFE_INTEGER-1},{
      type:"rename",collectionId:"c1",name:"New Name"
  }).reason,"REVISION_LIMIT");
});

test("rapid sequential edits preserve ordered document revisions without mutation",()=>{
  const start=C.empty();
  const d1=C.change(start,{type:"create",name:"One"}).document;
  const d2=C.change(d1,{type:"create",name:"Two"}).document;
  const d3=C.change(d2,{type:"set-member",collectionId:"c1",
    key:clock,enabled:true}).document;
  const d4=C.change(d3,{type:"set-member",collectionId:"c1",
    key:place,enabled:true}).document;
  const d5=C.change(d4,{type:"move-member",collectionId:"c1",
    key:place,direction:-1}).document;
  assert.deepEqual(clone(d5.collections[0].members),[place,clock]);
  assert.equal(d5.revision,5);
  assert.equal(d1.revision,1);
  assert.equal(start.revision,0);
  assert.equal(C.memberOf(d5,"c2",clock),false);
});

test("U3 singleton owns just its own atomic file with coalesced writer",()=>{
  const qml=read("services/favorites/FavoritesCollectionsStore.qml");
  assert.match(qml,/pragma Singleton/);
  assert.match(qml,/favorites-collections-v1\.json/);
  assert.match(qml,/atomicWrites: true/);
  assert.match(qml,/watchChanges: false/);
  assert.match(qml,/property var pendingDocument: null/);
  assert.match(qml,/property var queuedDocument: null/);
  assert.match(qml,/writeDispatchTimer\.start\(\)/);
  assert.match(qml,/root\.startWrite\(waiting\)/);
  assert.match(qml,/root\.collectionsSaved\(saved\.revision\)/);
  assert.match(qml,/root\.collectionsSaveFailed\(root\.errorCode\)/);
  assert.match(qml,/Policy\.parse\(raw\)/);
  assert.doesNotMatch(qml,/Process\s*\{|execDetached|FileView.*appcontrol/);
  assert.match(read("services/favorites/qmldir"),
      /singleton FavoritesCollectionsStore 1\.0 FavoritesCollectionsStore\.qml/);
});

test("reusable controls and U2 Clock preview preserve provider authority",()=>{
  const toggle=read("components/FavoritesCollectionToggleButton.qml");
  const panel=read("components/FavoritesCollectionPanel.qml");
  const preview=read("components/FavoritesUnifiedPreview.qml");
  const clockUI=read("widgets/TimeW.qml");
  assert.match(toggle,/property var collectionStore: null/);
  assert.match(toggle,/Resource\.normalize\(resource\)/);
  assert.match(toggle,/normalized\.record\.capabilities\.indexOf\("collection"\) >= 0/);
  assert.match(toggle,/onLeftClicked:/);
  assert.match(panel,/function createFromInput\(\)/);
  assert.match(panel,/FavoritesCollectionToggleButton\s*\{/);
  assert.match(panel,/moveMember\(/);
  assert.match(panel,/confirmDelete/);
  assert.match(preview,/property var collectionStore: null/);
  assert.match(preview,/id: collectionSwitch/);
  assert.match(preview,/FavoritesCollectionPanel\s*\{/);
  assert.match(clockUI,/collectionStore: FavoritesCollectionsStore/);
  assert.match(clockUI,/WorldZoneSearch\.contains\(/);
  assert.match(clockUI,/capabilities:\["collection"\]/);
  assert.match(clockUI,/TimeSettings\.toggleWorldFavorite\(/);
  for(const source of [toggle,panel,preview]) {
    assert.doesNotMatch(source,/Quickshell\.Io|FileView\s*\{|execDetached|Process\s*\{|kill -TERM/);
  }
});

test("legacy stores remain separate and unmodified",()=>{
  const app=read("services/favorites/FavoritesStore.qml");
  const defaultStore=read("services/favorites/FavoritesDefaultStore.qml");
  const world=read("services/time/TimeSettings.qml");
  const places=read("services/location/PlaceRegistry.qml");
  assert.match(app,/appcontrol-favorites\.json/);
  assert.match(defaultStore,/favorites-default-v1\.json/);
  assert.match(world,/time-world-favorites-v1\.json/);
  assert.match(places,/places-v1\.json/);
});
