#!/usr/bin/env python3
"""M22: exercise the ACTUAL quota status pane + service in offscreen Qt.

Creates fake Quickshell QML modules exclusively inside TemporaryDirectory.
The fake Process never executes a command and cannot access host market DB,
credentials, provider network, or the running operator Quickshell. Does not
claim native host acceptance or approval to deploy.
"""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

app = QGuiApplication([])
harness = Path(__file__).resolve().with_name(
    "finance_market_m22_quota_runtime_harness.qml"
)

with tempfile.TemporaryDirectory(prefix="finance-market-m22-qml-") as temp:
    # The ONLY Quickshell module in the test. All process calls are captured
    # in-memory, not forwarded to Python, shell, file system or real Qs.
    stub = Path(temp) / "Quickshell"
    io = stub / "Io"
    io.mkdir(parents=True)
    (stub / "qmldir").write_text(
        "module Quickshell\n"
        "singleton Quickshell 1.0 Quickshell.qml\n"
        "Scope 1.0 Scope.qml\n",
        encoding="utf-8"
    )
    (stub / "Quickshell.qml").write_text(r'''
pragma Singleton
import QtQuick
QtObject {
    property int callCount: 0
    property string lastCommand: ""
    property string nextPayload: ""
    function shellPath(path) { return "/M22-FAKE-NO-DISK/" + path; }
}
''', encoding="utf-8")
    (stub / "Scope.qml").write_text(r'''
import QtQuick
QtObject {
    default property list<QtObject> data
}
''', encoding="utf-8")
    (io / "qmldir").write_text(
        "module Quickshell.Io\n"
        "Process 1.0 Process.qml\n"
        "StdioCollector 1.0 StdioCollector.qml\n",
        encoding="utf-8"
    )
    (io / "StdioCollector.qml").write_text(r'''
import QtQuick
QtObject {
    property string text: ""
    signal streamFinished()
}
''', encoding="utf-8")
    (io / "Process.qml").write_text(r'''
import QtQuick
import Quickshell
QtObject {
    id: fakeProcess
    property bool running: false
    property QtObject stdout: null
    signal exited(int exitCode, int exitStatus)
    function exec(argv) {
        if (!Array.isArray(argv) || argv.length!==4
            || argv[0]!=="/usr/bin/env"
            || argv[1]!=="python3"
            || argv[2]!==Quickshell.shellPath(
                "scripts/finance/market_quota_status.py")
            || argv[3]!=="status")
            throw new Error("M22 blocked unexpected command");
        Quickshell.callCount += 1;
        Quickshell.lastCommand=JSON.stringify(argv);
        running=true;
        Qt.callLater(function() {
            if (!stdout) throw new Error("M22 fake stream not connected");
            stdout.text=Quickshell.nextPayload;
            stdout.streamFinished();
            running=false;
            exited(0,0);
        });
    }
}
''', encoding="utf-8")

    engine = QQmlEngine()
    engine.addImportPath(temp)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(harness)))
    if component.isError():
        raise RuntimeError("QML load: " +
                           "; ".join(map(str, component.errors())))
    root = component.create()
    if root is None:
        raise RuntimeError("QML create: " +
                           "; ".join(map(str, component.errors())))

    def pump():
        for _ in range(10):
            app.processEvents()

    def invoke(obj, name):
        assert QMetaObject.invokeMethod(obj, name), (
            f"QML callback missing: {name}"
        )
        pump()

    def prop(obj, name):
        pump()
        return obj.property(name)

    def setprop(obj, name, value):
        assert obj.setProperty(name, value), (
            f"Cannot set QML property: {name}"
        )
        pump()

    try:
        pane = root.findChild(QObject, "marketQuotaRealPane")
        service = root.findChild(QObject, "marketQuotaReaderService")
        refresh = root.findChild(QObject, "marketQuotaRefreshButton")
        back = root.findChild(QObject, "marketQuotaBackButton")
        assert all((pane,service,refresh,back)), (
            "Actual pane/service/ActionButtons were not instantiated"
        )

        def labels():
            return [str(x.property("text")) for x in
                    root.findChildren(QObject, "marketQuotaReservedLabel")]

        def counts():
            return int(prop(root, "fakeProcessCalls"))

        def check_command():
            command=str(prop(root, "fakeLastCommand"))
            assert command.startswith('["/usr/bin/env","python3",'),command
            assert "M22-FAKE-NO-DISK" in command,command
            assert command.endswith(',"status"]'),command
            assert "read_global_eodhd_history" not in command
            assert "read_alpha_vantage_free" not in command
            assert "reserve" not in command

        # The real pane remains inactive until the operator opens it.
        assert counts() == 0
        assert prop(service,"state") == "idle"
        invoke(root,"stageReady")
        setprop(pane,"active",True)
        assert counts() == 1
        check_command()
        assert prop(service,"state") == "ready"
        assert "LOCAL RESERVED 3 / 20" in labels(),labels()
        assert "LOCAL RESERVED 9 / 25" in labels(),labels()
        assert prop(refresh,"available") is True

        # No automatic polling. Neither a fresh UI render nor resizing
        # should spend another operation.
        setprop(root,"width",360)
        setprop(root,"height",720)
        assert len(labels()) == 2,labels()
        assert counts() == 1
        assert prop(pane,"width") == prop(root,"width")
        setprop(root,"width",660)
        assert counts() == 1

        # Click real refresh signal; it may only invoke the mocked local
        # read transport, never spawn a process or touch M20 quotas.
        invoke(root,"stageFull")
        invoke(refresh,"leftClicked")
        assert counts() == 2
        assert "LOCAL RESERVED 20 / 20" in labels(),labels()
        assert "LOCAL RESERVED 25 / 25" in labels(),labels()

        # No ledger: UNKNOWN rather than pretending both providers are zero.
        invoke(root,"stageAbsent")
        invoke(service,"refresh")
        assert counts() == 3
        assert prop(service,"state") == "absent"
        assert labels().count("LOCAL RESERVED UNKNOWN") == 2,labels()

        # A busy ledger and invalid payload must also never show fake zero.
        invoke(root,"stageBusy")
        invoke(service,"refresh")
        assert prop(service,"state") == "unavailable"
        assert labels().count("LOCAL RESERVED UNKNOWN") == 2
        invoke(root,"stageCorrupt")
        invoke(service,"refresh")
        assert prop(service,"state") == "unavailable"
        assert labels().count("LOCAL RESERVED UNKNOWN") == 2
        invoke(root,"stageInvalidCount")
        invoke(service,"refresh")
        assert prop(service,"state") == "unavailable"
        assert labels().count("LOCAL RESERVED UNKNOWN") == 2
        invoke(root,"stageError")
        invoke(service,"refresh")
        assert prop(service,"state") == "unavailable"
        assert labels().count("LOCAL RESERVED UNKNOWN") == 2

        # Close/open actual control. Close discards stale pane snapshot;
        # the next open issues exactly one new LOCAL mock read.
        total=counts()
        setprop(pane,"active",False)
        assert prop(service,"state") == "idle"
        assert prop(service,"snapshot") is None
        assert counts() == total
        invoke(root,"stageReady")
        setprop(pane,"active",True)
        assert counts() == total+1
        assert prop(service,"state") == "ready"

        # Verify real BACK ActionButton reaches the owning screen signal.
        invoke(back,"leftClicked")
        assert prop(root,"backEmitted") is True

        print("Finance M22 actual quota-pane Qt offscreen open/refresh/"
              "compact/unknown/back with inert no-network Quickshell: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        pump()
