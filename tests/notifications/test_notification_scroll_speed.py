#!/usr/bin/env python3
"""Notifications Control Bay: scroll-speed wheel routing and persistent lock."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"
BAR=ROOT/"components/NeonScrollBar.qml"

s=SERVICE.read_text()
h=HUB.read_text()
b=BAR.read_text()
assert 'property real scrollSpeedMultiplier: 1.0' in s
assert 'property bool scrollSpeedLocked: false' in s
assert 'function setScrollSpeed(value)' in s
assert 'function toggleScrollSpeedLock()' in s
assert 'path: Quickshell.dataPath("notification-scroll-settings.json")' in s
assert 'atomicWrites: true' in s
assert 'id: scrollSettingsSaveTimer' in s
assert 'id: scrollSpeedControls' in h
assert 'id: historySpeedSlider' in h
assert 'id: scrollSpeedRail' in h
assert 'id: scrollSpeedHandle' in h
assert 'id: historySpeedWheel' in h
assert 'acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad' in h
assert 'blocking: true' in h.split('id: historySpeedWheel',1)[1].split('header: Item',1)[0]
assert 'target: null' in h.split('id: historySpeedWheel',1)[1].split('header: Item',1)[0]
assert 'delta * NotificationsService.scrollSpeedMultiplier' in h
assert 'scrollBarArea.moveBy(' in h
assert 'scrollBarArea.wheelDelta(event)' in h
assert 'accountForContentOrigin: true' in h
assert 'wheelEnabled: false' in h
assert 'root.requestHistoryScrollSpeed(' in h
assert 'enabled: !NotificationsService.scrollSpeedLocked' in h
assert 'onTriggered: NotificationsService.toggleScrollSpeedLock()' in h
assert 'text: NotificationsService.scrollSpeedMultiplier.toFixed(1) + "×"' in h
assert 'property int controlBayHeight: 220' in h
assert 'property int wheelStep: 42' in b  # do not alter global defaults

# The Control Bay is fixed below the list, not an overlay that hides cards.
bay=h.split('// ===== CONTROL BAY',1)[1].split('// ===== CLEAR-ALL CONFIRMATION',1)[0]
assert bay.index('id: scrollSpeedControls') > bay.index('id: controlBay')
assert 'topMargin: 70' in bay
assert 'leftMargin: 22' in bay and 'rightMargin: 22' in bay
assert 'label: NotificationsService.scrollSpeedLocked ? "LOCKED" : "LOCK"' in bay

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
function extract(text,name) {
 const at=text.indexOf('function '+name+'(');assert(at>=0, 'missing '+name);
 const brace=text.indexOf('{',at);let depth=0;
 for (let i=brace;i<text.length;i++) {
  if(text[i]==='{')depth++;
  else if(text[i]==='}' && --depth===0)return text.slice(at,i+1);
 }
 throw new Error('unclosed '+name);
}
const saved=[];
const State={
 Math,Number,JSON,Object,Array,String,console,
 scrollSpeedMultiplier:1.0,scrollSpeedLocked:false,scrollSettingsReady:true,
 scrollSettingsSaveTimer:{restart() { State.savesScheduled++; }},
 scrollSettingsFile:{
  setText(text) {saved.push(text);},
  text() {return State.fileContent || '';}
 },
 savesScheduled:0,fileContent:''
};
vm.runInNewContext(['normalizeScrollSpeed','setScrollSpeed',
 'toggleScrollSpeedLock','scheduleScrollSettingsSave',
 'saveScrollSettings','loadScrollSettings'].map(n=>extract(source,n)).join('\n'),State);
assert.strictEqual(State.normalizeScrollSpeed(0),0.5);
assert.strictEqual(State.normalizeScrollSpeed(500),3);
assert.strictEqual(State.normalizeScrollSpeed(1.26),1.3);
assert.strictEqual(State.normalizeScrollSpeed('bad'),1);
assert.strictEqual(State.setScrollSpeed(2.16),true);
assert.strictEqual(State.scrollSpeedMultiplier,2.2);
assert.strictEqual(State.savesScheduled,1);
assert.strictEqual(State.setScrollSpeed(2.2),false,'unchanged speed has no extra writes');
State.toggleScrollSpeedLock();
assert.strictEqual(State.scrollSpeedLocked,true);
assert.strictEqual(State.savesScheduled,2);
assert.strictEqual(State.setScrollSpeed(0.5),false,'locked control rejects edits');
assert.strictEqual(State.scrollSpeedMultiplier,2.2,'lock is not a zero-speed switch');
State.saveScrollSettings();
const value=JSON.parse(saved[saved.length-1]);
assert.strictEqual(value.scrollSpeedMultiplier,2.2);
assert.strictEqual(value.scrollSpeedLocked,true);
State.scrollSpeedMultiplier=1;
State.scrollSpeedLocked=false;
State.fileContent=saved[saved.length-1];
State.loadScrollSettings();
assert.strictEqual(State.scrollSpeedMultiplier,2.2);
assert.strictEqual(State.scrollSpeedLocked,true);
State.fileContent='{"scrollSpeedMultiplier":8,"scrollSpeedLocked":false}';
State.loadScrollSettings();
assert.strictEqual(State.scrollSpeedMultiplier,3,'loaded values clamped');
assert.strictEqual(State.scrollSpeedLocked,false);
State.fileContent='{invalid';
State.loadScrollSettings();
assert.strictEqual(State.scrollSpeedMultiplier,3,'malformed prefs retain last valid');
State.scrollSettingsReady=false;
State.savesScheduled=2;
State.toggleScrollSpeedLock();
assert.strictEqual(State.savesScheduled,2,'never save during initial preference loading');
console.log('Scroll speed normalization, lock, and preference storage: PASS');
"""
subprocess.run(["node","-e",NODE,str(SERVICE)],check=True)
print("Notification Control Bay scroll-speed contracts: PASS")
