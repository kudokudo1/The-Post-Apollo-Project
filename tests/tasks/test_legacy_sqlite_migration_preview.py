#!/usr/bin/env python3
"""M10m legacy TASKS -> record-level SQLite dry-run and raw-backup proof.

All on-disk writes occur in disposable tempfile locations. Original source
and backup bytes must be identical, including unusual formatting and Unicode.
No user file, live Quickshell database, or GitHub account is touched.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "services/projects/LegacySqliteMigrationPreview.py"
RECORDS = ROOT / "services/projects/ExperimentalTaskSqliteRecordsV2.py"
def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

migration = module(PREVIEW, "m10m_migration_preview")
sqlite = module(RECORDS, "m10m_sqlite_record_store")
TIME = 1771521000000


def projects():
    return [
        {"id":"p2","name":"Dev 🏥", "createdAtMs":TIME+1,
         "updatedAtMs":TIME+7},
        {"id":"p19","name":"Personal","createdAtMs":TIME+2,
         "updatedAtMs":TIME+9},
    ]


def task(tid, project, title, done=False, due=None, priority="none"):
    return {"id":tid,"title":title,"done":done,
        "createdAtMs":TIME,"updatedAtMs":TIME+200,
        "priority":priority, "description":"First line\nSecond line ♥",
        "dueDate":due,"projectId":project}


def json_bytes(doc, *, indent=None):
    return (json.dumps(doc, ensure_ascii=False, indent=indent)+"\n").encode()


v3 = {"version":3,"nextId":100,"nextProjectId":29,
    "projects":projects(),
    "tasks":[
        task("t70","p2","Finish migration",due="2026-10-23",priority="urgent"),
        task("t3",None,"Unassigned",True,"2024-02-29","low"),
        task("t99","p19","Read SQLite notes",due=None,priority="medium")
    ]}
v2 = {"version":2,"nextId":12,
    "tasks":[{
        "id":"t11","title":"Old dated","done":True,
        "createdAtMs":TIME,"updatedAtMs":TIME+20,
        "priority":"high","description":"Archived","dueDate":"2024-02-29"
    }]}
v1 = {"version":1,"nextId":3,"tasks":[{
    "id":"t2","title":"Classic item","done":False,
    "createdAtMs":TIME,"updatedAtMs":TIME+40
}]}


def reject(raw, reason=None):
    try:
        migration.preview(raw)
    except migration.PreviewRejected as exc:
        if reason:
            assert reason in str(exc), (reason, str(exc))
        return
    raise AssertionError("migration accepted invalid source")


with tempfile.TemporaryDirectory(prefix="pa-m10m-migration-test-") as temp:
    root=Path(temp)
    for index, original in enumerate((v1,v2,v3),1):
        sample=root / str(index)
        sample.mkdir(mode=0o700)
        raw=json_bytes(original,indent=2) if index==3 else json_bytes(original)
        source_file=sample / "original-v3-or-legacy.json"
        source_file.write_bytes(raw)
        original_before=source_file.read_bytes()

        preview=migration.preview(raw)
        assert preview["ok"] and preview["sourceVersion"]==original["version"]
        assert preview["originalBytes"]==len(raw)
        assert preview["originalSha256"]==hashlib.sha256(raw).hexdigest()
        assert preview["writeReady"] is False
        assert preview["migrationPerformed"] is False
        assert preview["remoteWriteAuthorized"] is False
        assert preview["candidate"]["version"]==2
        assert preview["candidate"]["revision"]==0
        assert preview["candidate"]["operations"]==[]
        assert preview["candidate"]["nextId"]==original["nextId"]
        assert preview["candidate"]["nextProjectId"]==(
            original["nextProjectId"] if index==3 else 1)
        assert len(preview["candidate"]["tasks"])==len(original["tasks"])
        assert preview["compatibilityV3"]["version"]==3

        # Backup is a one-time copy of the ORIGINAL RAW SOURCE, not an
        # encoded/normalized derivative. Never overwrite an existing backup.
        backup=sample / "original.bytes"
        with backup.open("xb") as file:
            file.write(raw)
            file.flush()
            import os
            os.fsync(file.fileno())
        assert backup.read_bytes()==original_before
        assert hashlib.sha256(backup.read_bytes()).hexdigest()==preview["originalSha256"]
        try:
            with backup.open("xb"):
                pass
        except FileExistsError:
            pass
        else:
            raise AssertionError("Backup overwrite unexpectedly permitted")

        # An entirely DIFFERENT throwaway path contains the candidate SQLite
        # data. Actual legacy source is not opened by the adapter.
        dest=sample / "separate-target"
        dest.mkdir(mode=0o700)
        database=dest / "tasks.db"
        written=sqlite.initialize(database,preview["candidate"])
        assert written["localSaved"] is True
        loaded=sqlite.read(database)
        assert loaded["status"]=="READY"
        assert loaded["document"]==preview["candidate"]
        assert loaded["document"]["revision"]==0
        assert loaded["document"]["operations"]==[]
        assert loaded["document"]["nextId"]==original["nextId"]
        assert loaded["document"]["nextProjectId"]==(
            original["nextProjectId"] if index==3 else 1)
        # Strict logical equality of ORIGINAL's v3-compatible values.
        compatibility=preview["compatibilityV3"]
        assert [t["id"] for t in loaded["document"]["tasks"]]==[
            t["id"] for t in compatibility["tasks"]]
        assert [p["id"] for p in loaded["document"]["projects"]]==[
            p["id"] for p in compatibility["projects"]]
        for expected,actual in zip(compatibility["tasks"],
                                   loaded["document"]["tasks"]):
            for key in ("id","title","done","createdAtMs","updatedAtMs",
                        "priority","description","dueDate","projectId"):
                assert actual[key]==expected[key], (key,actual,expected)
            assert actual["remote"] is None
            assert actual["values"]=={}
        for expected,actual in zip(compatibility["projects"],
                                   loaded["document"]["projects"]):
            for key in ("id","name","createdAtMs","updatedAtMs"):
                assert actual[key]==expected[key]
            assert actual["family"]=="normal"
            assert actual["remote"] is None
        assert source_file.read_bytes()==original_before
        # Restore the backed-up bytes to a THIRD file. No mutation of source.
        recovered=sample / "restored-legacy.json"
        recovered.write_bytes(backup.read_bytes())
        assert recovered.read_bytes()==raw
        assert migration.preview(recovered.read_bytes())["originalSha256"]==(
            preview["originalSha256"])
        assert source_file.read_bytes()==original_before

    malformed=copy.deepcopy(v3)
    malformed["unrecognized"]="Never silently discard"
    reject(json_bytes(malformed),"UNRECOGNIZED_LEGACY_FIELDS")
    malformed=copy.deepcopy(v3)
    malformed["tasks"][0]["newColumn"]={"future":"unsupported"}
    reject(json_bytes(malformed),"UNRECOGNIZED_TASK_FIELDS")
    malformed=copy.deepcopy(v3)
    malformed["projects"][0]["family"]="git"
    reject(json_bytes(malformed),"UNRECOGNIZED_PROJECT_FIELDS")
    malformed=copy.deepcopy(v3)
    malformed["tasks"][0]["dueDate"]="2026-02-29"
    reject(json_bytes(malformed))
    malformed=copy.deepcopy(v3)
    malformed["tasks"][0]["projectId"]="p999"
    reject(json_bytes(malformed))
    malformed=copy.deepcopy(v3)
    malformed["nextId"]=70
    reject(json_bytes(malformed))
    malformed=copy.deepcopy(v3)
    malformed["version"]=4
    reject(json_bytes(malformed))
    reject(b'{"version":3,"version":3}',"DUPLICATE_LEGACY_JSON_KEY")
    reject(b'{"version":3,"\\u0076ersion":3}',"DUPLICATE_LEGACY_JSON_KEY")
    reject(b'{"tasks":[{"id":"t1","id":"t2"}]}',"DUPLICATE_LEGACY_JSON_KEY")
    reject(b"\xff\xfe","INVALID_SOURCE_UTF8")
    reject(b"{broken","INVALID_SOURCE_JSON")
    reject(b"","INVALID_SOURCE_BYTES")
    reject(b" "*1048577,"INVALID_SOURCE_BYTES")

    # Neither temporary database nor backup helper may have a default path
    # to the user's TASKS file or automatically install a desktop migration.
    source_text=PREVIEW.read_text()
    for forbidden in ("Quickshell.dataDir","ApolloHubTodoStore.qml",
                      "os.environ.get('HOME'","/var/home/mapple/",
                      "GitHubProjectsService"):
        assert forbidden not in source_text
    assert not hasattr(migration,"migrate_live_data")
    assert not hasattr(migration,"activate_store")
    assert not hasattr(migration,"save_to_disk")

print("TASKS M10m raw-byte backup, legacy->SQLite v2 dry-run and v3 parity: PASS")
