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
vm.runInContext(policyText.replace(/^\\.pragma library\\s*$/m,""),policy);
const asList=x=>JSON.parse(JSON.stringify(x));

function harness(route,extra={}) {
  const scheduled=[];
  const calls={launches:0};
  const env={
    menuOpen:true,
    subjectNavigationOpen:true,
    contextTerminalRequested:false,
    subjectTerminalMode:"terminal",
    currentView:"ground",
    subjectNavigator:{indexOpen:false,currentPath:route},
    Qt:{callLater:function(f){scheduled.push(f)}},
    terminalView:{
      terminalState:"IDLE",
      openTerminal:function(){calls.launches++;return true;},
      get terminalMode(){return env.subjectNavigationOpen
        ?env.subjectTerminalMode:env.currentView;}
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
    assert.equal(h.env.currentView,"ground","CLASSIC currentView unchanged");
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
  }
});

test("root masking/actor identity still uses the SAME original controller",()=>{
  assert.equal((station.match(/StationTerminal\\s*\\{/g)||[]).length,1);
  assert.equal((pane.match(/StationTerminal\\s*\\{/g)||[]).length,0);
  assert.equal((surface.match(/StationTerminal\\s*\\{/g)||[]).length,0);
  assert.equal((navigator.match(/StationTerminal\\s*\\{/g)||[]).length,0);
  assert.match(terminal,/sessionMode === "terminal" \\? "weather-screen"/);
  assert.match(terminal,/kittyActorConfirmed/);
  assert.match(terminal,/SwayGeometry\\.observedContentWindow/);
  assert.match(terminal,/function closeTerminal\\(\\)/);
  assert.match(terminal,/swaymsg/);
  assert.match(station,/terminalHoleActive:[\\s\\S]*?subjectTerminalMode : currentView/);
  assert.match(station,/terminalMode: weatherStation\\.subjectNavigationOpen\\s*\\? weatherStation\\.subjectTerminalMode/);
  assert.match(station,/StationChassisCutout\\s*\\{/);
  assert.match(station,/mask: Region\\s*\\{/);
  assert.match(station,/onLeftClicked: weatherStation\\.closeContextTerminal\\(\\)/);
  assert.match(terminal,/onVisibleChanged:[\\s\\S]*?closeTerminal\\(\\)/);
});

test("TOOLS signal chain never activates a CLASSIC page or a second actor",()=>{
  assert.match(pane,/signal terminalLaunchRequested\\(string mode\\)/);
  assert.match(pane,/onClicked:[\\s\\S]*?toolsPane\\.terminalLaunchRequested\\(toolsPane\\.terminalTarget\\)/);
  assert.match(pane,/model: ToolsPolicy\\.CONSOLE_MODES/);
  assert.match(surface,/signal terminalLaunchRequested\\(string mode\\)/);
  assert.match(surface,/onTerminalLaunchRequested: function\\(mode\\)/);
  assert.match(navigator,/signal terminalLaunchRequested\\(string mode\\)/);
  assert.equal((navigator.match(/browser\\.terminalLaunchRequested\\(mode\\)/g)||[]).length,2);
  assert.match(station,/onTerminalLaunchRequested: function\\(mode\\) \\{\\s*weatherStation\\.launchSubjectTerminal\\(mode\\)/);
  assert.ok(!pane.includes("legacyPageRequested"),"TOOLS must not jump to CLASSIC");
  assert.ok(!surface.includes("toolsPane.legacyPageRequested"));
  assert.ok(!navigator.includes("toolsLivePane.legacyPageRequested"));
  assert.match(station,/function openLegacyFromSubject\\(pageId\\)/,
    "other legacy routes remain until separately accepted");
  for(const text of [pane,surface,navigator,policyText]){
    for(const forbidden of ["FileView {","Process {","kitty --",
                             "swaymsg","weatherstation-starmap","closeTerminal("])
      assert.ok(!text.includes(forbidden),"no duplicate terminal/controller: "+forbidden);
  }
});

test.todo("operator Fedora/Sway live exact actor/window/input-mask acceptance");
