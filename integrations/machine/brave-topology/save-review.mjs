/* MACHINE // one-window, selected-tab, one-shot sealed save review.
 * No storage, background worker, network, tab movement or plaintext native IPC.
 * URL strings exist only in transient page memory, then WebCrypto plaintext
 * buffers are zeroed. JS strings cannot be guaranteed physically zeroized.
 */
import {classifySelectableUrl,sealSelectedSession,MAX_SELECTED_TABS} from "./session-seal.mjs";
import {SAVE_HOST,makeSealedSaveRequest,checkSealedSaveResponse} from "./save-host-protocol.mjs";

const byId=id=>document.getElementById(id);
const loadButton=byId("load-save-tabs"),saveButton=byId("save-sealed-tabs");
const closeButton=byId("close-save-review"),list=byId("save-tab-list");
const sensitive=byId("allow-sensitive-save"),label=byId("save-window-label");
const password=byId("save-passphrase"),confirmPassword=byId("save-passphrase-confirm");
const consent=byId("confirm-sealed-save"),status=byId("save-status");
const result=byId("save-result");
const entry=/^#([1-9][0-9]{0,14}):([1-9][0-9]{0,14})$/;
const match=location.hash.match(entry);
const sourceWindowId=match?Number(match[1]):null;
const sourceActiveId=match?Number(match[2]):null;
let rows=[];
let loaded=false,busy=false,closed=false,epoch=0,completed=false;

