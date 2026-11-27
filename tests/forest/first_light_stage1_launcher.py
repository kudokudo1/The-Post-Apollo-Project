"""Fixed Stage 1 exec boundary; no acquisition or provider in this launcher.

The outer reviewed GNU timeout remains original process-group custodian.
Close actual inherited nonstdio FDs in this single-threaded process,
then exec the fixed sibling verifier without creating another worker.
Offline modes reach only the fixed synthetic test entrypoint.
"""
import errno
import os
from pathlib import Path
import stat
import sys

BASE_ENV = {"PATH", "LANG"}
STAGE_ENV = BASE_ENV | {
    "RUNNER_ENVIRONMENT", "RUNNER_ARCH", "ImageOS", "ImageVersion",
    "GITHUB_ACTIONS", "GITHUB_EVENT_NAME", "GITHUB_RUN_ATTEMPT",
}
PYTHON = "/usr/bin/python3"
HERE = Path(__file__).resolve().parent


def close_extra_fds():
    # Listing /proc/self/fd opens its own directory FD; only EBADF is
    # an expected race when that enumeration FD is already closed.
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd > 2:
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd > 2:
            try:
                os.fstat(fd)
            except OSError as exc:
                if exc.errno == errno.EBADF:
                    continue
                raise
            raise ValueError("EXTRA_FD")


def main():
    if sys.argv[1:] == ["--offline-witness"]:
        target = HERE / "test_first_light_stage1.py"
        args = ["--fd-witness"]
        keys = BASE_ENV
    elif sys.argv[1:] == ["--offline-wait"]:
        target = HERE / "test_first_light_stage1.py"
        args = ["--fd-wait"]
        keys = BASE_ENV
    elif len(sys.argv) == 3 and sys.argv[1] == "--stage":
        target = HERE / "first_light_stage1.py"
        args = [sys.argv[2]]
        keys = STAGE_ENV
    else:
        raise ValueError("ARGUMENTS")
    if (sys.platform != "linux" or set(os.environ) != keys
            or os.environ["PATH"] != "/usr/bin:/bin"
            or os.environ["LANG"] != "C.UTF-8"):
        raise ValueError("ENVIRONMENT")
    null = os.stat("/dev/null")
    stdin = os.fstat(0)
    if not stat.S_ISCHR(stdin.st_mode) or stdin.st_rdev != null.st_rdev:
        raise ValueError("STDIN")
    os.fstat(1)
    os.fstat(2)
    env = {key: os.environ[key] for key in keys}
    close_extra_fds()
    # Same PID/process group, exact fixed interpreter and reviewed sibling.
    # No shell, pass_fds, provider start, second dispatch or retry.
    os.execve(PYTHON, [PYTHON, "-I", "-B", str(target), *args], env)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never include FD targets, environment values or arbitrary paths.
        print("STAGE1_HOLD LAUNCHER_REFUSAL", flush=True)
        sys.exit(2)
