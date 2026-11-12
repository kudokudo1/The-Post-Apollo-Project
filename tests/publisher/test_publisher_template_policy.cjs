#!/usr/bin/env node
"use strict";
// Exercise the production P1.3 engine. No files, account tokens or outgoing posts.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/publisher/PublisherTemplatePolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename:"PublisherTemplatePolicy.js"});

let doc = policy.emptyDocument();
assert.equal(policy.validate(doc).ok, true);
assert.equal(policy.view("empty",doc).writable, true);
for (const state of ["loading","saving","error","unsupported"])
    assert.equal(policy.view(state,doc).writable, false);

const facts = [
    {key:"role",value:"Field Representative"},
    {key:"location",value:"Kentucky"},
    {key:"apply_url",value:"https://example.org/apply?from=social"},
];
const pattern = "Hiring: {{role}} in {{location}}.\nApply: {{apply_url}}";
const render = policy.render(pattern, facts, "recruitment");
assert.equal(render.ok, true);
assert.equal(render.facts, 3);
assert.equal(render.body, "Hiring: Field Representative in Kentucky.\nApply: https://example.org/apply?from=social");
assert.equal(policy.render("Creative line {{role}} / {{location}} / {{apply_url}}",facts,"recruitment").ok,true);
assert.equal(policy.render(pattern.replace("{{location}}","elsewhere"),facts,"recruitment").reason,
             "LOCKED_FACT_NOT_USED");
assert.equal(policy.render(pattern + " {{unknown}}",facts,"recruitment").reason,
             "UNBOUND_PLACEHOLDER");
assert.equal(policy.render(pattern + " {{wrong-token}}",facts,"recruitment").reason,
             "MALFORMED_PLACEHOLDER");
assert.equal(policy.render(pattern + " {{",facts,"recruitment").reason,
             "MALFORMED_PLACEHOLDER");
assert.equal(policy.render(pattern.replace("{{apply_url}}",""),facts,"recruitment").reason,
             "LOCKED_FACT_NOT_USED");
assert.equal(policy.render("hello",[], "recruitment").reason,"REQUIRED_FACT_MISSING");
assert.equal(policy.render("hello",[], "resource").reason,"REQUIRED_FACT_MISSING");
assert.equal(policy.render("hello",[], "creator").ok,true);
assert.equal(policy.render("{{role}}",[{key:"role",value:"{{unsafe}}"}],"creator").reason,
             "INVALID_TEMPLATE");
assert.equal(policy.render("{{role}}",[{key:"role",value:"x"},{key:"role",value:"y"}],"creator").reason,
             "INVALID_TEMPLATE");
assert.equal(policy.preview("Post","creator","en","Hello {{topic}}","topic = New video").body,
             "Hello New video");
assert.equal(policy.preview("Post","creator","en","Hello {{topic}}","topic = ").reason,
             "INVALID_FACT");
assert.equal(policy.preview("Post","creator","es","Hola {{tema}}","tema = Aviso").ok,true);
assert.equal(policy.preview("Post","creator","zzz-ZZ-??","Hello","").reason,
             "INVALID_TITLE_OR_LANGUAGE");
assert.equal(policy.parseFactLines("role = engineer\nrole = moderator").reason,
             "DUPLICATE_FACT_KEY");
assert.equal(policy.parseFactLines("not an assignment").reason,
             "FACT_FORMAT_KEY_EQUALS_VALUE");
assert.equal(policy.parseFactLines("name = before{{test}}after").reason,
             "INVALID_FACT");
assert.equal(policy.parseFactLines("apply_url = https://example.org/?k=a=b").facts[0].value,
             "https://example.org/?k=a=b");

const saved = policy.save(doc,"","Kentucky Recruitment","recruitment","en",
    pattern,facts,1000);
assert.equal(saved.ok,true);
assert.equal(saved.templateId,"p1");
assert.equal(doc.templates.length,0,"no mutation of already-saved state");
assert.equal(saved.document.templates[0].name,"Kentucky Recruitment");
doc = saved.document;
const revised = policy.save(doc,"p1","Kentucky Recruitment","recruitment","en-US",
    "Now hiring {{role}} in {{location}}\n{{apply_url}}",facts,1500);
assert.equal(revised.ok,true);
assert.equal(revised.document.templates[0].createdAtMs,1000);
assert.equal(revised.document.templates[0].updatedAtMs,1500);
assert.equal(doc.templates[0].language,"en");
assert.equal(policy.save(doc,"p99","Unknown","creator","en","test",[],3000).reason,
             "UNKNOWN_TEMPLATE");
assert.equal(policy.save(doc,"p1","Old","recruitment","en",pattern,facts,900).reason,
             "STALE_CLOCK");
assert.equal(policy.save(doc,"","Too long?","creator","en","a".repeat(5001),[],900).reason,
             "INVALID_TEMPLATE");
assert.equal(policy.parse(JSON.stringify(revised.document)).ok,true);
assert.equal(policy.parse("{").reason,"MALFORMED_JSON");
assert.equal(policy.parse(JSON.stringify({...doc,token:"DO_NOT_COPY"})).reason,
             "UNKNOWN_FIELDS");
assert.equal(policy.parse(JSON.stringify({...doc,version:2})).reason,
             "UNSUPPORTED_VERSION");
const dup = JSON.parse(JSON.stringify(doc));
dup.templates.push(dup.templates[0]);
assert.equal(policy.parse(JSON.stringify(dup)).reason,"DUPLICATE_TEMPLATE_ID");
const bad = JSON.parse(JSON.stringify(doc));
bad.templates[0].facts.pop();
assert.equal(policy.parse(JSON.stringify(bad)).reason,"REQUIRED_FACT_MISSING");
const rewind = JSON.parse(JSON.stringify(doc));
rewind.nextId = 1;
assert.equal(policy.parse(JSON.stringify(rewind)).reason,"SEQUENCE_REWIND");
assert.equal(policy.parse("x".repeat(1100001)).reason,"INVALID_SOURCE");
for(const category of ["recruitment","resource","announcement","creator"]){
    const starter = policy.preset(category);
    assert.equal(typeof starter.pattern, "string");
    assert.equal(typeof starter.facts, "string");
    assert.equal(policy.preview("new",category,"en",starter.pattern,starter.facts).ok,false,
        "starter cannot silently invent or omit source facts");
}
console.log("Publisher P1.3 locked-fact template policy: all assertions passed");
