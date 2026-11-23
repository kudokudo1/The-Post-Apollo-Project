// FinanceW Research M4b-T1: one-shot transport lifecycle for review.
// NO filesystem, child process, network, storage import, or executable entrypoint.
// A caller-supplied dispatch callback is NOT an authorization grant.
import { prepareResearchWrite, acknowledgeResearchWrite } from "./research_investigation_write_contract.mjs";

const clone = value => JSON.parse(JSON.stringify(value));
const STATUS = Object.freeze({
  staged:"STAGED // NOT SENT",
  inFlight:"WRITE IN FLIGHT // DO NOT RETRY",
  acknowledged:"SAVE ACKNOWLEDGED",
  reviewRequired:"OUTCOME UNKNOWN // KEEP DRAFT // RELOAD AND REVIEW"
});

export class ResearchWriteAttempt {
  #proposal;
  #draft;
  #state = "staged";
  #result = null;

  constructor(intent, snapshot, options) {
    // Prepare first; any validation failure creates no attempt to dispatch.
    const proposal = prepareResearchWrite(intent, snapshot, options);
    this.#proposal = proposal;
    this.#draft = clone(intent);
  }

  get state() { return this.#state; }
  get message() { return STATUS[this.#state]; }
  get canRetry() { return false; }
  get wasDispatched() { return this.#state !== "staged"; }
  getDraft() { return this.#draft === null ? null : clone(this.#draft); }
  getVerifiedDocument() {
    return this.#result === null ? null : clone(this.#result);
  }

  async dispatchOnce(dispatch) {
    if (this.#state !== "staged") throw new Error("WRITE_ALREADY_ATTEMPTED");
    if (typeof dispatch !== "function") throw new TypeError("DISPATCH_REQUIRED");
    // State changes BEFORE yielding to the callback. A timeout, throw, crash,
    // unknown exit or mismatched acknowledgement never auto-dispatches again.
    this.#state = "inFlight";
    try {
      const reply = await dispatch(this.#proposal.frame);
      if (!reply || typeof reply !== "object" || Array.isArray(reply)
          || Object.keys(reply).length !== 3
          || !Number.isSafeInteger(reply.exitCode)
          || typeof reply.stdout !== "string" || typeof reply.stderr !== "string"
          || reply.exitCode !== 0 || reply.stderr !== "") throw new Error("UNTRUSTED_EXIT");
      const verified = acknowledgeResearchWrite(reply.stdout, this.#proposal);
      this.#result = clone(verified);
      this.#state = "acknowledged";
      this.#draft = null; // Clear only after exact M2 acknowledgement.
      return {state:"acknowledged", revision:verified.revision};
    } catch {
      this.#state = "reviewRequired";
      // Deliberately return no record or error detail that might expose source text.
      return {state:"reviewRequired", requiresReload:true, autoRetry:false};
    }
  }
}

// No exported helper can dispatch automatically or bind to the actual M2 writer.
// Future protected authorization and Qt/Node transport are separate, reviewed work.
