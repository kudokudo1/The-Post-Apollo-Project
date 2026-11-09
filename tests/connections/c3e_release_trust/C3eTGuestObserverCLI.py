#!/usr/bin/env python3
"""C3e-T: bounded CLI adapter for C4b-owner's already-running service probe.

This is a DOC-owned *opt-in tool*, not a C4b guest modification. Calls the
existing C3e-P actual process/script verifier; no network, writes, privileged
actions, login, authentication or provider permission. Process pins and signed
RPM hash MUST be supplied from independently checked C4b/C3e-O evidence, not
from the service itself. A printed JSON record is NOT remote attestation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "c3et_existing_c3ep", HERE / "C3ePRunningPythonSource.py")
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

RESULT_SCHEMA = "postapollo.connections.c3et-ci-guest-observation.v1"
REFUSED_SCHEMA = "postapollo.connections.c3et-ci-refused.v1"
GUEST_PATH = "/usr/libexec/post-apollo/connections-status-host"
CI_PREFIX = "/run/c3ep-ci-"


def number(s):
    try:
        value = int(s, 10)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("decimal integer required")
    if value < 1 or value > 2147483647 or str(value) != s:
        raise argparse.ArgumentTypeError("positive canonical decimal required")
    return value


def parser():
    p = argparse.ArgumentParser(description="CI-only read-only C4b process source probe")
    p.add_argument("--pid", type=number, required=True)
    p.add_argument("--start-ticks", required=True)
    p.add_argument("--uid", type=number, required=True)
    p.add_argument("--gid", type=number, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--script", required=True)
    p.add_argument("--signed-script-sha256", required=True)
    return p


def check_scope(args):
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
            os.geteuid() != 0 or sys.platform != "linux"):
        raise MOD.Refused("DISPOSABLE_CI_ROOT_ONLY")
    if args.script == GUEST_PATH:
        if (os.environ.get("POST_APOLLO_C4B_TEST_GUEST") != "1" or
                not Path("/run/ostree-booted").exists()):
            raise MOD.Refused("NO_REAL_C4B_GUEST_SCOPE")
    elif (not args.script.startswith(CI_PREFIX) or
            Path(args.script).name != "status-host"):
        raise MOD.Refused("UNAPPROVED_TEST_SCRIPT_SCOPE")
    if (not args.start_ticks.isdecimal() or
            int(args.start_ticks) <= 0 or
            len(args.start_ticks) > 32):
        raise MOD.Refused("PROCESS_START_PIN_INVALID")


def run(args):
    check_scope(args)
    observation = MOD.observe(
        pid=args.pid, expected_start=args.start_ticks,
        expected_uid=args.uid, expected_gid=args.gid,
        expected_script_path=args.script,
        expected_interpreter_path=args.python,
        expected_signed_script_sha256=args.signed_script_sha256)
    return {
        "schema": RESULT_SCHEMA,
        "observed_pid": observation["observed_pid"],
        "observed_start_ticks": observation["observed_start_ticks"],
        "observed_uid": observation["observed_uid"],
        "running_script_sha256": observation["running_script_sha256"],
        "script_file_matches_supplied_signed_payload":
            observation["script_file_matches_supplied_signed_payload"],
        "kernel_interpreter_inode_matches_expected":
            observation["kernel_interpreter_inode_matches_expected"],
        "commandline_matches_installed_entrypoint":
            observation["commandline_matches_installed_entrypoint"],
        "observedPathIsC4bGuestCandidate":
            observation["observedPathIsC4bGuestCandidate"],
        "installedGuestMeasured": False,
        "evidenceCryptographicallyAttested": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = run(args)
    except (MOD.Refused, OSError, ValueError) as error:
        # Do not include user-controlled names, raw process commandline or
        # environment in the result. Only a bounded diagnostic error code.
        code = str(error)
        if not code.isascii() or len(code) > 100 or not all(
                ch.isupper() or ch.isdigit() or ch == "_" for ch in code):
            code = "PROCESS_OBSERVATION_REFUSED"
        print(json.dumps({
            "schema": REFUSED_SCHEMA, "error": code,
            "hostAuthenticated": False, "canApprove": False,
            "credentialActionsEnabled": False, "productionAuthority": False,
        }, sort_keys=True), flush=True)
        return 3
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
