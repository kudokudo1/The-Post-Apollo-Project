"""Native Clock V2 Python-vs-QML cross-runtime schedule parity.

Same V2 document, same wall-time, same TZ. No user alarm data, sound or UI.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timedelta
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/time/AlarmNativeTickPolicy.py"
QML = ROOT / "services/time/AlarmManagerPolicy.js"

spec = importlib.util.spec_from_file_location("clock_bg2_native_tick", SOURCE)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)


def ms(y,m,d,h,minute,sec=0):
    return int(datetime(y,m,d,h,minute,sec).timestamp()*1000)


def alarm(day="2026-11-18",mode="once",hour=7,minute=30,**change):
    row = {
        "id": 1, "name": "A", "favorite": False, "note": "",
        "hour": hour, "minute": minute, "mode": mode,
        "weekdays": [3], "date": day if mode == "once" else "",
        "keepSaved": True, "enabled": True,
        "pausedUntilDate": "", "soundId": "chime",
        "soundEnabled": True, "volumePercent": 60,
        "lastFiredDay": "", "ringing": False, "ringStartedAtMs": 0,
        "snoozeUntilMs": 0, "completed": False,
        "lastEventKind": "none", "lastEventAtMs": 0,
        "lastExpectedAtMs": 0, "lastFiredAtMs": 0,
        "lastMissedAtMs": 0, "armedAtMs": ms(2026,11,17,7,0),
        "lastProcessedDueMs": 0,
    }
    row.update(change)
    return row


def doc(*rows):
    return {"version":2, "nextId":max([r["id"] for r in rows],default=0)+1,
            "alarms":list(rows)}


NODE = r"""
const fs=require("fs"),vm=require("vm");
const source=fs.readFileSync(process.argv[1],"utf8")
    .replace(/^\.pragma library\s*$/m,"");
