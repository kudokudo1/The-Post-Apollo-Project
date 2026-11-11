/* MACHINE // strict per-page, in-memory marker candidate lifecycle.
 *
 * The browser window and Sway container numbers are ephemeral observations.
 * This module has no clocks, storage, network, host actions or restore grant.
 * A focus/tab/page lifecycle event invalidates outstanding asynchronous reads.
 */
function positive(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function safePlace(value) {
  return typeof value === "string"
    && value.length >= 1 && value.length <= 128
    && !/[\u0000-\u001f\u007f]/.test(value);
}

export class MarkerCandidateLifecycle {
  #generation = 0;
  #candidate = null;

  begin({tabId, windowId, token}) {
    if (!positive(tabId) || !positive(windowId)
        || typeof token !== "string"
        || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(token)) {
      this.revoke();
      return null;
    }
    this.#generation += 1;
    return Object.freeze({generation: this.#generation, tabId, windowId, token});
  }

  isCurrent(ticket) {
    return ticket !== null && typeof ticket === "object"
      && ticket.generation === this.#generation;
  }

  accept(ticket, {tabId, windowId, token, conId, output, workspace}) {
    if (!this.isCurrent(ticket)) return {status: "stale"};
    if (!positive(tabId) || !positive(windowId) || !positive(conId)
        || ticket.tabId !== tabId || ticket.windowId !== windowId
        || ticket.token !== token || !safePlace(output) || !safePlace(workspace)) {
      this.revoke();
      return {status: "invalid"};
    }
    const next = Object.freeze({tabId, windowId, token, conId, output, workspace});
    const previous = this.#candidate;
    if (previous && Object.keys(next).some(key => next[key] !== previous[key])) {
      this.revoke();
      return {status: "changed"};
    }
    this.#candidate = next;
    return {status: "candidate", candidate: next};
  }

  revoke() {
    this.#generation += 1;
    this.#candidate = null;
  }

  get candidate() {
    return this.#candidate;
  }
}
