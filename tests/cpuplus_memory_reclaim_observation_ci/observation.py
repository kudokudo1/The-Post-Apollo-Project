"""Pure inspection contract for the exact #2798 archive and PREPARED schema.

Inputs are observations, not authority. No filesystem access, no lock bypass,
no protected caller, mutation, replay, deletion, or clearance.
"""
import hashlib
import json
import re

PIN = "9dfd8331445ecf60d3a37ea630d08b1f3f6789a2"
ARCHIVE_KEYS = {"version","state","candidate_blob","boot_id","identity","subvolume_id",
                "records_hex","withdrawal_witness","swap","can_execute","can_clear"}
NAMES = {"swapfile","withdrawal.json","withdrawal-result.json"}
LIMIT = 131072

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,
                      allow_nan=False).encode("ascii")+b"\n"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def decode(raw,limit):
    if type(raw) is not bytes or not 0<len(raw)<=limit:
        raise ValueError("invalid record length")
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:
                raise ValueError("duplicate key")
            result[k]=v
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError("invalid object")
    return value

def result(code,archive_digest=None):
    return {"version":1,"state":"RECOVERY_REVIEW_REQUIRED","code":code,
            "archive_sha256":archive_digest,"can_execute":False,"can_clear":False,
            "storage_release_verified":False}

def classify(helper, *, archive_presence, archive_raw, fence_presence, fence_names,
             prepared_raw, boot_id, extension_presence, identity=None,
             subvolume_id=None, directory_names=None, records_raw=None, snapshot=None):
    """Strictly classify supplied observation; does not establish protected provenance.

    Presence must be separately measured by a future trusted reader, never inferred
    from a failed read. No positive classification authorizes another operation.
    """
    if any(v not in ("ABSENT","PRESENT","UNKNOWN") for v in
           (archive_presence,fence_presence,extension_presence)):
        return result("INVALID_PRESENCE_OBSERVATION")
    if "UNKNOWN" in (archive_presence,fence_presence,extension_presence):
        return result("OBSERVATION_UNVERIFIED")
    if archive_presence=="ABSENT":
        if archive_raw is not None:
            return result("INCONSISTENT_ARCHIVE_OBSERVATION")
        if fence_presence=="PRESENT":
            return result("FENCE_WITHOUT_ARCHIVE")
        if prepared_raw is not None or fence_names is not None:
            return result("INCONSISTENT_FENCE_OBSERVATION")
        return result("NO_CUSTODY_OBSERVED")
    try:
        archive=decode(archive_raw,LIMIT)
        if canonical(archive)!=archive_raw or set(archive)!=ARCHIVE_KEYS:
            return result("ARCHIVE_SCHEMA_INVALID")
        if (type(archive["version"]) is not int or archive["version"]!=1
                or archive["state"]!="ARCHIVE_CUSTODY" or archive["candidate_blob"]!=PIN
                or archive["can_execute"] is not False or archive["can_clear"] is not False
                or not helper.canonical_boot_id(archive["boot_id"])
                or type(archive["subvolume_id"]) is not int or archive["subvolume_id"]<=0):
            return result("ARCHIVE_BINDING_INVALID")
        old=archive["identity"]
        if (type(old) is not list or len(old)!=4 or any(type(row) is not list or len(row)!=3
                or any(type(v) is not int or v<0 for v in row) or row[1]==0 for row in old)
                or len({tuple(row[:2]) for row in old})!=4 or old[0][2]!=0 or old[2][2]!=0
                or old[2][1]!=256 or old[1][2]<=0 or old[3][2]<=0):
            return result("ARCHIVE_IDENTITY_INVALID")
        hexes=archive["records_hex"]
        if type(hexes) is not list or len(hexes)!=2 or any(type(v) is not str or
                re.fullmatch(r"(?:[0-9a-f]{2}){1,16384}",v) is None for v in hexes):
            return result("ARCHIVE_RECORDS_INVALID")
        raw=[bytes.fromhex(v) for v in hexes]
        intent,outcome=[decode(v,16384) for v in raw]
        expected={"version":1,"boot_id":archive["boot_id"],
                  "withdrawal_digest":helper.withdrawal_digest(intent,outcome)}
        if (not helper.valid_outcome_boot_binding(intent,outcome)
                or intent.get("bootBinding",{}).get("bootId")!=archive["boot_id"]
                or intent.get("identity")!=old or archive["withdrawal_witness"]!=expected
                or intent.get("state")!="PREPARED" or outcome.get("state")!="VERIFIED"
                or outcome.get("extensionActive") is not False or outcome.get("fileRetained") is not True):
            return result("ARCHIVE_WITHDRAWAL_INVALID")
        swaps=archive["swap"]
        if (type(swaps) is not dict or not swaps or str(helper.EXT_FILE) in swaps
                or str(helper.SWAPFILE) not in swaps or any(type(k) is not str or not k.startswith("/")
                or type(v) is not list or len(v)!=3 or v[0] not in ("file","partition")
                or type(v[1]) is not int or v[1]<=0 or type(v[2]) is not int
                for k,v in swaps.items())):
            return result("ARCHIVE_SWAP_INVALID")
        sha=digest(archive_raw)
        if fence_presence=="ABSENT":
            if prepared_raw is not None or fence_names is not None:
                return result("INCONSISTENT_FENCE_OBSERVATION",sha)
            return result("ARCHIVE_ONLY_REVIEW_REQUIRED",sha)
        if fence_names==[] and prepared_raw is None:
            return result("EMPTY_FENCE_REVIEW_REQUIRED",sha)
        if fence_names!=["prepared.json"]:
            return result("FENCE_CONTENTS_UNRECOGNIZED",sha)
        marker=decode(prepared_raw,16384)
        if (canonical(marker)!=prepared_raw or marker!={"version":1,"state":"PREPARED",
                "archive_sha256":sha,"boot_id":archive["boot_id"],"can_execute":False,
                "can_clear":False} or type(marker["version"]) is not int
                or marker["can_execute"] is not False or marker["can_clear"] is not False):
            return result("PREPARED_BINDING_INVALID",sha)
        if not helper.canonical_boot_id(boot_id):
            return result("CURRENT_BOOT_UNVERIFIED",sha)
        if extension_presence=="ABSENT":
            # Directory absence does not prove physical release or completed work.
            return result("EXTENSION_ABSENT_OUTCOME_UNVERIFIED",sha)
        if boot_id!=archive["boot_id"]:
            return result("PRIOR_BOOT_CUSTODY_REVIEW_REQUIRED",sha)
        if identity!=old or subvolume_id!=archive["subvolume_id"]:
            return result("CURRENT_IDENTITY_MISMATCH",sha)
        if (type(directory_names) is not list or len(directory_names)!=3
                or set(directory_names)!=NAMES or records_raw!=raw):
            return result("CURRENT_RECORDS_OR_CONTENTS_MISMATCH",sha)
        current={p:[v["kind"],v["sizeKiB"],v["priority"]] for p,v in snapshot["rows"].items()}
        if current!=swaps:
            return result("CURRENT_SWAP_COMPOSITION_CHANGED",sha)
        if helper.withdrawal_boot_witness(intent,outcome,identity,snapshot,boot_id)!=expected:
            return result("CURRENT_WITHDRAWAL_UNVERIFIED",sha)
        return result("RETAINED_INACTIVE_CUSTODY_REVIEW_REQUIRED",sha)
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):
        return result("CUSTODY_UNVERIFIED")
