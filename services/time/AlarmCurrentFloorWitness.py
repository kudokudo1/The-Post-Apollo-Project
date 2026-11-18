#!/usr/bin/env python3
"""Clock BG1-B2B14: independently signed, read-only CURRENT floor witness.

This is NOT a release-floor authority, installed Clock issuer, session
enroller, alarm writer, or actuation path. A trusted root controller publishes
a BLOCKED witness BEFORE incrementing its durable floor; after commitment it
publishes CURRENT and the one-session signed file. Any incomplete pair denies.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from cryptography.exceptions import InvalidSignature


def _load():
    path=Path(__file__).resolve().with_name(
        "AlarmProtectedSessionEnrollment.py")
    spec=importlib.util.spec_from_file_location(
        "clock_b2b14_signed_session",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock signed session module unavailable")
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


Session=_load()
Origin=Session.Origin
SCHEMA="postapollo.clock.bg1.current-floor.v1"
PURPOSE="postapollo.clock.bg1.root-published-floor.v1"
DOMAIN=b"postapollo.clock.bg1.root-published-floor.v1\x00"
MANIFEST_FILE="clock-current-floor-v1.json"
SIGNATURE_FILE="clock-current-floor-v1.sig"
FIELDS=frozenset(("schema","purpose","role","bootId","releaseEpoch",
                  "releaseSequence","sessionSha256","state"))
MAX_SIZE=1024
AUTHORITY_FLAGS={
    "roleAuthenticated":False,"writerStopped":False,
    "releaseAcknowledged":False,"oldWriterRestartPrevented":False,
    "ownsRealAlarmFile":False,"canTransferOwnership":False,
    "canRing":False,"canNotify":False,
}


class Refused(ValueError):
    """Fixed reason only, no private paths or alarm contents."""


def canonical(payload):
    return Session.canonical(payload)


def validate(raw):
    if type(raw) is not bytes or not 1<=len(raw)<=MAX_SIZE:
        raise Refused("SIGNED_FLOOR_LENGTH_REFUSED")
    try:
        obj=json.loads(raw.decode("ascii"),
                       object_pairs_hook=Session._unique_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           Refused("SIGNED_FLOOR_NONFINITE_NUMBER")))
    except (UnicodeError,ValueError,TypeError,RecursionError) as exc:
        raise Refused("SIGNED_FLOOR_JSON_REFUSED") from exc
    if (type(obj) is not dict or set(obj)!=FIELDS
            or canonical(obj)!=raw
            or obj["schema"]!=SCHEMA or obj["purpose"]!=PURPOSE
            or obj["role"]!="clock-ui-bridge"
            or obj["state"] not in ("BLOCKED","CURRENT")
            or type(obj["releaseEpoch"]) is not int
            or type(obj["releaseSequence"]) is not int
            or not 1<=obj["releaseEpoch"]<=Session.MAX_EPOCH
            or not 1<=obj["releaseSequence"]<=Session.MAX_EPOCH
            or type(obj["sessionSha256"]) is not str
            or not Origin.HEX.fullmatch(obj["sessionSha256"])
            or type(obj["bootId"]) is not str):
        raise Refused("SIGNED_FLOOR_POLICY_REFUSED")
    if obj["bootId"]!=Session._kernel_boot():
        raise Refused("SIGNED_FLOOR_WRONG_BOOT")
    return obj


def make_record(*, epoch, sequence, session_raw, state):
    if (type(epoch) is not int or type(sequence) is not int
            or type(session_raw) is not bytes
            or not 1<=epoch<=Session.MAX_EPOCH
            or not 1<=sequence<=Session.MAX_EPOCH
            or state not in ("BLOCKED","CURRENT")):
        raise Refused("INVALID_CURRENT_FLOOR_REQUEST")
    raw=canonical({
        "schema":SCHEMA, "purpose":PURPOSE, "role":"clock-ui-bridge",
        "bootId":Session._kernel_boot(), "releaseEpoch":epoch,
        "releaseSequence":sequence,"state":state,
        "sessionSha256":hashlib.sha256(session_raw).hexdigest()})
    validate(raw)
    return raw


class ClockCurrentFloorWitness:
    """Read one root-published signature against independently pinned Clock key.

    Requires protected installed B2B9 root and exact B2B12 enrollment dir.
    Test mode only works within B2B12's disposable 0700 fixture tree.
    """

    def __init__(self, *, enrollment_directory, trust_directory,
                 pinned_root_sha256, minimum_epoch, minimum_sequence,
                 synthetic_only=False):
        self.synthetic=synthetic_only
        self.path=Path(enrollment_directory)
        try:
            self.origin=Origin.ClockInstalledRoleTrustPreflight(
                trust_directory=trust_directory,
                pinned_root_sha256=pinned_root_sha256,
                expected_role="clock-ui-bridge",
                minimum_epoch=minimum_epoch,
                minimum_sequence=minimum_sequence,
                disposable_test_mode=synthetic_only)
        except Origin.Refused as exc:
            raise Refused("CLOCK_FLOOR_ROOT_NOT_APPROVED") from exc
        self.minimum=(minimum_epoch,minimum_sequence)
        Session._protected_dir(self.path,disposable=synthetic_only)
        if synthetic_only and self.path.parent != self.origin.trust.parent:
            raise Refused("DISPOSABLE_FLOOR_SCOPE_MISMATCH")

    def read_signed(self):
        """Verified prior state, including BLOCKED, for trusted controller.

        This does NOT imply CURRENT and cannot be an admission result.
        Previously signed versions may precede the new installed role.
        """
        Session._protected_dir(self.path,disposable=self.synthetic)
        try:
            root,_,_=self.origin._load_bundle()
        except (Origin.Refused,Origin.Role.Refused,ValueError,OSError) as exc:
            raise Refused("CLOCK_FLOOR_ROLE_NOT_VERIFIED") from exc
        try:
            raw=Session._read_file(self.path/MANIFEST_FILE,
                                   length=MAX_SIZE,disposable=self.synthetic)
            sig=Session._read_file(self.path/SIGNATURE_FILE,
                                   length=64,disposable=self.synthetic)
        except Session.Refused as exc:
            raise Refused("CURRENT_FLOOR_FILE_UNVERIFIED") from exc
        if len(sig)!=64:
            raise Refused("FLOOR_SIGNATURE_LENGTH_REFUSED")
        try:
            root.verify(sig,DOMAIN+raw)
        except InvalidSignature as exc:
            raise Refused("FLOOR_SIGNATURE_NOT_TRUSTED") from exc
        return validate(raw)

    def inspect_current(self):
        obj=self.read_signed()
        if obj["state"]!="CURRENT":
            raise Refused("CONTROLLER_ISSUANCE_BLOCKED")
        try:
            _,role_raw,_=self.origin._load_bundle()
            role=Origin.Role._policy(role_raw)
        except (Origin.Refused,Origin.Role.Refused,ValueError,OSError) as exc:
            raise Refused("CLOCK_FLOOR_ROLE_NOT_VERIFIED") from exc
        version=(obj["releaseEpoch"],obj["releaseSequence"])
        if (version<self.minimum or version!=(
                role["releaseEpoch"],role["releaseSequence"])):
            raise Refused("CURRENT_FLOOR_ROLE_VERSION_MISMATCH")
        try:
            _,after_role,_=self.origin._load_bundle()
        except (Origin.Refused,ValueError) as exc:
            raise Refused("CLOCK_FLOOR_ROLE_CHANGED") from exc
        if after_role!=role_raw:
            raise Refused("CLOCK_FLOOR_ROLE_CHANGED")
        return {
            "releaseEpoch":version[0],
            "releaseSequence":version[1],
            "sessionSha256":obj["sessionSha256"],
            "floorSignatureVerified":True,
            "current":True,
            "fixtureOnly":self.synthetic,
            **AUTHORITY_FLAGS,
        }

    def compare_session(self, session_raw, *, expected=None):
        # Must be invoked before AND after B2B12 kernel-peer verification.
        observed=self.inspect_current()
        if (type(session_raw) is not bytes
                or hashlib.sha256(session_raw).hexdigest()!=
                observed["sessionSha256"]):
            raise Refused("SIGNED_SESSION_NOT_CURRENT_FLOOR")
        if expected is not None and (
                observed["releaseEpoch"],observed["releaseSequence"],
                observed["sessionSha256"])!=expected:
            raise Refused("CURRENT_FLOOR_CHANGED_DURING_OBSERVATION")
        return observed
