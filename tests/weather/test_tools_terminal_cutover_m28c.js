"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");

const policyText=read("widgets/weather/StationToolsSubjectPanelPolicy.js");
const pane=read("widgets/weather/StationToolsSubjectPane.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const terminal=read("widgets/weather/StationTerminal.qml");
const policy=vm.createContext({Array,Object,Math,Number,String,isFinite,Date});
vm.runInContext(policyText.replace(/^\.pragma library\s*$/m,""),policy);
const asList=x=>JSON.parse(JSON.stringify(x));

function harness(route,extra={}) {
  const scheduled=[];
  const calls={launches:0,routes:[]};
  const env={
    menuOpen:true,
    subjectNavigationOpen:true,
    contextTerminalRequested:false,
    subjectTerminalMode:"terminal",
    subjectNavigator:{
      indexOpen:false,currentPath:route,
      chooseRoute:function(next) {
        calls.routes.push(next);
        if (next!=="tools/terminal/star-map") return false;
        this.currentPath=next;
        this.indexOpen=false;
        return true;
      }
    },
    Qt:{callLater:function(f){scheduled.push(f)}},
    terminalView:{
      terminalState:"IDLE",
      outputName:"DP-3",
      openTerminal:function(){calls.launches++;return true;},
      get terminalMode(){return env.subjectTerminalMode;}
    }
  };
  if(extra.subjectNavigator)
    Object.assign(env.subjectNavigator,extra.subjectNavigator);
  Object.assign(env,Object.fromEntries(
    Object.entries(extra).filter(([k])=>k!=="subjectNavigator")
  ));
  const start=station.indexOf("function launchSubjectTerminal(mode) {");
  const end=station.indexOf("function closeContextTerminal()",start);
  assert.ok(start>=0 && end>start);
  const vmEnv=vm.createContext(env);
  vm.runInContext(station.slice(start,end),vmEnv);
  return {env:vmEnv,scheduled,calls};
}

test("TOOLS routes preserve the original STAR MAP plus seven context consoles",()=>{
  assert.deepEqual(asList(policy.CONSOLE_MODES),
    ["home","ground","sky","space","map","news","radio"]);
  assert.equal(policy.terminalModeForRoute("tools/terminal/star-map"),"terminal");
  for(const mode of policy.CONSOLE_MODES) {
    assert.equal(policy.terminalModeForRoute("tools/terminal/consoles",mode),mode);
    assert.equal(policy.isConsoleMode(mode),true);
  }
  assert.equal(policy.terminalModeForRoute("tools/terminal/consoles","not-a-mode"),"home");
  for(const other of ["tools/overview","tools/storage/cache","earth/overview",
                      "tools/terminal/bad",""])
    assert.equal(policy.terminalModeForRoute(other,"home"),"");
});

test("normal SUBJECTS launch remains on TOOLS and requests the sole terminal",()=>{
  for(const [route,mode] of [
    ["tools/terminal/star-map","terminal"],
    ...asList(policy.CONSOLE_MODES).map(mode=>["tools/terminal/consoles",mode])
  ]) {
    const h=harness(route);
    assert.equal(h.env.launchSubjectTerminal(mode),true,route+" "+mode);
    assert.equal(h.env.contextTerminalRequested,true);
    assert.equal(h.env.subjectTerminalMode,mode);
    assert.equal(h.env.subjectNavigationOpen,true,"no CLASSIC transfer");
    assert.equal(h.env.subjectNavigator.currentPath,route,"native TOOLS route unchanged");
    assert.equal(h.calls.launches,0,"launch deferred until view visible");
    assert.equal(h.scheduled.length,1);
    h.scheduled[0]();
    assert.equal(h.calls.launches,1,"one original actor");
    assert.equal(h.env.launchSubjectTerminal(mode),false,"cannot double-launch");
  }
});

test("reject unauthorized modes/routes, INDEX and closed station",()=>{
  for(const [route,mode,extra] of [
    ["tools/terminal/star-map","home",{}],
    ["tools/terminal/star-map","news",{}],
    ["tools/terminal/consoles","terminal",{}],
    ["tools/terminal/consoles","; swaymsg kill",{}],
    ["tools/overview","home",{}],
    ["earth/overview","home",{}],
    ["tools/terminal/consoles","home",{menuOpen:false}],
    ["tools/terminal/consoles","home",{subjectNavigationOpen:false}],
    ["tools/terminal/consoles","home",{contextTerminalRequested:true}],
    ["tools/terminal/consoles","home",{subjectNavigator:{indexOpen:true}}],
  ]) {
    const h=harness(route,extra);
    assert.equal(h.env.launchSubjectTerminal(mode),false,route+" "+mode);
    assert.equal(h.calls.launches,0);
    assert.equal(h.scheduled.length,0);
  }
  const starting=harness("tools/terminal/star-map",{
    terminalView:{terminalState:"STARTING",openTerminal(){throw Error("NO");}}
  });
  assert.equal(starting.env.launchSubjectTerminal("terminal"),false);
  const noScreen=harness("tools/terminal/star-map",{
    terminalView:{terminalState:"IDLE",outputName:"",
                  openTerminal(){throw Error("NO");}}
  });
  assert.equal(noScreen.env.launchSubjectTerminal("terminal"),false,
               "missing compositor output must refuse before overlay");
  assert.equal(noScreen.env.contextTerminalRequested,false);
});

test("queued session cannot start after route, owner or host changes",()=>{
  for(const update of [
    env=>{env.subjectNavigator.currentPath="media/news/reports";},
    env=>{env.subjectNavigationOpen=false;},
    env=>{env.menuOpen=false;},
    env=>{env.contextTerminalRequested=false;},
    env=>{env.subjectTerminalMode="news";}
  ]) {
    const h=harness("tools/terminal/star-map");
    assert.equal(h.env.launchSubjectTerminal("terminal"),true);
    update(h.env);
    h.scheduled[0]();
    assert.equal(h.calls.launches,0);
    assert.equal(h.env.contextTerminalRequested,false,
                 "aborted launch cannot strand hidden SUBJECTS");
  }
});

test("SUBJECTS header terminal reuses TOOLS STAR MAP route and exact one Kitty actor",()=>{
  for(const from of ["home/overview","weather/conditions/current",
                     "media/news/full","magick/overview",
                     "tools/terminal/star-map"]) {
    const h=harness(from);
    assert.equal(h.env.launchHeaderTerminal(),true,from);
    assert.deepEqual(h.calls.routes,["tools/terminal/star-map"]);
    assert.equal(h.env.subjectNavigator.currentPath,"tools/terminal/star-map");
    assert.equal(h.env.subjectNavigator.indexOpen,false);
    assert.equal(h.env.contextTerminalRequested,true);
    assert.equal(h.env.subjectTerminalMode,"terminal");
    assert.equal(h.scheduled.length,1);
    assert.equal(h.env.launchHeaderTerminal(),false,"no duplicate header launch");
    h.scheduled[0]();
    assert.equal(h.calls.launches,1,"launch from same root controller");
  }
  const index=harness("home/overview",{
    subjectNavigator:{indexOpen:true}
  });
  assert.equal(index.env.launchHeaderTerminal(),true);
  assert.equal(index.env.subjectNavigator.indexOpen,false,
               "the header exits INDEX through a real subject route");
});

test("SUBJECTS header terminal rejects unavailable host and invalid navigation",()=>{
  for(const extra of [
    {menuOpen:false},{subjectNavigationOpen:false},
    {contextTerminalRequested:true},
    {terminalView:{terminalState:"VISIBLE",outputName:"DP-3"}},
    {terminalView:{terminalState:"IDLE",outputName:""}},
    {subjectNavigator:{chooseRoute:()=>false}}
  ]) {
    const h=harness("home/overview",extra);
    assert.equal(h.env.launchHeaderTerminal(),false);
    assert.equal(h.env.contextTerminalRequested,
                 !!extra.contextTerminalRequested);
    assert.equal(h.calls.launches,0);
    assert.equal(h.scheduled.length,0);
    if(extra.subjectNavigator && extra.subjectNavigator.chooseRoute)
      assert.equal(h.env.subjectNavigator.currentPath,"home/overview",
                   "route denial must not overlay an unrelated page");
  }
});

test("header terminal deferred start revokes when subject owner changes",()=>{
  const h=harness("earth/maps/full");
  assert.equal(h.env.launchHeaderTerminal(),true);
  assert.equal(h.scheduled.length,1);
  h.env.subjectNavigator.currentPath="media/news/full";
  h.scheduled[0]();
  assert.equal(h.calls.launches,0);
  assert.equal(h.env.contextTerminalRequested,false);
});

test("header control occupies former CLOSE slot and switches TERMINAL/CLOSE",()=>{
  const start=station.indexOf("id: contextTerminalClose");
  const end=station.indexOf("id: terminalHeaderDivider",start);
  assert.ok(start>0 && end>start);
  const button=station.slice(start,end);
  assert.match(button,/label: terminalSessionActive \? "CLOSE" : "TERMINAL"/);
  assert.match(button,/width: 88/);
  assert.match(button,/available: weatherStation\.menuOpen/);
  assert.match(button,/subjectNavigationOpen[\s\S]*?terminalView\.outputName/);
  assert.match(button,/destructive: terminalSessionActive/);
  assert.match(button,/accentColor: terminalSessionActive \? Colors\.red : Colors\.cyan/);
  assert.match(button,/onLeftClicked: \{[\s\S]*?if \(terminalSessionActive\)[\s\S]*?weatherStation\.closeContextTerminal\(\);[\s\S]*?else[\s\S]*?weatherStation\.launchHeaderTerminal\(\);/);
  assert.match(station,/function launchHeaderTerminal\(\)/);
  assert.equal((station.match(/id: contextTerminalClose/g)||[]).length,1);
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
});

test("root masking/actor identity still uses the SAME original controller",()=>{
  assert.equal((station.match(/StationTerminal\s*\{/g)||[]).length,1);
  assert.equal((pane.match(/StationTerminal\s*\{/g)||[]).length,0);
  assert.equal((surface.match(/StationTerminal\s*\{/g)||[]).length,0);
  assert.equal((navigator.match(/StationTerminal\s*\{/g)||[]).length,0);
  assert.match(terminal,/sessionMode === "terminal" \? "weather-screen"/);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(terminal,/SwayGeometry\.observedContentWindow/);
  assert.match(terminal,/function closeTerminal\(\)/);
  assert.match(terminal,/swaymsg/);
  assert.match(station,/terminalHoleActive:[\s\S]*?terminalView\.sessionMode === subjectTerminalMode/);
  assert.match(station,/terminalMode: weatherStation\.subjectTerminalMode/);
  assert.match(station,/StationChassisCutout\s*\{/);
  assert.match(station,/mask: Region\s*\{/);
  assert.match(station,/weatherStation\.closeContextTerminal\(\);/);
  assert.match(station,/weatherStation\.launchHeaderTerminal\(\);/);
  assert.match(terminal,/onVisibleChanged:[\s\S]*?closeTerminal\(\)/);
});

test("TOOLS signal chain never activates a CLASSIC page or a second actor",()=>{
  assert.match(pane,/signal terminalLaunchRequested\(string mode\)/);
  assert.match(pane,/onClicked:[\s\S]*?toolsPane\.terminalLaunchRequested\(toolsPane\.terminalTarget\)/);
  assert.match(pane,/model: ToolsPolicy\.CONSOLE_MODES/);
  assert.match(surface,/signal terminalLaunchRequested\(string mode\)/);
  assert.match(surface,/onTerminalLaunchRequested: function\(mode\)/);
  assert.match(navigator,/signal terminalLaunchRequested\(string mode\)/);
  assert.equal((navigator.match(/browser\.terminalLaunchRequested\(mode\)/g)||[]).length,2);
  assert.match(station,/onTerminalLaunchRequested: function\(mode\) \{\s*weatherStation\.launchSubjectTerminal\(mode\)/);
  assert.ok(!pane.includes("legacyPageRequested"),"TOOLS must not jump to CLASSIC");
  assert.ok(!surface.includes("toolsPane.legacyPageRequested"));
  assert.ok(!navigator.includes("toolsLivePane.legacyPageRequested"));
  assert.ok(!station.includes("openLegacyFromSubject"),"legacy root route retired");
  for(const text of [pane,surface,navigator,policyText]){
    for(const forbidden of ["FileView {","Process {","kitty --",
                             "swaymsg","weatherstation-starmap","closeTerminal("])
      assert.ok(!text.includes(forbidden),"no duplicate terminal/controller: "+forbidden);
  }
});

test.todo("operator Fedora/Sway live exact actor/window/input-mask acceptance");
