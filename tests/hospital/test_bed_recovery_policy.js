/* Node contract tests for the QML-importable pure JS policy.
 * No live Quickshell, Git worktrees, Rooms, providers, or PX DB.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "services/hospital/HospitalBedRecoveryPolicy.js"), "utf8"
);
const ctx = vm.createContext({});
vm.runInContext(source, ctx, {filename:"HospitalBedRecoveryPolicy.js"});
let assertions = 0;
function check(name, condition) {
    assert.ok(condition, name);
    assertions += 1;
}

const origin = "kudokudo1/taskbars-post-apollo";
const branch = "feature/cpu-plus-plus";
const mk = (path, properties = {}) => Object.assign({
    path: path,
    label: "BED",
    origin: "git@github.com:kudokudo1/taskbars-post-apollo.git",
    branch: branch,
    head: "abc123",
    worktree: "CLEAN",
    isLive: false
}, properties);

check("ssh github slug", ctx.githubRepository(mk("/one").origin) === origin);
check("https github slug", ctx.githubRepository("https://github.com/KUDOKUDO1/TASKBARS-POST-APOLLO.git") === origin);
check("ssh scheme slug", ctx.githubRepository("ssh://git@github.com/kudokudo1/taskbars-post-apollo.git") === origin);
check("reject other host", ctx.githubRepository("https://evil.tld/kudokudo1/taskbars-post-apollo") === "");
check("reject malicious extra path", ctx.githubRepository("https://github.com/kudokudo1/taskbars-post-apollo/other") === "");
check("reject empty origin", ctx.githubRepository("NO ORIGIN") === "");
check("reject malformed expected repository", ctx.scanCandidates([mk("/one")], "", branch).length === 0);
check("reject unknown branch", ctx.scanCandidates([mk("/one")], origin, "").length === 0);
check("reject DETACHED expected branch", ctx.scanCandidates([mk("/one")], origin, "DETACHED").length === 0);
check("match valid Bed", ctx.scanCandidates([mk("/one")], origin, branch).length === 1);
check("reject different branch", ctx.scanCandidates([mk("/one",{branch:"main"})], origin, branch).length === 0);
check("reject foreign repo", ctx.scanCandidates([mk("/one",{origin:"git@github.com:other/other.git"})], origin, branch).length === 0);
check("reject remote-less repo", ctx.scanCandidates([mk("/one",{origin:"NO ORIGIN"})], origin, branch).length === 0);
check("reject missing Bed path", ctx.scanCandidates([mk("")], origin, branch).length === 0);
check("dedupe same path", ctx.scanCandidates([mk("/one"), mk("/one")], origin, branch).length === 1);
const dirty = ctx.scanCandidates([mk("/dirty",{worktree:"DIRTY • 3 CHANGES"})], origin, branch);
check("matching dirty Bed is candidate", dirty.length === 1 && dirty[0].dirty);
check("candidate never claims verification", dirty[0].verification === "CANDIDATE_UNVERIFIED");
const choices = ctx.scanCandidates([
    mk("/live",{isLive:true}),
    mk("/dirty",{worktree:"DIRTY • 3 CHANGES"}),
    mk("/clean")
], origin, branch);
check("prefer clean nonlive", choices.map(b=>b.path).join("|") === "/clean|/dirty|/live");
check("no automatic selection", !choices.some(c=>c.selected || c.allowed || c.verified));
check("clean Bed movement eligible", ctx.moveEligibility(mk("/one",{branch:"main"}),origin,branch,false).eligible);
check("no force on dirty Bed", ctx.moveEligibility(mk("/one",{branch:"main",worktree:"DIRTY • 2 CHANGES"}),origin,branch,false).reason === "BED_DIRTY");
check("no move while operation active", ctx.moveEligibility(mk("/one",{branch:"main"}),origin,branch,true).reason === "HOSPITAL_OPERATION_ACTIVE");
check("no move for foreign repo", ctx.moveEligibility(mk("/one",{branch:"main",origin:"https://github.com/other/other"}),origin,branch,false).reason === "PATIENT_REPOSITORY_UNVERIFIED");
check("no redundant move", ctx.moveEligibility(mk("/one"),origin,branch,false).reason === "BED_ALREADY_ON_BRANCH");
check("live Bed retains extra confirmation", ctx.moveEligibility(mk("/one",{branch:"main",isLive:true}),origin,branch,false).reason === "LIVE_BED_REQUIRES_SECOND_CONFIRMATION");

const qml = fs.readFileSync(path.join(root,"widgets/HospitalBedRecoveryDialog.qml"),"utf8");
for (const signal of [
    "signal selectBedRequested", "signal createBedRequested",
    "signal moveBedRequested", "signal registerBedRequested",
    "signal inspectOnlyRequested", "signal cancelled"
]) check("dialog exposes "+signal, qml.includes(signal));
check("dialog imports policy", qml.includes('HospitalBedRecoveryPolicy.js" as RecoveryPolicy'));
check("dialog labels candidates unverified", qml.includes("CANDIDATES, not execution clearance"));
check("dialog preserves draft on cancel", qml.includes("Parent retains pendingDraft"));
check("dialog requires arm for move", qml.includes("if (!root.moveArmed)"));
check("dialog does not write Git via subprocess", !/Process\s*\{|git\s+-C|exec\s*\(/.test(qml));
check("dialog does not issue Doctor turn", !qml.includes("agent turn") && !qml.includes("turnProcess"));
console.log("Hospital Bed Recovery policy + UI contract: PASS // "+assertions+" checks");
