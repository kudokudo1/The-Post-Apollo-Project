const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, "services/github/WorkflowSearchPolicy.js"), "utf8").replace(/^\.pragma library\s*/, ""), context);
const rows = Array.from({length: 240}, (_,i)=>({name:"Clock "+i,path:".github/workflows/clock-"+i+".yml"}));
rows.push({name:"Publish qualified native Fedora Xvfb image",path:".github/workflows/native-fedora-xvfb-publish.yml"});
assert.equal(context.filter(rows,"").length,241);
const hit=context.filter(rows," FeDoRa publish ");
assert.equal(hit.length,1);
assert.equal(hit[0].sourceIndex,240);
assert.equal(hit[0].workflow,rows[240]);
assert.equal(context.filter(rows,"native-fedora-xvfb-publish.yml").length,1);
assert.equal(context.filter(rows,"missing").length,0);
assert.equal(context.filter(null,"clock").length,0);
const ui=fs.readFileSync(path.join(root,"widgets/WorkflowLibraryView.qml"),"utf8");
for(const needle of ['objectName: "gitWorkflowSearch"', 'ListView {', 'model: root.filteredWorkflows', 'root.workflowSelected(modelData.sourceIndex)', 'root.libraryStore.addWorkflow(workflow)', 'root.githubService.runWorkflow(path, "")', 'root.libraryStore.workflowAvailable(path)', 'NO MATCH IN LOADED WORKFLOWS', 'accountForContentOrigin: true', 'clickToJump: true', 'wheelEnabled: true']) assert.ok(ui.includes(needle),needle);
assert.ok(!ui.includes("model: root.libraryStore.workflows"));
console.log("Workflow search and stable row identity contracts PASS");

// Library descendants use a parameterized shared signal; the host must not
// call that signal without a mouse-event argument on keyboard activation.
const host=fs.readFileSync(path.join(root,"widgets/GitW.qml"),"utf8");
assert.ok(host.includes('if (typeof item.activateFromGitKeyboard === "function")'));
assert.ok(host.includes("item.activateFromGitKeyboard();"));
assert.equal((ui.match(/function activateFromGitKeyboard\(\)/g)||[]).length,2);
assert.equal((ui.match(/triggered\(null\);/g)||[]).length,2);
assert.ok(!ui.includes("runAction ? Colors.green : Colors.orange"));
