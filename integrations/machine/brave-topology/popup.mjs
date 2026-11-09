import { projectBraveTopology } from "./topology.mjs";

const refreshButton = document.getElementById("refresh");
const status = document.getElementById("status");
const counts = document.getElementById("counts");
const windowList = document.getElementById("window-list");

function item(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

function show(topology) {
  windowList.replaceChildren();
  counts.textContent =
    topology.counts.browser_windows + " WINDOWS // "
    + topology.counts.tabs + " TABS // "
    + topology.counts.pinned_tabs + " PINNED";

  for (const entry of topology.windows) {
    const row = document.createElement("li");
    row.className = entry.current_browser_window ? "current" : "";
    row.appendChild(item(
      "strong",
      (entry.current_browser_window ? "THIS BRAVE WINDOW" : "BRAVE WINDOW")
      + " // TEMP " + entry.temporary_browser_window_id
    ));
    row.appendChild(item(
      "span",
      entry.tab_count + " TABS // " + entry.pinned_tab_count + " PINNED // "
      + (entry.active_tab_index === null
          ? "ACTIVE TAB UNKNOWN"
          : "ACTIVE POSITION " + (entry.active_tab_index + 1))
    ));
    windowList.appendChild(row);
  }

  status.textContent = topology.windows.length
    ? "LOCAL WINDOW COUNTS READY // NOTHING SAVED"
    : "NO NORMAL BRAVE WINDOWS REPORTED";
}

async function inspectOnce() {
  if (refreshButton.disabled) {
    return;
  }
  refreshButton.disabled = true;
  status.textContent = "READING NORMAL BRAVE WINDOWS";
  counts.textContent = "";
  windowList.replaceChildren();
  try {
    if (!chrome.windows || typeof chrome.windows.getAll !== "function"
        || typeof chrome.windows.getCurrent !== "function") {
      throw new Error("unavailable");
    }
    const [all, current] = await Promise.all([
      chrome.windows.getAll({ populate: true, windowTypes: ["normal"] }),
      chrome.windows.getCurrent({ populate: false }),
    ]);
    const currentId = Number.isSafeInteger(current?.id) && current.id > 0
      ? current.id : null;
    show(projectBraveTopology(all, currentId));
  } catch {
    // Do not echo private browser API error details into UI or logs.
    status.textContent = "WINDOW INVENTORY UNAVAILABLE // NO DATA STORED";
  } finally {
    refreshButton.disabled = false;
  }
}

// Opening the extension popup is the deliberate inspection gesture.
// No background listeners, storage, timers, network or native host access.
refreshButton.addEventListener("click", inspectOnce);
inspectOnce();
