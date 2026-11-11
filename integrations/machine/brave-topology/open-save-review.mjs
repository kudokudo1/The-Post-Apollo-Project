/* MACHINE // user-clicked disposable current-window sealed save review.
 * Does NOT read page URLs. The opener reads only the active temporary tab ID.
 * Requires the already-consented optional tab and native permissions.
 */
const button=document.getElementById("open-save-review");
const status=document.getElementById("save-review-open-status");
let busy=false;
async function openReview(){
  if(busy)return;
  busy=true;button.disabled=true;
  status.textContent="CHECKING OPTIONAL PERMISSIONS // NO URL READ";
  try {
    const hasTabs=await chrome.permissions.contains({permissions:["tabs"]});
    const hasNative=await chrome.permissions.contains({permissions:["nativeMessaging"]});
    if(!hasTabs||!hasNative){
      status.textContent="ALLOW BOTH TAB AND LOCAL ACCESS FIRST";
      return;
    }
    const win=await chrome.windows.getCurrent({populate:false});
    if(!win||win.type!=="normal"||win.incognito!==false||
       !Number.isSafeInteger(win.id)||win.id<=0)throw new Error("not a normal window");
    const active=await chrome.tabs.query({windowId:win.id,active:true});
    if(!Array.isArray(active)||active.length!==1||
       active[0].incognito!==false||!Number.isSafeInteger(active[0].id)||
       active[0].id<=0)throw new Error("active window invalid");
    const review=await chrome.tabs.create({
      windowId:win.id,active:true,pinned:false,
      url:chrome.runtime.getURL("save-review.html#"+win.id+":"+active[0].id)
    });
    if(!review||review.windowId!==win.id||review.incognito!==false)
      throw new Error("review tab invalid");
    status.textContent="SAVE REVIEW TAB OPENED // NO DATA SAVED YET";
  }catch{
    status.textContent="SAVE REVIEW UNAVAILABLE // NO DATA SAVED";
  }finally{busy=false;button.disabled=false}
}
button.addEventListener("click",openReview);
