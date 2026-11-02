#!/usr/bin/env node
/* TASKS M12m: model tests use the real v3 task policy + disposable JSON only. */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "../..");
const {LocalTicketCoordinatorM12m} = require("./fixtures/TaskLocalTicketCoordinatorM12m.cjs");
const {PrivateFixtureAdapterM12m} = require("./fixtures/TaskPrivateFixtureAdapterM12m.cjs");

// Reuse the CURRENT production policy without altering or importing any QML
// runtime. Node's sandbox parses the same policy implementation Quickshell uses.
const policyCode = fsSync.readFileSync(
    path.join(ROOT, "services/hub/ApolloHubTodoPolicy.js"), "utf8");
const scope = vm.createContext({});
vm.runInContext(policyCode.replace(/^\.pragma library\s*/, ""), scope,
                {filename:"ApolloHubTodoPolicy.js", timeout:1000});
const policy = {
    parse:scope.parse, validate:scope.validate, create:scope.create,
    createProject:scope.createProject, emptyDocument:scope.emptyDocument,
    update:scope.update
};

async function fixture(t, {raw} = {}) {
    const root = await fs.mkdtemp("/tmp/m12m-");
    t.after(async () => fs.rm(root, {recursive:true, force:true}));
    const parent = path.join(root, "m11e-fileview-test");
    await fs.mkdir(parent, {mode:0o700});
    const file = path.join(parent, "fixture-only.json");
    const start = raw === undefined ?
        JSON.stringify(policy.emptyDocument(), null, 2) + "\n" : raw;
    await fs.writeFile(file, start, {mode:0o600, flag:"wx"});
    const realStore = new PrivateFixtureAdapterM12m(file);
    return {root, file, realStore, start};
}

const add = (name, now = 1000) => doc => policy.create(doc, name, now);

test("private adapter refuses arbitrary/production paths and invalid names", () => {
    assert.throws(
        () => new PrivateFixtureAdapterM12m("/var/home/operator/.local/share/apollo-hub-todo-v1.json"),
        /M12M_PRIVATE_TEST_FIXTURE_ONLY/);
    assert.throws(
        () => new PrivateFixtureAdapterM12m("/tmp/other/m11e-fileview-test/fixture-only.json"),
        /M12M_PRIVATE_TEST_FIXTURE_ONLY/);
    assert.throws(() => new PrivateFixtureAdapterM12m("fixture-only.json"),
                  /ABSOLUTE_DISPOSABLE_FILE_REQUIRED/);
});

test("attach fails closed on unsupported data and never replaces source", async t => {
    const {realStore, file} = await fixture(t, {raw:'{"version":777}\n'});
    const core = new LocalTicketCoordinatorM12m({store:realStore, policy});
    assert.equal(await core.attach(), false);
    assert.equal(core.snapshot().phase, "RECOVERY_REVIEW");
    const ticket = core.submit(add("Cannot write"));
    assert.equal((await ticket.completion).state, "BLOCKED");
    assert.equal(await fs.readFile(file, "utf8"), '{"version":777}\n');
});

test("one ticket confirms only after independent readback of the real fixture", async t => {
    const {realStore, file, start} = await fixture(t);
    const events = [];
    const core = new LocalTicketCoordinatorM12m({
        store:realStore, policy, onStatus:s => events.push(s)
    });
    assert.equal(await core.attach(), true);
    const ticket = core.submit(add("First"));
    assert.match(ticket.ticketId, /^m12m-local-\d{6}$/);
    assert.equal(core.snapshot().confirmed.tasks.length, 0);
    const result = await ticket.completion;
    assert.equal(result.state, "CONFIRMED");
    assert.deepEqual(events.filter(e => e.ticketId === ticket.ticketId).map(e => e.state),
                     ["QUEUED", "PREPARING", "WRITING", "VERIFYING", "CONFIRMED"]);
    assert.equal(core.snapshot().phase, "READY");
    assert.equal(core.snapshot().confirmed.tasks[0].title, "First");
    assert.notEqual(await fs.readFile(file,"utf8"), start);
    assert.equal(policy.parse(await fs.readFile(file,"utf8")).ok, true);
});

test("FIFO tickets serialize mutations against last confirmed document", async t => {
    const {realStore} = await fixture(t);
    const core = new LocalTicketCoordinatorM12m({store:realStore, policy});
    await core.attach();
    const first = core.submit(add("First",1000));
    const second = core.submit(add("Second",1001));
    assert.equal((await first.completion).state, "CONFIRMED");
    assert.equal((await second.completion).state, "CONFIRMED");
    assert.deepEqual(core.snapshot().confirmed.tasks.map(x=>x.title),
                     ["First","Second"]);
    assert.notEqual(first.ticketId, second.ticketId);
});

test("ticket submitted during an in-flight write is queued, not concurrent", async t => {
    const {realStore} = await fixture(t);
    let release;
    const gate = new Promise(resolve => release=resolve);
    let active=0,maxActive=0;
    const store = {
        readExact: () => realStore.readExact(),
        replaceAtomic: async (next, previous) => {
            active++;
            maxActive = Math.max(maxActive,active);
            await gate;
            try { await realStore.replaceAtomic(next, previous); }
            finally {active--;}
        }
    };
    const core = new LocalTicketCoordinatorM12m({store, policy});
    await core.attach();
    const a=core.submit(add("One",1000));
    // Yield into the asynchronous write, while the gate holds it open.
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(core.snapshot().phase, "WRITING");
    const b=core.submit(add("Two",1001));
    assert.equal(core.snapshot().tickets[1].state, "QUEUED");
    release();
    assert.equal((await a.completion).state, "CONFIRMED");
    assert.equal((await b.completion).state, "CONFIRMED");
    assert.equal(maxActive,1);
    assert.equal(core.snapshot().confirmed.tasks.length,2);
});

