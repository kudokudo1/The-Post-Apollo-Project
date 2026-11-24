from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_drm_client_h4b as H

BASE = b"drm-driver:\tamdgpu\ndrm-pdev:\t0000:03:00.0\ndrm-client-id:\t42\n"


class DrmTests(unittest.TestCase):
    def test_standard_and_legacy_alias(self):
        for tail in (b"drm-resident-vram: 2 MiB\n",
                     b"drm-memory-vram: 2048 KiB\n",
                     b"drm-resident-vram: 2097152\ndrm-memory-vram: 2 MiB\n"):
            self.assertEqual(H._parse(BASE+tail), H.Client(b"0000:03:00.0", 42, 2097152))

    def test_wrong_driver_and_missing_identity(self):
        for raw in (BASE.replace(b"amdgpu", b"i915"),
                    BASE.replace(b"0000:03:00.0", b"../../etc"),
                    BASE.replace(b"drm-client-id:\t42\n", b""),
                    BASE.replace(b"0000:03:00.0", b"0000:03:20.0")):
            with self.assertRaises(H.I5.CgroupRefusal):
                H._parse(raw+b"drm-resident-vram: 1 KiB")

    def test_missing_resident_is_not_zero(self):
        with self.assertRaisesRegex(H.I5.CgroupRefusal, "DRM_RESIDENCY_UNAVAILABLE"):
            H._parse(BASE+b"drm-total-vram: 2 MiB\n")
        self.assertEqual(H._parse(BASE+b"drm-resident-vram: 0 KiB").resident, 0)

    def test_invalid_or_duplicate_values(self):
        for tail in (b"drm-resident-vram: -1 KiB",
                     b"drm-resident-vram: 1 MB",
                     b"drm-resident-vram: 9999999999999999999 MiB",
                     b"drm-resident-vram: 1 KiB\ndrm-resident-vram: 1 KiB",
                     b"drm-resident-vram: 1 KiB\ndrm-memory-vram: 2 KiB"):
            with self.assertRaises(H.I5.CgroupRefusal):
                H._parse(BASE+tail)

    def test_summary_keeps_device_and_client_separate(self):
        a = H.Client(b"0000:03:00.0", 42, 100)
        b = replace(a, resident=200)
        result = H._summary(a, b, (1000, 600), (1000, 700))
        self.assertEqual(result["client_resident_vram_sampled_max_bytes"], 200)
        self.assertEqual(result["device_headroom_hint_bytes"], 300)
        self.assertEqual(result["selected_drm_client_count"], 1)

    def test_changed_client_and_invalid_device_counters(self):
        a = H.Client(b"0000:03:00.0", 42, 100)
        for b in (replace(a, client_id=43), replace(a, bdf=b"0000:04:00.0")):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "DRM_CLIENT_REFERENCE_CHANGED"):
                H._summary(a, b, (1000, 500), (1000, 500))
        for d1, d2 in (((1000, 500), (2000, 600)), ((1000, 500), (1000, 1001)),
                       ((0, 0), (0, 0))):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "DRM_DEVICE_COUNTER_CHANGED_OR_INVALID"):
                H._summary(a, a, d1, d2)

    def test_real_counter_reads_and_fdinfo_fixture(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p/"fdinfo").mkdir()
            (p/"fdinfo"/"7").write_bytes(BASE+b"drm-resident-vram: 2 KiB\n")
            (p/"mem_info_vram_total").write_text("4096\n")
            (p/"mem_info_vram_used").write_text("2048\n")
            fd = os.open(root, os.O_RDONLY|os.O_DIRECTORY)
            try:
                self.assertEqual(H._client(fd, 7).resident, 2048)
                self.assertEqual(H._sample_device(fd), (4096, 2048))
                (p/"mem_info_vram_used").unlink()
                (p/"mem_info_vram_used").symlink_to(p/"mem_info_vram_total")
                with self.assertRaises(OSError):
                    H._sample_device(fd)
            finally:
                os.close(fd)

    def test_explicit_selection_validation(self):
        for value in (-1, True, H.MAX_FD+1):
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "INVALID_DRM_FD_SELECTION"):
                H.observe("/fixture", 123, value)
        with self.assertRaises(H.I6.MembershipRefusal):
            H.observe("/fixture", 0, 7)

    def test_real_proc_non_drm_fd_refusal(self):
        fd = os.open("/proc/self", os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaisesRegex(H.I5.CgroupRefusal, "NOT_DRM_DEVICE"):
                H._fd_reference(fd, fd)
        finally:
            os.close(fd)

    def test_observation_composition_and_scope_refusal(self):
        # Real directory handles; synthetic GPU/process identity adapters.
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            proc = p/"proc"
            group = p/"group"
            device = p/"device"
            for path in (proc, group, device):
                path.mkdir()
            (proc/"fdinfo").mkdir()
            (proc/"fdinfo"/"7").write_bytes(BASE+b"drm-resident-vram: 2 KiB\n")
            (device/"mem_info_vram_total").write_text("4096\n")
            (device/"mem_info_vram_used").write_text("2048\n")
            original_open = os.open
            def opening(path, flags, *args, **kwargs):
                return original_open(str(proc) if path == "/proc/123" else path,
                                     flags, *args, **kwargs)
            deviceid = H._device_identity(device)
            with patch.object(H.os, "open", side_effect=opening), \
                 patch.object(H.I5, "_open_group", side_effect=lambda _: original_open(group, H._DIR)), \
                 patch.object(H.I5, "_mount", return_value=("mount", "device")), \
                 patch.object(H.I6, "_boot", return_value=b"boot"), \
                 patch.object(H.I6, "_member", return_value="member"), \
                 patch.object(H, "_fd_reference", return_value=(1, 2, os.makedev(226, 128))), \
                 patch.object(H, "_device_path", return_value=str(device)), \
                 patch.object(H, "_link_identity", return_value=deviceid):
                result = H.observe("/fixture", 123, 7)
                self.assertEqual(result["device_headroom_hint_bytes"], 2048)
                for key in ("provider_runtime_instance_verified", "model_binding_verified",
                            "all_clients_observed", "physical_vram_deduplicated",
                            "ollama_device_mapping_verified", "allocatable_vram_established",
                            "safe_to_start_inference", "permission_granted", "production_authority"):
                    self.assertIs(result[key], False)
                self.assertNotIn("0000:03:00.0", str(result))
                self.assertNotIn(root, str(result))
                with patch.object(H, "_link_identity", return_value=(0, 0)):
                    with self.assertRaisesRegex(H.I5.CgroupRefusal, "DRM_PCI_REFERENCE_MISMATCH"):
                        H.observe("/fixture", 123, 7)
                with patch.object(H.I6, "_member", side_effect=["member", "changed"]):
                    with self.assertRaisesRegex(H.I5.CgroupRefusal, "DRM_SCOPE_CHANGED"):
                        H.observe("/fixture", 123, 7)
