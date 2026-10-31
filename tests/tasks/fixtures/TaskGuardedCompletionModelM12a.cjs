"use strict";

/**
 * TASKS M12a // Synthetic-only guarded UI completion state model.
 *
 * A PURE JavaScript protocol test. No I/O, subprocess, QML, FileView, journal,
 * host authentication, actual task data or production activation. The "host"
 * frames and booleans are caller-provided mock evidence and MUST NOT be
 * accepted as production security decisions.
 */
const crypto = require("node:crypto");

const STATES = Object.freeze([
  "DISCONNECTED", "READY", "RESERVING", "RESERVED", "FROZEN", "RECOVERY_REVIEW"
]);
const sha = value => crypto.createHash("sha256").update(
  JSON.stringify(value)).digest("hex");
const clone = value => JSON.parse(JSON.stringify(value));
const safeToken = value => typeof value === "string" &&
  /^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(value);
const exactKeys = (obj, names) => obj !== null &&
  typeof obj === "object" && !Array.isArray(obj) &&
  Object.keys(obj).length === names.length &&
  names.every(key => Object.hasOwn(obj, key));

class SyntheticGuardedModel {
  #confirmed;
  #sourceHash;
  #owner = null;
  #pending = null;
  #phase = "DISCONNECTED";
  #errorCode = "";

  constructor(confirmed) {
    if (!confirmed || typeof confirmed !== "object" ||
        !Array.isArray(confirmed.tasks) || !Array.isArray(confirmed.projects)) {
      throw new TypeError("SYNTHETIC_CONFIRMED_DOCUMENT_REQUIRED");
    }
    this.#confirmed = clone(confirmed);
    this.#sourceHash = sha(this.#confirmed);
  }

  static get syntheticOnly() { return true; }
  static get productionWriterAuthorized() { return false; }
  static get states() { return [...STATES]; }

