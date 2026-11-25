"""Offscreen Qt geometry of the actual inline Market panes, with inert process stubs."""
import os
import json
import shutil
import tempfile
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QML_DISABLE_DISK_CACHE"]="1"
from PySide6.QtCore import QObject, QUrl, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

ROOT=Path(__file__).resolve().parents[2]
app=QGuiApplication([])
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)
    def put(name, data):
        path=p/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(data)
    # Isolate actual Market QML from the live Quickshell environment.
    for name in ["FinanceStockHistoryPane.qml","FinanceStockDiscoveryPane.qml","FinanceGlobalPricePane.qml","FinanceAlphaVantageFreePane.qml","FinanceStockModePolicy.js","FinanceStockChartPointPolicy.js","FinanceStockRangeAnalysisPolicy.js","FinanceMarketDateControls.qml","FinanceDateInput.qml","tasks/TaskDateSegment.qml"]:
        path=p/"widgets"/name
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/"widgets"/name,path)
    for name in ["FinanceStockDiscoveryService.qml","FinanceGlobalPriceService.qml","FinanceAlphaVantageFreeService.qml","FinanceInputPolicy.js"]:
        path=p/"services"/"finance"/name
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/"services"/"finance"/name,path)
    put("widgets/FinanceMarketQuotaStatusPane.qml", "import QtQuick\nItem { property bool active: false; signal exitRequested() }")
    put("components/qmldir", "singleton Colors 1.0 Colors.qml\nGohuText 1.0 GohuText.qml\nActionButton 1.0 ActionButton.qml\nNeonScrollBar 1.0 NeonScrollBar.qml\n")
    for name in ["Colors.qml","GohuText.qml"]:
        shutil.copyfile(ROOT/"components"/name,p/"components"/name)
    put("components/ActionButton.qml", """import QtQuick
Item { property string label; property int labelPixelSize; property color accentColor; property bool selected; property bool available: true; signal leftClicked() }""")
    put("components/NeonScrollBar.qml", """import QtQuick
Item { property var flickable; property Item mountingParent; property string geometryMode; property string handleStyle; property int rightInset }""")
    put("Quickshell/qmldir","module Quickshell\nsingleton Quickshell 1.0 Quickshell.qml\nScope 1.0 Scope.qml\n")
    put("Quickshell/Quickshell.qml","pragma Singleton\nimport QtQuick\nQtObject { property int callCount: 0; function shellPath(path) { return '/no-exec/'+path } }")
    put("Quickshell/Scope.qml","import QtQuick\nQtObject { default property list<QtObject> data }")
    put("Quickshell/Io/qmldir","module Quickshell.Io\nProcess 1.0 Process.qml\nStdioCollector 1.0 StdioCollector.qml\n")
    put("Quickshell/Io/Process.qml","import QtQuick\nimport Quickshell\nQtObject { property bool running: false; property QtObject stdout; signal exited(int exitCode,int exitStatus); function exec(argv) { Quickshell.callCount++; throw Error('network/process forbidden in geometry test') } }")
    put("Quickshell/Io/StdioCollector.qml","import QtQuick\nQtObject { property string text; signal streamFinished() }")
    put("widgets/Probe.qml","""import QtQuick
import QtQuick.Window
import Quickshell
Window {
    readonly property int requestCount: Quickshell.callCount
    width: 620; height: 480; visible: true
    QtObject { id: monitor; objectName: "stocksMonitor"; property bool monitoring: true }
    FinanceStockHistoryPane { objectName: "stocksProbe"; anchors.fill: parent; sessionEnabled: monitor.monitoring }
}""")
    engine=QQmlEngine()
    engine.addImportPath(str(p))
    component=QQmlComponent(engine,QUrl.fromLocalFile(str(p/"widgets"/"Probe.qml")))
    assert component.isReady(), "\n".join(x.toString() for x in component.errors())
    root=component.create()
    assert root is not None, "\n".join(x.toString() for x in component.errors())
    QTest.qWait(80)
    app.processEvents()
    def item(name):
        found=root.findChild(QQuickItem,name)
        assert found is not None,name
        return found
    stocks=item("stocksProbe")
    controls=item("marketInlineStockControls")
    selection=item("marketCompactSelection")
    top=item("marketStockCommandRail")
    bottom=item("marketDayRangeRail")
    assert controls.parentItem()==selection.parentItem()
    assert controls.isVisible() and controls.height()>0
    assert selection.y()>=controls.y()+controls.height(), (selection.y(),controls.height())
    assert top.isVisible() and bottom.isVisible()
    def obj(name):
        found=root.findChild(QObject,name)
        assert found is not None,name
        return found
    def settle():
        QTest.qWait(80)
        app.processEvents()
    def assign(target,name,value):
        assert target.setProperty(name,engine.evaluate("("+json.dumps(value)+")")),name
    def val(target,name):
        v=target.property(name)
        return v.toVariant() if hasattr(v,"toVariant") else v
    def seed(feed,listing):
        assign(feed,"identity",{"figi":"BBG000000001","ticker":"ASML","name":"ASML","exchCode":"NA"})
        assign(feed,"candidates",[listing])
        assign(feed,"selectedListing",listing)
        assert feed.setProperty("startDate","2026-11-03")
        assert feed.setProperty("endDate","2026-11-03")
        assert feed.setProperty("presetDays",0)
        assert feed.setProperty("state","selected")
    # Selecting a provider makes its section occupy real layout height.
    assert controls.setProperty("priceOptionsOpen", True)
    QTest.qWait(80)
    app.processEvents()
    eod=item("marketInlineEodhdControls")
    assert eod.isVisible() and eod.height()>0
    assert controls.height()>=eod.y()+eod.height()
    finder=obj("marketDiscoveryReader")
    eodReader=obj("marketEodhdReader")
    query=item("marketStockQueryInput")
    assert query.setProperty("text","ASML")
    assert finder.setProperty("requestedQuery","ASML")
    seed(eodReader,{"symbol":"ASML.AS","code":"ASML","exchange":"AS","name":"ASML","currency":"EUR"})
    eodDates=item("marketEodhdDates")
    assert eodDates.setProperty("singleDay",True)
    settle()
    assert stocks.setProperty("discoveryOpen",False)
    settle()
    assert not controls.property("active") and controls.property("sessionActive")
    assert not controls.isVisible() and controls.height()==0
    assert finder.property("monitoring") and eodReader.property("monitoring")
    assert val(eodReader,"selectedListing")["symbol"]=="ASML.AS"
    assert eodReader.property("startDate")=="2026-11-03"
    assert eodDates.property("singleDay")
    assert controls.property("priceOptionsOpen")
    # A hidden search handler must not dispatch a request or discard selection.
    assert QMetaObject.invokeMethod(controls,"searchNow")
    assert finder.property("requestedQuery")=="ASML"
    assert stocks.setProperty("discoveryOpen",True)
    settle()
    assert controls.property("active") and eod.property("active")
    assert query.property("text")=="ASML"
    assert val(eodReader,"selectedListing")["currency"]=="EUR"
    assert eodDates.property("singleDay")
    assert eod.setProperty("alphaOpen", True)
    QTest.qWait(80)
    app.processEvents()
    alpha=item("marketInlineAlphaControls")
    assert alpha.isVisible() and alpha.height()>0
    assert eod.height()>=alpha.y()+alpha.height()
    assert selection.y()>=controls.y()+controls.height()
    alphaReader=obj("marketAlphaReader")
    seed(alphaReader,{"symbol":"ASML.AMS","name":"ASML","region":"Netherlands","currency":"EUR"})
    alphaDates=item("marketAlphaDates")
    assert alphaDates.setProperty("singleDay",True)
    settle()
    assert stocks.setProperty("discoveryOpen",False)
    settle()
    assert not controls.isVisible() and controls.height()==0
    assert not alpha.property("active") and alphaReader.property("monitoring")
    assert eod.property("alphaOpen") and controls.property("priceOptionsOpen")
    assert val(alphaReader,"selectedListing")["symbol"]=="ASML.AMS"
    assert alphaDates.property("singleDay")
    assert stocks.setProperty("discoveryOpen",True)
    settle()
    assert alpha.property("active") and alphaDates.property("singleDay")
    assert val(alphaReader,"selectedListing")["symbol"]=="ASML.AMS"
    # Real monitoring loss still clears provider and discovery custody.
    assert obj("stocksMonitor").setProperty("monitoring",False)
    settle()
    assert not finder.property("monitoring") and not alphaReader.property("monitoring")
    assert not eodReader.property("monitoring")
    assert not controls.property("priceOptionsOpen") and not eod.property("alphaOpen")
    assert val(alphaReader,"selectedListing") is None and val(eodReader,"selectedListing") is None
    assert not alphaDates.property("singleDay") and not eodDates.property("singleDay")
    assert top.isVisible() and bottom.isVisible()
    assert root.property("requestCount")==0
    root.close()
    root.deleteLater()
    app.processEvents()
print("M46b/c2 actual Qt inline geometry and provider selection continuity (inert processes): PASS")
