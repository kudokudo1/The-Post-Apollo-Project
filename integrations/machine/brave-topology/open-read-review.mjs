/* MACHINE // operator opens a separate encrypted snapshot review page.
 * No Brave tabs, history, native record, or URL is read at this step.
 */
const button=document.getElementById("open-read-review");
const status=document.getElementById("read-review-open-status");
let busy=false;
async function openReview(){
  if(busy)return;
  busy=true;button.disabled=true;
  status.textContent="CHECKING LOCAL PERMISSION // NO SNAPSHOT READ";
  try{
    const allowed=await chrome.permissions.contains({permissions:["nativeMessaging"]});
    if(!allowed){status.textContent="ALLOW LOCAL CONNECTION FIRST";return}
    const win=await chrome.windows.getCurrent({populate:false});
    if(!win||win.type!=="normal"||win.incognito!==false||
       !Number.isSafeInteger(win.id)||win.id<=0)throw new Error("invalid window");
    const tab=await chrome.tabs.create({
      windowId:win.id,active:true,pinned:false,
      url:chrome.runtime.getURL("read-review.html")
    });
    if(!tab||tab.windowId!==win.id||tab.incognito!==false)
      throw new Error("invalid review tab");
    status.textContent="ENCRYPTED READ REVIEW OPENED // NO DATA READ";
  }catch{
    status.textContent="READ REVIEW UNAVAILABLE // NO DATA READ";
  }finally{busy=false;button.disabled=false}
}
button.addEventListener("click",openReview);
