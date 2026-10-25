#!/usr/bin/env node
"use strict";
// Test the real Post-Apollo organization policy without any live accounts,
// file writes, browser processes, or desktop activation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/social/SocialIdentityPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const policy = vm.createContext({});
vm.runInContext(source,policy,{filename:"SocialIdentityPolicy.js"});

const base = policy.initialDocument();
const create = policy.createFamily(base,"Communities");
assert.equal(create.ok,true);
const twice = policy.createFamily(create.document,"Miscellaneous");
assert.equal(twice.ok,true);
const doc = twice.document;
assert.equal(policy.view("ready",doc,"").familyOptions.map(f=>f.title).join(","),
             "ALL APPS,Communities,Miscellaneous");
assert.equal(policy.reorderFamily(base,"family-1",-1).reason,"NO_CHANGE");
assert.equal(policy.reorderFamily(doc,"family-1",-1).reason,"NO_CHANGE");
assert.equal(policy.reorderFamily(doc,"family-3",1).reason,"NO_CHANGE");
assert.equal(policy.reorderFamily(doc,"family-2",0).reason,"INVALID_DIRECTION");
assert.equal(policy.reorderFamily(doc,"family-2","1").reason,"INVALID_DIRECTION");
assert.equal(policy.reorderFamily(doc,"bogus",1).reason,"INVALID_FAMILY");
assert.equal(policy.reorderFamily(doc,7,1).reason,"INVALID_FAMILY");

const movedFamily = policy.reorderFamily(doc,"family-3",-1);
assert.equal(movedFamily.ok,true);
assert.equal(movedFamily.document.identities[0].layout.families.map(f=>f.id).join(","),
             "family-1,family-3,family-2");
assert.equal(doc.identities[0].layout.families.map(f=>f.id).join(","),
             "family-1,family-2,family-3");
assert.equal(policy.view("ready",movedFamily.document,"").familyOptions[1].title,
             "Miscellaneous");
assert.equal(policy.view("ready",movedFamily.document,"").familyOptions[1].orderIndex,1);
assert.equal(policy.view("ready",movedFamily.document,"").familyOptions[1].familyCount,3);
assert.equal(policy.view("ready",movedFamily.document,"").railRows[32].serviceId,"bereal");
// Restore and use a new family for app-order tests.
const docWithDiscord = policy.moveAppToFamily(doc,"discord","family-2").document;
const movedTelegram = policy.moveAppToFamily(docWithDiscord,"telegram","family-2").document;
assert.equal(policy.view("ready",movedTelegram,"").appChoices[1].familyId,"family-2");
assert.equal(policy.view("ready",movedTelegram,"").appChoices[1].orderIndex,0);
assert.equal(policy.view("ready",movedTelegram,"").appChoices[1].siblingCount,2);
assert.equal(policy.view("ready",movedTelegram,"").appChoices[2].orderIndex,1);
assert.equal(policy.reorderApp(movedTelegram,"family-2","discord",-1).reason,"NO_CHANGE");
assert.equal(policy.reorderApp(movedTelegram,"family-2","telegram",1).reason,"NO_CHANGE");
assert.equal(policy.reorderApp(movedTelegram,"family-2","discord",2).reason,
             "INVALID_DIRECTION");
assert.equal(policy.reorderApp(movedTelegram,"family-2","discord",true).reason,
             "INVALID_DIRECTION");
assert.equal(policy.reorderApp(movedTelegram,"family-99","discord",1).reason,
             "INVALID_FAMILY");
assert.equal(policy.reorderApp(movedTelegram,"family-2","x",1).reason,
             "APP_NOT_IN_FAMILY");
assert.equal(policy.reorderApp(movedTelegram,"family-2","fake",1).reason,
             "INVALID_APP");

const swapped = policy.reorderApp(movedTelegram,"family-2","telegram",-1);
assert.equal(swapped.ok,true);
assert.equal(swapped.document.identities[0].layout.families[1].appIds.join(","),
             "telegram,discord");
assert.equal(movedTelegram.identities[0].layout.families[1].appIds.join(","),
             "discord,telegram");
const reorderedView = policy.view("ready",swapped.document,"");
assert.equal(reorderedView.visibleAppIndices.slice(-2).join(","),"2,1");
assert.equal(reorderedView.appChoices[2].orderIndex,0);
assert.equal(reorderedView.railRows.at(-2).serviceIndex,2);
assert.equal(reorderedView.railRows.at(-1).serviceIndex,1);
assert.equal(policy.validate(swapped.document).ok,true);

// Hiding is a visibility preference, never removal or account logout.
const hidden = policy.setAppHidden(swapped.document,"telegram",true);
assert.equal(hidden.ok,true);
assert.equal(hidden.document.identities[0].layout.hiddenAppIds.join(","),"telegram");
assert.equal(hidden.document.identities[0].layout.families[1].appIds.join(","),
             "telegram,discord");
