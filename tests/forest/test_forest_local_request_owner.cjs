const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const path = require("node:path");
const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../widgets/ForestLocalRequestOwner.js"),"utf8"),ctx);
const make = ctx.createLocalRequestOwner;
function setup() {
    const owner = make(), calls = [], correlation = {};
    const host = {
        submit(...args) { calls.push(["submit",...args]); return {accepted:true,correlation}; },
        stop(c) { calls.push(["stop",c]); return true; },
        withdraw(c) { calls.push(["withdraw",c]); }
    };
    let terminal = false;
    const presentation = {
        observe(v) { calls.push(["observe",v]); },
        attach(...args) { calls.push(["attach",...args]); return true; },
        receive(...args) { calls.push(["receive",...args]); terminal = args[1].terminal === true; return true; },
        state() { return {terminal,status:terminal?"LOCAL_COMMITTED":"GENERATING"}; },
        withdraw(v) { calls.push(["clear",v]); }
    };
    return {owner,calls,host,presentation,correlation};
}
{
    const {owner,calls}=setup();
    assert.equal(owner.submit("granite","hello",1),false);
    assert.equal(calls.length,0);
}
{
    const {owner,host,presentation,calls,correlation}=setup();
    assert.equal(owner.observe(host,1,"granite",presentation),true);
    const draft="  exact café\n🍃  ";
    assert.equal(owner.submit("granite",draft,1),true);
    assert.deepEqual(calls[1],["submit","granite",draft,1]);
    assert.deepEqual(calls[2],["attach",1,draft]);
    assert.equal(owner.submit("granite",draft,1),false);
    assert.equal(owner.receive(1,{},{}),false);
    assert.equal(owner.receive(2,correlation,{}),false);
    assert.equal(owner.receive(1,correlation,{}),true);
    assert.equal(owner.stop(),true);
    assert.equal(owner.stop(),false);
    assert.equal(calls.filter(c=>c[0]==="stop").length,1);
    assert.equal(calls.find(c=>c[0]==="stop")[1],correlation);
    assert.equal(owner.receive(1,correlation,{terminal:true}),true);
    assert.equal(owner.state().status,"LOCAL_COMMITTED");
    assert.equal(owner.receive(1,correlation,{}),false);
    owner.withdraw();
    assert.equal(calls.find(c=>c[0]==="withdraw")[1],correlation);
    assert.equal(owner.observe(host,1,"granite",presentation),false);
}
{
    const {owner,host,presentation,calls}=setup();
    host.submit=()=>null;
    owner.observe(host,1,"granite",presentation);
    assert.equal(owner.submit("other","hello",1),false);
    assert.equal(owner.submit("granite","🍃".repeat(1025),1),false);
    assert.equal(owner.submit("granite","hello",1),false);
    assert.equal(owner.state().canSubmit,true);
    assert.equal(calls.some(c=>c[0]==="attach"),false);
}
{
    const {owner,host,presentation}=setup();
    host.submit=()=>{throw Error("ambiguous");};
    owner.observe(host,1,"granite",presentation);
    assert.equal(owner.submit("granite","hello",1),false);
    assert.equal(owner.state().status,"UNKNOWN_HOLD");
    assert.equal(owner.state().canSubmit,false);
}
{
    const {owner,host,presentation,correlation,calls}=setup();
    host.submit=()=>{owner.withdraw();return {accepted:true,correlation};};
    owner.observe(host,1,"granite",presentation);
    assert.equal(owner.submit("granite","hello",1),false);
    assert.equal(calls.some(c=>c[0]==="attach"),false);
    assert.equal(calls.find(c=>c[0]==="withdraw")[1],correlation);
}
{
    const {owner,host,presentation,correlation,calls}=setup();
    presentation.attach=()=>false;
    owner.observe(host,1,"granite",presentation);
    assert.equal(owner.submit("granite","hello",1),false);
    assert.equal(owner.state().status,"UNKNOWN_HOLD");
    assert.equal(calls.find(c=>c[0]==="withdraw")[1],correlation);
}
{
    const {owner,host,presentation,correlation,calls}=setup();
    owner.observe(host,1,"granite",presentation);
    owner.submit("granite","hello",1);
    assert.equal(owner.observe(host,2,"other",presentation),true);
    assert.equal(owner.receive(1,correlation,{}),false);
    assert.equal(owner.stop(),false);
    assert.equal(calls.find(c=>c[0]==="withdraw")[1],correlation);
}
for (const result of ["HELD", "REFUSED"]) {
    const {owner,host,presentation,calls}=setup();
    host.submit=(...args)=>{calls.push(["submit",...args]);return result;};
    owner.observe(host,1,"granite",presentation);
    const draft="  exact public text  ";
    assert.equal(owner.submit("granite",draft,1),false);
    assert.deepEqual(calls[1],["submit","granite",draft,1]);
    assert.equal(owner.state().status,result);
    assert.equal(owner.state().canSubmit,false);
    assert.equal(owner.submit("granite",draft,1),false);
    assert.equal(owner.stop(),false);
    assert.equal(calls.filter(c=>c[0]==="submit").length,1);
    assert.equal(calls.some(c=>c[0]==="attach"),false);
}
{
    const {owner,host,presentation,calls}=setup();
    owner.observe(host,1,"granite",presentation);
    assert.equal(owner.submit("granite","a".repeat(4097),1),false);
    assert.equal(calls.some(c=>c[0]==="submit"),false);
    assert.equal(owner.submit("granite","a".repeat(4096),1),true);
}
console.log("FOREST_LOCAL_REQUEST_OWNER_PASS 10");
