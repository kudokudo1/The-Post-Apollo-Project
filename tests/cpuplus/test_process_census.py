import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpuplus_process_census as census


def row(pid, start=10, ticks=100, stamp=1000000000, io=None, name="quickshell"):
    return {"pid": pid, "name": name, "startTicks": start, "ticks": ticks,
            "observedNs": stamp, "rssKiB": 123, "threads": 2, "io": io}


class CensusTests(unittest.TestCase):
    def test_stat_comm_parentheses(self):
        fields = ["S"] + ["0"] * 21
        fields[11], fields[12], fields[17], fields[19], fields[21] = "7", "8", "3", "19", "20"
        parsed = census.parse_stat("42 (name with ) space) " + " ".join(fields), 4096)
        self.assertEqual(parsed, {"pid":42,"name":"name with ) space","ticks":15,
                                  "threads":3,"startTicks":19,"rssKiB":80})

    def test_io_missing_duplicate_and_nonnegative(self):
        self.assertEqual(census.parse_io("read_bytes: 0\nwrite_bytes: 9\n"),
                         {"read_bytes":0,"write_bytes":9})
        for text in ("read_bytes: 1", "read_bytes: -1\nwrite_bytes: 1",
                     "read_bytes: 1\nread_bytes: 2\nwrite_bytes: 3"):
            with self.assertRaises(ValueError):
                census.parse_io(text)

    def test_identity_and_unavailable_deltas(self):
        old = {1:row(1,io={"read_bytes":10,"write_bytes":20}),2:row(2),3:row(3)}
        current = {1:row(1,ticks=300,stamp=3000000000,io={"read_bytes":30,"write_bytes":10}),
                   2:row(2,start=11,ticks=999,stamp=3000000000),
                   4:row(4,stamp=3000000000),
                   3:row(3,ticks=90,stamp=3000000000)}
        result = {item["pid"]:item for item in census.compare(old,current,100)}
        self.assertEqual(result[1]["cpuPct"],100.0)
        self.assertEqual(result[1]["readBps"],10.0)
        self.assertIsNone(result[1]["writeBps"])
        for pid in (2,3,4):
            self.assertIsNone(result[pid]["cpuPct"])
        self.assertIsNone(result[2]["readBps"])

    def test_ranked_union_and_focus_cap(self):
        rows = []
        for i in range(100):
            rows.append({"pid":i+1,"name":"kitty" if i < 20 else "other",
                         "rssKiB":i,"cpuPct":None if i == 0 else i,
                         "readBps":100-i,"writeBps":None})
        selected, matches = census.select_rows(rows)
        self.assertEqual(matches,20)
        self.assertLessEqual(len(selected),4*census.TOP+census.FOCUS_LIMIT)
        self.assertEqual(len(selected),len({r["pid"] for r in selected}))
        self.assertIn(100,{r["pid"] for r in selected})

    def test_native_proc_smoke(self):
        result = subprocess.run([sys.executable,"-B",str(ROOT/"scripts/cpuplus_process_census.py"),
                                 "--duration","1","--interval","1"],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(records[-1],{"schema":census.SCHEMA,"event":"complete","samples":1})
        self.assertEqual(records[0]["event"],"census")
        self.assertGreater(records[0]["observed"],0)
        self.assertTrue(records[0]["rows"])
        self.assertLess(len(result.stdout),65536)
        self.assertNotIn("cmdline",result.stdout)


if __name__ == "__main__":
    unittest.main()
