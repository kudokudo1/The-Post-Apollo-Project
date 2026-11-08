#!/usr/bin/env python3
"""Hospital atomic attach PX capability gate source contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
view = (root / "widgets/HospitalRegisteredWorkerView.qml").read_text()
actor = (root / "services/hospital/HospitalWorkerAttachmentActionService.qml").read_text()
policy = (root / "services/hospital/HospitalWorkerAttachmentCapabilityPolicy.js").read_text()
issues = []

def require(ok, issue):
    if not ok:
        issues.append(issue)

require('function probeCapability()' in actor and '"agent", "session-attach", "--help"' in actor,
        "Read-only probe must target the matching installed PX command")
require('id: capabilityProcess' in actor
        and 'onExited: function(code, exitStatus)' in actor
        and 'CapabilityPolicy.evaluate(' in actor,
        "Capability must be set from the actual subprocess exit result")
require('capabilityChecked: false' in actor and 'capabilityAvailable: false' in actor
        and 'capabilityChecking: false' in actor,
        "Default to unsupported until an actual local check completes")
require('if (running || process.running || capabilityProcess.running)' in actor,
        "No probe is allowed during commit or another probe")
require('capabilityChecked = false;' in actor
        and 'capabilityAvailable = false;' in actor
        and 'capabilityChecking = true;' in actor,
        "Rechecking must immediately disarm stale capability")
require('|| !capabilityChecked || !capabilityAvailable' in actor,
        "An explicit direct attach call must refuse absent or old PX")
require('root.capabilityAvailable = probe.supported;' in actor
        and 'root.capabilityChecked = true;' in actor,
        "Ready is conditional on the parsed exact PX help contract")
require('typeof code === "number"' in policy and 'code === 0' in policy,
        "A missing/invalid exit code must not be treated as zero")
require('"--assignment-id"' in policy and '"--mode"' in policy
        and '"--confirm"' in policy and 'px agent session-attach' in policy,
        "Never confuse legacy session-create with atomic attach")
require('NOT PROVIDER REACHABILITY' in policy
        and 'NOT AUTHORIZED' in policy,
        "CLI existence cannot be labeled as worker authority or provider heartbeat")

require('attachmentAction.probeCapability();' in view,
        "Entering preview must probe the installed PX executable")
require('label: "RECHECK PX ATTACH SUPPORT"' in view,
        "An operator must be able to recheck after PX installation")
require('text: attachmentAction.capabilityReason' in view
        and 'attachmentAction.capabilityDetail' in view,
        "Unavailable installed PX must display an actionable reason")
require('onCapabilityCheckingChanged: root.attachmentArmKey = ""' in view
        and 'onCapabilityAvailableChanged: root.attachmentArmKey = ""' in view,
        "Reprobes and capability changes must disarm the queued Session request")
require('function armAttachment()' in view and 'function confirmAttachment()' in view,
        "Original two-click flow remains")
require(view.count('!attachmentAction.capabilityChecked') >= 2,
        "Both ARM and CONFIRM runtime paths must refuse unknown capability")
require(view.count('&& attachmentAction.capabilityChecked') >= 2
        and view.count('&& attachmentAction.capabilityAvailable') >= 2,
        "Both REVIEW and CONFIRM controls must be disabled without support")
require('attachmentAction.attach(candidate)' in view,
        "Existing exact-candidate CLI path remains the only mutation path")
require('label: "CONFIRM ATTACH // REGISTER IDLE SESSION"' in view,
        "Operator sees the exact registration action")
require('PROVIDER NOT LAUNCHED' in view and 'CHAT is read-only' in view,
        "Registration is not a provider launch or browser ChatGPT attachment")
require('mutationAuthorized: false' in (root / "services/hospital/HospitalWorkerAttachmentPreviewPolicy.js").read_text(),
        "Read-only preview cannot grant execution permission")
for unsafe in ('"session-put"', '"session-create"', '"room-bind"',
               '"orchestrate-ready"', '"quick"', '"turn"'):
    require(unsafe not in actor, "New gate must not use legacy or execution command " + unsafe)

if issues:
    print("HOSPITAL PX ATTACH CAPABILITY CONTRACT // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL PX ATTACH CAPABILITY CONTRACT // PASS // old/missing endpoint refused; operator can recheck")
