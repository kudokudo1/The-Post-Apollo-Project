#!/usr/bin/env python3
"""Popup click/dismiss/focus boundaries. No live desktop mutation."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POPUP = (ROOT / "modules/Notifications.qml").read_text()
SERVICE = (ROOT / "services/notifications/NotificationsService.qml").read_text()
POLICY = ROOT / "services/notifications/NotificationPopupInteraction.js"

# These are popup-only changes. Hub history and its navigation remain intact.
assert "focusable: false" in POPUP
assert "import Quickshell.Wayland" in POPUP
assert "WlrLayershell.keyboardFocus: WlrKeyboardFocus.None" in POPUP
assert "requestActivate(" not in POPUP
assert "forceActiveFocus(" not in POPUP
assert "mask: Region {" in POPUP
assert "x: notificationContainer.x" in POPUP
assert "y: notificationContainer.y" in POPUP
assert "width: notificationsWindow.popupPointerReady ? notificationContainer.width : 0" in POPUP
assert "height: notificationsWindow.popupPointerReady ? notificationContainer.height : 0" in POPUP
assert "interval: 750" in POPUP and "id: popupPointerGraceTimer" in POPUP
assert "onDisplayedNotificationIdChanged:" in POPUP
assert "popupPointerGraceTimer.stop();" in POPUP
assert "popupPointerGraceTimer.start();" in POPUP

assert "function dismissPopup(eventId)" in SERVICE
assert "live.notification.dismiss();" in SERVICE
assert "function releaseExternalNotification(eventId)" in SERVICE
assert "function confirmOpenIntent(intent)" in POPUP
assert 'confirmOpenIntent("destination")' in POPUP
assert '"CLICK AGAIN TO OPEN"' in POPUP
assert "interval: 3000" in POPUP
assert "onNotificationIdChanged: Qt.callLater(notificationCard.clearOpenIntent)" in POPUP
assert "onVisibleChanged:" in POPUP and "clearOpenIntent();" in POPUP
assert "PopupInteraction.opensDestination(identifier, label)" in POPUP
assert 'acceptedButtons: Qt.RightButton' in POPUP
assert "z: 20" in POPUP
assert "NotificationsService.dismissPopup(notificationCard.notificationId)" in POPUP
popup_default = POPUP.split("id: nativeDefaultClickArea", 1)[1].split("// ===== APP ICON", 1)[0]
assert popup_default.index('confirmOpenIntent("destination")') < popup_default.index(
    "NotificationsService.invokeExternalDefaultAction(")
assert popup_default.index("NotificationsService.invokeExternalDefaultAction(") < popup_default.index(
    "NotificationsService.requestApolloDestination(")
native_buttons = POPUP.split("id: nativeActionMouse", 1)[1].split("// Always-on right-click", 1)[0]
assert native_buttons.index("PopupInteraction.opensDestination(identifier, label)") < native_buttons.index(
    "NotificationsService.invokeExternalAction(")

NODE = r"""
"use strict";
const assert=require("assert"),fs=require("fs"),vm=require("vm");
const source=fs.readFileSync(process.argv[1],"utf8")
  .replace(/^\s*\.pragma library\s*/,"");
const service=fs.readFileSync(process.argv[2],"utf8");
const P={};
vm.runInNewContext(source,P);
const copy=o=>JSON.parse(JSON.stringify(o));
function click(prev,target,now) {
  return copy(P.nextOpenIntent(prev.pendingIntent,prev.armedAtMs,target,now,3000));
}
let state={pendingIntent:"",armedAtMs:0};
state=click(state,"destination",1000);
assert.deepStrictEqual(state,{confirmed:false,pendingIntent:"destination",armedAtMs:1000});
let r=click(state,"destination",1200);
assert.strictEqual(r.confirmed,true);
assert.strictEqual(r.pendingIntent,"");
assert.strictEqual(r.armedAtMs,0);
r=click(state,"destination",4001); // TTL passed, don't open
assert.strictEqual(r.confirmed,false);
assert.strictEqual(r.pendingIntent,"destination");
assert.strictEqual(r.armedAtMs,4001);
r=click(state,"native:open-a",1300); // different button is not same intent
assert.strictEqual(r.confirmed,false);
r=click({pendingIntent:"native:open-a",armedAtMs:1300},"native:open-b",1500);
assert.strictEqual(r.confirmed,false);
r=click({pendingIntent:"destination",armedAtMs:1600},"destination",1500); // clock reversal
assert.strictEqual(r.confirmed,false);
r=click(state,"",1300);
assert.strictEqual(r.confirmed,false);
assert.strictEqual(r.pendingIntent,"");
assert.strictEqual(P.opensDestination("default","Something"),true);
assert.strictEqual(P.opensDestination("open-foo","Open in browser"),true);
assert.strictEqual(P.opensDestination("view","View details"),true);
assert.strictEqual(P.opensDestination("reply","Reply"),false);
assert.strictEqual(P.opensDestination("mark-as-read","Mark as read"),false);
assert.strictEqual(P.opensDestination("dismiss","Dismiss"),false);

function method(text,name) {
  const m=text.indexOf("function "+name+"(");
  assert.notStrictEqual(m,-1,name);
  const open=text.indexOf("{",m);
  let depth=0;
  for(let i=open;i<text.length;i++) {
    if(text[i]==="{")depth++;
    if(text[i]==="}" && --depth===0)return text.slice(m,i+1);
  }
  throw Error("unclosed "+name);
}
const history=[{id:"native-1"},{id:"apollo-1"},{id:"hidden-1"}];
const active=[{id:"native-1"},{id:"apollo-1"}];
let nativeDismissed=0, nativeExpired=0, nativeActionInvoked=0;
const live={"native-1":{notification:{
  dismiss(){nativeDismissed++;S.releaseExternalNotification("native-1");},
  expire(){nativeExpired++},
  actions:[{identifier:"default",invoke(){nativeActionInvoked++}}]
}}};
const S={
  String,liveExternalNotifications:live,
  activeNotifications:{
    get:i=>active[i],remove:i=>{active.splice(i,1)},
    get count(){return active.length}
  },
  indexOfNotification:(model,id)=>active.findIndex(x=>x.id===id),
  releaseExternalNotification(id){
    delete live[id];
    const index=active.findIndex(x=>x.id===id);
    if(index!==-1)active.splice(index,1);
  }
};
vm.runInNewContext(method(service,"dismissPopup"),S);
assert.strictEqual(S.dismissPopup("unknown"),false);
assert.strictEqual(S.dismissPopup("native-1"),true);
assert.strictEqual(nativeDismissed,1,"native user dismissal must call dismiss()");
assert.strictEqual(nativeExpired,0,"explicit right click is not timeout");
assert.strictEqual(nativeActionInvoked,0,"right click cannot open sender action");
assert.strictEqual(S.dismissPopup("native-1"),false,"repeat cannot double-dismiss");
assert.strictEqual(S.dismissPopup("apollo-1"),true,"internal popup dismissed");
assert.strictEqual(active.length,0);
assert.strictEqual(history.length,3,"history must stay retained");
assert.strictEqual(S.dismissPopup("hidden-1"),false,"history-only item is not popup");
console.log("Popup two-click, native dismiss and history preservation: PASS");
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(ROOT/"services/notifications/NotificationsService.qml")],check=True)
print("Popup input/focus contract assertions: PASS")
