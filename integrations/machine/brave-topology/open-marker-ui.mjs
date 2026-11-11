/* Explicit operator action opens ONE temporary marker tab in THIS window.
 * Does not inspect or change existing tabs, windows, browser profile, or Sway.
 */
const openButton = document.getElementById("open-marker");
const markerStatus = document.getElementById("marker-open-status");
let opening = false;

async function openMarker() {
  if (opening) return;
  opening = true;
  openButton.disabled = true;
  markerStatus.textContent = "OPENING ONE TEMPORARY TEST TAB";
  try {
    const win = await chrome.windows.getCurrent({populate:false});
    if (!win || win.type !== "normal" || win.incognito !== false
        || !Number.isSafeInteger(win.id) || win.id <= 0) {
      throw new Error("unsupported");
    }
    const token = crypto.randomUUID();
    const tab = await chrome.tabs.create({
      windowId: win.id, active: true, pinned: false,
      url: chrome.runtime.getURL("marker.html#" + token),
    });
    if (!tab || tab.windowId !== win.id || tab.incognito !== false) {
      throw new Error("new tab not isolated");
    }
    markerStatus.textContent = "TEST TAB OPENED // NO EXISTING TABS CHANGED";
  } catch {
    markerStatus.textContent = "TEST TAB UNAVAILABLE // NO IDENTITY CLAIM";
  } finally {
    openButton.disabled = false;
    opening = false;
  }
}

openButton.addEventListener("click", openMarker);
