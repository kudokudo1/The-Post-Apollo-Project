"use strict";
// Synthetic bulk Burn scope and result test, no native files.
const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const assert=require("node:assert/strict"),test=require("node:test");
const qml=fs.readFileSync(path.resolve(__dirname,"../../modules/Trash.qml"),"utf8");
function m(name){
    const i=qml.indexOf("    function "+name+"(");assert.ok(i>=0,name);
    const start=qml.indexOf("{",i);let n=0;
    for(let j=start;j<qml.length;j++){if(qml[j]==="{")n++;if(qml[j]==="}")n--;
        if(n===0)return qml.slice(i,j+1);}
    throw Error(name);
}
const methods=["armResearchBurnAll","armBurnAll","advanceResearchBurn",
 "confirmResearchBurn","confirmBurn","clearConfirmation","clearResearchBurn",
 "dismissBurnReceipt","showBurnReceipt","failBurnReceipt"].map(m).join("\n");
const rows=[
 {id:"a".repeat(32),kind:"SAVED EVENT",title:"Storm copy",state:"trashed"},
 {id:"b".repeat(32),kind:"SAVED RESEARCH",title:"Scrape copy",state:"trashed"},
 {id:"c".repeat(32),kind:"SAVED EVENT",title:"Active",state:"archived"}
];
function h(overrides={}){
 const ctx={
   menuOpen:true,activeMode:"burn",burnFilter:"records",
   busy:false,researchBusy:false,confirmMode:"",confirmUri:"",
   confirmOriginal:"",confirmName:"",confirmRevision:"",confirmCount:0,
   burnAllPointerRelocated:false,revision:"f".repeat(64),total:9,
   researchRows:rows,researchBinRows:rows.slice(0,2),researchBinCount:2,
   researchBinDigest:"d".repeat(64),researchRevision:12,
   researchBurnId:"",researchBurnScope:"",researchBurnTitle:"",
   researchBurnCount:0,researchBurnDigest:"",researchBurnRevision:-1,
   researchBurnPointerRelocated:false,researchBurnClickArmed:false,
   researchBurnLoadComplete:false,researchBurnLoadProgress:0,
   burnUiStage:"",burnReceiptItems:[],burnReceiptCount:0,
   burnReceiptVerified:false,burnReceiptRequested:0,
   burnReceiptMessage:"",burnReceiptScope:"",
   calls:[],animations:0,
   researchBurnArmAnimation:{restart(){ctx.animations++},stop(){}},
   burnCommitDelay:{restart(){ctx.animations++},stop(){}},
   runResearch(action,args){
     ctx.calls.push({engine:"copies",action,args:Array.from(args)});return true;
   },
   run(action,args){
     ctx.calls.push({engine:"gio",action,args:Array.from(args)});return true;
   },
   ...overrides
 };
 vm.createContext(ctx);vm.runInContext(methods,ctx);return ctx;
}
function clickThrough(ctx){
 ctx.researchBurnPointerRelocated=true;
 assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
 assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
 ctx.researchBurnLoadComplete=true;
 assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
 assert.equal(ctx.burnUiStage,"clicked");
 assert.equal(ctx.calls.length,0);
 ctx.burnUiStage="working";
}

test("managed bulk uses one shared confirmation and exact managed-only scope",()=>{
 const ctx=h();assert.equal(vm.runInContext("armResearchBurnAll()",ctx),true);
 assert.equal(ctx.researchBurnScope,"all");
 assert.equal(ctx.researchBurnCount,2);
 assert.equal(ctx.researchBurnDigest,"d".repeat(64));
 clickThrough(ctx);
 assert.equal(vm.runInContext("confirmResearchBurn()",ctx),true);
 assert.deepEqual(Array.from(ctx.calls),[{
   engine:"copies",action:"burn-all",
   args:["12","2","d".repeat(64),"BURN_ALL_MANAGED_COPIES_CONFIRMED"]
 }]);
 assert.equal(ctx.researchBurnId,"__managed_bin_all__");
 vm.runInContext(
 'showBurnReceipt({verified:true,burnedItems:[{name:"Storm copy",kind:"SAVED EVENT"},{name:"Scrape copy",kind:"SAVED RESEARCH"}]},"MANAGED COPIES // ALL",2)',ctx);
 assert.equal(ctx.burnReceiptVerified,true);
 assert.equal(ctx.burnReceiptItems.length,2);
 assert.equal(ctx.activeMode,"burn");
 assert.equal(vm.runInContext("dismissBurnReceipt()",ctx),true);
 assert.equal(ctx.researchBurnId,"");
});

