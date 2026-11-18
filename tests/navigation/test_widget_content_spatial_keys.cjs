#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");
const policy={};
vm.runInNewContext(
  read("components/WidgetContentSpatialPolicy.js").replace(/^\.pragma library\s*/m,""),
  policy,{filename:"WidgetContentSpatialPolicy.js"});
const nav=read("components/WidgetContentKeyboardNavigator.qml");
const button=read("components/ActionButton.qml");
const weather=read("widgets/weather/WeatherStationW.qml");
const finance=read("widgets/FinanceW.qml");
const tasks=read("widgets/TasksW.qml");
const company=read("widgets/CompanyNetworkW.qml");
const overview=read("widgets/weather/StationSubjectOverviewRail.qml");

test("HJKL and arrows are EXACT directional alternatives",()=>{
  const vectors=[[16777234,72,-1,0],[16777237,74,0,1],
                 [16777235,75,0,-1],[16777236,76,1,0]];
  for(const [arrow,vim,dx,dy] of vectors) {
    assert.deepEqual([...policy.directionForKey(arrow)],[dx,dy]);
    assert.deepEqual([...policy.directionForKey(vim)],[dx,dy]);
  }
  for(const key of [9,13,27,65,83,0])
    assert.equal(policy.directionForKey(key),null);
});
test("Spatial selection starts on content and follows row/column, bounded at edge",()=>{
  const r=[
    {x:10,y:15,width:75,height:35,visible:true},
    {x:115,y:15,width:75,height:35,visible:true},
    {x:10,y:85,width:75,height:35,visible:true},
    {x:115,y:85,width:75,height:35,visible:true},
    {x:500,y:500,width:75,height:35,visible:false}
  ];
  assert.equal(policy.initialIndex(r),0);
  assert.equal(policy.nextIndex(r,-1,1,0),0);
  assert.equal(policy.nextIndex(r,0,1,0),1);
  assert.equal(policy.nextIndex(r,0,0,1),2);
  assert.equal(policy.nextIndex(r,1,0,1),3);
  assert.equal(policy.nextIndex(r,2,1,0),3);
  assert.equal(policy.nextIndex(r,0,-1,0),0);
  assert.equal(policy.nextIndex(r,3,1,0),3);
  assert.equal(policy.nextIndex([],0,1,0),-1);
});
test("Content selector is visibly separate from ModeButton and never owns focus",()=>{
  assert.match(nav,/objectName: "widget-content-keyboard-selection"/);
  assert.match(nav,/border.color: Colors.yellow/);
  assert.match(nav,/focus: false/);
  assert.doesNotMatch(nav,/Keys\.onPressed|Shortcut \{|MouseArea \{/);
  assert.match(nav,/property Item contentRoot: null/);
  assert.match(nav,/function selectInitial\(\)/);
  assert.match(nav,/function handleDirectionKey\(key,modifiers\)/);
  assert.match(nav,/modifiers!==Qt.NoModifier/);
  assert.match(nav,/function scrollIntoView\(target\)/);
  assert.match(nav,/node.keyboardNavTarget === true/);
  assert.match(nav,/node.destructive !== true/);
  assert.match(nav,/const kind=button.keyboardActivationSignal/);
  assert.match(nav,/if\(kind!=="leftClicked" && kind!=="triggered"/);
  assert.match(nav,/kind!=="clicked"/);
  assert.match(nav,/button.leftClicked\(null\)/);
  assert.match(button,/property bool keyboardNavTarget: true/);
  assert.match(button,/property string keyboardActivationSignal: ""/);
  assert.match(overview,/keyboardActivationSignal: "clicked"/);
});
test("Tab owns main rail; arrows/HJKL never update main navigation cursor",()=>{
  for(const [file,source,selection] of [
    ["TASKS",tasks,"tasksContentKeys"],
    ["Company",company,"companyContentKeys"]
  ]) {
    assert.match(source,/function cycleMainMode\(direction\)/);
    assert.match(source,/Qt.Key_Tab/);
    assert.match(source,/Qt.Key_Backtab/);
    assert.match(source,/Qt.Key_H/);
    assert.match(source,/Qt.Key_J/);
    assert.match(source,/Qt.Key_K/);
    assert.match(source,/Qt.Key_L/);
    assert.match(source,new RegExp(selection+"\\.handleDirectionKey"));
    assert.match(source,new RegExp(selection+"\\.activate\\(\\)"));
    assert.doesNotMatch(
      source.slice(source.indexOf("function moveContentKey(key,modifiers)"),
        source.indexOf("function moveNavigationCursor(direction)")),
      /keyboardModeCursor|selectMainMode/);
    assert.match(source,/WidgetContentKeyboardNavigator \{/);
    assert.doesNotMatch(source,/context: Qt.WindowShortcut/);
  }
});
test("Weather content selector stays inside workspace, not SUBJECTS rail",()=>{
  assert.match(weather,/id: weatherContentKeys/);
  assert.match(weather,/anchors.fill: subjectNavigator/);
  assert.match(weather,/contentRoot: subjectNavigator/);
  assert.match(weather,/return weatherContentKeys.handleDirectionKey\(key,modifiers\)/);
  assert.match(weather,/return weatherContentKeys.activate\(\)/);
  assert.match(weather,/function cycleMainMode\(direction\)/);
  assert.match(weather,/subjectNavigator.cycleSubjects\(direction\)/);
  assert.match(weather,/function cycleBottomSubMode\(direction\)/);
  assert.match(weather,/subjectNavigator.cycleWorkspaceTab\(direction\)/);
  assert.match(weather,/!subjectNavigator.indexOpen/);
});
test("Finance plain arrows navigate work area, not left mode rail",()=>{
  assert.match(finance,/id: financeContentKeys/);
  assert.match(finance,/contentRoot: workArea/);
  assert.match(finance,/return financeContentKeys.handleDirectionKey\(key,modifiers\)/);
  assert.match(finance,/return financeContentKeys.move\(0,Number\(direction\)<0\?-1:1\)/);
  assert.match(finance,/return financeContentKeys.move\(Number\(direction\)<0\?-1:1,0\)/);
  assert.match(finance,/return financeContentKeys.activate\(\)/);
  assert.match(finance,/financeKeyboardAnchor.activeFocus/);
  assert.match(finance,/function cycleMainMode\(direction\)/);
  assert.match(finance,/function cycleBudgetSubMode\(direction\)/);
  assert.match(finance,/function cycleBudgetSection\(direction\)/);
  assert.match(finance,/keyboardNavTarget: false\s+\/\/ Shift\+arrow/);
  assert.match(finance,/keyboardActivationSignal: "leftClicked"/);
  assert.doesNotMatch(finance,
    /function moveNavigationZone\(direction\) \{\s+if \(selectedMainMode !== "budget"\)/);
});
