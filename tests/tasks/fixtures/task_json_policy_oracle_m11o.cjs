#!/usr/bin/env node
"use strict";
// Execute the real ApolloHubTodoPolicy.js in a Node VM to serve as the
// read-only authority for M11o's Python test-copy admission comparisons.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const file = path.join(__dirname, "../../../services/hub/ApolloHubTodoPolicy.js");
const source = fs.readFileSync(file, "utf8").replace(/^\.pragma library\s*/m, "");
const ctx = vm.createContext({});
vm.runInContext(source, ctx, {filename:"ApolloHubTodoPolicy.js"});
const rawItems = JSON.parse(fs.readFileSync(0, "utf8"));
if (!Array.isArray(rawItems) || rawItems.length > 120 ||
    rawItems.some(raw => typeof raw !== "string"))
    throw new Error("INVALID_TEST_BATCH");
const out = rawItems.map(raw => {
    const result = ctx.parse(raw);
    return {ok:result.ok === true, reason:result.reason || ""};
});
process.stdout.write(JSON.stringify(out) + "\n");
