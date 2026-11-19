"""BG2 real native fixture schedule/save/delivery outbox tests.

An actual old writer subprocess exits before the native fixture is allowed
to atomically update a disposable QML-compatible V2 alarm file. Never plays
sound, notifies a user, or changes a mounted Quickshell instance.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    item=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=item
    spec.loader.exec_module(item)
    return item


Fixture=load(ROOT/"tests/time/test_clock_bg1_native_cutover_controller.py",
             "clock_bg2_native_cutover_harness")
Parity=load(ROOT/"tests/time/test_clock_bg2_native_tick_parity.py",
            "clock_bg2_native_tick_harness")
Engine=load(ROOT/"services/time/AlarmNativeFixtureEngine.py",
            "clock_bg2_actual_native_fixture")


class NativeFixtureEngineTests(unittest.TestCase):
    def setUp(self):
        self.h=Fixture.NativeCutoverRealKernelTests(
            methodName="test_real_kernel_writer_exit_and_final_fsync_to_fixture_selection")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.base=Parity.doc(Parity.alarm())
        self.h.raw=(json.dumps(self.base,indent=2,ensure_ascii=False)+"\n").encode()
        self.h.source.write_bytes(self.h.raw)
        self.h.source.chmod(0o600)
        self.h.digest=hashlib.sha256(self.h.raw).hexdigest()

    def selected(self):
        self.h.launch()
        c=self.h.controller_for_old()
        c.request_shutdown()
        self.h.exit_writer()
        c.witness_exit()
        c.witness_final_sync()
        c.select_fixture_native()
        return c

    def reject(self,callback,reason):
        with self.assertRaises(Engine.Refused) as thrown:
            callback()
        self.assertEqual(str(thrown.exception),reason)

    def test_real_native_fixture_v2_ring_file_write_and_one_delivery(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        now=Parity.ms(2026,11,18,7,30)
        result=engine.step(now)
        self.assertEqual(result["phase"],"SAVED")
        self.assertEqual(result["started"],[1])
        self.assertFalse(result["canRing"])
        self.assertFalse(result["canNotify"])
        saved=json.loads(self.h.source.read_text())
        self.assertTrue(saved["alarms"][0]["ringing"])
        self.assertEqual(saved["alarms"][0]["ringStartedAtMs"],now)
        self.assertEqual(saved["alarms"][0]["lastEventKind"],"fired")
        self.assertEqual(stat.S_IMODE(self.h.source.stat().st_mode),0o600)
        callbacks=[]
        delivered=engine.deliver(callbacks.append)
        self.assertEqual(delivered["phase"],"DELIVERED")
        self.assertEqual(len(callbacks),1)
        self.assertEqual(callbacks[0]["started"],[1])
        self.assertEqual(callbacks[0]["missed"],[])
        self.assertNotIn("PRIVATE",json.dumps(callbacks))
        same=engine.step(now+1000)
        self.assertEqual(same["phase"],"UNCHANGED")
        self.assertEqual(len(callbacks),1)

    def test_missed_alarm_is_persisted_and_does_not_fake_sound(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        report=engine.step(Parity.ms(2026,11,18,7,33))
        self.assertEqual(report["started"],[])
        self.assertEqual(report["missed"],[1])
        data=json.loads(self.h.source.read_text())["alarms"][0]
        self.assertFalse(data["ringing"])
        self.assertEqual(data["lastEventKind"],"missed")
        result=[]
        engine.deliver(result.append)
        self.assertEqual(result[0]["started"],[])
        self.assertEqual(result[0]["missed"],[1])

    def test_no_native_step_before_old_writer_exit_and_cutover_selection(self):
        self.h.launch()
        c=self.h.controller_for_old()
        c.request_shutdown()
        self.reject(lambda:Engine.ClockFixtureNativeEngine(
            controller=c,synthetic_only=True),
            "SYNTHETIC_NATIVE_HANDOFF_REQUIRED")
        self.h.exit_writer()
        c.witness_exit()
        self.reject(lambda:Engine.ClockFixtureNativeEngine(
            controller=c,synthetic_only=True),
            "SYNTHETIC_NATIVE_HANDOFF_REQUIRED")

    def test_real_production_engine_constructor_is_unavailable(self):
        self.reject(lambda:Engine.ClockFixtureNativeEngine(
            controller=None,synthetic_only=False),
            "PRODUCTION_BG2_NOT_INSTALLED")

    def test_refuse_out_of_band_source_mutation_before_tick(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        self.h.source.write_bytes(self.h.raw+b" ")
        self.h.source.chmod(0o600)
        self.reject(lambda:engine.step(Parity.ms(2026,11,18,7,30)),
                    "BG2_SOURCE_CHANGED_OUTSIDE_OWNER")

    def test_altered_source_after_saved_step_blocks_delivery(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        engine.step(Parity.ms(2026,11,18,7,30))
        self.h.source.write_bytes(self.h.raw)
        self.h.source.chmod(0o600)
        sent=[]
        self.reject(lambda:engine.deliver(sent.append),
                    "BG2_SOURCE_CHANGED_OUTSIDE_OWNER")
        self.assertEqual(sent,[])

    def test_link_swap_refused_before_native_step(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        backup=self.h.source.with_name("backup.json")
        self.h.source.rename(backup)
        self.h.source.symlink_to(backup)
        self.reject(lambda:engine.step(Parity.ms(2026,11,18,7,30)),
                    "BG2_SOURCE_READ_REFUSED")

    def test_delivery_callback_crash_leaves_uncertain_and_no_retry(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        engine.step(Parity.ms(2026,11,18,7,30))
        invoked=[]
        def crash(event):
            invoked.append(event)
            raise RuntimeError("synthetic delivery connection fell")
        with self.assertRaisesRegex(RuntimeError,"synthetic delivery"):
            engine.deliver(crash)
        self.assertEqual(len(invoked),1)
        self.reject(lambda:engine.deliver(invoked.append),
                    "BG2_NO_SAVED_OCCURRENCE_TO_EMIT")
        self.reject(engine.reconcile,"BG2_DELIVERY_OUTCOME_UNCERTAIN")
        self.reject(lambda:engine.step(Parity.ms(2026,11,18,7,31)),
                    "BG2_PENDING_OR_UNCERTAIN_DELIVERY")

    def test_prepared_before_atomic_write_is_crash_hold_not_auto_retry(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        event=json.dumps({"started":[1],"missed":[],"expired":[]})
        engine.db.execute(
            "INSERT INTO native_tick_outbox"
            "(phase,before_digest,after_digest,now_ms,events)"
            "VALUES('PREPARED',?,?,?,?)",
            (engine.digest,"f"*64,Parity.ms(2026,11,18,7,30),event))
        self.reject(engine.reconcile,"BG2_PREPARED_WRITE_UNCERTAIN")
        self.reject(lambda:engine.step(Parity.ms(2026,11,18,7,30)),
                    "BG2_PENDING_OR_UNCERTAIN_DELIVERY")

    def test_prepared_after_atomic_replace_recovers_saved_outbox(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        now=Parity.ms(2026,11,18,7,30)
        result=Engine.Policy.tick(self.base,now)
        updated=(json.dumps(result["document"],indent=2,
                            ensure_ascii=False)+"\n").encode()
        after=hashlib.sha256(updated).hexdigest()
        event=json.dumps({"started":[1],"missed":[],"expired":[]})
        engine.db.execute(
            "INSERT INTO native_tick_outbox"
            "(phase,before_digest,after_digest,now_ms,events)"
            "VALUES('PREPARED',?,?,?,?)",
            (engine.digest,after,now,event))
        # This recreates the exact state after rename + fsync but before
        # the database phase commit.
        engine._write_atomic(engine.digest,updated)
        self.assertEqual(engine.reconcile(),"SAVED")
        observed=[]
        engine.deliver(observed.append)
        self.assertEqual(observed[0]["started"],[1])
        self.assertEqual(engine.reconcile(),"DELIVERED")

    def test_controller_close_forbids_subsequent_native_timing(self):
        controller=self.selected()
        engine=Engine.ClockFixtureNativeEngine(
            controller=controller,synthetic_only=True)
        controller.close()
        self.reject(lambda:engine.step(Parity.ms(2026,11,18,7,30)),
                    "SYNTHETIC_NATIVE_HANDOFF_REQUIRED")

    def test_background_loop_after_real_writer_exit_and_no_duplicate_ring(self):
        engine=Engine.ClockFixtureNativeEngine(
            controller=self.selected(),synthetic_only=True)
        times=[Parity.ms(2026,11,18,7,30),
               Parity.ms(2026,11,18,7,30,1)]
        calls=[]
        def now():
            return times.pop(0)
        count=engine.run_fixture_loop(
            get_now_ms=now,should_stop=lambda:len(times)==0,
            deliver=calls.append,interval_seconds=0.001,limit=4)
        self.assertEqual(count,2)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]["started"],[1])

    def test_native_engine_never_activates_real_sound_or_notification(self):
        source=(ROOT/"services/time/AlarmNativeFixtureEngine.py").read_text()
        for forbidden in ("paplay", "pw-play", "notify-send", "QML IPC",
                          "AudioOutput","canRing\":True","canNotify\":True"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
