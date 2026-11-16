"""P50 canonical signed-release consistency and REAL P49 subprocess denial.

All signing roots in these tests are freshly generated CI fixture secrets and
are NOT operator-enrolled production keys. No external provider, keyring,
personal contact, iPhone, RPM installation, systemd start or C5 consent.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services" / "phone"
sys.path.insert(0, str(SOURCE))
import PhonePersonalInstalledReleaseP50 as Release
import PhonePersonalHostSocketP47 as SocketHost


def make_release(bundle: Path, private=None, **fields):
    if private is None:
        private = Ed25519PrivateKey.generate()
    document = {
        "schema": Release.SCHEMA,
        "role": Release.ROLE,
        "purpose": Release.PURPOSE,
        "audience": Release.AUDIENCE,
        "unit": Release.UNIT_NAME,
        "releaseEpoch": 2,
        "releaseSequence": 9,
        "files": Release._measured(bundle),
    }
    document.update(fields)
    raw = Release.canonical(document)
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return raw, private.sign(Release.DOMAIN + raw), public


class ReleaseConsistencyTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory(prefix="p50-test-bundle-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.bundle = self.root / "phone"
        (self.bundle / "systemd").mkdir(parents=True)
        for path in (*Release.SOURCE_NAMES, Release.UNIT_FILE):
            dst = self.bundle / path
            shutil.copy2(SOURCE / path, dst)
            dst.chmod(0o600)
        self.raw, self.sig, self.pub = make_release(self.bundle)

    def verify(self, **override):
        args = dict(
            manifest=self.raw, signature=self.sig, root_public=self.pub,
            bundle=self.bundle, minimum_epoch=2, minimum_sequence=9,
        )
        args.update(override)
        return Release.verify_candidate(**args)

    def test_separate_ed25519_root_and_exact_real_source_content(self):
        result = self.verify()
        self.assertEqual(result, Release.RESULT)
        self.assertIs(result["installedHostVerified"], False)
        self.assertIs(result["keyReleaseAuthorized"], False)
        self.assertIs(result["personalSaveAuthorized"], False)
        self.assertIs(result["c5HumanConsentVerified"], False)
        self.assertNotIn("contact", json.dumps(result))
        self.assertEqual(set(json.loads(self.raw)["files"]), Release.NAMES)
        self.assertNotIn(self.pub, self.raw)

    def test_forged_identity_c4b_role_and_all_other_cross_role_forgery_refuse(self):
        changes = (
            {"schema": "postapollo.identity.c4b.silverblue.synthetic-release.ci-v1"},
            {"role": "postapollo.identity.native-command-gateway.deny-only-ci"},
            {"purpose": "personal.contact.metadata-write"},
            {"audience": "postapollo.connections.c3ey-disposable-root-issuer.ci"},
            {"unit": "post-apollo-identity-silverblue-ci.service"},
            {"releaseEpoch": 1},
            {"releaseSequence": 8},
            {"releaseEpoch": True},
            {"releaseSequence": 9.0},
            {"hostAuthenticated": True},
        )
        for change in changes:
            raw, sig, key = make_release(self.bundle, **change)
            with self.subTest(change=change):
                with self.assertRaisesRegex(
                    Release.OriginRefused, "^PHONE_STATUS_ORIGIN_REFUSED$"
                ):
                    self.verify(manifest=raw, signature=sig, root_public=key)

    def test_tampered_source_and_unapproved_extra_missing_files_refuse(self):
        original = (self.bundle / Release.SOURCE_NAMES[0]).read_bytes()
        (self.bundle / Release.SOURCE_NAMES[0]).write_bytes(original + b"# TAMPER\n")
        with self.assertRaises(Release.OriginRefused):
            self.verify()
        (self.bundle / Release.SOURCE_NAMES[0]).write_bytes(original)
        self.assertEqual(self.verify(), Release.RESULT)
        obj = json.loads(self.raw)
        for files in (
            {**obj["files"], "extra.py": "a" * 64},
            {k: v for k, v in obj["files"].items() if k != Release.UNIT_FILE},
            {**obj["files"], Release.UNIT_FILE: "0" * 64},
        ):
            raw, sig, pub = make_release(self.bundle, files=files)
            with self.subTest(files=sorted(files)):
                with self.assertRaises(Release.OriginRefused):
                    self.verify(manifest=raw, signature=sig, root_public=pub)

    def test_signature_wrong_root_wrong_message_old_epoch_and_bool_floors(self):
        stranger = Ed25519PrivateKey.generate()
        wrong_key = stranger.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        for changes in (
            {"root_public": wrong_key},
            {"signature": b"x" * 64},
            {"manifest": self.raw + b"\n"},
            {"minimum_epoch": 3},
            {"minimum_sequence": 10},
            {"minimum_epoch": True},
            {"minimum_sequence": 1.0},
            {"root_public": b"short"},
            {"signature": b"short"},
        ):
            with self.subTest(fields=list(changes)):
                with self.assertRaises(Release.OriginRefused):
                    self.verify(**changes)

    def test_duplicate_noncanonical_and_nonprintable_payload_refuse(self):
        bad = (
            self.raw[:-1] + b',"role":"' + Release.ROLE.encode() + b'"}',
            b" " + self.raw,
            json.dumps(json.loads(self.raw), indent=2).encode("ascii"),
            self.raw.replace(b'"releaseEpoch":2', b'"releaseEpoch":NaN'),
            b"\x00" + self.raw,
            b"{" + b"x" * 4097 + b"}",
        )
        for sample in bad:
            with self.subTest(sample=sample[:35]):
                with self.assertRaises(Release.OriginRefused):
                    self.verify(manifest=sample)

    def test_symlink_group_writable_hardlink_and_missing_unit_fail_closed(self):
        src = self.bundle / Release.SOURCE_NAMES[0]
        copy = src.read_bytes()
        src.unlink()
        src.symlink_to(self.bundle / Release.SOURCE_NAMES[1])
        with self.assertRaises(Release.OriginRefused):
            self.verify()
        src.unlink()
        src.write_bytes(copy)
        src.chmod(0o622)
        with self.assertRaises(Release.OriginRefused):
            self.verify()
        src.chmod(0o600)
        linked = self.bundle / "LINKED"
        os.link(src, linked)
        with self.assertRaises(Release.OriginRefused):
            self.verify()
        linked.unlink()
        self.assertEqual(self.verify(), Release.RESULT)
        (self.bundle / Release.UNIT_FILE).unlink()
        with self.assertRaises(Release.OriginRefused):
            self.verify()

    def test_read_paths_still_cannot_enroll_root_or_save(self):
        folder = self.root / "evidence"
        folder.mkdir()
        manifest = folder / "manifest"
        signature = folder / "signature"
        pub = folder / "public"
        for path, data in ((manifest, self.raw), (signature, self.sig),
                           (pub, self.pub)):
            path.write_bytes(data)
            path.chmod(0o600)
        args = dict(bundle=self.bundle, manifest_path=manifest,
                    signature_path=signature, root_path=pub,
                    minimum_epoch=2, minimum_sequence=9)
        self.assertEqual(Release.verify_candidate_from_paths(**args), Release.RESULT)
        pub.write_bytes(b"0" * 32)
        with self.assertRaises(Release.OriginRefused):
            Release.verify_candidate_from_paths(**args)
        pub.write_bytes(self.pub)
        pub.chmod(0o666)
        with self.assertRaises(Release.OriginRefused):
            Release.verify_candidate_from_paths(**args)

    def test_no_production_wiring_or_key_vault_exports(self):
        source = (SOURCE / "PhonePersonalInstalledReleaseP50.py").read_text()
        for term in (
            "import dbus", "subprocess", "secret-tool", "Vault.commit(",
            "os.environ", "if __name__ ==", "QtQuick", "print(",
            "keyReleaseAuthorized\": True", "personalSaveAuthorized\": True",
        ):
            self.assertNotIn(term, source)


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux process required")
class ActualStatusHostSignedPreflightTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory(prefix="p50-live-proc-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.sockdir = self.root / "socket"
        self.sockdir.mkdir(mode=0o700)
        self.files = self.root / "signed"
        self.files.mkdir()
        self.raw, self.sig, self.pub = make_release(SOURCE)
        self.m = self.files / "manifest"
        self.s = self.files / "signature"
        self.k = self.files / "public"
        for path, data in ((self.m, self.raw), (self.s, self.sig),
                           (self.k, self.pub)):
            path.write_bytes(data)
            path.chmod(0o600)
        self.procs = []
        self.addCleanup(self.stop_all)

    def stop_all(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()

    def start(self):
        env = os.environ.copy()
        env["POST_APOLLO_PHONE_STATUS_CI_ONLY"] = "1"
        env["POST_APOLLO_PHONE_STATUS_NO_SAVE"] = "1"
        proc = subprocess.Popen([
            sys.executable, "-I", "-B",
            str(SOURCE / "PhonePersonalStatusHostP49.py"),
            "--private-status-dir", str(self.sockdir),
            "--ci-signed-manifest", str(self.m),
            "--ci-signed-signature", str(self.s),
            "--ci-release-root", str(self.k),
        ], env=env, cwd=str(ROOT),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.procs.append(proc)
        return proc

    def await_socket(self, proc):
        socket_path = self.sockdir / SocketHost.SOCKET_NAME
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if socket_path.is_socket():
                return socket_path
            if proc.poll() is not None:
                self.fail("signed preflight host refused before socket")
            time.sleep(0.04)
        self.fail("signed status host socket timeout")

    def test_real_signed_process_start_deny_save_and_shutdown(self):
        process = self.start()
        path = self.await_socket(process)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(2)
            conn.connect(str(path))
            conn.sendall(SocketHost.REQUEST_FRAME)
            reply = b""
            while not reply.endswith(b"\n"):
                reply += conn.recv(4096)
        doc = json.loads(reply)
        self.assertEqual(doc, SocketHost.STATUS)
        self.assertIs(doc["personalSaveAuthorized"], False)
        self.assertIs(doc["installedIdentityVerified"], False)
        self.assertIs(doc["keyReadAuthorized"], False)
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(out, b"")
        self.assertEqual(err, b"")
        self.assertFalse(path.exists())

    def test_tampered_signature_prevents_actual_service_start(self):
        self.s.write_bytes(bytes(64))
        proc = self.start()
        out, err = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertEqual(out, b"")
        self.assertEqual(err, b"")
        self.assertFalse((self.sockdir / SocketHost.SOCKET_NAME).exists())


if __name__ == "__main__":
    unittest.main()
