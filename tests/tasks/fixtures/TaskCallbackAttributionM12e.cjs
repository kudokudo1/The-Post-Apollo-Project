"use strict";

/**
 * M12e synthetic-only callback attribution and native-trace ambiguity model.
 *
 * No native FileView invocation, task IO, process, network, live host or
 * production authority. The M11g standalone native harness can report
 * callback tags; those tags have no durable stage identity.
 *
 * Host replies used by tests are plain objects, NOT authenticated receipts.
 * This isolates callback ordering and proves why external durable evidence
 * is required before publishing. Never import into production TASKS.
 */
const crypto = require("node:crypto");

const TAGS = new Set([
  "FILE_SAVED", "FILE_READBACK_OK", "FILE_LOAD_FAILED",
  "FILE_SAVE_FAILURE", "FILE_READBACK_MISMATCH",
  "HOST_ADMIT", "HOST_SETTLED", "HOST_EXIT"
]);
const digest = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const copy = x => JSON.parse(JSON.stringify(x));
const isToken = x => typeof x === "string" &&
  /^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,95}$/.test(x);
const exact = (x, keys) => x !== null && typeof x === "object" &&
  !Array.isArray(x) && Object.keys(x).length === keys.length &&
  keys.every(key => Object.hasOwn(x,key));

/**
 * Two distinct possible physical histories can yield the *same native event*
 * transcript. The event has no source inode/session/epoch/stage/provenance.
 */
function callbackTranscript(world) {
  if (world !== "current" && world !== "stale") throw Error("SYNTHETIC_WORLD_ONLY");
  const actual = world === "current" ? "STAGE_A" : "STAGE_PREVIOUS";
  return {
    physicalOrigin: actual, // intentionally excluded from observable transcript
    observable: [
      { tag: "FILE_SAVED" },
      { tag: "FILE_READBACK_OK" }
    ]
  };
}

