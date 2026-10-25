#!/usr/bin/env node
"use strict";
// Execute the actual Post-Apollo Social family policy. No credentials, files,
// browser profiles, QML compositor or login providers are modified.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const script=fs.readFileSync(path.join(__dirname,
    "../../services/social/SocialIdentityPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const policy=vm.createContext({});
vm.runInContext(script,policy,{filename:"SocialIdentityPolicy.js"});

const base=policy.initialDocument();
assert.equal(policy.validate(base).ok,true);
assert.equal(policy.view("ready",base,"").familyOptions.length,1);
assert.equal(policy.view("ready",base,"").appChoices.length,32);
assert.equal(policy.view("ready",base,"").appChoices[3].id,"x");
assert.equal(policy.view("ready",base,"").appChoices[3].familyId,"family-1");
assert.equal(policy.view("ready",base,"").appChoices[3].serviceIndex,3);
assert.equal(policy.view("ready",base,"").activeName,"Default");
assert.equal(policy.view("ready",base,"").nextFamilyId,2);

let r=policy.createFamily(base,"  Gaming ");
assert.equal(r.ok,true);
assert.equal(r.familyId,"family-2");
let withGaming=r.document;
assert.equal(withGaming.identities[0].layout.families.length,2);
assert.equal(withGaming.identities[0].layout.families[1].name,"Gaming");
assert.equal(withGaming.identities[0].layout.families[1].expanded,true);
assert.equal(withGaming.identities[0].layout.families[1].appIds.length,0);
assert.equal(base.identities[0].layout.families.length,1);
assert.equal(policy.view("ready",withGaming,"").familyOptions[1].title,"Gaming");
assert.equal(policy.view("ready",withGaming,"").familyOptions[1].count,0);

for(const [name,reason] of [
    ["", "INVALID_FAMILY_NAME"],
    ["  ", "INVALID_FAMILY_NAME"],
    ["bad\nfamily", "INVALID_FAMILY_NAME"],
    ["x".repeat(33), "INVALID_FAMILY_NAME"],
    ["gAMING", "DUPLICATE_FAMILY_NAME"],
    ["all apps", "DUPLICATE_FAMILY_NAME"]
])assert.equal(policy.createFamily(withGaming,name).reason,reason);
assert.equal(policy.createFamily({...base,version:42},"New").reason,"UNSUPPORTED_VERSION");

r=policy.renameFamily(withGaming,"family-2","  Communities ");
assert.equal(r.ok,true);
const renamed=r.document;
assert.equal(renamed.identities[0].layout.families[1].name,"Communities");
assert.equal(renamed.identities[0].layout.families[1].id,"family-2");
assert.equal(withGaming.identities[0].layout.families[1].name,"Gaming");
assert.equal(policy.renameFamily(renamed,"missing","Name").reason,"INVALID_FAMILY");
assert.equal(policy.renameFamily(renamed,"family-2","Communities").reason,"NO_CHANGE");
assert.equal(policy.renameFamily(renamed,"family-2","all apps").reason,
             "DUPLICATE_FAMILY_NAME");
assert.equal(policy.renameFamily(renamed,"family-2","\u0000").reason,
             "INVALID_FAMILY_NAME");

r=policy.moveAppToFamily(renamed,"discord","family-2");
assert.equal(r.ok,true);
const moved=r.document;
assert.equal(moved.identities[0].layout.families[0].appIds.includes("discord"),false);
assert.equal(moved.identities[0].layout.families[1].appIds.join(","),"discord");
assert.equal(renamed.identities[0].layout.families[0].appIds.includes("discord"),true);
assert.equal(policy.validate(moved).ok,true);
assert.equal(policy.view("ready",moved,"").visibleAppIndices.length,32);
assert.equal(policy.view("ready",moved,"").visibleAppIndices.at(-1),1);
assert.equal(policy.view("ready",moved,"").appChoices[1].familyId,"family-2");
assert.equal(policy.view("ready",moved,"").familyOptions[0].count,31);
assert.equal(policy.view("ready",moved,"").familyOptions[1].count,1);
assert.equal(policy.moveAppToFamily(moved,"discord","family-2").reason,"NO_CHANGE");
assert.equal(policy.moveAppToFamily(moved,"badservice","family-2").reason,
             "INVALID_APP");
assert.equal(policy.moveAppToFamily(moved,"discord","invalid").reason,
             "INVALID_FAMILY");