function clearReview(){
  rows=[];
  loaded=false;
  list.replaceChildren();
  consent.checked=false;
  sensitive.checked=false;
}
function clearPasswords(){
  password.value="";
  confirmPassword.value="";
}
function setBusy(value){
  busy=value;
  loadButton.disabled=value;
  saveButton.disabled=value||completed||!loaded;
  closeButton.disabled=value;
}
function still(ticket){return !closed && epoch===ticket && !document.hidden}
function notify(value){if(!closed)status.textContent=value}
async function ownTab(){
  const tab=await chrome.tabs.getCurrent();
  if(!tab||!tab.active||tab.incognito!==false||
      !Number.isSafeInteger(tab.id)||tab.id<=0||
      tab.windowId!==sourceWindowId)throw new Error("wrong review tab");
  const win=await chrome.windows.get(tab.windowId,{populate:false});
  if(!win||win.id!==sourceWindowId||win.type!=="normal"||
      win.incognito!==false||win.focused!==true)throw new Error("wrong window");
  return tab;
}
async function allowed(){
  const a=await chrome.permissions.contains({permissions:["tabs"]});
  const b=await chrome.permissions.contains({permissions:["nativeMessaging"]});
  return a===true&&b===true;
}
function render(){
  const items=[];
  for(const row of rows){
    const li=document.createElement("li");
    const lbl=document.createElement("label");
    const checkbox=document.createElement("input");
    checkbox.type="checkbox";
    checkbox.checked=row.checked;
    checkbox.disabled=row.risk==="excluded"||
      (row.risk==="sensitive"&&!sensitive.checked);
    checkbox.addEventListener("change",()=>{
      row.checked=checkbox.checked&& !checkbox.disabled;
      if(!checkbox.disabled)row.checked=checkbox.checked;
    });
    const name=document.createElement("span");
    name.textContent="TAB "+String(row.index+1).padStart(2,"0")+
      " // "+row.host+" // "+
      (row.risk==="sensitive"?"QUERY/FRAGMENT REVIEW":
       row.risk==="candidate"?"ELIGIBLE":"EXCLUDED");
    lbl.append(checkbox,name);
    li.append(lbl);
    items.push(li);
  }
  list.replaceChildren(...items);
}
async function loadOnce(){
  if(busy||closed||!match||completed)return;
  const ticket=++epoch;
  clearReview();
  result.textContent="";
  setBusy(true);
  notify("VERIFYING WINDOW AND OPTIONAL PERMISSIONS");
  try{
    if(!await allowed()||!still(ticket))throw new Error("no permission");
    const own=await ownTab();
    if(!still(ticket))return;
    const win=await chrome.windows.get(sourceWindowId,{populate:true});
    if(!still(ticket))return;
    if(!win||win.id!==sourceWindowId||win.type!=="normal"||
       win.incognito!==false||!Array.isArray(win.tabs)||
       win.tabs.length>64)throw new Error("unsupported window");
    const fresh=[];
    for(const tab of win.tabs){
      if(tab.id===own.id)continue;
      if(tab.incognito!==false||!Number.isSafeInteger(tab.id)||tab.id<=0||
          !Number.isSafeInteger(tab.index)||tab.index<0||
          typeof tab.pinned!=="boolean")throw new Error("unsafe tab");
      const risk=classifySelectableUrl(tab.url);
      let host="NON-WEB";
      if(risk!=="excluded")host=new URL(tab.url).hostname.slice(0,100);
      fresh.push({id:tab.id,index:tab.index,url:tab.url,pinned:tab.pinned,
                  wasActive:tab.id===sourceActiveId,risk,host,checked:false});
    }
    if(!still(ticket))return;
    const again=await ownTab();
    if(!still(ticket)||again.id!==own.id||!await allowed()||!still(ticket))return;
    rows=fresh;
    loaded=true;
    render();
    notify("WINDOW TABS LOADED // SELECT EACH TAB // NOTHING SAVED");
  }catch{
    if(still(ticket)){
      clearReview();notify("WINDOW LOAD REFUSED // NO DATA SAVED");
    }
  }finally{
    setBusy(false);
    if(!closed)saveButton.disabled=!loaded||completed||busy;
  }
}
async function saveOnce(){
  if(busy||closed||!loaded||completed||!match)return;
  const chosen=rows.filter(r=>r.checked);
  if(!consent.checked||!chosen.length||chosen.length>MAX_SELECTED_TABS||
     chosen.some(r=>r.risk==="excluded"||
                   (r.risk==="sensitive"&&!sensitive.checked))||
     password.value.length<16||password.value!==confirmPassword.value){
    notify("SELECT TABS, CONFIRM CONSENT AND MATCH A 16+ CHARACTER PASSPHRASE");
    return;
  }
  const passphrase=password.value;
  clearPasswords();
  const ticket=++epoch;
  let submitted=false;
  setBusy(true);
  notify("REVALIDATING SELECTED TABS // NO SAVE YET");
  try{
    if(!await allowed()||!still(ticket))throw new Error("permission");
    const own=await ownTab();
    if(!still(ticket))return;
    const current=await chrome.windows.get(sourceWindowId,{populate:true});
    if(!still(ticket))return;
    if(!current||current.id!==sourceWindowId||current.type!=="normal"||
       current.incognito!==false||!Array.isArray(current.tabs))throw new Error("changed window");
    const lookup=new Map(current.tabs.map(tab=>[tab.id,tab]));
    const selected=[];
    for(const row of chosen){
      const currentTab=lookup.get(row.id);
      if(!currentTab||currentTab.incognito!==false||
         currentTab.windowId!==sourceWindowId||
         currentTab.index!==row.index||currentTab.url!==row.url||
         currentTab.pinned!==row.pinned)throw new Error("tab changed");
      selected.push({index:row.index,pinned:row.pinned,url:row.url,
                     wasActive:row.wasActive});
    }
    const verified=await ownTab();
    if(verified.id!==own.id||!await allowed()||!still(ticket))return;
    notify("ENCRYPTING SELECTED TABS LOCALLY");
    const envelope=await sealSelectedSession({
      label:label.value,tabs:selected,passphrase,
      includeSensitive:sensitive.checked
    });
    if(!still(ticket))return;
    const challenge=crypto.randomUUID();
    const request=makeSealedSaveRequest(challenge,envelope);
    notify("SENDING ONLY ENCRYPTED DATA TO DISPOSABLE VAULT");
    submitted=true;
    const reply=await chrome.runtime.sendNativeMessage(SAVE_HOST,request);
    if(!still(ticket))return;
    const saved=checkSealedSaveResponse(challenge,reply);
    completed=true;
    clearReview();
    result.textContent="SEALED RECORD ID // "+saved.record_id;
    notify("ENCRYPTED SNAPSHOT STORED // DISPOSABLE VAULT // NO RESTORE");
  }catch{
    if(still(ticket)){
      notify(submitted?"SAVE RESULT UNCONFIRMED // DO NOT RETRY WITHOUT CHECKING VAULT":
             "ENCRYPTION OR SELECTION REFUSED // NOTHING SUBMITTED");
    }
  }finally{
    clearPasswords();
    setBusy(false);
    saveButton.disabled=!loaded||completed||busy;
  }
}
function invalidate(){
  epoch++;
  clearReview();
  clearPasswords();
  if(!closed){
    result.textContent="";
    notify(busy?"FOCUS LOST // SAVE MAY BE PENDING // CHECK VAULT BEFORE RETRY":
                 "REVIEW EXPIRED ON FOCUS LOSS // LOAD AGAIN");
  }
}
loadButton.addEventListener("click",loadOnce);
saveButton.addEventListener("click",saveOnce);
sensitive.addEventListener("change",()=>{
  if(!sensitive.checked)for(const row of rows)if(row.risk==="sensitive")row.checked=false;
  render();
});
closeButton.addEventListener("click",async()=>{
  invalidate();closed=true;
  try{
    const tab=await chrome.tabs.getCurrent();
    if(tab&&tab.id>0&&tab.windowId===sourceWindowId&&tab.incognito===false)
      await chrome.tabs.remove(tab.id);
  }catch{/* browser X still closes the review tab */}
});
window.addEventListener("blur",invalidate);
window.addEventListener("pagehide",()=>{invalidate();closed=true;});
document.addEventListener("visibilitychange",()=>{if(document.hidden)invalidate();});
if(!match||!Number.isSafeInteger(sourceWindowId)||!Number.isSafeInteger(sourceActiveId)){
  loadButton.disabled=true;saveButton.disabled=true;
  notify("INVALID DISPOSABLE WINDOW REFERENCE // REFUSED");
}else{
  saveButton.disabled=true;
}
