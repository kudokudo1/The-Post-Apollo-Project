"""Pure source tests with synthetic observations. No privileged I/O."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from observation import canonical,classify,digest,PIN

path=Path(__file__).resolve().parents[2]/"scripts/post-apollo-memory-add-swap"
loader=importlib.machinery.SourceFileLoader("memory_helper",str(path))
spec=importlib.util.spec_from_loader(loader.name,loader)
helper=importlib.util.module_from_spec(spec)
loader.exec_module(helper)
BOOT="1d934ec2-d18e-441a-9bbf-37e404632201"
OTHER="2d934ec2-d18e-441a-9bbf-37e404632201"

def fixture():
    identity=[[1,256,0],[1,257,16*helper.GIB],[2,256,0],[2,257,8*helper.GIB]]
    intent={"version":1,"state":"PREPARED","targetGiB":16,"timeNs":100,
            "identity":identity,"evidence":{"targetGiB":16,"baseSizeKiB":16777212,
            "extensionSizeKiB":8388604,"extensionUsedKiB":0},
            "bootBinding":{"version":1,"bootId":BOOT}}
    outcome={"version":1,"state":"VERIFIED","targetGiB":16,"timeNs":101,
            "sizeKiB":16777212,"basePriority":10,"extensionActive":False,"fileRetained":True,
            "bootBinding":{"version":1,"bootId":BOOT,"intentDigest":helper.intent_digest(intent)}}
    snapshot={"rows":{str(helper.SWAPFILE):{"kind":"file","sizeKiB":16777212,"usedKiB":0,"priority":10}}}
    raw=[canonical(intent),canonical(outcome)]
    archive=canonical({"version":1,"state":"ARCHIVE_CUSTODY","candidate_blob":PIN,
        "boot_id":BOOT,"identity":identity,"subvolume_id":300,"records_hex":[v.hex() for v in raw],
        "withdrawal_witness":{"version":1,"boot_id":BOOT,
                              "withdrawal_digest":helper.withdrawal_digest(intent,outcome)},
        "swap":{str(helper.SWAPFILE):["file",16777212,10]},"can_execute":False,"can_clear":False})
    marker=canonical({"version":1,"state":"PREPARED","archive_sha256":digest(archive),
                      "boot_id":BOOT,"can_execute":False,"can_clear":False})
    return dict(archive_presence="PRESENT",archive_raw=archive,fence_presence="PRESENT",
        fence_names=["prepared.json"],prepared_raw=marker,boot_id=BOOT,extension_presence="PRESENT",
        identity=identity,subvolume_id=300,directory_names=["swapfile","withdrawal.json","withdrawal-result.json"],
        records_raw=raw,snapshot=snapshot)

class Observation(unittest.TestCase):
    def check(self,code,**changes):
        got=classify(helper,**dict(fixture(),**changes))
        self.assertEqual(got["code"],code)
        self.assertIs(got["can_execute"],False)
        self.assertIs(got["can_clear"],False)
        self.assertIs(got["storage_release_verified"],False)
    def test_exact_retained(self):
        self.check("RETAINED_INACTIVE_CUSTODY_REVIEW_REQUIRED")
    def test_archive_only(self):
        self.check("ARCHIVE_ONLY_REVIEW_REQUIRED",fence_presence="ABSENT",fence_names=None,prepared_raw=None)
    def test_partial_archive(self):
        self.check("CUSTODY_UNVERIFIED",archive_raw=b"{")
    def test_empty_fence(self):
        self.check("EMPTY_FENCE_REVIEW_REQUIRED",fence_names=[],prepared_raw=None)
    def test_orphan_fence(self):
        self.check("FENCE_WITHOUT_ARCHIVE",archive_presence="ABSENT",archive_raw=None)
    def test_unrecognized_fence(self):
        self.check("FENCE_CONTENTS_UNRECOGNIZED",fence_names=["prepared.json","result.json"])
    def test_prior_boot(self):
        self.check("PRIOR_BOOT_CUSTODY_REVIEW_REQUIRED",boot_id=OTHER)
    def test_absence_is_not_completion(self):
        self.check("EXTENSION_ABSENT_OUTCOME_UNVERIFIED",extension_presence="ABSENT")
    def test_current_record_change(self):
        self.check("CURRENT_RECORDS_OR_CONTENTS_MISMATCH",records_raw=[b"{}",b"{}"])
    def test_changed_subvolume(self):
        self.check("CURRENT_IDENTITY_MISMATCH",subvolume_id=301)
    def test_active_extension(self):
        f=fixture()
        f["snapshot"]["rows"][str(helper.EXT_FILE)]={"kind":"file","sizeKiB":8388604,"usedKiB":0,"priority":9}
        self.check("CURRENT_SWAP_COMPOSITION_CHANGED",snapshot=f["snapshot"])
    def test_unknown_observation(self):
        self.check("OBSERVATION_UNVERIFIED",archive_presence="UNKNOWN")
    def test_wrong_archive_digest(self):
        self.check("PREPARED_BINDING_INVALID",prepared_raw=fixture()["prepared_raw"].replace(
            digest(fixture()["archive_raw"]).encode(),b"0"*64))
    def test_no_custody(self):
        self.check("NO_CUSTODY_OBSERVED",archive_presence="ABSENT",archive_raw=None,
                   fence_presence="ABSENT",fence_names=None,prepared_raw=None)

if __name__=="__main__":
    unittest.main()