assert.equal(swapped.document.identities[0].layout.hiddenAppIds.length,0);
assert.equal(policy.view("ready",hidden.document,"").appChoices[2].hidden,true);
assert.equal(policy.view("ready",hidden.document,"").visibleAppIndices.includes(2),false);
assert.equal(policy.view("ready",hidden.document,"").visibleAppIndices.includes(1),true);
assert.equal(policy.reorderApp(hidden.document,"family-2","telegram",1).ok,true);
assert.equal(policy.setAppHidden(hidden.document,"telegram",true).reason,"NO_CHANGE");
assert.equal(policy.setAppHidden(hidden.document,"telegram",1).reason,
             "INVALID_VISIBILITY");
assert.equal(policy.setAppHidden(hidden.document,"bogus",true).reason,"INVALID_APP");
const shown = policy.setAppHidden(hidden.document,"telegram",false);
assert.equal(shown.ok,true);
assert.equal(shown.document.identities[0].layout.hiddenAppIds.length,0);
assert.equal(policy.view("ready",shown.document,"").visibleAppIndices.includes(2),true);
assert.equal(policy.view("ready",shown.document,"").appChoices[2].hidden,false);
assert.equal(policy.setAppHidden(shown.document,"telegram",false).reason,"NO_CHANGE");

// Copying keeps hide, order and family structure, but later choices do not leak
// between Post-Apollo identities, even when their family IDs match.
const copied = policy.create(hidden.document,"Gaming","copy","identity-1").document;
assert.equal(policy.view("ready",copied,"").appChoices[2].hidden,true);
const gamingUp = policy.reorderFamily(copied,"family-2",-1).document;
const gamingShow = policy.setAppHidden(gamingUp,"telegram",false).document;
const gamingAppUp = policy.reorderApp(gamingShow,"family-2","discord",-1).document;
assert.equal(gamingAppUp.identities[0].layout.families[1].appIds.join(","),
             "telegram,discord");
assert.equal(gamingAppUp.identities[0].layout.hiddenAppIds.join(","),"telegram");
assert.equal(gamingAppUp.identities[0].layout.families.map(f=>f.id).join(","),
             "family-1,family-2,family-3");
assert.equal(gamingAppUp.identities[1].layout.families.map(f=>f.id).join(","),
             "family-2,family-1,family-3");
assert.equal(gamingAppUp.identities[1].layout.hiddenAppIds.length,0);
assert.equal(gamingAppUp.identities[1].layout.families[0].appIds.join(","),
             "discord,telegram");
const back = policy.select(gamingAppUp,"identity-1").document;
assert.equal(policy.view("ready",back,"").appChoices[2].hidden,true);
assert.equal(policy.view("ready",back,"").familyOptions[1].title,"Communities");

// Start-empty identity: hide/show choices don't invent a family.
const empty = policy.create(base,"Blank","empty","").document;
assert.equal(policy.view("ready",empty,"").visibleAppIndices.length,0);
const emptyHidden = policy.setAppHidden(empty,"discord",true).document;
assert.equal(policy.view("ready",emptyHidden,"").appChoices[1].hidden,true);
assert.equal(policy.view("ready",emptyHidden,"").appChoices[1].familyId,"");
assert.equal(policy.view("ready",emptyHidden,"").visibleAppIndices.length,0);
assert.equal(policy.reorderFamily(empty,"family-1",1).reason,"INVALID_FAMILY");
const newFamily = policy.createFamily(emptyHidden,"Gaming").document;
const assigned = policy.moveAppToFamily(newFamily,"discord","family-1").document;
assert.equal(policy.view("ready",assigned,"").visibleAppIndices.length,0);
assert.equal(policy.setAppHidden(assigned,"discord",false).ok,true);

// Corrupt or future-version configuration remains read-only and is not repaired.
const unsupported = {...base,version:2};
assert.equal(policy.reorderFamily(unsupported,"family-1",1).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.reorderApp(unsupported,"family-1","x",1).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.setAppHidden(unsupported,"x",true).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.view("unsupported",unsupported,"UNSUPPORTED_VERSION").writable,
             false);
assert.equal(policy.view("unsupported",unsupported,"UNSUPPORTED_VERSION").visibleAppIndices.length,
             32);

// Injected secret-like fields remain absent from serialization.
const injected = policy.clone(hidden.document);
injected.secret = "NEVER_COPY_ME";
injected.identities[0].layout.hiddenAppIds.extraSecret = "NEVER_COPY_ME";
const sanitized = policy.parse(JSON.stringify(injected));
assert.equal(sanitized.ok,true);
assert.equal(JSON.stringify(sanitized.document).includes("NEVER_COPY_ME"),false);

console.log("Social ordering and visibility: family, app, hidden, copies, safeguards PASS");
