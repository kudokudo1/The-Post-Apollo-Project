import assert from "node:assert/strict";
import {
  acknowledgeResearchWrite, prepareResearchWrite, writeFailureState, WriteRefusal
} from "../../scripts/finance/research_investigation_write_contract.mjs";
import { createInvestigation } from "../../scripts/finance/research_investigations.mjs";

const when = "2026-11-23T12:00:00.000Z";
const uuids = [
  "12345678-1234-4234-8234-123456789abc",
  "12345678-1234-4234-8234-123456789abd",
  "12345678-1234-4234-8234-123456789abe"
];
let n = 0;
const options = {clock:()=>when,newId:()=>uuids[n++]};
const failure = code => e => e instanceof WriteRefusal && e.message === code;
const base = {schemaVersion:1, revision:0, investigations:[]};

const create = prepareResearchWrite(
  {action:"create",title:"Public filing notes",question:"What happened?"},base,options);
assert.equal(create.priorRevision,0);
assert.equal(create.command.action,"create");
assert.equal(create.command.expectedRevision,0);
assert.equal(create.command.id,"case-"+uuids[0]);
assert.equal(create.expected.revision,1);
assert.equal(create.expected.investigations.length,1);
assert.equal(base.investigations.length,0,"preflight cannot mutate caller data");
assert.equal(JSON.parse(create.frame).id,create.command.id);
assert.equal(acknowledgeResearchWrite(
  "FINANCE_RESEARCH_STORE_RESULT "+JSON.stringify(create.expected)+"\n",create
).investigations[0].title,"Public filing notes");

const attach = prepareResearchWrite({
  action:"attach",investigationId:create.command.id,title:"Example source",
  summary:"Observation requiring separate verification",
  url:"https://www.sec.gov/Archives/edgar/data/320193/sample.htm"
},create.expected,options);
assert.equal(attach.command.action,"attach");
assert.equal(attach.command.evidence.source,"manual",
  "a typed SEC URL must NOT claim authenticated SEC provenance");
assert.equal(attach.command.evidence.reviewed,false);
assert.equal(attach.command.evidence.id,"source-"+uuids[1]);
assert.equal(attach.expected.revision,2);
assert.equal(attach.expected.investigations[0].evidence.length,1);
assert.equal(create.expected.investigations[0].evidence.length,0);

const remove = prepareResearchWrite({
  action:"remove",investigationId:create.command.id,
  evidenceId:attach.command.evidence.id
},attach.expected,options);
assert.equal(remove.expected.revision,3);
assert.equal(remove.expected.investigations[0].evidence.length,0);
assert.equal(acknowledgeResearchWrite(
  "FINANCE_RESEARCH_STORE_RESULT "+JSON.stringify(remove.expected)+"\n",remove
).revision,3);

for (const invalid of [
  {action:"attach",investigationId:create.command.id,title:"Example",
    summary:"An arbitrary note",url:"https://example.com",source:"sec-edgar-submissions"},
  {action:"create",title:"Case",question:"What?",id:"borrowed-id"},
  {action:"remove",investigationId:create.command.id,evidenceId:"nonexistent"},
  {action:"delete",investigationId:create.command.id},
  {action:"create",title:"",question:"Missing title"},
  {action:"attach",investigationId:create.command.id,title:"Source",
    summary:"Spoof",url:"https://user:password@example.com/path"},
  {action:"attach",investigationId:"other",title:"Source",
    summary:"Missing case",url:"https://example.com"}
]) {
  assert.throws(()=>prepareResearchWrite(invalid,create.expected,
    {clock:()=>when,newId:()=>uuids[0]}), failure(
    invalid.action === "attach" && invalid.source ||
    invalid.action === "create" && Object.hasOwn(invalid,"id") ||
    invalid.action === "delete" ? "INVALID_INTENT" : "INVALID_RESEARCH_CHANGE"));
}
assert.throws(()=>prepareResearchWrite(
  {action:"create",title:"x",question:"y"},{...base,revision:-1},
  {clock:()=>when,newId:()=>uuids[0]}),failure("INVALID_SNAPSHOT"));
assert.throws(()=>prepareResearchWrite(
  {action:"create",title:"x",question:"y"},base,
  {clock:()=>when,newId:()=>"not-uuid"}),failure("INVALID_GENERATED_ID"));
assert.throws(()=>prepareResearchWrite(
  {action:"create",title:"x",question:"y"},base,
  {clock:()=>"invalid-date",newId:()=>uuids[0]}),failure("INVALID_CLOCK"));

const correct = "FINANCE_RESEARCH_STORE_RESULT "+JSON.stringify(create.expected)+"\n";
for(const wrong of [
  "", "FINANCE_RESEARCH_STORE_RESULT {bad JSON\n",
  correct+correct,
  "FINANCE_RESEARCH_STORE_RESULT "+
    JSON.stringify({...create.expected,revision:2})+"\n",
  "FINANCE_RESEARCH_STORE_RESULT "+
    JSON.stringify({...create.expected,investigations:[]})+"\n",
  "FINANCE_RESEARCH_STORE_RESULT "+
    JSON.stringify({...create.expected,silent:"extra"})+"\n"
]) {
  assert.throws(()=>acknowledgeResearchWrite(wrong,create),
    e=>e instanceof WriteRefusal);
}
assert.deepEqual(writeFailureState(),{
  state:"review-required",
  message:"WRITE OUTCOME UNKNOWN // KEEP DRAFT // RELOAD BEFORE ANOTHER ACTION",
  allowRetry:false
});
console.log("Finance Research M4b write-intent contract: PASS");
