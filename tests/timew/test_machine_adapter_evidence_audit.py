#!/usr/bin/env python3
"""M2c2 audited vendor/repository evidence is documentation, not live support."""
import copy
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"services"/"time"))
from MachineAdapterEvidencePolicy import AuditError, validate_audit, summarize_audit

audit=json.loads((root/"docs"/"timew-machine-m2c2-app-capability-evidence.json").read_text())
before=copy.deepcopy(audit)
clean=validate_audit(audit)
assert clean==audit and before==audit
summary=summarize_audit(audit)
assert summary["entry_count"]>=8
assert summary["family_counts"]["browser"]>=2
assert summary["family_counts"]["terminal"]>=3
assert summary["family_counts"]["editor"]>=1
assert summary["evidence_counts"]["documented_interface"]>=5
assert summary["read_only"] and not summary["executable"]
assert not summary["privacy_consent_granted"]
assert summary["live_implementations_verified"]==0
assert summary["recovery_actions_available"]==[]
assert "Post-Apollo Proton browser companion" in [x["subject"] for x in audit["entries"]]
assert "Ghostty Linux" in [x["subject"] for x in audit["entries"]]
assert "VS Code UI and extension APIs" in [x["subject"] for x in audit["entries"]]
assert "Kitty sessions" in [x["subject"] for x in audit["entries"]]
assert "WezTerm CLI" in [x["subject"] for x in audit["entries"]]
for row in clean["entries"]:
    assert row["live_enabled"] is False
    assert row["runtime_verified"] is False
    assert row["arbitrary_checkpoint_reconstruction_verified"] is False
    assert not any(x in row for x in ("password","cookie","url","title","pid","command"))
    for src in (row["official_source"],row["secondary_source"]):
        if src is not None and not src.startswith("https://"):
            assert (root/src).is_file(), src

def refuse(change):
    obj=copy.deepcopy(audit)
    change(obj)
    try:
        validate_audit(obj)
    except AuditError:
        return
    raise AssertionError("unsafe evidence claim accepted")
refuse(lambda x:x.update(status="runtime_verified"))
refuse(lambda x:x.update(runtime_implementation_count=1))
refuse(lambda x:x.update(schema_version=True))
refuse(lambda x:x.update(private_browser_history="SECRET"))
refuse(lambda x:x["entries"][0].update(live_enabled=True))
refuse(lambda x:x["entries"][0].update(runtime_verified=True))
refuse(lambda x:x["entries"][0].update(arbitrary_checkpoint_reconstruction_verified=True))
refuse(lambda x:x["entries"][0].update(permissions=["tabs"]))
refuse(lambda x:x["entries"][0].update(account_token="PRIVATE"))
refuse(lambda x:x["entries"][0].update(official_source="file:///tmp/private"))
refuse(lambda x:x["entries"][0].update(evidence="installed"))
refuse(lambda x:x["entries"][0].update(capability="\nINVALID"))
refuse(lambda x:x["entries"][0].update(constraints=["same","same"]))
refuse(lambda x:x["entries"].append(copy.deepcopy(x["entries"][0])))
refuse(lambda x:x.update(entries=x["entries"]*9))
refuse(lambda x:x.update(entries="not a list"))
refuse(lambda x:x["entries"][0].update(family="unknown"))
assert audit==before
print("MACHINE M2C2: SOURCE-BACKED DOCUMENTATION GATE PASS / NO LIVE SUPPORT CLAIMS")
