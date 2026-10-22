#!/usr/bin/env python3
"""Apollo event -> already mounted widget view, with explicit safe routes."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"services/notifications/ApolloNotificationRoute.js"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"
POPUP=ROOT/"modules/Notifications.qml"
SHELL=ROOT/"shell.qml"

s=SERVICE.read_text()
h=HUB.read_text()
p=POPUP.read_text()
sh=SHELL.read_text()
assert 'signal apolloNavigationRequested(var destination)' in s
assert 'function apolloDestinationFor(eventId)' in s
assert 'ApolloNotificationRoute.routeFor(notifications.get(index))' in s
assert 'function hasApolloDestination(eventId)' in s
assert 'function requestApolloDestination(eventId)' in s
assert 'apolloNavigationRequested(destination);' in s
assert 'NotificationsService.requestApolloDestination(notificationId)' in h
assert 'NotificationsService.invokeExternalDefaultAction(notificationId)' in h
assert h.index('NotificationsService.invokeExternalDefaultAction(notificationId)') \
    < h.index('NotificationsService.requestApolloDestination(notificationId)')
assert 'NotificationsService.hasApolloDestination(notificationCard.notificationId)' in p
assert 'NotificationsService.requestApolloDestination(' in p
assert 'function onApolloNavigationRequested(destination)' in sh
assert 'shellRoot.openApolloNotificationRoute(destination);' in sh
assert 'function openApolloNotificationRoute(destination)' in sh
assert 'hospitalWindow.openReports(String(route.team || ""));' in sh
assert 'gitWindow.openGithubPullRequest(' in sh
assert 'cpuPlusWindow.selectThermalSubMode(route.subMode === "fan" ? 1 : 0);' in sh
assert 'weatherStationWindow.currentView = view;' in sh
assert 'notificationsHubWindow.activeFilter = "system";' in sh
assert 'root.bringAppHere(notificationEntry.sourceId, notificationEntry.source)' in h, (
    "Bring Here stays a separate workspace operation"
)

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const policy=fs.readFileSync(process.argv[1],'utf8').replace(/^\s*\.pragma library\s*$/m,'');
const service=fs.readFileSync(process.argv[2],'utf8');
const shell=fs.readFileSync(process.argv[3],'utf8');
function extract(src,name) {
 const i=src.indexOf('function '+name+'(');assert(i>=0,'missing '+name);
 const begin=src.indexOf('{',i);let level=0;
 for(let n=begin;n<src.length;n++) {
  if(src[n]==='{')level++;
  else if(src[n]==='}'&&--level===0)return src.slice(i,n+1);
 }
 throw Error('unclosed '+name);
}
const P={String,Number,Array,Object};
vm.runInNewContext(policy,P);
const notify=(sourceId,eventType,other)=>({
 sourceId, context:{eventType,...other}
});
const route=(...args)=>JSON.parse(JSON.stringify(P.routeFor(notify(...args))));
assert.deepStrictEqual(route('cpu-plus','hardware-thermal-limit'),
 {widget:'cpu',mode:'thermal',subMode:'temp'});
assert.deepStrictEqual(route('cpu-plus-fan-health','fan-rpm-recovered'),
 {widget:'cpu',mode:'thermal',subMode:'fan'});
assert.deepStrictEqual(route('cpu-plus-system','system-observation-report'),
 {widget:'cpu',mode:'system',subMode:'ALL'});
assert.deepStrictEqual(route('cpu-plus-resource-pressure','resource-pressure-warning',{metric:'memory'}),
 {widget:'cpu',mode:'system',subMode:'MEMORY'});
assert.deepStrictEqual(route('cpu-plus-resource-pressure','resource-pressure-warning',{metric:'storage'}),
 {widget:'cpu',mode:'system',subMode:'STORAGE'});
assert.deepStrictEqual(route('weather-brief','weather-daily-report'),
 {widget:'weather',view:'ground'});
assert.deepStrictEqual(route('weather-space-storm','geomagnetic-storm-escalated'),
 {widget:'weather',view:'space'});
assert.deepStrictEqual(route('hospital','room-reports-newly-listed',{roomId:'Team 3'}),
 {widget:'hospital',view:'reports',team:'Team 3'});
assert.deepStrictEqual(route('git-local-journal','git-journal-failed'),
 {widget:'git',view:'operations'});
assert.deepStrictEqual(route('github','github-review-replied-verified',
 {repository:'kudokudo1/The-Post-Apollo-Project',pullRequestNumber:456}),
 {widget:'git',view:'pull',repository:'kudokudo1/The-Post-Apollo-Project',number:456});
assert.deepStrictEqual(route('github','github-issue-closed-verified',{issueNumber:12}),
 {widget:'git',view:'issues'});
assert.deepStrictEqual(route('notifications-storage-health','notification-history-storage-error'),
 {widget:'notifications',view:'system'});
assert.strictEqual(P.routeFor(notify('Brave','hardware-thermal-limit')),null,
 'external browser must not get Apollo routing');
assert.strictEqual(P.routeFor(notify('cpu-plus','open-danger',{mode:'delete'})),null);
assert.strictEqual(P.routeFor(notify('cpu-plus',null)),null);
assert.strictEqual(P.routeFor(notify('apollo-update-monitor','software-update-offer')),null,
 'review/authorization-required update offer remains outside auto-routing');
assert.strictEqual(P.routeFor(notify('audio-default-output-health','audio-default-output-unavailable')),null,
 'no audio health menu adapter is registered yet');

const history=[{id:'event-1',sourceId:'cpu-plus',context:{eventType:'hardware-thermal-limit'}},
               {id:'event-2',sourceId:'Brave',context:{eventType:'hardware-thermal-limit'}}];
const signals=[];
const Service={
 String, notifications:{count:history.length,get:i=>history[i]},
 indexOfNotification:(model,id)=>history.findIndex(x=>x.id===id),
 ApolloNotificationRoute:{routeFor:P.routeFor},
 apolloNavigationRequested:route=>signals.push(JSON.parse(JSON.stringify(route)))
};
vm.runInNewContext(['apolloDestinationFor','hasApolloDestination','requestApolloDestination']
 .map(n=>extract(service,n)).join('\n'),Service);
assert.strictEqual(Service.requestApolloDestination('missing'),false);
assert.strictEqual(Service.requestApolloDestination('event-2'),false);
assert.strictEqual(Service.requestApolloDestination('event-1'),true);
assert.deepStrictEqual(signals,[{widget:'cpu',mode:'thermal',subMode:'temp'}],
 'only a real stored and allowlisted event can emit a route');

const calls=[];
const recorder=name=> (...v)=>{calls.push([name,...v]);return true;};
const cpu={menuOpen:false,open:recorder('cpu.open'),selectMode:recorder('cpu.mode'),
 selectThermalSubMode:recorder('cpu.thermal'),selectSystemSubMode:recorder('cpu.system')};
const weather={mainModes:[{id:'ground'},{id:'space'}],open:recorder('weather.open'),
 set currentView(v){calls.push(['weather.view',v])},
 set navigationIndex(v){calls.push(['weather.index',v])}};
const hospital={menuOpen:false,open:recorder('hospital.open'),
 openReports:recorder('hospital.reports'),openReception:recorder('hospital.reception')};
const git={menuOpen:false,open:recorder('git.open'),
 openGithubPullRequest:recorder('git.pr'),showGitPage:recorder('git.page'),
 showGitOperations:recorder('git.operations'),showGithubPage:recorder('github.page'),
 showGithubIssues:recorder('github.issues'),showGithubControl:recorder('github.control')};
const notifications={open:recorder('notifications.open'),
 set activeFilter(v){calls.push(['notifications.filter',v])}};
const Shell={String,Number,console,cpuPlusWindow:cpu,weatherStationWindow:weather,
 hospitalWindow:hospital,gitWindow:git,notificationsHubWindow:notifications,
 shellRoot:{requestControlKeyboard:recorder('focus')}};
vm.runInNewContext(extract(shell,'openApolloNotificationRoute'),Shell);
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'cpu',mode:'thermal',subMode:'fan'}),true);
assert.deepStrictEqual(calls,[['cpu.open'],['cpu.mode',2],['cpu.thermal',1],
 ['focus','cpu','notification-route']]);calls.length=0;
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'weather',view:'space'}),true);
assert(calls.some(x=>x[0]==='weather.view'&&x[1]==='space'));calls.length=0;
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'hospital',view:'reports',team:'Team 3'}),true);
assert(calls.some(x=>x[0]==='hospital.reports'&&x[1]==='Team 3'));calls.length=0;
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'git',view:'pull',repository:'owner/repo',number:12}),true);
assert(calls.some(x=>x[0]==='git.pr'&&x[1]==='owner/repo'&&x[2]===12));calls.length=0;
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'notifications',view:'system'}),true);
assert(calls.some(x=>x[0]==='notifications.filter'&&x[1]==='system'));calls.length=0;
assert.strictEqual(Shell.openApolloNotificationRoute({widget:'finance',view:'safety'}),false);
assert.deepStrictEqual(calls,[],'unsupported routes may not open arbitrary menus');
console.log('Apollo event identity, shell dispatch and fallback contracts: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(SERVICE),str(SHELL)],check=True)
print("Apollo notification destination routing: PASS")
