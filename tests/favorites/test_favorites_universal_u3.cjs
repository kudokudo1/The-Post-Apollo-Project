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

test("legacy owners retain write authority; only approved safe collection IDs are allowed",()=>{
  for(const good of [clock,place,newWidget,
      key("time","timezone","UTC"),key("places","saved-place","1"),
      key("weather-home","panel","home/auto"),
      key("weather-home","card","sky|next-hours"),
      key("radio","station","123e4567-e89b-42d3-a456-000000000001"),
      key("notifications","source","org.mozilla.firefox"),
      key("appcontrol","item","org.mozilla.firefox.desktop")]) {
    assert.equal(C.checkMemberKey(good).ok,true,good);
  }
  const denied=[
    key("appcontrol","item","run|secret-command"),
    key("appcontrol","item","run:firefox"),
    key("appcontrol","item","mode:2:◇  private.txt"),
    key("appcontrol","item","task|hidden-process"),
    key("appcontrol","item","org.example.secret-vault.desktop"),
    key("appcontrol","preferred-action","run|firefox|kitty"),
    key("hospital","activity","pinned|reports|report|2026-11-08T18:12:05.000Z|1"),
    key("hospital","activity","room-24"),
    key("radio","station","not-a-uuid"),
    key("radio","station","123e4567-e89b-72d3-a456-000000000001"),
    key("notifications","source","website:my-private-site"),
    key("notifications","source","https://example.com/account"),
    key("notifications","source","private-mail"),
    key("weather-home","card","sky|next-hours/../secret"),
    key("weather-home","panel","home/admin"),
    key("weather-home","card","space|geomagnetic\nsecret"),
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
      key:key("appcontrol","item","run:app-1 --private-token"),enabled:true}).ok,false);
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


test("U6a collection grouping persists approved cross-widget IDs without owner mutation",()=>{
  const keys=[
    key("weather-home","panel","home/history"),
    key("weather-home","card","space|geomagnetic"),
    key("radio","station","123e4567-e89b-42d3-a456-000000000002"),
    key("notifications","source","github"),
    key("appcontrol","item","org.mozilla.firefox.desktop"),
    clock,place
  ];
  let doc=C.change(C.empty(),{type:"create",name:"Daily Operations"}).document;
  for(const item of keys) {
    const result=C.change(doc,{type:"set-member",collectionId:"c1",
                                key:item,enabled:true});
    assert.equal(result.ok,true,item);
    assert.equal(result.changed,true,item);
    doc=result.document;
  }
  const serialized=JSON.stringify(doc);
  const persisted=C.parse(serialized);
  assert.equal(persisted.ok,true);
  assert.deepEqual(clone(persisted.document.collections[0].members),keys);
  assert.equal(persisted.document.revision,keys.length+1);
  assert.equal(C.change(persisted.document,{type:"set-member",collectionId:"c1",
      key:keys[0],enabled:true}).changed,false);
  const moved=C.change(persisted.document,{type:"move-member",
      collectionId:"c1",key:keys[4],direction:-1});
  assert.equal(moved.ok,true);
  assert.equal(C.memberOf(moved.document,"c1",keys[4]),true);
  const removed=C.change(moved.document,{type:"set-member",
      collectionId:"c1",key:keys[2],enabled:false});
  assert.equal(removed.ok,true);
  assert.equal(C.memberOf(removed.document,"c1",keys[2]),false);
  assert.equal(C.memberOf(persisted.document,"c1",keys[2]),true);
  // Only the local collection document changed, never any owner snapshot.
  assert.equal(serialized.includes("https://"),false);
  assert.equal(serialized.includes("private"),false);
});

test("U6a rejected owner identities cannot enter even a previously valid document",()=>{
  const unsafe=[
    key("appcontrol","item","mode:2:◇  /home/private/report.pdf"),
    key("appcontrol","item","hidden:btop"),
    key("appcontrol","monitor-watch","watchbox|system|CPU"),
    key("notifications","source","website:session:example.org"),
    key("notifications","source","org.example.secret-app"),
    key("radio","station","123e4567-e89b-72d3-a456-000000000002"),
    key("hospital","activity","pinned|reports|report|2026-11-08T18:12:05.000Z|1"),
    key("weather-home","panel","home/../../credentials")
  ];
  const doc=C.change(C.empty(),{type:"create",name:"Safe"}).document;
  for(const member of unsafe) {
    const change=C.change(doc,{type:"set-member",collectionId:"c1",
        key:member,enabled:true});
    assert.equal(change.ok,false,member);
    assert.equal(C.parse(JSON.stringify({...doc,collections:[
      {...doc.collections[0],members:[member]}]})).ok,false,member);
  }
  assert.equal(doc.collections[0].members.length,0);
});

test("U6a read-only collection controls use selected key, still enforce store policy",()=>{
  const panel=read("components/FavoritesCollectionPanel.qml");
  const toggle=read("components/FavoritesCollectionToggleButton.qml");
  const cpu=read("widgets/cpuplus/CpuPlusFavoritesHubPane.qml");
  const store=read("services/favorites/FavoritesCollectionsStore.qml");
  assert.match(panel,/property string collectionKey: ""/);
  assert.match(toggle,/property string collectionKey: ""/);
  assert.match(panel,/collectionStore\.acceptsKey\(resourceKey\)/);
  assert.match(toggle,/collectionStore\.acceptsKey\(resourceKey\)/);
  assert.match(panel,/collectionKey: panel\.collectionKey/);
  assert.match(cpu,/collectionKey: pane\.selectedResource/);
  assert.match(toggle,/collectionStore\.toggleMember\(collectionId,resourceKey\)/);
  assert.match(store,/Policy\.checkMemberKey\(key\)\.ok/);
  assert.match(store,/favorites-collections-v1\.json/);
  for(const source of [panel,toggle,cpu]) {
    assert.doesNotMatch(source,/execDetached|Process\s*\{|FileView\s*\{|loadMedia\(/);
  }
});
