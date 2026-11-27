const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const policy = vm.createContext({});
vm.runInContext(read("services/diagnostics/CpuPlusDiagnosticsPolicy.js"), policy);
const route = vm.createContext({});
vm.runInContext(read("services/notifications/ApolloNotificationRoute.js").replace(/^\s*\.pragma library\s*/, ""), route);
const plain = value => JSON.parse(JSON.stringify(value));
const id = "timeabc-abc-def-1";
const secret = "RAW REPORT MUST NOT ENTER NOTIFICATION HISTORY";
const report = {id, status:"COMPLETE", summary:secret, text:secret};
for (const kind of ["memory", "inventory", "threads", "census", "storage", "appcontrol", "hostcpu", "gpu"]) {
    for (const status of ["COMPLETE", "CANCELLED", "NOT VERIFIED"]) {
        const notice = plain(policy.noticeFor(kind, {...report,status}));
        assert.equal(notice.id,"apollo-cpu-diag-"+id);
        assert.ok(notice.title.includes(status));
        assert.ok(!JSON.stringify(notice).includes(secret));
        assert.equal(notice.severity,status==="COMPLETE"?"normal":"warning");
        assert.deepEqual(plain(policy.referenceFor(notice)),{kind,id});
        assert.deepEqual(plain(route.routeFor(notice)),{widget:"cpu",view:"diagnostics",reportKind:kind,reportId:id});
        for (const wrong of [
            {...notice,id:"different"},
            {...notice,sourceId:"external"},
            {...notice,context:{...notice.context,reportKind:"arbitrary"}},
            {...notice,context:{...notice.context,reportId:"../file"}},
            {...notice,context:{...notice.context,origin:"external"}}
        ]) {
            assert.equal(policy.referenceFor(wrong),null);
            assert.equal(route.routeFor(wrong),null);
        }
    }
}
assert.equal(policy.noticeFor("unknown",report),null);
assert.equal(policy.noticeFor("memory",{...report,status:"RUNNING"}),null);
assert.equal(policy.noticeFor("memory",{...report,id:"invalid"}),null);
const owner = read("services/diagnostics/CpuPlusDiagnostics.qml");
const methods = owner.slice(owner.indexOf("    function reportFor("),owner.indexOf("    function publishResult("));
const model = vm.createContext({Policy:policy,reports:{memory:report},selectedReport:"census",memoryMenuIndex:0,archiveRows:[],selectedArchiveId:""});
vm.runInContext(methods,model);
assert.equal(model.reportFor("memory",id),report);
assert.equal(model.selectExactReport("memory",id),true);
assert.equal(model.memoryMenuIndex,4);
assert.equal(model.selectedReport,"memory");
model.reports = {memory:{...report,id:"timeabc-abc-def-2",text:"new"}};
assert.equal(model.reportFor("memory",id),null);
assert.equal(model.selectExactReport("memory",id),false);
assert.equal(model.reportFor("__proto__",id),null);
model.archiveRows = [{...report,kind:"memory"}];
assert.equal(model.selectExactReport("memory",id),true);
assert.equal(model.selectedArchiveId,id);
assert.equal(model.reportFor("memory",id).text,secret);
assert.equal(model.reportFor("census",id),null);
const shell = read("shell.qml");
const popup = read("modules/Notifications.qml");
assert.match(shell,/function onCaptureFinished\(job, reportId\)[\s\S]*?NotificationsService\.pushRich\(notice\)/);
assert.match(shell,/if \(!CpuPlusDiagnostics\.selectExactReport\(route.reportKind, route.reportId\)\) return false;/);
assert.match(popup,/function exactActiveDiagnostic\(\)[\s\S]*?NotificationsService\.activeNotifications[\s\S]*?CpuPlusDiagnostics\.reportFor\(ref.kind, ref.id\)/);
assert.match(popup,/diagnosticClipboard\.text = exact.report.text;[\s\S]*?diagnosticClipboard\.copy\(\);[\s\S]*?diagnosticClipboard\.text = "";/);
assert.match(popup,/identifier === "open-diag"[\s\S]*?confirmOpenIntent\("destination"\)/);
assert.match(owner,/captureFinished\(kind, captureId\)/);
assert.match(owner,/owner.publishResult\("NOT VERIFIED", "RUNNER UNAVAILABLE/);
assert.equal((owner.match(/captureFinished\(kind, captureId\)/g)||[]).length,1);
console.log("Diagnostic notification metadata, exact-report refusal and action contracts PASS");
