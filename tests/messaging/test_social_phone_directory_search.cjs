"use strict";
// Exercises the same pure QML JavaScript directly, with no provider I/O.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
const filename = path.join(__dirname, "../../widgets/messanger/PhoneDirectorySearch.js");
vm.runInContext(fs.readFileSync(filename, "utf8"), ctx, {filename});
const native = values => JSON.parse(JSON.stringify(values));

const contacts = [
 {id:"u:3",displayNameInProfile:"zoe",organization:"",primary:"222"},
 {id:"u:2",displayNameInProfile:"Alice",organization:"School",primary:"111"},
 {id:"u:1",displayNameInProfile:"Bryn",organization:"Office",primary:"333"},
 {id:"u:4",displayNameInProfile:"alex",organization:"Doctor",primary:"444"},
 {id:"u:5",displayNameInProfile:"9th",organization:"",primary:"555"},
 {id:"u:6",displayNameInProfile:"",organization:"",primary:"666"},
];
const messages = [
 {id:"thread-a",displayNameInProfile:"Alex",lastMessage:"Heading home"},
 {id:"thread-b",displayNameInProfile:"Cora",lastMessage:"Call me tomorrow"},
 {id:"thread-c",displayNameInProfile:"Bryn",lastMessage:"Busy"}
];

test("alphabetical sections sorted by displayed name with magenta UI-owned heading rows", () => {
  const rows = native(ctx.contactDirectoryRows(contacts));
  assert.deepEqual(rows.filter(r=>r.kind==="heading").map(r=>r.letter),["#","A","B","U","Z"]);
  assert.deepEqual(rows.filter(r=>r.kind==="contact").map(r=>r.card.id),
    ["u:5","u:4","u:2","u:1","u:6","u:3"]);
  assert.equal(contacts[0].id,"u:3"); // original order unchanged
});

test("contacts search is case-insensitive and looks at name, organization, primary", () => {
  assert.deepEqual(native(ctx.filterContacts(contacts," al ")).map(x=>x.id),["u:2","u:4"]);
  assert.deepEqual(native(ctx.filterContacts(contacts," SCHOOL ")).map(x=>x.id),["u:2"]);
  assert.deepEqual(native(ctx.filterContacts(contacts,"444")).map(x=>x.id),["u:4"]);
  assert.deepEqual(native(ctx.filterContacts(contacts,"missing")),[]);
  assert.equal(ctx.filterContacts(contacts,"").length,6);
});

test("messages search covers loaded conversation names and previews only", () => {
  assert.deepEqual(native(ctx.filterConversations(messages,"call")).map(x=>x.id),["thread-b"]);
  assert.deepEqual(native(ctx.filterConversations(messages,"bRyN")).map(x=>x.id),["thread-c"]);
  assert.deepEqual(native(ctx.filterConversations(messages,"nobody")),[]);
  assert.equal(ctx.filterConversations(messages,"").length,3);
});

test("empty, malformed and non-ASCII names are handled without fake contact identities", () => {
  assert.equal(ctx.sectionLetter("Alpha"),"A");
  assert.equal(ctx.sectionLetter("9th Avenue"),"#");
  assert.equal(ctx.sectionLetter(" Élodie"),"#");
  assert.equal(ctx.sectionLetter(""),"#");
  assert.deepEqual(native(ctx.contactDirectoryRows(null)),[]);
  assert.deepEqual(native(ctx.filterConversations(null,"a")),[]);
  assert.deepEqual(native(ctx.filterContacts(null,"a")),[]);
  assert.deepEqual(native(ctx.contactDirectoryRows([null,{id:"x",displayNameInProfile:"B"}]))
    .filter(x=>x.kind==="contact").map(x=>x.card.id),["x"]);
});

test("read-only presentation never modifies projected cards or conversations", () => {
 const beforeContacts = JSON.stringify(contacts), beforeMessages=JSON.stringify(messages);
 ctx.filterContacts(contacts,"z");
 ctx.contactDirectoryRows(ctx.filterContacts(contacts,"a"));
 ctx.filterConversations(messages,"head");
 assert.equal(JSON.stringify(contacts),beforeContacts);
 assert.equal(JSON.stringify(messages),beforeMessages);
});

test("stable tie ordering does not turn ephemeral ids into storage keys", () => {
 const values = [
  {id:"read-1",displayNameInProfile:"Sam"},
  {id:"read-2",displayNameInProfile:"SAM"},
  {id:"read-3",displayNameInProfile:"Sam"}
 ];
 assert.deepEqual(native(ctx.contactDirectoryRows(values))
   .filter(x=>x.kind==="contact").map(x=>x.card.id),["read-1","read-2","read-3"]);
});
