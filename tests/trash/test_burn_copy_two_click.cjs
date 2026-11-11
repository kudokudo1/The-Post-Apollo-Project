"use strict";
// Synthetic QML Burn click + receipt lifecycle. No GIO or local files.
const fs=require("node:fs"), path=require("node:path"), vm=require("node:vm");
const assert=require("node:assert/strict"), test=require("node:test");
const qml=fs.readFileSync(path.resolve(__dirname,"../../modules/Trash.qml"),"utf8");

function method(name) {
    const i=qml.indexOf("    function "+name+"(");
    assert.ok(i>=0,"missing method "+name);
    const start=qml.indexOf("{",i);
    let n=0;
    for(let j=start;j<qml.length;j++) {
        if(qml[j]==="{")n++;
        if(qml[j]==="}")n--;
        if(n===0)return qml.slice(i,j+1);
    }
    throw Error("bad method "+name);
}
const methods=[
    "armResearchBurn","advanceResearchBurn","confirmResearchBurn",
    "clearResearchBurn","clearConfirmation","showBurnReceipt",
    "failBurnReceipt","dismissBurnReceipt","armBurn","confirmBurn"
].map(method).join("\n");

const copy={id:"0123456789abcdef0123456789abcdef",kind:"SAVED EVENT",
            title:"Storm copy",state:"trashed"};
function harness(overrides={}) {
    const ctx={
        menuOpen:true,activeMode:"burn",busy:false,researchBusy:false,
        confirmMode:"",confirmUri:"",confirmOriginal:"",confirmName:"",
        confirmRevision:"",confirmCount:0,burnAllPointerRelocated:false,
        total:1,revision:"b".repeat(64),
        researchRows:[copy],researchRevision:8,researchBurnId:"",
        researchBurnTitle:"",researchBurnScope:"",researchBurnRevision:-1,
        researchBurnCount:0,researchBurnDigest:"",researchBinCount:1,
        researchBinRows:[copy],researchBinDigest:"d".repeat(64),
        researchBurnPointerRelocated:false,researchBurnClickArmed:false,
        researchBurnLoadComplete:false,researchBurnLoadProgress:0,
        burnUiStage:"",burnReceiptItems:[],burnReceiptRequested:0,
        burnReceiptCount:0,burnReceiptVerified:false,
        burnReceiptMessage:"",burnReceiptScope:"",
        calls:[],started:0,stopped:0,delays:0,delayStops:0,
        researchBurnArmAnimation:{
            restart(){ctx.started++},stop(){ctx.stopped++}
        },
        burnCommitDelay:{
            restart(){ctx.delays++},stop(){ctx.delayStops++}
        },
        runResearch(action,args){
            ctx.calls.push({engine:"copies",action,args:Array.from(args)});
            return true;
        },
        run(action,args){
            ctx.calls.push({engine:"gio",action,args:Array.from(args)});
            return true;
        },
        ...overrides
    };
    vm.createContext(ctx);
    vm.runInContext(methods,ctx);
    return ctx;
}
function armTwoClicks(ctx,expression){
    assert.equal(vm.runInContext(expression,ctx),true);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    ctx.researchBurnPointerRelocated=true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.equal(ctx.researchBurnClickArmed,true);
    assert.equal(ctx.started,1);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    ctx.researchBurnLoadComplete=true;
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),true);
    assert.equal(ctx.burnUiStage,"clicked");
    assert.equal(ctx.delays,1);
    assert.equal(ctx.calls.length,0);
}

