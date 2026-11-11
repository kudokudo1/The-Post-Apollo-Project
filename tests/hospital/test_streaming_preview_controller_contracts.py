#!/usr/bin/env python3
"""Pure streaming preview controller + Surgery integration contracts.

Uses Node's built-in JS runtime only; no Vosk, PipeWire, model or host writes.
The main Hospital Acceptance workflow discovers this *contracts.py test.
"""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/hospital/HospitalStreamingPreviewPolicy.js"
INSERTION = ROOT / "services/hospital/HospitalDictationTextPolicy.js"
MANAGER = ROOT / "widgets/HospitalWorkforceManagerView.qml"
HOST = ROOT / "widgets/HospitalW.qml"
WHISPER = ROOT / "services/hospital/HospitalLiveDictationService.qml"
PROBE = ROOT / "scripts/hospital_streaming_vosk_probe.py"

NODE_CHECKS = r"""
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const p = vm.runInNewContext(
    fs.readFileSync(process.argv[1], "utf8") +
    "\n({ begin, receive, finish, cancel })");
const insert = vm.runInNewContext(
    fs.readFileSync(process.argv[2], "utf8") + "\nappendTranscription");
const emit = (kind, text, revision) =>
    ({kind, text, revision, clear_provisional: kind === "commit"});
let s = p.begin("goal", "JOB", "Existing", 4000, "run_one123");
assert(s && s.active && s.draft === "Existing");
assert.strictEqual(p.begin("goal", "SETUP", "", 4000, "run_bad123"), null);
assert.strictEqual(p.begin("unknown", "JOB", "", 4000, "run_bad123"), null);
assert.strictEqual(p.begin("goal", "JOB", "", 4000, "short"), null);
assert.strictEqual(p.begin("intake", "SETUP", "already too long", 3, "run_bad123"), null);
function take(token, packet) {
    let outcome = p.receive(s, token, packet, insert);
    if (outcome.accepted) s = outcome.state;
    return outcome;
}
let r = take("run_one123", emit("hypothesis", "why do", 1));
assert(r.accepted && !r.changedDraft);
assert.strictEqual(s.provisional, "why do");
assert.strictEqual(s.draft, "Existing");
assert.strictEqual(s.revision, 1);
r = take("run_one123", emit("hypothesis", "why did", 2));
assert(r.accepted && s.provisional === "why did");
assert.strictEqual(s.draft, "Existing");
assert.strictEqual(take("stale_run999", emit("commit", "wrong room", 3)).accepted, false);
assert.strictEqual(s.draft, "Existing");
assert.strictEqual(take("run_one123", emit("commit", "gap", 4)).accepted, false);
assert.strictEqual(s.revision, 2);
assert.strictEqual(take("run_one123", emit("commit", "bad\u0000word", 3)).accepted, false);
assert.strictEqual(take("run_one123", emit("commit", "another", 3)).accepted, true);
assert.strictEqual(s.draft, "Existing another");
assert.strictEqual(s.provisional, "");
assert.strictEqual(s.revision, 3);
assert.strictEqual(take("run_one123", emit("commit", "another", 3)).accepted, false);
r = take("run_one123", emit("hypothesis", "wait I", 4));
assert(r.accepted && s.draft === "Existing another");
const cancellation = p.cancel(s);
assert.strictEqual(cancellation.original, "Existing");
assert.strictEqual(cancellation.draft, "Existing another");
assert.strictEqual(p.finish(s, "stale_run999"), null);
const done = p.finish(s, "run_one123");
assert(!done.active && done.provisional === "");
assert.strictEqual(done.draft, "Existing another");
assert.strictEqual(p.receive(done, "run_one123",
    emit("commit", "late", 5), insert).accepted, false);
let empty = p.begin("intake", "SETUP", "", 4000, "run_empty123");
r = p.receive(empty, "run_empty123",
    emit("hypothesis", "before final", 1), insert);
empty = r.state;
r = p.receive(empty, "run_empty123", emit("commit", "", 2), insert);
assert(r.accepted && !r.changedDraft);
assert.strictEqual(r.state.provisional, "");
assert.strictEqual(r.state.draft, "");
let bounded = p.begin("done", "JOB", "AB", 5, "run_bound123");
assert.strictEqual(p.receive(bounded, "run_bound123",
    emit("hypothesis", "LONG", 1), insert).accepted, false);
assert.strictEqual(p.receive(bounded, "run_bound123",
    emit("commit", "LONG", 1), insert).accepted, false);
assert.strictEqual(p.receive(bounded, "run_bound123",
    {kind:"commit", text:"ok", revision:1, clear_provisional:false},
    insert).accepted, false);
assert.strictEqual(p.receive(bounded, "run_bound123",
    {kind:"commit", text:"ok", revision:1, clear_provisional:true, save:true},
    insert).accepted, false);
assert.strictEqual(p.receive(bounded, "run_bound123",
    emit("hypothesis", "[SILENCE]", 1), insert).accepted, false);
const good = p.receive(bounded, "run_bound123",
    emit("commit", "ok", 1), insert);
assert(good.accepted && good.changedDraft);
assert.strictEqual(good.state.draft, "AB ok");
assert.strictEqual(good.state.provisional, "");
for (const field of ["intake", "goal", "constraints", "done", "checklist"]) {
    const mode = field === "intake" ? "SETUP" : "JOB";
    assert(p.begin(field, mode, "", 4000, "run_each123").active);
    assert.strictEqual(p.begin(field, mode === "SETUP" ? "JOB" : "SETUP",
       "", 4000, "run_each123"), null);
}
console.log("STREAMING PREVIEW JS // PASS // stale owner, revisions, cancel, limits");
"""


