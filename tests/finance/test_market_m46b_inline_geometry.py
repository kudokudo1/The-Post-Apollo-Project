"""Offscreen Qt geometry of the actual inline Market panes, with inert process stubs."""
import os
import shutil
import tempfile
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QML_DISABLE_DISK_CACHE"]="1"
from PySide6.QtCore import QObject, QUrl
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
    put("Quickshell/Quickshell.qml","pragma Singleton\nimport QtQuick\nQtObject { function shellPath(path) { return '/no-exec/'+path } }")
    put("Quickshell/Scope.qml","import QtQuick\nQtObject { default property list<QtObject> data }")
    put("Quickshell/Io/qmldir","module Quickshell.Io\nProcess 1.0 Process.qml\nStdioCollector 1.0 StdioCollector.qml\n")
    put("Quickshell/Io/Process.qml","import QtQuick\nQtObject { property bool running: false; property QtObject stdout; signal exited(int exitCode,int exitStatus); function exec(argv) { throw Error('network/process forbidden in geometry test') } }")
    put("Quickshell/Io/StdioCollector.qml","import QtQuick\nQtObject { property string text; signal streamFinished() }")
    put("widgets/Probe.qml","""import QtQuick
import QtQuick.Window
Window {
    width: 620; height: 480; visible: true
    QtObject { id: monitor; property bool monitoring: true }
    FinanceStockHistoryPane { objectName: "stocksProbe"; anchors.fill: parent; stockFeed: monitor }
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
    # Selecting a provider makes its section occupy real layout height.
    assert controls.setProperty("priceOptionsOpen", True)
    QTest.qWait(80)
    app.processEvents()
    eod=item("marketInlineEodhdControls")
    assert eod.isVisible() and eod.height()>0
    assert controls.height()>=eod.y()+eod.height()
    assert eod.setProperty("alphaOpen", True)
    QTest.qWait(80)
    app.processEvents()
    alpha=item("marketInlineAlphaControls")
    assert alpha.isVisible() and alpha.height()>0
    assert eod.height()>=alpha.y()+alpha.height()
    assert selection.y()>=controls.y()+controls.height()
    assert stocks.setProperty("discoveryOpen",False)
    QTest.qWait(80)
    app.processEvents()
    assert not controls.isVisible() and controls.height()==0
    assert top.isVisible() and bottom.isVisible()
    root.close()
    root.deleteLater()
    app.processEvents()
print("M46b actual Qt inline stock/provider geometry (inert services/processes): PASS")