test("single copy persists through second-click glow and background commit",()=>{
    const ctx=harness();
    armTwoClicks(ctx,"armResearchBurn(researchRows[0])");
    assert.equal(ctx.researchBurnId,copy.id);
    ctx.burnUiStage="working"; // simulated 420ms delayed callback
    assert.equal(vm.runInContext("confirmResearchBurn()",ctx),true);
    assert.equal(ctx.calls.length,1);
    assert.deepEqual(Array.from(ctx.calls[0].args),
       [copy.id,"8","BURN_SAVED_COPY_CONFIRMED"]);
    assert.equal(ctx.researchBurnId,copy.id); // do not close before receipt
    vm.runInContext(
       'showBurnReceipt({verified:true,burnedItems:[{name:"Storm copy",kind:"SAVED EVENT",source:"WEATHER"}]},"MANAGED COPY",1)',
       ctx);
    assert.equal(ctx.burnUiStage,"result");
    assert.equal(ctx.burnReceiptVerified,true);
    assert.equal(ctx.burnReceiptItems[0].name,"Storm copy");
    assert.equal(ctx.activeMode,"burn");
    assert.equal(vm.runInContext("dismissBurnReceipt()",ctx),true);
    assert.equal(ctx.researchBurnId,"");
    assert.equal(ctx.burnUiStage,"");
    assert.equal(ctx.activeMode,"burn");
});

test("single GIO file uses identical confirmation and waits for named receipt",()=>{
    const ctx=harness();
    const item={name:"note.txt",uri:"trash:///note.txt",original:"/tmp/note.txt"};
    ctx.file=item;
    armTwoClicks(ctx,"armBurn(file)");
    assert.equal(ctx.activeMode,"burn");
    assert.equal(ctx.confirmMode,"item");
    assert.equal(ctx.confirmName,"note.txt");
    ctx.burnUiStage="working";
    assert.equal(vm.runInContext("confirmBurn()",ctx),true);
    assert.deepEqual(Array.from(ctx.calls[0].args),
       ["burn",item.uri,item.original,"BURN_CONFIRMED"]);
    assert.equal(ctx.confirmMode,"item");
    vm.runInContext(
      'showBurnReceipt({verified:true,burnedItems:[{name:"note.txt",kind:"SYSTEM FILE",original:"/tmp/note.txt"}]},"SYSTEM TRASH // FILE",1)',
      ctx);
    assert.equal(ctx.burnReceiptItems[0].name,"note.txt");
    assert.equal(ctx.activeMode,"burn");
    vm.runInContext("dismissBurnReceipt()",ctx);
    assert.equal(ctx.confirmMode,"");
});

test("cancel before commit and incomplete animation cannot delete",()=>{
    const ctx=harness();
    vm.runInContext("armResearchBurn(researchRows[0])",ctx);
    ctx.researchBurnPointerRelocated=true;
    vm.runInContext("advanceResearchBurn()",ctx);
    assert.equal(vm.runInContext("advanceResearchBurn()",ctx),false);
    assert.equal(ctx.calls.length,0);
    assert.equal(vm.runInContext("dismissBurnReceipt()",ctx),true);
    assert.equal(ctx.calls.length,0);
    assert.equal(ctx.researchBurnId,"");
});

test("working and second-click flash do not allow early dismissal",()=>{
    for(const stage of ["clicked","working"]) {
        const ctx=harness({burnUiStage:stage});
        assert.equal(vm.runInContext("dismissBurnReceipt()",ctx),false);
        assert.equal(ctx.burnUiStage,stage);
        assert.equal(ctx.calls.length,0);
    }
});

test("failure and partial verification never claim everything was burned",()=>{
    const ctx=harness();
    vm.runInContext('failBurnReceipt("GIO_INDEX_UNAVAILABLE")',ctx);
    assert.equal(ctx.burnUiStage,"error");
    assert.equal(ctx.burnReceiptVerified,false);
    assert.match(ctx.burnReceiptMessage,/NOT CONFIRMED/);
    vm.runInContext(
      'showBurnReceipt({verified:true,partial:true,burnedItems:[{name:"one.txt",kind:"SYSTEM FILE"}]},"SYSTEM TRASH // ALL",2)',ctx);
    assert.equal(ctx.burnReceiptVerified,false);
    assert.equal(ctx.burnReceiptCount,1);
    assert.equal(ctx.burnReceiptRequested,2);
    assert.equal(ctx.burnUiStage,"result");
});

