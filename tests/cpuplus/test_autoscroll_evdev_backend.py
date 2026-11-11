"""Experimental backend safety: no root, no keyboard, fake uinput smoke."""
from pathlib import Path
import json
import os
import stat
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"services/input"))
import AutoscrollEvdevBackend as backend


class BackendRules(unittest.TestCase):
    def test_kernel_mouse_only_whitelist(self):
        keys, rels=backend.validate_mouse({
            1:[272,273,274,275],2:[0,1,8,6]})
        self.assertIn(274,keys)
        self.assertIn(11,rels)
        self.assertIn(12,rels)
        with self.assertRaisesRegex(backend.DriverError,"NOT_MOUSE_ONLY"):
            backend.validate_mouse({1:[272,273,274,30],2:[0,1]})
        with self.assertRaisesRegex(backend.DriverError,"NOT_MOUSE_ONLY"):
            backend.validate_mouse({1:[272,273,274],2:[0,1],3:[0]})
        with self.assertRaisesRegex(backend.DriverError,"NOT_MOUSE_ONLY"):
            backend.validate_mouse({1:[272,273,274],2:[0]})
        with self.assertRaisesRegex(backend.DriverError,"NOT_MOUSE_ONLY"):
            backend.validate_mouse({1:[272,273,274],2:[0,1,255]})

    def test_device_must_be_actual_physical_char_event(self):
        with self.assertRaisesRegex(backend.DriverError,"DEVICE_PATH_REQUIRED"):
            backend.select_physical_device("/tmp/mouse")
        with patch.object(Path,"resolve",return_value=Path("/dev/input/event3")),patch.object(
                Path,"stat",return_value=SimpleNamespace(st_mode=stat.S_IFREG)):
            with self.assertRaisesRegex(backend.DriverError,
                                        "NOT_A_PHYSICAL_EVENT_DEVICE"):
                backend.select_physical_device("/dev/input/by-id/usb-mouse")
        with patch.object(Path,"resolve",return_value=Path("/dev/keyboard/event3")),patch.object(
                Path,"stat",return_value=SimpleNamespace(st_mode=stat.S_IFCHR)):
            with self.assertRaisesRegex(backend.DriverError,
                                        "NOT_A_PHYSICAL_EVENT_DEVICE"):
                backend.select_physical_device("/dev/input/event3")

    def test_default_and_misconfigured_live_start_are_refused(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(backend.DriverError,
                                        "EXPERIMENTAL_NONROOT_OPTIN_REQUIRED"):
                backend.run_live("/dev/input/event0")
        self.assertEqual(backend.main(["--live"]),2)
        self.assertEqual(backend.main([]),2)

    def test_probe_never_opens_device_or_changes_permissions(self):
        with patch.object(backend,"no_native_lock",return_value=True),patch.object(
                backend.importlib.util,"find_spec",return_value=None):
            result=backend.probe()
        self.assertEqual(result["status"],"unavailable")
        self.assertFalse(result["enabled"])
        self.assertFalse(result["permission_changes"])
        self.assertFalse(result["global_overlay"])
        self.assertFalse(result["escape_binding"])
        self.assertFalse(result["hardware_verified"])

    def test_sway_focus_only_one_real_seat(self):
        with patch.object(backend.subprocess,"run",return_value=SimpleNamespace(
                returncode=0,stdout=json.dumps([{"name":"seat0","focus":42}]))):
            self.assertEqual(backend.sway_focus(),"seat0:42")
        for reply in ('[]','[{"name":"seat0","focus":0}]',
                      '[{"name":"seat0","focus":1},{"name":"seat1","focus":2}]'):
            with patch.object(backend.subprocess,"run",return_value=SimpleNamespace(
                    returncode=0,stdout=reply)):
                self.assertIsNone(backend.sway_focus())

    def test_source_does_not_install_privileged_service(self):
        text=(ROOT/"services/input/AutoscrollEvdevBackend.py").read_text()
        for forbidden in ("sudo ", "pkexec", "chmod 666", "usermod ",
                          "systemctl enable", "os.system", "shell=True",
                          "pynput", "keyboard.read", "EVIOCGRAB"):
            self.assertNotIn(forbidden,text)
        self.assertIn("source.ungrab()",text)
        self.assertIn("virtual.close()",text)


class FakeLinuxIntegration(unittest.TestCase):
    def test_live_driver_fake_mouse_continuous_wheel_and_cleanup(self):
        events=[
            [SimpleNamespace(type=1,code=274,value=1),
             SimpleNamespace(type=0,code=0,value=0)],
            [SimpleNamespace(type=2,code=1,value=220),
             SimpleNamespace(type=0,code=0,value=0)],
        ]
        outputs=[]
        device=SimpleNamespace(name="USB Mouse",fd=47,
            info=SimpleNamespace(vendor=0x4321,product=0x1234,bustype=3),
            grabbed=False,closed=False)
        def cap(absinfo=False):return {1:[272,273,274],2:[0,1,8]}
        def grab():device.grabbed=True
        def ungrab():device.grabbed=False
        def close():device.closed=True
        def read():return events.pop(0)
        device.capabilities=cap
        device.grab=grab
        device.ungrab=ungrab
        device.close=close
        device.read=read
        def InputDevice(path):return device
        class FakeUInput:
            def __init__(self,caps,**kwargs):
                self.closed=False
                self.caps=caps
                outputs.append(self)
            def write(self,typ,code,value):
                outputs.append((typ,code,value))
            def syn(self):outputs.append(("syn",))
            def close(self):self.closed=True
        ecodes=SimpleNamespace(EV_SYN=0,EV_KEY=1,EV_REL=2)
        module=ModuleType("evdev")
        module.InputDevice=InputDevice
        module.UInput=FakeUInput
        module.ecodes=ecodes
        callbacks={}
        def install_signal(signal_code,callback):callbacks[signal_code]=callback
        poll_count=[0]
        def select_ready(read_fds,write_fds,error_fds,timeout):
            poll_count[0]+=1
            if poll_count[0]>8:
                callbacks[backend.signal.SIGTERM](backend.signal.SIGTERM,None)
            return ([device.fd] if events else [],[],[])
        clock=[0.0]
        def monotonic():
            clock[0]+=0.015
            return clock[0]
        with patch.dict(sys.modules,{"evdev":module}),patch.dict(os.environ,{
                backend.RUN_MARKER:"1","SWAYSOCK":"/fake/sway"},clear=True),patch.object(
                backend.os,"getuid",return_value=1000),patch.object(
                backend,"no_native_lock",return_value=True),patch.object(
                backend,"sway_focus",return_value="seat0:42"),patch.object(
                backend,"select_physical_device",return_value=Path("/dev/input/event3")),patch.object(
                backend,"import_evdev",return_value=module),patch.object(
                backend.select,"select",side_effect=select_ready),patch.object(
                backend.time,"monotonic",side_effect=monotonic),patch.object(
                backend.signal,"signal",side_effect=install_signal):
            self.assertEqual(backend.run_live("/dev/input/by-id/mockmouse"),0)
        self.assertTrue(device.closed)
        self.assertFalse(device.grabbed)
        self.assertTrue(outputs[0].closed)
        self.assertTrue(any(isinstance(x,tuple) and len(x)==3
                            and x[1]==backend.REL_WHEEL_HI_RES and x[2]<0
                            for x in outputs))
        self.assertFalse(any(isinstance(x,tuple) and len(x)==3
                             and x[1]==backend.REL_Y and x[2]==220
                             for x in outputs))


if __name__=="__main__":
    unittest.main()
