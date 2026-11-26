#!/usr/bin/env python3
"""Synthetic-only checks: procfs parser and non-invasive thread sampling."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory


root = Path(__file__).resolve().parents[2]
source = root / "scripts/syntagma_quickshell_thread_sampler.py"
spec = importlib.util.spec_from_file_location("quickshell_sampler", source)
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)


def stat(pid, name, state="R", user=0, system=0, start=42):
    # /proc stat fields after (comm): state is field 3, utime/stime 14/15,
    # starttime 22. Fill enough fields so wrong offsets visibly fail.
    fields = ["0"] * 24
    fields[0] = state
    fields[11] = str(user)
    fields[12] = str(system)
    fields[19] = str(start)
    return f"{pid} ({name}) " + " ".join(fields) + "\n"


parsed = sampler.parse_stat_line(stat(123, "Quickshell Qt (UI)", "S", 31, 11, 5432))
assert parsed == {
    "name": "Quickshell Qt (UI)", "state": "S",
    "ticks": 42, "start": 5432,
}

previous = {
    123: sampler.parse_stat_line(stat(123, "quickshell", "R", 80, 20, 10)),
    124: sampler.parse_stat_line(stat(124, "QSGRenderThread", "R", 40, 10, 20)),
}
current = {
    123: sampler.parse_stat_line(stat(123, "quickshell", "R", 105, 20, 10)),
    124: sampler.parse_stat_line(stat(124, "QSGRenderThread", "S", 45, 10, 20)),
    125: sampler.parse_stat_line(stat(125, "new thread", "R", 123, 0, 99)),
}
sample = sampler.build_sample(previous, current, 0.25, 100, 123, 456789, 1)
assert sample["totalCpuPct"] == 120.0, sample
assert sample["main"]["cpuPct"] == 100.0
assert sample["main"]["state"] == "R"
assert sample["threadCount"] == 3
assert sample["top"][0]["tid"] == 123
assert sample["sampleIntervalMs"] == 250
# New threads and reused TIDs cannot inherit stale CPU ticks.
assert sampler.build_sample(previous,
                            {123: sampler.parse_stat_line(stat(123, "quickshell", user=999, start=11))},
                            0.25, 100, 123, 456790)["totalCpuPct"] == 0.0

with TemporaryDirectory() as d:
    proc = Path(d)
    for pid, start in [(123, 20), (124, 40)]:
        process = proc / str(pid)
        process.mkdir()
        (process / "comm").write_text("quickshell\n")
        (process / "stat").write_text(stat(pid, "quickshell", start=start))
        task = process / "task" / str(pid)
        task.mkdir(parents=True)
        (task / "stat").write_text(stat(pid, "quickshell", user=10, start=start))
        (task / "wchan").write_text("do_epoll_wait\n")
    other = proc / "900"
    other.mkdir()
    (other / "comm").write_text("firefox\n")
    (other / "stat").write_text(stat(900, "firefox", start=200))
    wrapper = proc / "555"
    wrapper.mkdir()
    (wrapper / "stat").write_text(stat(555, "timeout").replace(" R 0 ", " R 123 ", 1))
    assert sampler.launching_quickshell(proc, parent=555) == 123
    assert sampler.launching_quickshell(proc, parent=123) == 123
    assert sampler.launching_quickshell(proc, parent=900) is None
    assert sampler.launching_quickshell(proc, parent=555, uid=999999) is None
    assert sampler.find_quickshell(proc) == 124
    assert sampler.find_quickshell(proc, uid=999999) is None
    assert sampler.read_threads(proc, 124)[124]["ticks"] == 10
    info = sampler.build_sample({}, sampler.read_threads(proc, 124), .25, 100,
                                124, 5555)
    sampler.add_wchan(info, proc, 124)
    assert info["top"][0]["wchan"] == "do_epoll_wait"

text = source.read_text()
for expected in ('/proc', 'os.getuid()', 'time.monotonic()', 'read_threads(',
                 'build_sample(', 'sampleIntervalMs', 'quickshell-exited-or-replaced'):
    assert expected in text
for forbidden in ('ptrace(', 'os.kill(', 'subprocess.', 'sudo ', 'systemctl ',
                  'killall ', 'pkill '):
    assert forbidden not in text

print("SYNTAGMA THREAD SAMPLER // SYNTHETIC CHECKS PASS; RUNTIME UNTESTED")

# Bounded ASCII JSONL includes newline and escape expansion.
lines = []
writer = sampler.WorkshopOutput(lines.append)
writer.emit({"name": "é"})
assert writer.size == len(lines[0].encode("ascii")) + 1
before = writer.size
try:
    writer.emit({"value": "x" * 65536})
    raise AssertionError("oversized output accepted")
except sampler.WorkshopOutputLimit:
    pass
assert len(lines) == 1 and writer.size == before

# Exercise actual main on synthetic procfs, with a deterministic clock.
import contextlib
import io
import json
from unittest.mock import patch
with TemporaryDirectory() as d:
    proc = Path(d)
    process = proc / "123"
    task = process / "task" / "123"
    task.mkdir(parents=True)
    (process / "comm").write_text("quickshell\n")
    (process / "stat").write_text(stat(123, "quickshell", start=456))
    (task / "stat").write_text(stat(123, "quickshell", start=456))
    (task / "wchan").write_text("do_epoll_wait\n")
    clock = [0.0]
    def advance(seconds):
        clock[0] += seconds
    output = io.StringIO()
    with patch.object(sampler, "Path", lambda _: proc), \
            patch.object(sampler.time, "monotonic", lambda: clock[0]), \
            patch.object(sampler.time, "sleep", advance), contextlib.redirect_stdout(output):
        assert sampler.main(["--workshop", "--duration", "2", "--interval", "0.5", "--top", "2"]) == 0
    records = [json.loads(line) for line in output.getvalue().splitlines()]
    assert records[0]["topCount"] == 2 and records[0]["startTicks"] == 456
    assert records[-1]["samples"] == 4 and records[-1]["observedMs"] == 2000
    assert all(r["startTicks"] == 456 for r in records)
    assert len(output.getvalue().encode("ascii")) <= 65536
    # PID reuse midway must fail without a complete receipt.
    clock[0] = 0.0
    output = io.StringIO()
    def replace_pid(seconds):
        advance(seconds)
        (process / "stat").write_text(stat(123, "quickshell", start=999))
    with patch.object(sampler, "Path", lambda _: proc), \
            patch.object(sampler.time, "monotonic", lambda: clock[0]), \
            patch.object(sampler.time, "sleep", replace_pid), contextlib.redirect_stdout(output):
        assert sampler.main(["--workshop", "--duration", "2", "--interval", "0.5", "--top", "2"]) != 0
    assert all(json.loads(line)["event"] != "complete" for line in output.getvalue().splitlines())
for argv in [
    ["--workshop", "--duration", "30", "--interval", "0.1"],
    ["--workshop", "--duration", "2", "--pid", "123"],
    ["--workshop", "--duration", "2", "--parent-quickshell"],
]:
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            sampler.main(argv)
        raise AssertionError("invalid configured args accepted")
    except SystemExit as error:
        assert error.code == 2
print("DIAG D1b configured sampler synthetic procfs and output cap PASS")
