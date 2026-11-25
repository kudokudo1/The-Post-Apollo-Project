import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from reclaim_custody import CHECKS, PIN, digest, fence_state, plan

path = Path(__file__).resolve().parents[2] / "scripts/post-apollo-memory-add-swap"
loader = importlib.machinery.SourceFileLoader("memory_helper", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)

def fixture():
    identity = [(1,2,0),(1,3,16*helper.GIB),(1,4,0),(1,5,8*helper.GIB)]
    intent = {"version":1,"state":"PREPARED","targetGiB":16,"timeNs":100,
              "identity":[list(row) for row in identity],
              "evidence":{"targetGiB":16,"baseSizeKiB":16777212,
                          "extensionSizeKiB":8388604,"extensionUsedKiB":0}}
    outcome = {"version":1,"state":"VERIFIED","targetGiB":16,"timeNs":101,
               "sizeKiB":16777212,"basePriority":10,"extensionActive":False,"fileRetained":True}
    boot = "1d934ec2-d18e-441a-9bbf-37e404632201"
    intent["bootBinding"] = {"version":1,"bootId":boot}
    outcome["bootBinding"] = dict(intent["bootBinding"], intentDigest=digest(intent))
    return dict(candidate_blob=PIN, identity=identity,intent=intent,outcome=outcome,
                snapshot={"rows":{str(helper.SWAPFILE):{"kind":"file","sizeKiB":16777212,
                              "usedKiB":0,"priority":10}}},
                directory_names=["swapfile","withdrawal.json","withdrawal-result.json"],
                boot_id=boot,
                checks=dict.fromkeys(CHECKS,True),existing_fence=False)

class Reclaim(unittest.TestCase):
    def run_plan(self, **changes):
        return plan(helper, **dict(fixture(), **changes))

    def test_exact_proposal_not_authority(self):
        result = self.run_plan()
        self.assertEqual(result["state"],"ARCHIVE_CUSTODY_PROPOSED")
        self.assertFalse(result["can_execute"])
        self.assertEqual(result["archive_digest"],digest(result["bundle"]))
        self.assertEqual(result["bundle"]["expected_file_bytes"],8*helper.GIB)
        self.assertEqual(result["bundle"]["version"],2)
        self.assertEqual(result["bundle"]["withdrawal_witness"],
                         {"version":1,"boot_id":fixture()["boot_id"],
                          "withdrawal_digest":digest([fixture()["intent"],fixture()["outcome"]])})

    def test_identity_and_boot_change(self):
        f=fixture(); f["identity"][3]=(1,9,8*helper.GIB)
        self.assertEqual(plan(helper,**f)["state"],"BLOCKED")
        self.assertEqual(self.run_plan(boot_id="2d934ec2-d18e-441a-9bbf-37e404632201")["state"],"BLOCKED")

    def test_legacy_v1_witness_not_inferred(self):
        f=fixture()
        del f["intent"]["bootBinding"]
        del f["outcome"]["bootBinding"]
        self.assertEqual(plan(helper,**f)["code"],"CONTEMPORANEOUS_BOOT_WITNESS_REQUIRED")
        # A self-computed digest is no substitute for a contemporaneous record.
        with self.assertRaises(TypeError):
            plan(helper,**f,withdrawal_witness={"version":1,"boot_id":f["boot_id"],
                "withdrawal_digest":digest([f["intent"],f["outcome"]])})

    def test_old_candidate_refused(self):
        self.assertEqual(self.run_plan(candidate_blob="6bac8be7b1de6883f480a95944d6ba1130852270")["code"],
                         "CANDIDATE_MISMATCH")

    def test_partial_or_forged_binding_refused(self):
        for change in ("missing", "wrong-digest", "different-boot", "changed-intent"):
            f=fixture()
            if change=="missing": del f["outcome"]["bootBinding"]
            elif change=="wrong-digest": f["outcome"]["bootBinding"]["intentDigest"]="0"*64
            elif change=="different-boot": f["outcome"]["bootBinding"]["bootId"]="2d934ec2-d18e-441a-9bbf-37e404632201"
            else: f["intent"]["timeNs"]=99
            self.assertEqual(plan(helper,**f)["state"],"BLOCKED")

    def test_nil_and_prior_boot_refused(self):
        for boot in ("00000000-0000-0000-0000-000000000000",
                     "2d934ec2-d18e-441a-9bbf-37e404632201"):
            self.assertEqual(self.run_plan(boot_id=boot)["code"],
                             "CONTEMPORANEOUS_BOOT_WITNESS_REQUIRED")

    def test_proposal_detached_from_input(self):
        f=fixture()
        result=plan(helper,**f)
        f["intent"]["bootBinding"]["bootId"]="changed"
        self.assertEqual(result["archive_digest"],digest(result["bundle"]))

    def test_active_or_missing_base(self):
        f=fixture(); f["snapshot"]["rows"][str(helper.EXT_FILE)]={"kind":"file","sizeKiB":8388604,"usedKiB":0,"priority":9}
        self.assertEqual(plan(helper,**f)["state"],"BLOCKED")
        self.assertEqual(self.run_plan(snapshot={"rows":{}})["state"],"BLOCKED")

    def test_missing_and_not_started_outcomes(self):
        for outcome in (None,{"state":"NOT_STARTED","code":"RAM_HEADROOM"}):
            self.assertEqual(self.run_plan(outcome=outcome)["state"],"BLOCKED")

    def test_extra_directory_contents(self):
        for name in ("archive-pending.json","reactivation.json","other"):
            self.assertEqual(self.run_plan(directory_names=fixture()["directory_names"]+[name])["state"],"BLOCKED")

    def test_every_precondition_required(self):
        for key in CHECKS:
            f=fixture(); f["checks"][key]=False
            self.assertEqual(plan(helper,**f)["code"],"PROTECTED_PRECONDITIONS_UNVERIFIED")

    def test_unknown_or_existing_fence(self):
        for value in (None,True,0):
            self.assertEqual(self.run_plan(existing_fence=value)["code"],"RECLAIM_RECOVERY_REQUIRED")

    def test_fence_survives_missing_directory(self):
        marker={"version":1,"state":"PREPARED","archive_digest":"a"*64}
        for absent in (True,False,None):
            result=fence_state(True,marker,archive_verified=True,extension_absent=absent)
            self.assertEqual(result["state"],"RECOVERY_REQUIRED")
            self.assertFalse(result["can_clear"])

    def test_no_clear_even_verified_absence(self):
        marker={"version":1,"state":"VERIFIED_ABSENT","archive_digest":"a"*64}
        result=fence_state(True,marker,archive_verified=True,extension_absent=True)
        self.assertEqual(result["code"],"RECORDED_ABSENCE_REVIEW_REQUIRED")
        self.assertFalse(result["can_execute"])
        self.assertFalse(result["can_clear"])

    def test_corrupt_fence_is_not_absence(self):
        for marker in (None,{},{"version":1,"state":"PREPARED","archive_digest":"../x"}):
            self.assertEqual(fence_state(True,marker,archive_verified=False,extension_absent=True)["state"],"RECOVERY_REQUIRED")

if __name__ == "__main__":
    unittest.main()
