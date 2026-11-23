import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function load(path){
    const context=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+path,import.meta.url),"utf8"),context);
    return context;
}
const Provider=load("FinanceBankingProviderPolicy.js");
const Handoff=load("FinanceBankingOfficialHandoffPolicy.js");
const domains={
    cashapp:["https://cash.app/","cash.app"],
    chime:["https://www.chime.com/","www.chime.com"],
    paypal:["https://www.paypal.com/","www.paypal.com"]
};
const expectedSections={
    cashapp:["payments","card","stocks","borrow","savings","security"],
    chime:["card","transfers","credit","security"],
    paypal:["payments","cards","savings","paylater","security"]
};

for(const p of Provider.providers()) {
    const restricted=p.features.filter(f=>f.kind==="restricted").map(f=>f.id);
    if(p.id==="bank") {
        for(const feature of p.features) {
            const result=Handoff.destination(p.id,feature.id);
            assert.equal(result.ok,false);
            assert.equal(Handoff.canOpen(result,p.id,feature.id),false);
        }
        continue;
    }
    assert.deepEqual(Array.from(restricted),expectedSections[p.id],
        p.id+" catalog restrictions changed: revisit official handoff policy");
    for(const f of p.features) {
        const target=Handoff.destination(p.id,f.id);
        if(f.kind!=="restricted") {
            assert.equal(target.ok,false,p.id+" "+f.id);
            assert.equal(Handoff.canOpen(target,p.id,f.id),false);
            continue;
        }
        assert.equal(target.ok,true,p.id+" "+f.id);
        assert.equal(target.url,domains[p.id][0]);
        assert.equal(target.host,domains[p.id][1]);
        assert.equal(target.kind,"official-homepage");
        assert.equal(target.requiresConfirmation,true);
        assert.equal(target.passesCredentials,false);
        assert.equal(target.executesFinancialAction,false);
        assert.equal(Handoff.canOpen(target,p.id,f.id),true);
        for(const field of ["url","host","kind","providerId","sectionId",
                "requiresConfirmation","passesCredentials","executesFinancialAction"]) {
            const changed={...target,[field]:"tampered"};
            assert.equal(Handoff.canOpen(changed,p.id,f.id),false,
                "must reject tampering of "+field);
        }
        assert.equal(Handoff.canOpen(target,p.id,"home"),false);
        assert.equal(Handoff.canOpen(target,"bank",f.id),false);
    }
}
for(const provider of ["constructor","toString","__proto__","","Cash App",
        "cashapp?redirect=evil","https://cash.app/"]) {
    const r=Handoff.destination(provider,"payments");
    assert.equal(r.ok,false,provider);
    assert.equal(Handoff.canOpen(r,provider,"payments"),false);
}
for(const value of [null,undefined,{},[],4,true]) {
    assert.equal(Handoff.destination(value,"payments").ok,false);
    assert.equal(Handoff.destination("cashapp",value).ok,false);
}
assert.equal(Handoff.destination("cashapp","INVALID").ok,false);
assert.equal(Handoff.destination("cashapp","home").ok,false);
assert.equal(Handoff.destination("chime","stocks").ok,false);
assert.equal(Handoff.destination("paypal","borrow").ok,false);
assert.equal(Handoff.destination("bank","security").ok,false);
assert.equal(Handoff.canOpen({ok:true,url:"https://evil.example"}, "cashapp","stocks"),false);
assert.equal(Handoff.canOpen(null,"cashapp","stocks"),false);
assert.equal(Handoff.canOpen(undefined,"cashapp","stocks"),false);
assert.equal(Handoff.canOpen({ok:true},"cashapp","stocks"),false);
assert.equal(Handoff.canOpen(Handoff.destination("cashapp","stocks"),"cashapp","payments"),false);
console.log("Banking M4d: fixed verified provider homepages, feature restrictions, explicit confirmation metadata and hostile provider inputs PASS");
