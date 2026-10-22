#!/usr/bin/env python3
"""Offline Chromium/Firefox read-only Proton companion contract tests."""
from pathlib import Path
import importlib.util
import io
import json
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "integrations/proton/browser"
JS = PILOT / "background.js"
HOST = PILOT / "proton_native_host.py"
CHROMIUM = json.loads((PILOT / "manifest.json").read_text())
FIREFOX = json.loads((PILOT / "manifest.firefox.json").read_text())
CHROMIUM_HOST = json.loads((PILOT / "native-host.example.json").read_text())
FIREFOX_HOST = json.loads((PILOT / "native-host.firefox.example.json").read_text())

assert CHROMIUM["manifest_version"] == FIREFOX["manifest_version"] == 3
assert CHROMIUM["background"] == {"service_worker": "background.js"}
assert FIREFOX["background"] == {"scripts": ["background.js"]}
assert "browser_specific_settings" not in CHROMIUM
FIREFOX_ID = FIREFOX["browser_specific_settings"]["gecko"]["id"]
assert FIREFOX_HOST["allowed_extensions"] == [FIREFOX_ID]
assert "allowed_origins" not in FIREFOX_HOST
assert CHROMIUM_HOST["allowed_origins"] == ["chrome-extension://REPLACE_WITH_ACTUAL_EXTENSION_ID/"]
assert "allowed_extensions" not in CHROMIUM_HOST
for manifest in (CHROMIUM, FIREFOX):
    assert sorted(manifest["permissions"]) == ["activeTab", "nativeMessaging"]
    assert "content_scripts" not in manifest
    assert "host_permissions" not in manifest
    assert "webRequest" not in manifest["permissions"]
for manifest in (CHROMIUM_HOST, FIREFOX_HOST):
    assert manifest["path"].startswith("/ABSOLUTE/")
    assert manifest["name"] == "org.postapollo.proton_mail"

spec = importlib.util.spec_from_file_location("postapollo_proton_multibrowser", HOST)
assert spec and spec.loader
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
chromium_origin = "chrome-extension://" + "a" * 32 + "/"
mozilla_manifest = "/home/test/.mozilla/native-messaging-hosts/org.postapollo.proton_mail.json"
env = {
    "POST_APOLLO_PROTON_EXTENSION_ORIGIN": chromium_origin,
    "POST_APOLLO_PROTON_FIREFOX_EXTENSION_ID": FIREFOX_ID,
}
assert host.resolve_caller([chromium_origin], env) == (chromium_origin, chromium_origin)
assert host.resolve_caller([mozilla_manifest, FIREFOX_ID], env) == (FIREFOX_ID, FIREFOX_ID)
assert host.resolve_caller(["https://mail.proton.me"], env) is None
assert host.resolve_caller(["chrome-extension://" + "b" * 32 + "/"], env) is None
assert host.resolve_caller([mozilla_manifest, "other@extensions.invalid"], env) is None
assert host.resolve_caller(["relative/org.postapollo.proton_mail.json", FIREFOX_ID], env) is None
assert host.resolve_caller(["/tmp/not-our-host.json", FIREFOX_ID], env) is None
assert host.resolve_caller([mozilla_manifest], env) is None
assert host.resolve_caller([mozilla_manifest, FIREFOX_ID, chromium_origin], env) is None
assert host.resolve_caller([mozilla_manifest, FIREFOX_ID], {}) is None
assert host.trusted_firefox_id(FIREFOX_ID, FIREFOX_ID)
assert not host.trusted_firefox_id(FIREFOX_ID, "*")
assert not host.trusted_firefox_id("anything@example.org", "anything@*")
assert not host.trusted_firefox_id(chromium_origin, chromium_origin)

def frame(payload: dict) -> io.BytesIO:
    raw = json.dumps(payload).encode("utf8")
    return io.BytesIO(struct.pack("=I", len(raw)) + raw)

for caller in (chromium_origin, FIREFOX_ID):
    incoming = frame({"protocol": 1, "kind": "PING"})
    outgoing = io.BytesIO()
    assert host.serve(caller, caller, incoming, outgoing)
    wire = outgoing.getvalue()
    assert struct.unpack("=I", wire[:4])[0] == len(wire) - 4
    result = json.loads(wire[4:])
    assert result == {
        "protocol": 1,
        "kind": "PONG",
        "origin": "https://mail.proton.me",
        "mailboxAccess": False,
        "messageIdentityVerified": False,
        "capabilities": [],
    }
    assert not host.serve(caller, caller, frame({"protocol": 1, "kind": "archive"}), io.BytesIO())
    assert not host.serve(caller, caller,
                          frame({"protocol": 1, "kind": "PING", "token": "x"}), io.BytesIO())

source = JS.read_text(encoding="utf8")
assert "document." not in source
assert "XMLHttpRequest" not in source
assert "fetch(" not in source
assert "cookies" not in source.lower()
assert "localStorage" not in source
assert "mailboxAccess !== false" in source
assert "messageIdentityVerified !== false" in source

NODE = r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const source=fs.readFileSync(process.argv[1],"utf8");

async function run(kind, response, connectionError=false) {
  const calls=[], infos=[], warnings=[], listeners=[];
  const api = {
    action:{onClicked:{addListener(fn){listeners.push(fn)}}},
    runtime:{lastError:null,sendNativeMessage(name,request,callback) {
      calls.push({name,request});
      if(kind==="chromium") {
        if(connectionError) api.runtime.lastError={message:"private failure"};
        callback(connectionError ? undefined : response);
        api.runtime.lastError=null;
      } else {
        return connectionError ? Promise.reject(new Error("private failure")) : Promise.resolve(response);
      }
    }}
  };
  const scope={URL,console:{info:(m)=>infos.push(m),warn:(m)=>warnings.push(m)}};
  scope[kind==="firefox"?"browser":"chrome"]=api;
  vm.runInNewContext(source,scope,{filename:"background.js"});
  assert.strictEqual(listeners.length,1);
  const click=listeners[0];
  click({url:"https://mail.proton.me.evil.test/login"});
  click({url:"https://mail.proton.me@evil.test/inbox"});
  click({url:"https://example.org/"});
  click({url:"not a url"});
  assert.strictEqual(calls.length,0);
  click({url:"https://mail.proton.me/u/0/inbox"});
  await Promise.resolve();
  await Promise.resolve();
  assert.strictEqual(calls.length,1);
  assert.strictEqual(calls[0].name,"org.postapollo.proton_mail");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(calls[0].request)),{protocol:1,kind:"PING"});
  assert.strictEqual(Object.keys(calls[0].request).length,2);
  assert.strictEqual(infos.length,connectionError || response.mailboxAccess ? 0 : 1);
  assert.strictEqual(warnings.length,connectionError || response.mailboxAccess ? 1 : 0);
  assert.ok(![...warnings,...infos].some(t=>t.includes("private failure")));
}
(async()=>{
 const safe={protocol:1,kind:"PONG",origin:"https://mail.proton.me",
   mailboxAccess:false,messageIdentityVerified:false,capabilities:[]};
 for(const family of ["chromium","firefox"]) {
   await run(family,safe);
   await run(family,{...safe,mailboxAccess:true});
   await run(family,safe,true);
 }
 console.log("Chromium and Firefox read-only WebExtension mocks: PASS");
})().catch(e=>{console.error(e);process.exit(1)});
"""
subprocess.run(["node", "-e", NODE, str(JS)], check=True)
print("Proton multi-browser companion contracts: PASS")
