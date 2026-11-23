import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { Readable } from "node:stream";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createInvestigation } from "../../scripts/finance/research_investigations.mjs";
import { REQUEST, RESULT_PREFIX, ReadRefusal, performRead, readOneLine
} from "../../scripts/finance/research_investigation_read_bridge.mjs";

const fixtureTime = "2026-11-23T01:00:00Z";
const cases = createInvestigation([], {
  id: "case-1", title: "Source review", question: "What was filed?", timestamp: fixtureTime
});
const expected = {schemaVersion:1, revision:3, investigations:cases};
assert.equal(performRead(REQUEST, command => {
  assert.deepEqual(command, {action:"list"});
  return expected;
}), RESULT_PREFIX + JSON.stringify(expected) + "\n");
assert.throws(() => performRead('{"action":"create"}\n', () => expected),
  e => e instanceof ReadRefusal && e.message === "INVALID_REQUEST");
assert.throws(() => performRead('{"action":"list","hidden":true}\n', () => expected),
  e => e instanceof ReadRefusal && e.message === "INVALID_REQUEST");
assert.throws(() => performRead(REQUEST, () => ({...expected,revision: -1})),
  e => e instanceof ReadRefusal && e.message === "INVALID_RESULT");
assert.throws(() => performRead(REQUEST, () => ({...expected,extra:"secret"})),
  e => e instanceof ReadRefusal && e.message === "INVALID_RESULT");
assert.throws(() => performRead(REQUEST, () => ({...expected,investigations:[{id:"bad"}]})),
  e => e instanceof ReadRefusal && e.message === "INVALID_RESULT");
assert.equal(await readOneLine(Readable.from([
  Buffer.from('{"action":"'),Buffer.from('list"}\n')
])),REQUEST);
await assert.rejects(readOneLine(Readable.from([Buffer.from("x".repeat(257)+"\n")])),
  e => e instanceof ReadRefusal && e.message === "INVALID_FRAME");

const script = fileURLToPath(new URL("../../scripts/finance/research_investigation_read_bridge.mjs", import.meta.url));
const base = fs.mkdtempSync(path.join(os.tmpdir(), "finance-research-m4-"));
function cli(input,extraArgs=[]) {
  return spawnSync(process.execPath,[script,...extraArgs],{
    encoding:"utf8",input,timeout:3000, maxBuffer:1024*1024,
    env:{...process.env,XDG_DATA_HOME:base}
  });
}
try {
  let response = cli(REQUEST);
  assert.equal(response.status,0,response.stderr);
  assert.equal(JSON.parse(response.stdout.slice(RESULT_PREFIX.length)).revision,0);
  assert.equal(fs.existsSync(path.join(base,"post-apollo")),false,
    "read-only invocation must not create storage");
  for (const input of ['{"action":"create"}\n','{"action":"list"}',REQUEST+REQUEST]) {
    response=cli(input);
    assert.equal(response.status,1);
    assert.equal(response.stdout,"");
    assert.match(response.stderr,/^FINANCE_RESEARCH_READ_ERROR (?:INVALID_REQUEST|INVALID_FRAME)\n$/);
  }
  response=cli(REQUEST,["--allow-writes"]);
  assert.equal(response.status,1);
  assert.match(response.stderr,/INVALID_ARGUMENTS/);
  const dir=path.join(base,"post-apollo","finance","research-investigations");
  fs.mkdirSync(dir,{recursive:true,mode:0o700});
  const file=path.join(dir,"investigations.json");
  fs.writeFileSync(file,JSON.stringify(expected)+"\n",{mode:0o600});
  response=cli(REQUEST);
  assert.equal(response.status,0,response.stderr);
  assert.deepEqual(JSON.parse(response.stdout.slice(RESULT_PREFIX.length)),expected);
  assert.equal(fs.statSync(file).mode & 0o077,0);
  fs.writeFileSync(file,"{bad JSON",{mode:0o600});
  response=cli(REQUEST);
  assert.equal(response.status,1);
  assert.equal(response.stdout,"");
  assert.match(response.stderr,/READ_UNAVAILABLE/);
  assert.equal(fs.readFileSync(file,"utf8"),"{bad JSON","must not repair corrupted store");
  console.log("Finance Research M4 read bridge: PASS");
} finally {
  fs.rmSync(base,{recursive:true,force:true});
}
