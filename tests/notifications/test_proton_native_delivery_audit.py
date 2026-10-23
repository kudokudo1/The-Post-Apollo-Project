#!/usr/bin/env python3
"""Opt-in and privacy-only Chromium/Brave -> Quickshell metadata audit."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"services/notifications/mail/ProtonNativeDeliveryAudit.js"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
source=POLICY.read_text(encoding="utf8")
qml=SERVICE.read_text(encoding="utf8")
assert source.startswith(".pragma library")
assert 'import "mail/ProtonNativeDeliveryAudit.js" as ProtonNativeDeliveryAudit' in qml
assert 'POST_APOLLO_PROTON_DELIVERY_AUDIT' in qml
assert 'protonNativeAuditSamples >= 12' in qml
assert 'root.auditProtonNativeDelivery(notification);' in qml
assert 'ProtonNativeDeliveryAudit.safeLine(observed)' in qml
assert 'console.info(line)' in qml
assert 'protonNativeAuditEnabled' in qml

for forbidden in (
        ".summary", ".body", ".image", ".appIcon", ".cookie",
        "localStorage", "getAttribute", "fetch(", "XMLHttpRequest",
        "sendNativeMessage", "NotificationAction.invoke", ".click("):
    assert forbidden not in source, forbidden

NODE=r"""
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const text=fs.readFileSync(process.argv[1],"utf8")
 .replace(/^\s*\.pragma library\s*$/m,"");
const ctx={String,Number,Math,Object,Array,RegExp};
vm.runInNewContext(text,ctx);
const clone=x=>JSON.parse(JSON.stringify(x));
const probe=n=>clone(ctx.collect(n));
const isBrowser=ctx.isBrowserNotification;
assert.strictEqual(isBrowser("Brave",""),true);
assert.strictEqual(isBrowser("Brave Browser",""),true);
assert.strictEqual(isBrowser("","brave-browser"),true);
assert.strictEqual(isBrowser("","com.brave.browser"),true);
assert.strictEqual(isBrowser("Chromium",""),true);
assert.strictEqual(isBrowser("Firefox",""),true);
assert.strictEqual(isBrowser("youtube-brave-tampered",""),false);
assert.strictEqual(isBrowser("unknown","unknown"),false);
assert.strictEqual(probe(null),null);
assert.strictEqual(probe({appName:"Other App",desktopEntry:"app",hints:{tag:"PRIVATE"}}),null);
const privateData={
 appName:"Brave Browser",desktopEntry:"brave-browser",
 summary:"SECRET SUBJECT 182",body:"private.mail@example.test",
 hints:{
  "desktop-entry":"private.fake",
  "category":"email.arrived",
  "x-kde-origin-name":"mail.proton.me",
  "tag":"SECRET_MESSAGE_ID_123",
  "unexpected-secret-hint-name":"SECRET HINT VALUE"
 },
 actions:[{identifier:"PRIVATE-action-key",text:"PRIVATE-action-label"}]
};
const result=probe(privateData);
assert.deepStrictEqual(result,{
 browserCandidate:true,hintCount:5,
 categoryHint:true,desktopEntryHint:true,kdeOriginHint:true,tagHint:true,
 actionCount:1,messageIdentityVerified:false,canMutate:false
});
const line=ctx.safeLine(result);
assert.ok(line.startsWith("PA_PROTON_DELIVERY_AUDIT"));
assert.ok(line.includes("tagHint=true"));
assert.ok(line.includes("identity NOT verified"));
for(const secret of [
  "SECRET", "PRIVATE", "mail.proton.me", "@example", "email.arrived",
  "unexpected-secret-hint-name", "desktop-entry", "Brave Browser"
]){
  // The fixed presence field desktopEntryHint is safe, but the raw key
  // "desktop-entry" must never appear as its own token.
  assert.ok(!line.includes(secret),secret);
}
assert.deepStrictEqual(probe({...privateData,hints:{}}),{
 browserCandidate:true,hintCount:0,
 categoryHint:false,desktopEntryHint:false,kdeOriginHint:false,tagHint:false,
 actionCount:1,messageIdentityVerified:false,canMutate:false
});
assert.strictEqual(ctx.safeLine({...result,tagHint:"secret"}),"");
assert.strictEqual(ctx.safeLine({...result,messageIdentityVerified:true}),"");
assert.strictEqual(ctx.safeLine({...result,canMutate:true}),"");
assert.strictEqual(ctx.safeLine({...result,extra:"private"}),"");
assert.strictEqual(ctx.safeLine({...result,hintCount:100}),"");
assert.strictEqual(ctx.safeLine({...result,actionCount:20}),"");
assert.strictEqual(ctx.safeLine(null),"");
assert.strictEqual(probe({...privateData,
 hints:Object.fromEntries(Array.from({length:200},(_,i)=>["SECRET"+i,"PRIVATE"]))}).hintCount,99);
assert.strictEqual(probe({...privateData,
 actions:Array.from({length:200},()=>({text:"PRIVATE"}))}).actionCount,9);
console.log("Proton native metadata presence-only audit: PASS");
"""
subprocess.run(["node","-e",NODE,str(POLICY)],check=True)
print("Proton native delivery audit contracts: PASS")
