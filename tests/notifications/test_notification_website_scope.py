#!/usr/bin/env python3
"""Runtime-style JavaScript policy contract for browser website/app targeting.

Executes the actual QML service functions under Node with minimal ListModel
doubles. No browser, network, filesystem policy mutation, or real notification
content is required.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
IDENTITY = ROOT / "services/notifications/BrowserSiteIdentity.js"

NODE = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const identity = fs.readFileSync(process.argv[2], 'utf8');
function extract(code, name) {
  const index = code.indexOf('function ' + name + '(');
  assert(index >= 0, 'missing function ' + name);
  const start = code.indexOf('{', index);
  let depth = 0;
  for (let i = start; i < code.length; i++) {
    if (code[i] === '{') depth++;
    else if (code[i] === '}' && --depth === 0)
      return code.slice(index, i + 1);
  }
  throw new Error('unclosed function ' + name);
}
class Model {
  constructor() { this.rows = []; }
  get count() { return this.rows.length; }
  get(i) { return this.rows[i]; }
  append(x) { this.rows.push({...x}); }
  setProperty(i, k, v) { this.rows[i][k] = v; }
  remove(i) { this.rows.splice(i, 1); }
  clear() { this.rows.length = 0; }
}
let now = 100000;
class Clock extends Date { static now() { return now; } }
const Site = {String};
vm.runInNewContext(['token','hostnameFor'].map(n=>extract(identity,n)).join('\n'),Site);
const S = {
  String, Number, Math, encodeURIComponent, Date: Clock,
  BrowserSiteIdentity: {hostnameFor: Site.hostnameFor},
  sourcePolicies: new Model(),
  activeNotifications: new Model(),
  defaultSnoozeDurationMs: 86400000,
  policyVersion: 1,
  policyRevision: 0,
  schedulePolicySave() {}
};
const functions = [
  'sourceKey', 'websiteKey', 'policyIndex', 'policyFor',
  'isDnd', 'isSnoozed', 'shouldSuppress', 'ensurePolicy',
  'markPoliciesChanged', 'suppressActiveForKey', 'compactPolicy',
  'setDnd', 'toggleDnd', 'snoozeApp', 'clearSnooze', 'policyDocument'
];
vm.runInNewContext(functions.map(n=>extract(source,n)).join('\n'),S);

const parent = S.sourceKey('brave-browser', 'Brave');
const yt = S.websiteKey('brave-browser', 'Brave', 'www.youtube.com');
const gh = S.websiteKey('brave-browser', 'Brave', 'github.com');
const unknown = S.websiteKey('brave-browser', 'Brave', '');
assert.strictEqual(parent, 'brave-browser');
assert.strictEqual(unknown, '');
assert.notStrictEqual(yt, gh);
assert.notStrictEqual(yt, parent);
assert.strictEqual(yt, S.websiteKey('brave-browser','Brave','youtube.com'));
assert.strictEqual(yt, S.websiteKey('brave-browser','Brave','m.youtube.com'));
assert.notStrictEqual(yt, S.websiteKey('chromium','Chromium','youtube.com'));
assert.notStrictEqual(yt, S.websiteKey('brave-browser','Brave','youtube.com.evil.test'));
assert.strictEqual(S.websiteKey('brave-browser','Brave','not a site'), '');

const entry = (id, websiteHost) => ({id, source:'Brave', sourceId:'brave-browser', websiteHost});
const youtube = entry('youtube', 'www.youtube.com');
const github = entry('github', 'github.com');
const plain = entry('ordinary-browser', '');
S.activeNotifications.append(youtube);
S.activeNotifications.append(github);
S.activeNotifications.append(plain);
S.setDnd(yt, 'brave-browser', 'Brave // YouTube', true);
assert.strictEqual(S.policyFor(yt).source, 'Brave // YouTube');
assert.deepStrictEqual(S.activeNotifications.rows.map(e=>e.id), ['github','ordinary-browser']);
assert.strictEqual(S.shouldSuppress(youtube.sourceId,youtube.source,youtube.websiteHost),true);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),false);
assert.strictEqual(S.shouldSuppress(plain.sourceId,plain.source,plain.websiteHost),false);

// Legacy parent key remains authoritative across all of its children.
S.setDnd(parent, 'brave-browser', 'Brave', true);
assert.strictEqual(S.activeNotifications.count, 0);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),true);
assert.strictEqual(S.shouldSuppress(plain.sourceId,plain.source,plain.websiteHost),true);
assert.strictEqual(S.isDnd(gh),false, 'do not pretend the child has its own rule');
assert.strictEqual(S.isDnd(parent),true);

// Removing a broad rule must not accidentally delete an unrelated child rule.
S.setDnd(parent, 'brave-browser', 'Brave', false);
assert.strictEqual(S.shouldSuppress(youtube.sourceId,youtube.source,youtube.websiteHost),true);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),false);
assert.strictEqual(S.shouldSuppress(plain.sourceId,plain.source,plain.websiteHost),false);

// Site ZZ persists in the exact same policy model, independently from DND.
S.snoozeApp(gh,'brave-browser','Brave // GitHub');
assert.strictEqual(S.isSnoozed(gh),true);
assert.strictEqual(S.isSnoozed(parent),false);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),true);
assert.strictEqual(S.shouldSuppress(plain.sourceId,plain.source,plain.websiteHost),false);
const saved = S.policyDocument();
assert(saved.policies.some(p => p.appKey === gh && p.snoozeUntil > now));
assert(saved.policies.some(p => p.appKey === yt && p.dnd === true));
S.clearSnooze(gh);
assert.strictEqual(S.isSnoozed(gh),false);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),false);

// An old persisted DND policy (without any child identities) still controls
// future website notifications without a migration or renamed sourceId.
S.sourcePolicies.clear();
S.sourcePolicies.append({
 appKey:'brave-browser', source:'Brave', sourceId:'brave-browser',
 dnd:true, snoozeUntil:0
});
assert.strictEqual(S.shouldSuppress(youtube.sourceId,youtube.source,youtube.websiteHost),true);
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),true);
assert.strictEqual(S.shouldSuppress(plain.sourceId,plain.source,plain.websiteHost),true);

// Timed parent snooze also inherits, and expires without disturbing children.
S.sourcePolicies.clear();
S.sourcePolicies.append({
 appKey:'brave-browser', source:'Brave', sourceId:'brave-browser',
 dnd:false, snoozeUntil:now+1000
});
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),true);
now += 1001;
assert.strictEqual(S.shouldSuppress(github.sourceId,github.source,github.websiteHost),false);
console.log('Website/site scoped DND ZZ and legacy inheritance: PASS');
"""
subprocess.run(["node","-e",NODE,str(SERVICE),str(IDENTITY)],check=True)
print("Notification website policy scope: PASS")