  get phase() { return this.#phase; }
  get sourceHash() { return this.#sourceHash; }

  #review(code) {
    this.#phase = "RECOVERY_REVIEW";
    this.#errorCode = code;
    // The pending candidate stays private for operator review. Never publish
    // or auto-replay it, and never erase the last confirmed document.
    return false;
  }

  attachSyntheticOwner(frame) {
    if (this.#phase !== "DISCONNECTED") return false;
    if (!exactKeys(frame, [
      "testOnly", "sessionId", "epoch", "generation",
      "baselineHash", "testTrustCheck", "testBackupReadback"
    ]) || frame.testOnly !== true ||
        frame.testTrustCheck !== true ||
        frame.testBackupReadback !== true ||
        !safeToken(frame.sessionId) ||
        !Number.isSafeInteger(frame.epoch) || frame.epoch < 0 ||
        !Number.isSafeInteger(frame.generation) || frame.generation < 1 ||
        frame.baselineHash !== this.#sourceHash) {
      return this.#review("SYNTHETIC_PREFLIGHT_REFUSED");
    }
    this.#owner = {
      sessionId: frame.sessionId, epoch: frame.epoch,
      generation: frame.generation
    };
    this.#phase = "READY";
    this.#errorCode = "";
    return true;
  }

  request(policyResult, stageId) {
    const rejected = { queued: false, admitted: false, saved: false };
    if (this.#phase !== "READY" || this.#pending !== null) return rejected;
    if (!safeToken(stageId) ||
        !policyResult || policyResult.ok !== true ||
        !policyResult.document || typeof policyResult.document !== "object" ||
        !Array.isArray(policyResult.document.tasks) ||
        !Array.isArray(policyResult.document.projects)) return rejected;
    const candidate = clone(policyResult.document);
    const expectedHash = sha(candidate);
    if (expectedHash === this.#sourceHash) return rejected;
    this.#pending = {
      stageId, candidate, expectedHash, beforeHash: this.#sourceHash,
      sessionId: this.#owner.sessionId, epoch: this.#owner.epoch,
      generation: this.#owner.generation, nativeNotifications: 0
    };
    this.#phase = "RESERVING";
    // "queued" is not durable admission, a FileView write or a save.
    return { queued: true, admitted: false, saved: false };
  }

  reservation(frame) {
    if (this.#phase !== "RESERVING" || this.#pending === null) return false;
    const p = this.#pending;
    if (!exactKeys(frame, [
      "kind", "stageId", "sessionId", "epoch", "generation",
      "beforeHash", "expectedHash", "durablyReserved"
    ]) || frame.kind !== "RESERVED" || frame.durablyReserved !== true ||
        frame.stageId !== p.stageId || frame.sessionId !== p.sessionId ||
        frame.epoch !== p.epoch || frame.generation !== p.generation ||
        frame.beforeHash !== p.beforeHash ||
        frame.expectedHash !== p.expectedHash) {
      return this.#review("STAGE_RESERVATION_UNCERTAIN");
    }
    this.#phase = "RESERVED";
    return true;
  }

  nativeCallback(kind) {
    if (kind !== "onSaved" && kind !== "onLoaded" &&
        kind !== "onSaveFailed" && kind !== "onLoadFailed") return false;
    // Real FileView callbacks do not contain durable stage provenance:
    // no native notification can ever publish confirmed task content.
    if (this.#pending === null) return false;
    if (kind === "onSaveFailed" || kind === "onLoadFailed")
      return this.#review("NATIVE_IO_UNCERTAIN");
    if (kind === "onSaved" && this.#phase === "RESERVED")
      this.#pending.nativeNotifications += 1;
    return false;
  }

  settlement(frame) {
    if (this.#phase !== "RESERVED" || this.#pending === null) return false;
    const p = this.#pending;
    if (!exactKeys(frame, [
      "kind", "stageId", "sessionId", "epoch", "generation",
      "beforeHash", "expectedHash", "actualReadbackHash",
      "journalSettled", "testOnly"
    ]) || frame.kind !== "SETTLED" || frame.testOnly !== true ||
        frame.journalSettled !== true || frame.stageId !== p.stageId ||
        frame.sessionId !== p.sessionId || frame.epoch !== p.epoch ||
        frame.generation !== p.generation ||
        frame.beforeHash !== p.beforeHash ||
        frame.expectedHash !== p.expectedHash ||
        frame.actualReadbackHash !== p.expectedHash) {
      return this.#review("SETTLEMENT_UNCERTAIN");
    }
    // ONLY the accepted synthetic host settlement can publish. This model
    // does NOT prove that a real frame is authenticated or actually durable.
    this.#confirmed = clone(p.candidate);
    this.#sourceHash = p.expectedHash;
    this.#pending = null;
    this.#phase = "READY";
    this.#errorCode = "";
    return true;
  }

  hostExit() {
    return this.#phase === "DISCONNECTED" ||
      this.#phase === "RECOVERY_REVIEW" ? false :
      this.#review("FRESH_OWNER_REVIEW_REQUIRED");
  }

  freeze() {
    if (this.#phase === "READY") {
      this.#phase = "FROZEN";
      return true;
    }
    if (this.#pending !== null)
      return this.#review("FREEZE_WITH_PENDING_STAGE");
    return false;
  }

  snapshot() {
    const confirmed = clone(this.#confirmed);
    const pending = this.#pending !== null;
    // Overlay proposed for a future UI. Existing TodoPolicy.view currently
    // hides rows on error. This is deliberately NOT wired into that policy.
    return {
      syntheticOnly: true,
      productionWriterAuthorized: false,
      state: this.#phase === "READY" ? (confirmed.tasks.length ? "ready" : "empty")
        : pending && (this.#phase === "RESERVING" ||
                     this.#phase === "RESERVED") ? "saving"
        : this.#phase === "RECOVERY_REVIEW" ? "error" : "loading",
      phase: this.#phase,
      writable: this.#phase === "READY",
      error: this.#errorCode,
      pending,
      confirmed, items: clone(confirmed.tasks),
      pendingStageId: pending ? this.#pending.stageId : null,
      confirmedHash: this.#sourceHash
    };
  }
}

module.exports = { SyntheticGuardedModel, sha };
