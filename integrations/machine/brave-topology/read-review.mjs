/* MACHINE // manual encrypted read-back, authenticated redacted review only.
 * Only an opaque record UUID crosses the native boundary before read.
 * Native host returns ciphertext; passphrase and decrypted URLs stay inside
 * this transient page, which renders hostnames/positions only.
 */
import {READ_HOST,makeReadRequest,verifyReadReply} from "./read-host-protocol.mjs";
import {inspectSealedSnapshot} from "./session-unseal.mjs";

const id=x=>document.getElementById(x);
const button=id("decrypt-read-once"),forget=id("forget-read");
const close=id("close-read-review"),record=id("read-record-id");
const password=id("read-passphrase"),status=id("read-status");
const summary=id("read-summary"),list=id("read-tab-list");
let inFlight=false,closed=false,epoch=0,completed=false;
const validId=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function clear(){
  summary.textContent="";
  list.replaceChildren();
  password.value="";
}
function expire(reason){
  epoch++;
  clear();
  completed=false;
  if(!closed)status.textContent=reason;
}
function current(ticket){return !closed&&!document.hidden&&ticket===epoch}
async function ownTab(){
  const tab=await chrome.tabs.getCurrent();
  if(!tab||!tab.active||tab.incognito!==false||
     !Number.isSafeInteger(tab.id)||tab.id<=0||
     !Number.isSafeInteger(tab.windowId)||tab.windowId<=0)
    throw new Error("invalid review tab");
  const win=await chrome.windows.get(tab.windowId,{populate:false});
  if(!win||win.type!=="normal"||win.incognito!==false||win.focused!==true)
    throw new Error("invalid review window");
  return tab.id;
}
function render(review){
  const nodes=review.tabs.map(entry=>{
    const li=document.createElement("li");
    li.textContent="TAB "+String(entry.position+1).padStart(2,"0")+
      " // "+entry.hostname+
      " // "+(entry.risk==="sensitive"?"SENSITIVE URL":"WEB")+
      (entry.pinned?" // PINNED":"")+
      (entry.was_active?" // PREVIOUS ACTIVE":"");
    return li;
  });
  summary.textContent=review.window_label+" // "+review.tab_count+" TABS // "+
    review.pinned_count+" PINNED // "+review.sensitive_count+
    " SENSITIVE // NO RESTORE";
  list.replaceChildren(...nodes);
}
async function readOnce(){
  if(inFlight||closed||completed)return;
  const wanted=record.value.trim();
  const passphrase=password.value;
  password.value="";
  if(!validId.test(wanted)||passphrase.length<16||passphrase.length>1024){
    status.textContent="VALID RECORD ID AND PASSPHRASE REQUIRED";
    return;
  }
  inFlight=true;button.disabled=true;
  clear(); const ticket=++epoch;
  status.textContent="READING ONE ENCRYPTED SNAPSHOT // NO RESTORE";
  try{
    const tabId=await ownTab();
    if(!current(ticket))return;
    if(await chrome.permissions.contains({permissions:["nativeMessaging"]})!==true
       ||!current(ticket))throw new Error("permission");
    const nonce=crypto.randomUUID();
    const response=await chrome.runtime.sendNativeMessage(
      READ_HOST,makeReadRequest(nonce,wanted));
    if(!current(ticket))return;
    const checked=verifyReadReply(nonce,wanted,response);
    const review=await inspectSealedSnapshot(checked.envelope,passphrase);
    if(!current(ticket))return;
    if(await ownTab()!==tabId||!current(ticket))return;
    render(review);
    completed=true;
    status.textContent="AES-GCM AUTHENTICATED // REDACTED REVIEW // NO RESTORE";
  }catch{
    if(current(ticket)){
      clear();
      status.textContent="READ OR DECRYPT REFUSED // NO RESTORE";
    }
  }finally{
    password.value="";
    inFlight=false;
    if(!closed)button.disabled=false;
  }
}
button.addEventListener("click",readOnce);
forget.addEventListener("click",()=>{
  expire("PREVIEW FORGOTTEN // NO SESSION ACTION");
  record.value="";
});
close.addEventListener("click",async()=>{
  expire("PREVIEW CLOSED");closed=true;
  try{
    const tab=await chrome.tabs.getCurrent();
    if(tab&&tab.incognito===false&&Number.isSafeInteger(tab.id)&&tab.id>0)
      await chrome.tabs.remove(tab.id);
  }catch{/* standard browser X remains available */}
});
window.addEventListener("blur",()=>expire("FOCUS LOST // PREVIEW EXPIRED"));
window.addEventListener("pagehide",()=>{expire("PAGE CLOSED");closed=true});
document.addEventListener("visibilitychange",()=>{
  if(document.hidden)expire("REVIEW HIDDEN // PREVIEW EXPIRED");
});
