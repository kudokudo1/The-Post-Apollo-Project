#!/usr/bin/env python3
"""Cross-repo PX signed Room lifecycle ↔ Trash++ JSON, disposable DB only.

Unsigned CLI mutations must fail. A generated signer is injected ONLY into
the verifier's in-process fixture to exercise atomic PX state and bin JSON.
"""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
PXROOT = ROOT / "px-source"
PX = PXROOT / "bin" / "px-hospital-store"
assert PX.is_file(), "Exact PX PR #130 checkout required"
sys.path.insert(0,str(PXROOT / "bin"))
import px_hospital_room_lifecycle as life
import px_hospital_room_authority as auth

with tempfile.TemporaryDirectory(prefix="hospital-trashpp-cross-") as tmp:
    env = dict(os.environ, PX_HOSPITAL_DATA_DIR=tmp)
    db_path = Path(tmp) / "hospital.db"
    def run(*args,good=True):
        p = subprocess.run(["python3",str(PX),*args,"--json"],
                           env=env,capture_output=True,text=True,timeout=20)
        if good:
            assert p.returncode==0,(args,p.stdout,p.stderr)
            return json.loads(p.stdout)
        assert p.returncode!=0,(args,p.stdout,p.stderr)
        return p.stderr
    def db():
        c=sqlite3.connect(db_path,isolation_level=None,timeout=5)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c
    assert run("status")["schema_version"]==12
    run("patient-put","sample","example/sample")
    run("room-put","room-sample","--patient-id","sample")
    review=run("room-lifecycle-review","room-sample")
    assert review["roomId"]=="room-sample"
    assert review["state"]=="ACTIVE" and review["canTrash"] is True
    assert review["operatorAuthenticated"] is False
    assert review["requiresOwnerReview"] is True
    assert len(review["digest"])==64 and review["revision"]==0

    # No QML confirmation or direct CLI argument can authorize a deletion.
    refused=run("room-lifecycle-trash","room-sample",
        "--expected-revision","0","--expected-digest",review["digest"],
        "--confirm-room-id","room-sample",good=False)
    assert "signed-authorization-file" in refused
    assert run("room-lifecycle-bin")==[]

    fixture_signer=Ed25519PrivateKey.generate()
    def authorized(action):
        with db() as con:
            snapshot=life.review(con,"room-sample")
            now=int(time.time())
            body={
                "schema":auth.SCHEMA,"audience":auth.AUDIENCE,"action":action,
                "roomId":"room-sample","patientId":"sample",
                "repository":"example/sample",
                "expectedRevision":snapshot["revision"],
                "expectedDigest":snapshot["digest"],
                "operatorId":"operator-fixture", "approvalId":"grant-"+secrets.token_hex(12),
                "seatId":"native-seat-fixture", "hostId":"native-host-fixture",
                "retentionApproved":True,
                "nonce":auth._b64(os.urandom(32)),
                "issuedAt":now, "expiresAt":now+40,
            }
            signed=auth.DOMAIN+auth.canonical(body)
            frame=auth.canonical({"body":body,
                "signature":auth._b64(fixture_signer.sign(signed))})
            grant=auth._verify_bytes(frame,fixture_signer.public_key())
            return life.transition(con,"room-sample",action,snapshot["revision"],
                                   snapshot["digest"],"room-sample",
                                   authorization=grant)
    result=authorized("TRASH")
    assert result["originalPreserved"] is True
    assert result["burnAllowed"] is False
    assert result["grantSignatureVerified"] is True
    assert result["operatorAuthenticated"] is False
    assert result["state"]=="TRASHED" and result["revision"]==1
    assert "room-sample" not in [x["id"] for x in run("rooms")]
    rows=run("room-lifecycle-bin")
    assert len(rows)==1 and rows[0]["roomId"]=="room-sample"
    assert rows[0]["kind"]=="HOSPITAL ROOM" and rows[0]["burnAllowed"] is False
    assert rows[0]["revision"]==1
    witness=run("room-lifecycle-review","room-sample")
    assert witness["canRestore"] is True
    assert witness["operatorAuthenticated"] is False
    restored=authorized("RESTORE")
    assert restored["state"]=="ACTIVE" and restored["originalPreserved"] is True
    assert run("room-lifecycle-bin")==[]
    assert "room-sample" in [x["id"] for x in run("rooms")]
    with db() as con:
        assert con.execute("SELECT count(*) FROM room_lifecycle_authorizations").fetchone()[0]==2
        assert con.execute("SELECT count(*) FROM room_lifecycle_receipts").fetchone()[0]==2

print("HOSPITAL ↔ PX SIGNED ROOM CONTRACT // PASS // unsigned CLI refuses, trusted fixture grant, atomic Trash → Restore, production hold")