const scope={};vm.createContext(scope);vm.runInContext(source,scope);
const cases=JSON.parse(fs.readFileSync(0,"utf8"));
const actual=cases.map(v=>scope.tick(v.document,v.now_ms));
process.stdout.write(JSON.stringify(actual));
"""


class NativeClockParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["TZ"] = "America/New_York"
        if hasattr(time,"tzset"):
            time.tzset()

    def build_cases(self):
        today=ms(2026,11,18,7,30)
        base=alarm()
        cases=[]
        def add(name,t,row):
            cases.append({"label":name,"now_ms":t,"document":doc(row)})
        add("one due now",today,base)
        add("one early",today-1000,base)
        add("one grace 90s",today+90000,base)
        add("one missed 121s",today+121000,base)
        add("one yesterday missed",today,alarm(day="2026-11-17"))
        add("one future",today,alarm(day="2026-11-19"))
        add("disabled",today,alarm(enabled=False))
        add("one finished disabled",today,alarm(enabled=False,completed=True))
        add("already fired once",today,alarm(lastFiredDay="2026-11-18"))
        add("already processed",today,alarm(lastProcessedDueMs=today))
        add("paused future",today,alarm(pausedUntilDate="2026-11-20"))
        add("paused expires",today,alarm(pausedUntilDate="2026-11-18"))
        add("snooze pending",today,alarm(snoozeUntilMs=today+300000))
        add("snooze exact",today,alarm(snoozeUntilMs=today))
        add("snooze 90sec late",today,alarm(snoozeUntilMs=today-90000))
        add("snooze missed",today,alarm(snoozeUntilMs=today-121000))
        add("weekly arm missing",today,alarm(mode="weekly",armedAtMs=0))
        add("weekly due",today,alarm(mode="weekly"))
        add("weekly missed",today+180000,alarm(mode="weekly"))
        add("weekly already processed",today,alarm(mode="weekly",lastProcessedDueMs=today))
        add("weekly rollback clock",today,alarm(mode="weekly",armedAtMs=today+60000))
        add("ring active once",today,alarm(ringing=True,ringStartedAtMs=today-60000))
        add("ring expires once",today,alarm(ringing=True,ringStartedAtMs=today-900000))
        add("ring expires removed",today,alarm(ringing=True,ringStartedAtMs=today-900000,keepSaved=False))
        add("ring expires weekly",today,alarm(mode="weekly",ringing=True,ringStartedAtMs=today-900000))
        add("ring starts with user sound",today,alarm(soundId="user-"+"a"*64))
        add("bad string name",today,alarm(name="bad\nname"))
        add("invalid volume",today,alarm(volumePercent=200))
        add("invalid bool",today,alarm(enabled=1))
        add("invalid favorite null",today,alarm(favorite=None))
        add("invalid note null",today,alarm(note=None))
        add("missing optional favorite",today,{k:v for k,v in base.items() if k != "favorite"})
        add("missing optional recovery",today,{k:v for k,v in base.items() if k not in ("armedAtMs","lastProcessedDueMs")})
        # After local midnight: Wednesday's late 23:59 alarm still eligible.
        after_midnight=ms(2026,11,19,0,0,40)
        add("weekly midnight grace",after_midnight,
            alarm(mode="weekly",hour=23,minute=59,weekdays=[3]))
        add("weekly missed yesterday",ms(2026,11,19,7,0),
            alarm(mode="weekly",hour=23,minute=59,weekdays=[3]))
        add("one at 23:59 next date",after_midnight,
            alarm(day="2026-11-19",hour=23,minute=59))
        # Real local wall clock transitions on both DST dates.
        add("DST spring after jump",ms(2026,3,8,3,5),
            alarm(day="2026-03-08",hour=3,minute=0,armedAtMs=ms(2026,3,7,7,0)))
        add("DST fall after fold",ms(2026,11,1,2,5),
            alarm(day="2026-11-01",hour=2,minute=0,armedAtMs=ms(2026,10,31,7,0)))
        # Multi-alarm document catches accidental mutation and ordering.
        two=alarm(id=2,name="B",hour=8,minute=0)
        cases.append({"label":"two independent alarms","now_ms":today,
                      "document":doc(base,two)})
        cases.append({"label":"empty file","now_ms":today,
                      "document":doc()})
        return cases

    def test_cross_runtime_js_python_v2_tick_parity(self):
        cases=self.build_cases()
        result=subprocess.run(["node","-e",NODE,str(QML)],
                              input=json.dumps(cases),text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              check=True,env={**os.environ,"TZ":"America/New_York"},
                              timeout=20)
        javascript=json.loads(result.stdout)
        self.assertEqual(len(javascript),len(cases))
        for index,(case,expected) in enumerate(zip(cases,javascript)):
            actual=native.tick(case["document"],case["now_ms"])
            self.assertEqual(actual,expected,
                msg="Clock V2 mismatch: "+case["label"]+
                    " case="+str(index)+" native="+str(actual)+
                    " qml="+str(expected))

    def test_invalid_document_is_not_mutated_or_scheduled(self):
        data=doc(alarm())
        data["version"]=3
        before=json.dumps(data,sort_keys=True)
        result=native.tick(data,ms(2026,11,18,7,30))
        self.assertFalse(result["changed"])
        self.assertEqual(result["started"],[])
        self.assertEqual(json.dumps(data,sort_keys=True),before)

    def test_successive_ticks_never_duplicate_same_occurrence(self):
        first=native.tick(doc(alarm()),ms(2026,11,18,7,30))
        self.assertEqual(first["started"],[1])
        again=native.tick(first["document"],ms(2026,11,18,7,30,5))
        self.assertEqual(again["started"],[])
        self.assertFalse(again["changed"])

    def test_pure_module_cannot_activate_audio_or_open_files(self):
        text=SOURCE.read_text(encoding="utf8")
        self.assertNotIn("subprocess",text)
        self.assertNotIn("os.system",text)
        self.assertNotIn("socket.",text)
        self.assertNotIn("Popen(",text)
        self.assertNotIn("canRing",text)
        self.assertNotIn("canNotify",text)


if __name__ == "__main__":
    unittest.main()