class PreviewContracts(unittest.TestCase):
    def test_node_state_transitions_and_editor_insertion(self):
        runner = subprocess.run(
            ["node", "-e", NODE_CHECKS, str(POLICY), str(INSERTION)],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
            check=False)
        self.assertEqual(runner.returncode, 0,
                         runner.stderr or runner.stdout)
        self.assertIn("STREAMING PREVIEW JS // PASS", runner.stdout)

    def test_current_surgery_wires_only_dormant_preview_state(self):
        manager = MANAGER.read_text()
        policy = POLICY.read_text()
        host = HOST.read_text()
        whisper = WHISPER.read_text()
        self.assertIn(
            'import "../services/hospital/HospitalStreamingPreviewPolicy.js"'
            ' as StreamingPreviewPolicy', manager)
        for name in ("beginStreamingPreview", "acceptStreamingPreview",
                     "finishStreamingPreview", "cancelStreamingPreview"):
            self.assertIn("function " + name + "(", manager)
        self.assertIn("StreamingPreviewPolicy.receive(activePreview, token,",
                      manager)
        self.assertIn("packet, DictationTextPolicy.appendTranscription)", manager)
        self.assertIn("if (outcome.changedDraft)", manager)
        self.assertIn("field.value = outcome.state.draft;", manager)
        self.assertIn("managerArea.streamingPreviewActive", manager)
        self.assertIn("if (!root.active || !svc || svc.busy || root.otherVoiceBusy", manager)
        self.assertIn("|| root.streamingPreviewState.active", manager)
        self.assertIn("&& !root.streamingPreviewState.active", manager)
        self.assertIn('text: "HEARING // " +', manager)
        self.assertIn("root.streamingPreviewState.provisional", manager)
        self.assertIn("readOnly: managerArea.voiceActive", manager)
        self.assertIn("|| managerArea.streamingPreviewActive", manager)
        self.assertIn("field.value = oldState.original;", manager)
        self.assertIn("if (field && field.value === oldState.draft)", manager)
        self.assertIn("field.value !== activePreview.draft", manager)
        self.assertIn("root.cancelStreamingPreview();", manager)
        self.assertIn("if (managerArea.streamingPreviewActive)", manager)
        self.assertIn("root.cancelDictation();", manager)
        self.assertIn("root.dictationField = key;", manager)
        self.assertIn("root.speechInputService.stopRecording(false)", manager)
        self.assertIn("label: \"CANCEL\"", manager)
        self.assertIn('managerArea.stopInProgress ? Colors.red', manager)
        self.assertIn("property var streamingPreviewState: ({active: false})",
                      manager)
        self.assertNotIn("HospitalStreamingPreviewPolicy", host)
        self.assertNotIn("streamingPreviewState", whisper)
        self.assertNotIn("hospital_streaming_vosk_probe", manager)
        self.assertNotIn("hospital_streaming_vosk_probe", whisper)
        self.assertNotIn("pw-record", policy)
        for forbidden in ("submit(", "startRecording(", "Process {",
                          "session-attach", "openUrl(", "fetch(",
                          "OPENAI_API_KEY", "saveRoom(", "activateAssignment("):
            self.assertNotIn(forbidden, policy)
        self.assertIn("MAX_REVISIONS = 300", policy)
        self.assertIn("MAX_TEXT = 4000", policy)
        self.assertIn("MAX_WALL_SECONDS = 45", PROBE.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
