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
