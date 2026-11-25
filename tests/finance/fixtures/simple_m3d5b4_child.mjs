// Disposable child process for M3d5b4. Never a live writer.
import {createM3d5b4DisposableCustodian,
  inspectM3d5b4DisposableReceipt}
  from "../../../scripts/finance/simple_m3d5b4_disposable_confirmation.mjs";
import {prepareOfflineCategorizedReview}
  from "../../../scripts/finance/simple_m3d2_offline_review.mjs";
import {makeView,sourceOptions}
  from "./simple_m3d5b4_payload.mjs";
let input="";
for await(const chunk of process.stdin){
  input+=chunk.toString();
  if(input.length>4096)throw Error("disposable-input-too-large");
}
const {sandboxRoot,mode="seal",receiptId,modify,override={}}=JSON.parse(input);
const options={sandboxRoot,...sourceOptions,...override};
const view=makeView();
function mutate(v,name){
  if(name==="amount")v.candidate.amountCents=-1400;
  if(name==="category")v.selectedCategoryId="other";
  if(name==="hidden")v.snapshot.categories[0].hidden=true;
  if(name==="budget")v.snapshot.categories[0].availableCents=4300;
  if(name==="source")v.snapshot.sourceKey="f".repeat(64);
}
function output(value){process.stdout.write(JSON.stringify(value)+"\n");}
if(mode==="inspect"){
  mutate(view,modify);
  output(await inspectM3d5b4DisposableReceipt({
    ...options,receiptId,view
  }));
}else{
  const custody=createM3d5b4DisposableCustodian(options);
  const previousReview=prepareOfflineCategorizedReview(view);
  const staged=custody.stage({view,previousReview});
  if(!staged.ok){output(staged);}
  else if(mode==="stage"){output(staged);}
  else if(mode==="cancel"){
    const canceled=custody.cancel();
    output({staged,canceled,after:await custody.confirm({
      confirmationText:staged.confirmationPrompt,current:view
    })});
  }else if(mode==="wrong"){
    const denied=await custody.confirm({
      confirmationText:"NOT THE CONFIRMATION",current:view
    });
    output({staged,denied,after:await custody.confirm({
      confirmationText:staged.confirmationPrompt,current:view
    })});
  }else{
    mutate(view,modify);
    const promise=custody.confirm({
      confirmationText:staged.confirmationPrompt,current:view
    });
    if(mode==="double"){
      const again=custody.confirm({
        confirmationText:staged.confirmationPrompt,current:view
      });
      output({staged,results:await Promise.all([promise,again]),
        dispatch:custody.dispatch()});
    }else if(mode==="cancel-race"){
      const cancel=custody.cancel();
      output({staged,cancel,result:await promise});
    }else{
      const sealed=await promise;
      if(mode==="crash-after-seal"){
        // Stage was already given to the caller before confirmation.
        // Simulate a process dying after fsync but before the final ACK.
        output({staged});
        process.exit(47);
      }
      output({staged,sealed,dispatch:custody.dispatch()});
    }
  }
}
