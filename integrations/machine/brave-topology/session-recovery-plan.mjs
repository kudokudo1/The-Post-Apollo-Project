/* MACHINE // synthetic browser-session recovery eligibility, phase 1.
 *
 * This pure function accepts explicitly supplied test fixtures. It has NO
 * browser access, storage, IPC, logs, network, file writes or restore actions.
 * URL strings are examined in memory to classify future capture risk. The
 * returned plan contains NO URLs, titles, fragments, queries, browser IDs,
 * Sway IDs or profile names, including on error.
 *
 * This is NOT an authorization to read real tabs: chrome.tabs URL access
 * requires a separate browser permission and explicit operator consent.
 */
export const SESSION_PLAN_KIND = "machine-brave-session-recovery-eligibility-v1";
export const MAX_SESSION_WINDOWS = 64;
export const MAX_SESSION_TABS_PER_WINDOW = 2048;
export const MAX_SESSION_TOTAL_TABS = 8192;
const MAX_URL_LENGTH = 4096;
const LABEL = /^[A-Za-z][A-Za-z0-9 _.-]{0,47}$/;

function refuse() {
  throw new TypeError("SESSION RECOVERY PREVIEW REFUSED");
}

function nonnegative(v) {
  return Number.isSafeInteger(v) && v >= 0;
}

function classifyUrl(value) {
  if (typeof value !== "string" || value.length < 1
      || value.length > MAX_URL_LENGTH
      || /[\u0000-\u001f\u007f]/.test(value)) {
    return "not_eligible";
  }
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    return "not_eligible";
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return "not_eligible";
  }
  if (!parsed.hostname || parsed.username || parsed.password) {
    return "not_eligible";
  }
  // Query strings and fragments can carry password-reset/session tokens.
  // Paths can also be sensitive; plain URLs remain *eligibility only*.
  // No URL is returned by this model or approved for persistence.
  return parsed.search || parsed.hash
    ? "requires_sensitive_review" : "candidate_only";
}

export function planSyntheticBraveSession(rawWindows) {
  if (!Array.isArray(rawWindows) || rawWindows.length > MAX_SESSION_WINDOWS) {
    refuse();
  }
  const windows = [];
  const usedLabels = new Set();
  let total = 0;
  let candidates = 0;
  let reviews = 0;
  let excluded = 0;
  let privateSkipped = 0;
  for (const source of rawWindows) {
    if (!source || typeof source !== "object" || Array.isArray(source)) {
      refuse();
    }
    // Skip private windows before accessing their tab content or label.
    if (source.incognito === true) {
      privateSkipped++;
      continue;
    }
    if (source.incognito !== false) {
      refuse();
    }
    if (source.type !== "normal") {
      continue;
    }
    const label = source.operator_label;
    const tabs = source.tabs;
    if (typeof label !== "string" || !LABEL.test(label) ||
        !Array.isArray(tabs) || tabs.length > MAX_SESSION_TABS_PER_WINDOW ||
        total + tabs.length > MAX_SESSION_TOTAL_TABS) {
      refuse();
    }
    const key = label.toLowerCase();
    if (usedLabels.has(key)) refuse();
    usedLabels.add(key);
    const seen = new Set();
    const positions = [];
    let activePosition = null;
    let pinned = 0;
    for (const entry of tabs) {
      if (!entry || typeof entry !== "object" || Array.isArray(entry)
          || !nonnegative(entry.index) || entry.index >= tabs.length
          || seen.has(entry.index)
          || typeof entry.active !== "boolean"
          || typeof entry.pinned !== "boolean"
          || (entry.incognito !== undefined && entry.incognito !== false)) {
        refuse();
      }
      seen.add(entry.index);
      if (entry.active) {
        if (activePosition !== null) refuse();
        activePosition = entry.index;
      }
      if (entry.pinned) pinned++;
      const eligibility = classifyUrl(entry.url);
      if (eligibility === "candidate_only") candidates++;
      else if (eligibility === "requires_sensitive_review") reviews++;
      else excluded++;
      positions.push({position: entry.index, eligibility});
    }
    positions.sort((a,b)=>a.position-b.position);
    total += tabs.length;
    windows.push({
      operator_label: label, display_slot: windows.length + 1,
      tab_count: tabs.length, pinned_tab_count: pinned,
      active_tab_position: activePosition,
      tab_eligibility: positions
    });
  }
  return {
    kind: SESSION_PLAN_KIND,
    status: "synthetic_preview_only",
    read_only: true,
    browser_permission_requested: false,
    user_tab_urls_exported: false,
    titles_exported: false,
    private_windows_excluded: true,
    persistent_session_identity_verified: false,
    browser_sway_binding_verified: false,
    persisted: false,
    restore_allowed: false,
    safe_actions: [],
    counts: {
      normal_windows: windows.length, tabs: total,
      candidate_only: candidates, requires_sensitive_review: reviews,
      not_eligible: excluded, private_windows_skipped: privateSkipped
    },
    windows
  };
}

// Comparing a former browser-window count signature with today's count
// cannot establish which restarted browser window owns a saved session.
// It is always a manual identity gate, even when every count is identical.
export function assessRestartPairing(plan, observedNormalTabCounts) {
  if (!plan || plan.kind !== SESSION_PLAN_KIND ||
      plan.restore_allowed !== false || plan.persisted !== false ||
      !Array.isArray(plan.windows) ||
      !Array.isArray(observedNormalTabCounts) ||
      observedNormalTabCounts.length > MAX_SESSION_WINDOWS ||
      observedNormalTabCounts.some(n => !nonnegative(n) ||
          n > MAX_SESSION_TABS_PER_WINDOW)) {
    refuse();
  }
  return {
    status: "manual_pairing_required",
    saved_window_slots: plan.windows.length,
    observed_window_slots: observedNormalTabCounts.length,
    count_signature_may_repeat: true,
    browser_sway_binding_verified: false,
    persistent_session_identity_verified: false,
    session_restorable: false,
    restore_allowed: false,
    safe_actions: []
  };
}
