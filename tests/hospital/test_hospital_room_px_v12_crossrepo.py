#!/usr/bin/env python3
"""Cross-repo PX v12 ↔ Trash++ Room JSON contract, disposable DB only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PX = ROOT / "px-source" / "bin" / "px-hospital-store"
assert PX.is_file(), "PX PR #130 must be checked out separately"

with tempfile.TemporaryDirectory(prefix="hospital-trashpp-cross-") as tmp:
    env = dict(os.environ, PX_HOSPITAL_DATA_DIR=tmp)
    def run(*args):
        proc = subprocess.run(["python3",str(PX),*args,"--json"],
                              env=env,capture_output=True,text=True,timeout=20)
        assert proc.returncode==0,(args,proc.stdout,proc.stderr)
        return json.loads(proc.stdout)
    assert run("status")["schema_version"]==12
    run("patient-put","sample","example/sample")
    run("room-put","room-sample","--patient-id","sample")
    review=run("room-lifecycle-review","room-sample")
    assert review["roomId"]=="room-sample"
    assert review["state"]=="ACTIVE" and review["canTrash"] is True
    assert review["operatorAuthenticated"] is False
    assert review["requiresOwnerReview"] is True
    assert len(review["digest"])==64 and review["revision"]==0
    result=run("room-lifecycle-trash","room-sample",
               "--expected-revision","0",
               "--expected-digest",review["digest"],
               "--confirm-room-id","room-sample")
    assert result["originalPreserved"] is True
    assert result["burnAllowed"] is False
    assert result["operatorAuthenticated"] is False
    assert result["state"]=="TRASHED" and result["revision"]==1
    names=[x["id"] for x in run("rooms")]
    assert "room-sample" not in names
    rows=run("room-lifecycle-bin")
    assert len(rows)==1 and rows[0]["roomId"]=="room-sample"
    assert rows[0]["kind"]=="HOSPITAL ROOM" and rows[0]["burnAllowed"] is False
    assert rows[0]["revision"]==1
    witness=run("room-lifecycle-review","room-sample")
    assert witness["canRestore"] is True
    restored=run("room-lifecycle-restore","room-sample",
                 "--expected-revision",str(witness["revision"]),
                 "--expected-digest",witness["digest"],
                 "--confirm-room-id","room-sample")
    assert restored["state"]=="ACTIVE" and restored["originalPreserved"] is True
    assert run("room-lifecycle-bin")==[]
    assert "room-sample" in [x["id"] for x in run("rooms")]
print("HOSPITAL PX V12 ↔ TRASH++ CONTRACT // PASS // exact JSON, state, bin, restore, production authorization HOLD")