assert.equal(policy.moveAppToFamily(moved,"discord",null).reason,
             "INVALID_FAMILY");

// Moving an already-hidden app preserves the independent visibility flag.
const hidden=policy.clone(moved);
hidden.identities[0].layout.hiddenAppIds.push("x");
const hiddenMove=policy.moveAppToFamily(hidden,"x","family-2").document;
assert.equal(hiddenMove.identities[0].layout.hiddenAppIds.includes("x"),true);
assert.equal(policy.view("ready",hiddenMove,"").visibleAppIndices.includes(3),false);

// Copied identities receive detached layout arrays and separate edits.
const copyResult=policy.create(moved,"Work","copy","identity-1");
assert.equal(copyResult.ok,true);
const copied=copyResult.document;
assert.equal(copied.activeId,"identity-2");
assert.equal(copied.identities[1].layout.families[1].name,"Communities");
const workRename=policy.renameFamily(copied,"family-2","Office");
assert.equal(workRename.ok,true);
const workMove=policy.moveAppToFamily(workRename.document,"telegram","family-2");
assert.equal(workMove.ok,true);
assert.equal(workMove.document.identities[0].layout.families[1].name,"Communities");
assert.equal(workMove.document.identities[0].layout.families[1].appIds.join(","),
             "discord");
assert.equal(workMove.document.identities[1].layout.families[1].name,"Office");
assert.equal(workMove.document.identities[1].layout.families[1].appIds.join(","),
             "discord,telegram");
const back=policy.select(workMove.document,"identity-1").document;
assert.equal(policy.view("ready",back,"").activeName,"Default");
assert.equal(policy.view("ready",back,"").familyOptions[1].title,"Communities");

// Start-empty users can create the first family, then assign any known app.
const blank=policy.create(base,"Blank","empty","").document;
assert.equal(policy.view("ready",blank,"").familyOptions.length,0);
assert.equal(policy.view("ready",blank,"").appChoices[1].familyId,"");
const made=policy.createFamily(blank,"My networks").document;
assert.equal(made.identities[1].layout.families[0].id,"family-1");
const placed=policy.moveAppToFamily(made,"discord","family-1").document;
assert.equal(policy.view("ready",placed,"").visibleAppIndices.join(","),"1");
assert.equal(policy.view("ready",placed,"").railRows[1].serviceIndex,1);
assert.equal(policy.view("ready",blank,"").railRows[0].kind,"empty");

// Reject duplicate saved family names, invalid membership and stale schema.
const dup=policy.clone(moved);
dup.identities[0].layout.families[1].name="all apps";
assert.equal(policy.validate(dup).ok,false);
const duplicateMembership=policy.clone(moved);
duplicateMembership.identities[0].layout.families[1].appIds.push("telegram");
duplicateMembership.identities[0].layout.families[0].appIds.push("discord");
assert.equal(policy.validate(duplicateMembership).ok,false);
const invalidDoc={version:999,identities:[]};
assert.equal(policy.view("unsupported",invalidDoc,"UNSUPPORTED_VERSION").writable,false);
assert.equal(policy.view("unsupported",invalidDoc,"UNSUPPORTED_VERSION").familyOptions.length,0);
assert.equal(policy.view("unsupported",invalidDoc,"UNSUPPORTED_VERSION").railRows.length,33);

const injected=policy.clone(moved);
injected.identities[0].layout.families[1].authToken="SECRET_NEVER_SAVE";
injected.identities[0].credentials="SECRET_NEVER_SAVE";
const scrubbed=policy.parse(JSON.stringify(injected));
assert.equal(scrubbed.ok,true);
assert.equal(JSON.stringify(scrubbed.document).includes("SECRET_NEVER_SAVE"),false);

// Enforce explicit family bounds with no mutation on failure.
const full=policy.initialDocument();
full.identities[0].layout.families=[];
for(let i=1;i<=policy.MAX_FAMILIES;i++)
    full.identities[0].layout.families.push({
        id:"family-"+i,name:"Group"+i,appIds:[],expanded:true
    });
full.identities[0].layout.nextFamilyId=policy.MAX_FAMILIES+1;
assert.equal(policy.validate(full).ok,true);
assert.equal(policy.createFamily(full,"Extra").reason,"FAMILY_CAPACITY");
assert.equal(full.identities[0].layout.families.length,policy.MAX_FAMILIES);

console.log("Social family manager: create/rename/move/isolation/validation PASS");