test("GIO bulk uses same two clicks and GIO-specific revision",()=>{
 const ctx=h({burnFilter:"files"});
 assert.equal(vm.runInContext("armBurnAll()",ctx),true);
 assert.equal(ctx.confirmMode,"all");
 assert.equal(ctx.confirmCount,9);
 clickThrough(ctx);
 assert.equal(vm.runInContext("confirmBurn()",ctx),true);
 assert.deepEqual(Array.from(ctx.calls),[{
  engine:"gio",action:"burn-all",
  args:["burn-all","f".repeat(64),"9","BURN_ALL_CONFIRMED"]
 }]);
 assert.equal(ctx.confirmMode,"all");
});

test("stale state prevents managed bulk deletion before backend",()=>{
 for(const update of [
  {researchBinCount:3},{researchBinRows:[]},
  {researchBinDigest:"0".repeat(64)},{researchRevision:13}
 ]){
   const ctx=h();
   vm.runInContext("armResearchBurnAll()",ctx);
   clickThrough(ctx);
   Object.assign(ctx,update);
   assert.equal(vm.runInContext("confirmResearchBurn()",ctx),false);
   assert.equal(ctx.calls.length,0);
 }
});
test("system GIO bulk refuses stale inventory",()=>{
 for(const update of [{revision:"0".repeat(64)},{total:10}]){
   const ctx=h({burnFilter:"files"});
   vm.runInContext("armBurnAll()",ctx);
   clickThrough(ctx);
   Object.assign(ctx,update);
   assert.equal(vm.runInContext("confirmBurn()",ctx),false);
   assert.equal(ctx.calls.length,0);
 }
});
test("bulk arming requires explicit filter and never mixes backends",()=>{
 for(const filter of ["all","events","research"]){
   const ctx=h({burnFilter:filter});
   assert.equal(vm.runInContext("armBurnAll()",ctx),false);
   // Managed bulk is only enabled through the records filter button.
   assert.match(qml,/trashLauncher\.burnFilter === "records"/);
 }
 const ctx=h({researchBinCount:0,researchBinRows:[]});
 assert.equal(vm.runInContext("armResearchBurnAll()",ctx),false);
 assert.equal(ctx.calls.length,0);
});
test("unified Burn screen and opaque filling button remain intact",()=>{
 assert.match(qml,/id: researchBurnReview/);
 assert.match(qml,/id: burnSourceFilters/);
 assert.match(qml,/id: researchBurnList/);
 assert.match(qml,/model: trashLauncher\.burnDisplayRows/);
 assert.match(qml,/id: burnAllManagedCopiesButton/);
 assert.equal((qml.match(/id: managedResearchBurnConfirm/g)||[]).length,1);
 assert.doesNotMatch(qml,/id: burnAllConfirmMenu/);
 assert.match(qml,/id: researchBurnLoadFill/);
 assert.match(qml,/height: Math\.max\(0, parent\.height - 4\)/);
 assert.match(qml,/id: researchBurnLabelWhite/);
 assert.match(qml,/id: researchBurnLabelClip/);
 assert.match(qml,/color: Colors\.black\s+text: researchBurnFace\.displayedLabel/);
 assert.match(qml,/idleFillColor: Colors\.black/);
 assert.match(qml,/selectedBorderColor: Colors\.magenta/);
});