test("one visual modal and one Burn workspace hold result until DONE",()=>{
    assert.equal((qml.match(/id: managedResearchBurnConfirm/g)||[]).length,1);
    assert.doesNotMatch(qml,/id: burnAllConfirmMenu/);
    assert.match(qml,/visible: trashLauncher\.burnConfirmationOpen/);
    assert.match(qml,/id: burnReviewContent/);
    assert.match(qml,/id: burnResultContent/);
    assert.match(qml,/id: burnReceiptList/);
    assert.match(qml,/model: trashLauncher\.burnReceiptItems/);
    assert.match(qml,/id: burnReceiptDone/);
    assert.match(qml,/DONE \/\/ RETURN TO BURN/);
    assert.match(qml,/function showBurnReceipt\(/);
    assert.match(qml,/function failBurnReceipt\(/);
    assert.match(qml,/burnUiStage = "clicked";/);
    assert.match(qml,/interval: 420/);
    assert.match(qml,/selected: trashLauncher\.burnUiStage === "clicked"/);
    assert.match(qml,/selectedBorderColor: Colors\.magenta/);
    assert.match(qml,/onLeftClicked: trashLauncher\.advanceResearchBurn\(\)/);
    assert.match(qml,/visible: researchBurnFace\.loading/);
    assert.match(qml,/id: researchBurnLabelClip/);
});

test("orange fill persists after loading and black label covers full width",()=>{
    const face=qml.slice(qml.indexOf("id: researchBurnFace"),
                         qml.indexOf("id: cancelManagedResearchBurn"));
    const guard=/readonly property bool loading:\s*trashLauncher\.researchBurnClickArmed\s*&& trashLauncher\.burnUiStage === ""/;
    assert.match(face,guard);
    // Read the actual QML visibility expression. Its evaluation, not the
    // animation-complete flag, decides when the overlay is shown.
    const expr=face.match(guard)[0].split("loading:")[1].trim();
    for (const sample of [
        {armed:false,stage:"",finished:false,visible:false},
        {armed:true,stage:"",finished:false,visible:true},
        {armed:true,stage:"",finished:true,visible:true},
        {armed:true,stage:"clicked",finished:true,visible:false},
        {armed:true,stage:"working",finished:true,visible:false}
    ]) {
        const visible=vm.runInNewContext(expr,{
            trashLauncher:{
                researchBurnClickArmed:sample.armed,
                researchBurnLoadComplete:sample.finished,
                burnUiStage:sample.stage
            }
        });
        assert.equal(visible,sample.visible,JSON.stringify(sample));
    }
    assert.match(face,/visible: researchBurnFace\.loading/g);
    assert.equal((face.match(/visible: researchBurnFace\.loading/g)||[]).length,2);
    assert.match(face,/\* trashLauncher\.researchBurnLoadProgress/);
    assert.match(face,/height: Math\.max\(0, parent\.height - 4\)/);
    assert.match(face,/color: Colors\.black\s+text: researchBurnFace\.displayedLabel/);
    assert.match(face,/: "CLICK AGAIN \/\/ BURN"/);
    assert.match(face,/horizontalAlignment: Text\.AlignHCenter/);
});

test("single Burn menu filters both sources and requires scope for bulk",()=>{
    assert.match(qml,/id: burnSourceFilters/);
    assert.match(qml,/model: trashLauncher\.burnDisplayRows/);
    assert.match(qml,/fileRows\.concat\(copyRows\)/);
    for(const v of ["all","files","records","events","research"]){
        assert.ok(qml.includes('{id:"'+v+'", label:'),v);
    }
    assert.match(qml,/onLeftClicked: trashLauncher\.setMode\("burn"\)/);
    assert.match(qml,/trashLauncher\.burnFilter === "files"/);
    assert.match(qml,/trashLauncher\.burnFilter === "records"/);
    assert.match(qml,/onLeftClicked: \{\s+if \(trashLauncher\.burnFilter === "files"\)/);
});
