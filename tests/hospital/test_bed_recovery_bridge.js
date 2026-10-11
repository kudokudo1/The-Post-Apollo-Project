/* Source bridge regression: validates cross-file safety wiring only.
 * This does NOT claim QML runtime interaction coverage.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const load = file => fs.readFileSync(path.join(root,file),"utf8");
const source = load("services/hospital/HospitalBedRecoveryPolicy.js");
const context = vm.createContext({});
vm.runInContext(source,context);
let passed = 0;
function test(label, value) {assert.ok(value,label); ++passed;}
const refusals = [
  "RuntimeError: HOSPITAL TARGET REFUSED // TARGET_BED_MISMATCH",
  "HOSPITAL TARGET REFUSED // TARGET_BRANCH_MISMATCH",
  "Traceback\nRuntimeError: HOSPITAL TARGET REFUSED // PATIENT_REPOSITORY_MISMATCH"
];
test("bed mismatch recognized",context.targetRefusalCode(refusals[0])==="TARGET_BED_MISMATCH");
test("branch mismatch recognized",context.targetRefusalCode(refusals[1])==="TARGET_BRANCH_MISMATCH");
test("repository mismatch recognized",context.targetRefusalCode(refusals[2])==="PATIENT_REPOSITORY_MISMATCH");
test("ordinary PX failure ignored",context.targetRefusalCode("PX PROVIDER EXIT 1")==="");
test("unrelated error ignored",context.targetRefusalCode("HOSPITAL ASSIGNMENT REFUSED")==="");
test("empty input ignored",context.targetRefusalCode(null)==="");

const adapter=load("services/hospital/HospitalRoomConversationAdapter.qml");
const view=load("widgets/HospitalRoomChatView.qml");
const host=load("widgets/HospitalW.qml");
const modal=load("widgets/HospitalBedRecoveryDialog.qml");
const feed=load("components/ConversationFeed.qml");

test("adapter imports tested refusal parser",adapter.includes('import "HospitalBedRecoveryPolicy.js" as RecoveryPolicy'));
test("adapter calls refusal parser",adapter.includes("RecoveryPolicy.targetRefusalCode(detail)"));
test("adapter provides target failure signal",adapter.includes("signal targetMismatchDetected(string roomId, string code, string detail)"));
test("adapter sends refusal signal only when failed",adapter.includes("Number(code) !== 0 && adapter.targetRefusalCode"));
test("adapter preserves failed Room before failure cleanup",adapter.indexOf("adapter.targetMismatchDetected(",adapter.indexOf("id: turnProcess")) < adapter.indexOf('adapter.pendingTurnBody = "";',adapter.indexOf("adapter.targetMismatchDetected(",adapter.indexOf("id: turnProcess"))));
test("adapter never signals on provider success",adapter.indexOf("adapter.targetMismatchDetected(",adapter.indexOf("id: turnProcess")) > adapter.indexOf("adapter.sendSuccessSerial += 1;",adapter.indexOf("id: turnProcess")));
test("view exposes scoped refusal",view.includes("signal targetMismatchDetected(string roomId, string code, string detail, string draft)"));
test("view forwards unsent draft",view.includes('String(adapter.pendingTurnBody || "")'));
test("view exposes in-flight status",view.includes("readonly property bool doctorTurnActive: adapter.sending"));
test("host receives scope-safe signal",host.includes("onTargetMismatchDetected: function(roomId, code, detail, draft)"));
test("host refuses wrong-Room recovery",host.includes("roomId !== root.selectedRoomTeam"));
test("host checks candidate Floor",host.includes("current.floorId") && host.includes("floorService.floorId"));
test("host uses existing Bed selector",host.includes("floorService.selectBed(index)"));
test("host never auto-retries",!host.includes("roomChatView.sendMessage(") && !host.includes("adapter.sendMessage("));
test("host clears stale recovery on Room change",host.includes("onSelectedRoomTeamChanged:") && host.includes("recoveryRoomId !== selectedRoomTeam"));
test("host clears recovery when leaving chat",host.includes('operationsSurface !== "chat"'));
test("host clears recovery when menu closes",host.includes("if (!root.menuOpen) {\n            root.clearBedRecovery();"));
test("host requests explicit safe Bed creation",host.includes("bedOperationService.createNew("));
test("host cannot launch forced move",host.includes("moveWorkerClearance: false"));
test("modal enforces global worker clearance",modal.includes("operationActive || operationBusy || !moveWorkerClearance"));
test("composer clears only on success",feed.includes("if (pendingSendSerial >= 0 && sendSuccessSerial > pendingSendSerial)"));
test("candidate selection never grants authority",source.includes("verification: \"CANDIDATE_UNVERIFIED\""));
console.log("Hospital Bed Recovery chat bridge: PASS // "+passed+" checks");