test("rejected policy mutation cannot overwrite and later valid work succeeds", async t => {
    const {realStore,start,file} = await fixture(t);
    const core=new LocalTicketCoordinatorM12m({store:realStore,policy});
    await core.attach();
    const invalid=core.submit(add("   ",1000));
    assert.equal((await invalid.completion).state, "REJECTED");
    assert.equal(await fs.readFile(file,"utf8"), start);
    const good=core.submit(add("Allowed",1001));
    assert.equal((await good.completion).state,"CONFIRMED");
});

test("external edit before the save blocks queued tickets and retains last confirmed", async t => {
    const {realStore,file,start} = await fixture(t);
    const core = new LocalTicketCoordinatorM12m({store:realStore,policy});
    await core.attach();
    const outsider=policy.create(policy.emptyDocument(),"Outside",900);
    await fs.writeFile(file, JSON.stringify(outsider.document,null,2)+"\n");
    const a=core.submit(add("Attempt",1000));
    const b=core.submit(add("Followup",1001));
    assert.deepEqual([ (await a.completion).state, (await b.completion).state],
                     ["REVIEW_REQUIRED","BLOCKED"]);
    assert.equal(core.snapshot().error,"EXTERNAL_SOURCE_CHANGED");
    assert.equal(core.snapshot().confirmed.tasks.length,0);
    assert.equal(core.snapshot().lastDraft.tasks[0].title,"Attempt");
    assert.notEqual(await fs.readFile(file,"utf8"),start);
    assert.equal((await core.submit(add("Third")).completion).state,"BLOCKED");
});

test("uncertain error after actual rename never reports confirmation or auto-retries", async t => {
    const {realStore} = await fixture(t);
    const store={
        readExact:()=>realStore.readExact(),
        replaceAtomic:async (next,previous)=>{
            await realStore.replaceAtomic(next,previous);
            throw new Error("SIMULATED_PROCESS_EXIT_AFTER_RENAME");
        }
    };
    const core = new LocalTicketCoordinatorM12m({store,policy});
    await core.attach();
    const ticket=core.submit(add("Possibly written"));
    assert.equal((await ticket.completion).state,"REVIEW_REQUIRED");
    assert.equal(core.snapshot().confirmed.tasks.length,0);
    assert.equal(core.snapshot().lastDraft.tasks[0].title,"Possibly written");
    assert.equal(core.snapshot().phase,"RECOVERY_REVIEW");
    // A new process can inspect on-disk state, but cannot invent a durable
    // completion receipt for the previous in-memory ticket.
    const fresh=new LocalTicketCoordinatorM12m({store:realStore,policy});
    assert.equal(await fresh.attach(),true);
    assert.equal(fresh.snapshot().confirmed.tasks[0].title,"Possibly written");
    assert.equal(fresh.snapshot().tickets.length,0);
});

test("readback mismatch enters review and preserves pending draft", async t => {
    const {realStore,file} = await fixture(t);
    const store={
        readExact:()=>realStore.readExact(),
        replaceAtomic:async (next,old)=>{
            await realStore.replaceAtomic(next,old);
            const external=policy.create(policy.emptyDocument(),"Other bytes",1000);
            await fs.writeFile(file,JSON.stringify(external.document,null,2)+"\n");
        }
    };
    const core=new LocalTicketCoordinatorM12m({store,policy});
    await core.attach();
    const ticket=core.submit(add("Expected"));
    assert.equal((await ticket.completion).state,"REVIEW_REQUIRED");
    assert.equal(core.snapshot().error,"READBACK_MISMATCH");
    assert.equal(core.snapshot().confirmed.tasks.length,0);
    assert.equal(core.snapshot().lastDraft.tasks[0].title,"Expected");
});

test("snapshot mutation and UI observer throwing cannot rewrite persistence state", async t => {
    const {realStore} = await fixture(t);
    const core=new LocalTicketCoordinatorM12m({
        store:realStore,policy,onStatus:()=>{throw Error("observer crash");}
    });
    await core.attach();
    const ticket=core.submit(add("Immutable"));
    assert.equal((await ticket.completion).state,"CONFIRMED");
    const exported=core.snapshot();
    exported.confirmed.tasks[0].title="Modified outside";
    assert.equal(core.snapshot().confirmed.tasks[0].title,"Immutable");
});

test("source code remains isolated from one live QML FileView", () => {
    const prod=fsSync.readFileSync(
        path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fsSync.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.match(prod,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.equal((prod.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((prod.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.doesNotMatch(prod + shell,/TaskLocalTicketCoordinatorM12m/);
    assert.doesNotMatch(prod + shell,/TaskPrivateFixtureAdapterM12m/);
    assert.match(prod,/Quickshell\.dataDir \+ "\/apollo-hub-todo-v1\.json"/);
});
