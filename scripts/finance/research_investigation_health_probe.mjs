#!/usr/bin/env node
// Research M5: explicit, local-only, read-only health probe.
// Output never includes source URLs, titles, questions, summaries or credentials.
// No write action, network request, automatic cleanup, or retry mode exists.
import { fileURLToPath } from "node:url";
import path from "node:path";
import { run } from "./research_investigation_store.mjs";
import { auditResearchSnapshot } from "./research_investigation_source_health.mjs";

export const RESULT_PREFIX = "FINANCE_RESEARCH_HEALTH_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_HEALTH_ERROR ";
const MAX_FRAME_BYTES = 256;
const MAX_RESULT_BYTES = 50000;
const isExact = (obj,keys) => obj && typeof obj === "object"
  && !Array.isArray(obj) && Object.keys(obj).length === keys.length
  && keys.every(k=>Object.prototype.hasOwnProperty.call(obj,k));
export class HealthProbeRefusal extends Error {}
function refuse(code) { throw new HealthProbeRefusal(code); }

export function performHealthProbe(frame, readStore=run) {
  if (typeof frame !== "string" || !frame.endsWith("\n")
      || Buffer.byteLength(frame,"utf8") > MAX_FRAME_BYTES
      || frame.indexOf("\n") !== frame.length-1) refuse("INVALID_FRAME");
  let request;
  try { request=JSON.parse(frame.slice(0,-1)); }
  catch { refuse("INVALID_REQUEST"); }
  if (!isExact(request,["action","asOf","staleDays"])
      || request.action !== "audit") refuse("INVALID_REQUEST");
  // Validate options before accessing storage. This is a synthetic empty input.
  try {
    auditResearchSnapshot({schemaVersion:1,revision:0,investigations:[]},
      {asOf:request.asOf,staleDays:request.staleDays});
  } catch { refuse("INVALID_REQUEST"); }
  const snapshot=readStore({action:"list"}); // Explicit read only.
  const report=auditResearchSnapshot(snapshot,{
    asOf:request.asOf,staleDays:request.staleDays
  });
  const payload=JSON.stringify(report);
  if (Buffer.byteLength(payload,"utf8") > MAX_RESULT_BYTES)
    refuse("RESULT_TOO_LARGE");
  return RESULT_PREFIX+payload+"\n";
}
export async function consumeHealthFrame(input) {
  const buffers=[];
  let total=0,done=false;
  for await(const chunk of input) {
    const bytes=Buffer.isBuffer(chunk)?chunk:Buffer.from(chunk);
    total+=bytes.length;
    if(total>MAX_FRAME_BYTES)refuse("INVALID_FRAME");
    const nl=bytes.indexOf(10);
    if(nl !== -1 && nl !== bytes.length-1)refuse("INVALID_FRAME");
    buffers.push(bytes);
    if(nl !== -1){done=true;break;}
  }
  if(!done)refuse("INVALID_FRAME");
  return Buffer.concat(buffers).toString("utf8");
}
const isMain = process.argv[1]
  && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if(isMain){
  try {
    if(process.argv.length!==2)refuse("INVALID_ARGUMENTS");
    const frame=await consumeHealthFrame(process.stdin);
    process.stdout.write(performHealthProbe(frame));
  }catch(error){
    process.stderr.write(ERROR_PREFIX+
      (error instanceof HealthProbeRefusal ? error.message : "READ_UNAVAILABLE")
      +"\n");
    process.exitCode=1;
  }
}
