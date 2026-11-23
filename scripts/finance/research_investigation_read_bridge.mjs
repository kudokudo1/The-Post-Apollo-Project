#!/usr/bin/env node
// FinanceW Research M4a: explicit, read-only bridge for the M2 local store.
// This executable has no write commands, no API calls and no automatic retries.
// A single newline-terminated list request is enough; stdin need not close.
import { fileURLToPath } from "node:url";
import path from "node:path";
import { run } from "./research_investigation_store.mjs";
import { validateCollection } from "./research_investigations.mjs";

export const REQUEST = '{"action":"list"}\n';
export const RESULT_PREFIX = "FINANCE_RESEARCH_READ_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_READ_ERROR ";
const MAX_REQUEST_BYTES = 256;
const MAX_RESPONSE_BYTES = 500000;

export class ReadRefusal extends Error {}
function refuse(code) { throw new ReadRefusal(code); }
function isExactDocument(doc) {
  return doc && typeof doc === "object" && !Array.isArray(doc)
    && Object.keys(doc).length === 3
    && Object.prototype.hasOwnProperty.call(doc, "schemaVersion")
    && Object.prototype.hasOwnProperty.call(doc, "revision")
    && Object.prototype.hasOwnProperty.call(doc, "investigations")
    && doc.schemaVersion === 1
    && Number.isSafeInteger(doc.revision) && doc.revision >= 0
    && validateCollection(doc.investigations);
}
export function performRead(raw, readStore = run) {
  if (raw !== REQUEST) refuse("INVALID_REQUEST");
  const document = readStore({action:"list"});
  if (!isExactDocument(document)) refuse("INVALID_RESULT");
  const payload = JSON.stringify(document);
  if (Buffer.byteLength(payload, "utf8") > MAX_RESPONSE_BYTES) refuse("RESULT_TOO_LARGE");
  return RESULT_PREFIX + payload + "\n";
}
export async function readOneLine(input) {
  let total = 0;
  const buffers = [];
  for await (const chunk of input) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    total += bytes.length;
    if (total > MAX_REQUEST_BYTES) refuse("INVALID_FRAME");
    buffers.push(bytes);
    if (bytes.includes(10)) break;
  }
  const frame = Buffer.concat(buffers);
  if (frame.length === 0 || frame[frame.length - 1] !== 10) refuse("INVALID_FRAME");
  return frame.toString("utf8");
}
const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  try {
    // Reject all executable flags. Nothing can switch this bridge into write mode.
    if (process.argv.length !== 2) refuse("INVALID_ARGUMENTS");
    const frame = await readOneLine(process.stdin);
    process.stdout.write(performRead(frame));
  } catch (error) {
    process.stderr.write(ERROR_PREFIX + (error instanceof ReadRefusal
      ? error.message : "READ_UNAVAILABLE") + "\n");
    process.exitCode = 1;
  }
}
