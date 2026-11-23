// Research M4b-T2: explicitly disposable, test-only dispatcher.
// This module never resolves XDG_DATA_HOME, the user's home, or production storage.
// It is not an identity check, permission grant, or authorized live writer.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { run, Refusal } from "./research_investigation_store.mjs";

const MAX_COMMAND_BYTES = 8192;
const PREFIX = "FINANCE_RESEARCH_STORE_RESULT ";
const allowedFields = Object.freeze({
  create:["action","expectedRevision","id","title","question","timestamp"],
  attach:["action","expectedRevision","investigationId","evidence","timestamp"],
  remove:["action","expectedRevision","investigationId","evidenceId","timestamp"]
});
function exactFields(value, keys) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === keys.length
    && keys.every(key => Object.prototype.hasOwnProperty.call(value,key));
}
const refusal = () => ({exitCode:1,stdout:"",stderr:"DISPOSABLE_TEST_REFUSAL"});

export class DisposableResearchDispatcher {
  #root;
  #dir;
  #closed = false;
  #dispatches = 0;
  constructor(targetOverride) {
    // There is no configurable target path, even for a test caller.
    if (targetOverride !== undefined) throw new TypeError("TARGET_OVERRIDE_FORBIDDEN");
    this.#root = fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m4b-t2-"));
    fs.chmodSync(this.#root,0o700);
    this.#dir = path.join(this.#root,"research");
  }
  get mode() { return "DISPOSABLE_TEST_ONLY"; }
  get dispatchCount() { return this.#dispatches; }
  get closed() { return this.#closed; }

  dispatch(frame) {
    if (this.#closed) return refusal();
    if (typeof frame !== "string"
        || Buffer.byteLength(frame,"utf8") > MAX_COMMAND_BYTES
        || !frame.endsWith("\n")
        || frame.indexOf("\n") !== frame.length-1) return refusal();
    let command;
    try { command = JSON.parse(frame); } catch { return refusal(); }
    if (!command || !Object.prototype.hasOwnProperty.call(allowedFields,command.action)
        || !exactFields(command,allowedFields[command.action])
        || !Number.isSafeInteger(command.expectedRevision)
        || command.expectedRevision < 0) return refusal();
    this.#dispatches += 1;
    try {
      // M2 performs its ordinary locks/revision checks, *but only* on a fresh
      // OS-created private temp location. No user-selected target is possible.
      const doc = run(command,this.#dir);
      return {exitCode:0,stdout:PREFIX+JSON.stringify(doc)+"\n",stderr:""};
    } catch (error) {
      // Never expose file contents, paths, or caller input in response messages.
      if (error instanceof Refusal) return refusal();
      return refusal();
    }
  }

  readTestSnapshot() {
    if (this.#closed) throw new Error("DISPOSABLE_CLOSED");
    return structuredClone(run({action:"list"},this.#dir));
  }

  destroy() {
    if (this.#closed) return;
    this.#closed = true;
    // The root comes exclusively from mkdtemp and is not caller-controlled.
    fs.rmSync(this.#root,{recursive:true,force:true});
  }
}
