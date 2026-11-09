/*
 * MACHINE Brave topology pilot, intentionally weaker than session identity.
 *
 * Pure projection from an explicit chrome.windows.getAll() result. Never
 * reads or returns URLs, titles, tab IDs, tab groups, profiles, session
 * files, browsing history, contents or incognito windows. A browser window
 * ID exists only for the current browser run and is NOT a Sway container ID.
 *
 * This function has no browser API access, I/O, logging or storage.
 */
export const TOPOLOGY_KIND = "machine-brave-window-topology-readonly-v1";
export const MAX_NORMAL_WINDOWS = 64;
export const MAX_TABS_PER_WINDOW = 2048;
export const MAX_TOTAL_TABS = 8192;

function invalid() {
  throw new TypeError("BROWSER WINDOW INVENTORY UNAVAILABLE");
}

function positiveId(value) {
  return Number.isSafeInteger(value) && value > 0;
}

export function projectBraveTopology(rawWindows, currentWindowId = null) {
  if (!Array.isArray(rawWindows) || rawWindows.length > MAX_NORMAL_WINDOWS) {
    invalid();
  }
  if (currentWindowId !== null && !positiveId(currentWindowId)) {
    invalid();
  }

  const usedWindowIds = new Set();
  const windows = [];
  let totalTabs = 0;
  let totalPinned = 0;

  for (const source of rawWindows) {
    if (source === null || typeof source !== "object") {
      invalid();
    }

    // Private browsing is explicitly out of scope even if the API supplied
    // it despite the manifest's incognito:not_allowed setting.
    if (source.incognito === true) {
      continue;
    }
    if (source.incognito !== false) {
      invalid();
    }
    if (source.type !== "normal") {
      continue;
    }

    const id = source.id;
    const tabs = source.tabs;
    if (!positiveId(id) || usedWindowIds.has(id) || !Array.isArray(tabs)
        || tabs.length > MAX_TABS_PER_WINDOW
        || totalTabs + tabs.length > MAX_TOTAL_TABS) {
      invalid();
    }
    usedWindowIds.add(id);

    let pinned = 0;
    let activeIndex = null;
    const usedIndexes = new Set();
    for (const tab of tabs) {
      if (tab === null || typeof tab !== "object"
          || !Number.isSafeInteger(tab.index) || tab.index < 0
          || tab.index >= tabs.length || usedIndexes.has(tab.index)
          || typeof tab.pinned !== "boolean"
          || typeof tab.active !== "boolean"
          || (tab.incognito !== undefined && tab.incognito !== false)) {
        invalid();
      }
      usedIndexes.add(tab.index);
      if (tab.pinned) {
        pinned += 1;
      }
      if (tab.active) {
        if (activeIndex !== null) {
          invalid();
        }
        activeIndex = tab.index;
      }
    }
    // Discarded or restoring browsers can temporarily have no selected
    // tab. We report that uncertainty rather than inventing one.
    totalTabs += tabs.length;
    totalPinned += pinned;
    windows.push({
      temporary_browser_window_id: id,
      current_browser_window: id === currentWindowId,
      tab_count: tabs.length,
      pinned_tab_count: pinned,
      active_tab_index: activeIndex,
    });
  }

  windows.sort((a, b) =>
    Number(b.current_browser_window) - Number(a.current_browser_window)
    || a.temporary_browser_window_id - b.temporary_browser_window_id
  );

  return {
    kind: TOPOLOGY_KIND,
    status: "ready",
    read_only: true,
    capture_scope: "browser_window_counts_only",
    private_windows_included: false,
    title_url_contents_included: false,
    temporary_ids_only: true,
    sway_window_binding_verified: false,
    restart_session_identity_verified: false,
    tabs_restorable: false,
    safe_restore_actions: [],
    counts: {
      browser_windows: windows.length,
      tabs: totalTabs,
      pinned_tabs: totalPinned,
    },
    windows,
  };
}
