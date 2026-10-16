#!/usr/bin/env python3
"""Multi-dimensional notification classification: origin, domain, severity."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/NotificationFacets.js"
text = POLICY.read_text(encoding="utf-8")
assert "function facetsFor(event)" in text
assert "function matches(filter, facets, favorite)" in text
assert "function warning(category, severity)" in text
assert "message" not in text.lower().split("function facetsFor(event)")[1].split("function matches(")[0], "never infer facets from private message contents"
NODE = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8').replace(/^\s*\.pragma library\s*$/m,'');
const ctx={String};
vm.runInNewContext(source,ctx,{filename:'NotificationFacets.js'});
const apolloSystem=ctx.facetsFor({source:'CPU++',sourceId:'cpu-plus-system',
  category:'internal',severity:'normal',context:{origin:'apollo',domain:'system'}});
assert.strictEqual(apolloSystem.origin,'apollo');
assert.strictEqual(apolloSystem.domain,'system');
assert.strictEqual(apolloSystem.severity,'normal');
assert(ctx.matches('apollo',apolloSystem,false));
assert(ctx.matches('system',apolloSystem,false));
assert(!ctx.matches('warning',apolloSystem,false));
assert(!ctx.matches('apps',apolloSystem,false));
const warning=ctx.facetsFor({source:'CPU++',sourceId:'cpu-plus',
  category:'internal',severity:'critical'});
assert(ctx.matches('apollo',warning,false));
assert(ctx.matches('system',warning,false));
assert(ctx.matches('warning',warning,false));
const weather=ctx.facetsFor({source:'WEATHER REPORT',sourceId:'weather-brief',
  category:'internal',severity:'normal'});
assert.strictEqual(weather.domain,'weather');
assert(ctx.matches('apollo',weather,false));
assert(!ctx.matches('system',weather,false));
const apolloSocial=ctx.facetsFor({source:'APOLLO MESSENGER',category:'internal',
  context:{origin:'apollo',domain:'social'}});
assert(ctx.matches('apollo',apolloSocial,false));
assert(ctx.matches('social',apolloSocial,false));
const externalNetwork=ctx.facetsFor({source:'NetworkManager',category:'network.error',
  severity:'warning'});
assert(ctx.matches('system',externalNetwork,false));
assert(ctx.matches('warning',externalNetwork,false));
assert(!ctx.matches('apollo',externalNetwork,false));
const unknown=ctx.facetsFor({source:'Brave',category:'generic',severity:'normal'});
assert(ctx.matches('apps',unknown,false));
assert(ctx.matches('favorites',unknown,true));
assert(!ctx.matches('favorites',unknown,false));
assert(ctx.matches('all',unknown,false));
console.log('independent notification facets: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("Notification facet contracts: PASS")
