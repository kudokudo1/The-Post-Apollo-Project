#!/usr/bin/env python3
"""Configured memory observer: deterministic synthetic procfs, no host changes."""
import contextlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
import cpuplus_quickshell_memory_observer as observer

def stat(start):
    fields=["S"]+["0"]*23
    fields[19]=str(start)
    return "123 (quickshell) "+" ".join(fields)

with TemporaryDirectory() as folder:
    root=Path(folder)
    process=root/"123"
    process.mkdir()
    (process/"comm").write_text("quickshell\n")
    (process/"stat").write_text(stat(456))
    values={key:0 for key in observer.FIELDS}
    values.update(Rss=100,Pss=80,Private_Dirty=20,Private_Clean=10)
    (process/"smaps_rollup").write_text("".join(f"{key}: {v} kB\n" for key,v in values.items()))
    clock=[0.0]
    def sleep(seconds):
        clock[0]+=seconds
    out=io.StringIO()
    with patch.object(observer,"Path",lambda _:root), patch.object(observer.time,"monotonic",lambda:clock[0]), patch.object(observer.time,"sleep",sleep), contextlib.redirect_stdout(out):
        assert observer.main(["--workshop","--duration","5","--interval","5"])==0
    rows=[json.loads(line) for line in out.getvalue().splitlines()]
    assert len(rows)==3
    assert rows[0]["sampleIntervalMs"] is None and rows[1]["sampleIntervalMs"]==5000
    assert rows[-1]["calibration"]=={"kind":"memory","durationSeconds":5,"intervalMs":5000}
    assert rows[-1]["observedMs"]==5000 and rows[-1]["samples"]==2
    assert rows[-1]["startTicks"]==456
    assert len(out.getvalue().encode("ascii"))<=65536
    # A newer same-user shell exists, but a dump must observe its launcher.
    newer=root/"124"
    newer.mkdir()
    (newer/"comm").write_text("quickshell\n")
    (newer/"stat").write_text(stat(789).replace("123 (","124 ("))
    (newer/"smaps_rollup").write_text((process/"smaps_rollup").read_text())
    clock[0]=0.0
    out=io.StringIO()
    with patch.object(observer,"Path",lambda _:root), patch.object(observer.time,"monotonic",lambda:clock[0]), patch.object(observer.time,"sleep",sleep), patch.object(observer.os,"getppid",return_value=123), patch.object(observer,"find_quickshell",side_effect=AssertionError("newest fallback forbidden")), contextlib.redirect_stdout(out):
        assert observer.main(["--workshop","--parent-quickshell","--duration","5","--interval","5"])==0
    pinned=[json.loads(line) for line in out.getvalue().splitlines()]
    assert all(row["pid"]==123 and row["startTicks"]==456 for row in pinned)
    assert pinned[-1]["event"]=="complete" and pinned[-1]["observedMs"]==5000
    out=io.StringIO()
    with patch.object(observer,"Path",lambda _:root), patch.object(observer.os,"getppid",return_value=999), patch.object(observer,"find_quickshell",side_effect=AssertionError("newest fallback forbidden")), contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        assert observer.main(["--workshop","--parent-quickshell","--duration","5","--interval","5"])==2
    assert not out.getvalue()
    # Remove the competing fixture before the existing newest-selection test.
    for child in newer.iterdir():
        child.unlink()
    newer.rmdir()
    clock[0]=0.0
    out=io.StringIO()
    def replace(seconds):
        sleep(seconds)
        (process/"stat").write_text(stat(999))
    with patch.object(observer,"Path",lambda _:root), patch.object(observer.time,"monotonic",lambda:clock[0]), patch.object(observer.time,"sleep",replace), contextlib.redirect_stdout(out):
        assert observer.main(["--workshop","--duration","5","--interval","5"])!=0
    assert all(json.loads(line)["event"]!="complete" for line in out.getvalue().splitlines())
for args in [["--workshop","--duration","120","--interval","5"],["--workshop","--duration","5","--interval","5","--pid","123"],["--parent-quickshell"],["--workshop","--parent-quickshell","--pid","123"],["--workshop","--parent-quickshell","--workshop-identity","123","456"]]:
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            observer.main(args)
        raise AssertionError("unsafe configuration accepted")
    except SystemExit as error:
        assert error.code==2
print("DIAG D1c configured memory synthetic procfs PASS")