class CallbackAttributionProbe {
  #stage = null;
  #confirmed = null;
  #confirmedRaw = "";
  #pending = null;
  #phase = "DISCONNECTED";
  #reason = "";
  #callbacks = [];
  constructor(initialRaw, initialDocument) {
    if (typeof initialRaw !== "string" || initialRaw.length === 0 ||
        initialDocument === null || typeof initialDocument !== "object" ||
        !Array.isArray(initialDocument.tasks))
      throw Error("SYNTHETIC_INITIAL_DOCUMENT_REQUIRED");
    this.#confirmedRaw = initialRaw;
    this.#confirmed = copy(initialDocument);
  }
  attach(frame) {
    if (this.#phase !== "DISCONNECTED" ||
        !exact(frame,["sessionId","epoch","generation","fixtureOnly"]) ||
        !isToken(frame.sessionId) ||
        !Number.isSafeInteger(frame.epoch) || frame.epoch < 0 ||
        !Number.isSafeInteger(frame.generation) || frame.generation < 1 ||
        frame.fixtureOnly !== true) {
      return this.#review("UNVERIFIED_SYNTHETIC_OWNER");
    }
    this.#stage = { ...frame };
    this.#phase = "READY";
    return true;
  }
  stage(ticket) {
    if (this.#phase !== "READY" || this.#pending) return false;
    if (!exact(ticket, ["stageId","raw","candidate","baselineHash"]) ||
        !isToken(ticket.stageId) || typeof ticket.raw !== "string" ||
        ticket.raw.length < 1 || ticket.raw.length > 65536 ||
        ticket.baselineHash !== digest(this.#confirmedRaw) ||
        !ticket.candidate || !Array.isArray(ticket.candidate.tasks) ||
        digest(ticket.raw) === ticket.baselineHash) return false;
    this.#pending = {
      stageId: ticket.stageId, raw: ticket.raw,
      expectedHash: digest(ticket.raw), baselineHash: ticket.baselineHash,
      candidate: copy(ticket.candidate),
      sessionId: this.#stage.sessionId, epoch: this.#stage.epoch,
      generation: this.#stage.generation,
      nativeSeen: false, readbackSeen: false
    };
    this.#phase = "QUEUED";
    return true;
  }
  reserve(frame) {
    if (!this.#pending || this.#phase !== "QUEUED") return false;
    const p = this.#pending;
    if (!exact(frame,["kind","stageId","sessionId","epoch","generation",
                     "baselineHash","expectedHash","durableFixtureReservation"]) ||
        frame.kind !== "RESERVED" ||
        frame.durableFixtureReservation !== true ||
        frame.stageId !== p.stageId || frame.sessionId !== p.sessionId ||
        frame.epoch !== p.epoch || frame.generation !== p.generation ||
        frame.baselineHash !== p.baselineHash ||
        frame.expectedHash !== p.expectedHash)
      return this.#review("RESERVATION_UNCERTAIN");
    this.#phase = "RESERVED";
    return true;
  }
  nativeEvent(tag) {
    if (!TAGS.has(tag)) return false;
    this.#callbacks.push(tag);
    if (tag === "HOST_EXIT") return this.#review("HOST_IDENTITY_LOST");
    if (["FILE_LOAD_FAILED", "FILE_SAVE_FAILURE", "FILE_READBACK_MISMATCH"].includes(tag))
      return this.#review("NATIVE_IO_UNCERTAIN");
    if (!this.#pending || this.#phase === "RECOVERY_REVIEW") return false;
    if (tag === "FILE_SAVED") {
      if (this.#phase !== "RESERVED" || this.#pending.nativeSeen)
        return this.#review("NATIVE_CALLBACK_AMBIGUOUS");
      this.#pending.nativeSeen = true;
      // The notification never identifies what was physically saved.
      // A separate deferred readback and host journal settlement are needed.
    } else if (tag === "FILE_READBACK_OK") {
      // This tag is just a claim. It cannot stand in for actual bytes.
      return false;
    }
    return false;
  }
  readback(ticket, raw) {
    const p = this.#pending;
    if (!p || this.#phase !== "RESERVED" || !p.nativeSeen ||
        !exact(ticket,["stageId","sessionId","epoch","generation"]) ||
        ticket.stageId !== p.stageId || ticket.sessionId !== p.sessionId ||
        ticket.epoch !== p.epoch || ticket.generation !== p.generation ||
        typeof raw !== "string" ||
        raw !== p.raw || digest(raw) !== p.expectedHash)
      return this.#review("DEFERRED_READBACK_UNCERTAIN");
    p.readbackSeen = true;
    this.#phase = "VERIFYING";
    return true;
  }
  settle(receipt) {
    const p = this.#pending;
    if (!p || this.#phase !== "VERIFYING" || !p.readbackSeen ||
        !exact(receipt,["kind","stageId","sessionId","epoch","generation",
                       "baselineHash","actualSourceHash","expectedHash",
                       "journalSettled","testOnly"]) ||
        receipt.kind !== "SETTLED" || receipt.testOnly !== true ||
        receipt.journalSettled !== true ||
        receipt.stageId !== p.stageId || receipt.sessionId !== p.sessionId ||
        receipt.epoch !== p.epoch || receipt.generation !== p.generation ||
        receipt.baselineHash !== p.baselineHash ||
        receipt.actualSourceHash !== p.expectedHash ||
        receipt.expectedHash !== p.expectedHash)
      return this.#review("HOST_SETTLEMENT_UNCERTAIN");
    this.#confirmed = copy(p.candidate);
    this.#confirmedRaw = p.raw;
    this.#pending = null;
    this.#phase = "READY";
    return true;
  }
  freeze() {
    return this.#review("EXPLICIT_FREEZE_REVIEW");
  }
  #review(reason) {
    this.#phase = "RECOVERY_REVIEW";
    this.#reason = reason;
    return false;
  }
  snapshot() {
    return {
      phase: this.#phase, reason: this.#reason,
      confirmed: copy(this.#confirmed),
      confirmedHash: digest(this.#confirmedRaw),
      pending: this.#pending !== null,
      confirmedPublicationAllowed: false,
      writable: this.#phase === "READY",
      nativeTags: [...this.#callbacks],
      syntheticOnly: true,
      productionWriterAuthorized: false
    };
  }
}

module.exports = { callbackTranscript, CallbackAttributionProbe, digest };
