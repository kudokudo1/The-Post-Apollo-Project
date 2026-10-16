#!/usr/bin/env python3
"""Multi-dimensional notification classification: origin, domain, severity."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/NotificationFacets.js"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"
text = POLICY.read_text(encoding="utf-8")
hub = HUB.read_text(encoding="utf-8")
assert 'import "../../services/notifications/NotificationFacets.js" as NotificationFacets' in hub
assert 'const facets = NotificationFacets.facetsFor(entry);' in hub
assert 'classification.group, facets))' in hub
assert 'NotificationFacets.matches(root.activeFilter, facets, false)' in hub
assert "function facetsFor(event)" in text
assert "function matches(filter, facets, favorite)" in text
assert "function warning(category, severity)" in text
classification = text.split("function facetsFor(event)")[1].split("function matches(")[0]
assert "e.message" not in classification and "e.title" not in classification, "never infer facets from private contents"
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
const social=ctx.facetsFor({source:'Discord',sourceId:'discord',
  category:'generic',severity:'normal'});
assert.strictEqual(social.origin,'external');
assert.strictEqual(social.domain,'social');
assert(ctx.matches('social',social,false));
assert(!ctx.matches('apps',social,false));
const socialHint=ctx.facetsFor({source:'Some App',category:'im.received'});
assert(ctx.matches('social',socialHint,false));
const externalSystem=ctx.facetsFor({source:'NetworkManager',
  category:'device.error'});
assert(ctx.matches('system',externalSystem,false));
const unknown=ctx.facetsFor({source:'Brave',category:'generic',severity:'normal'});
assert(ctx.matches('apps',unknown,false));
assert(ctx.matches('favorites',unknown,true));
assert(!ctx.matches('favorites',unknown,false));
assert(ctx.matches('all',unknown,false));

const hub=fs.readFileSync(process.argv[2],'utf8');
const start=hub.indexOf('    function notificationMatches(');
const end=hub.indexOf('    // ===== ICON HELPER',start);
assert(start>=0 && end>start);
const runtime={
  root:{
    activeFilter:'all',searchQuery:'',
    isWarning:ctx.warning,
    appKeyFor:(sourceId,source)=>sourceId||source
  },
  NotificationsService:{isFavorite:key=>key==='cpu-plus-system'},
  NotificationFacets:{matches:ctx.matches}
};
vm.runInNewContext(hub.slice(start,end),runtime,{filename:'NotificationsHubW.qml::filter'});
function shown(view,event,facets) {
  runtime.root.activeFilter=view;
  return runtime.notificationMatches(
    event.source,event.sourceId,event.title||'',event.message||'',
    event.category,event.severity,'apollo',facets
  );
}
const report={source:'CPU++',sourceId:'cpu-plus-system',
  category:'internal',severity:'normal',title:'CPU++ // SYSTEM REPORT'};
assert(shown('apollo',report,apolloSystem));
assert(shown('system',report,apolloSystem));
assert(!shown('warning',report,apolloSystem));
assert(shown('favorites',report,apolloSystem));
const hot={...report,sourceId:'cpu-plus',severity:'critical'};
assert(shown('apollo',hot,warning));
assert(shown('system',hot,warning));
assert(shown('warning',hot,warning));
assert(!shown('favorites',hot,warning));
assert(shown('social',{source:'Discord',category:'generic',
  severity:'normal'},social));
assert(!shown('system',{source:'Discord',category:'generic',
  severity:'normal'},social));
console.log('independent notification facets: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(HUB)], check=True)
print("Notification facet contracts: PASS")
