import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// W7 native smoke: MAGICK SERVICES with absent providers and one compact
// HOME health card. Synthetic/unavailable state only, no source fetching.
ShellRoot {
    id: root
    property int ticks: 0
    property bool done: false
    function fail(reason) {
        if(done)return;
        done=true;
        console.error("W7_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 520
        height: 300
        visible: true
        color: "black"
        Weather.StationMagickSubjectPane {
            id: magickPage
            anchors.fill: parent
            subjectRoute: "magick/services/health"
            weatherService: null
            celestialSource: null
            runtimeNowMs: 0
        }
        Weather.StationHomeMetricCard {
            id: testCard
            x: 4
            y: 248
            width: 152
            height: 48
            visible: true
            compact: true
            servicesCompact: true
            title: "WEATHER"
            valueText: "SOURCE READY"
            detailText: "PROVIDER HEALTH DATA"
            footerText: "LAST SUCCESS // 08:07"
        }
    }
    Timer {
        interval: 200
        repeat: true
        running: !root.done
        onTriggered: {
            root.ticks++;
            if(root.ticks>22)return root.fail("TIMEOUT");
            if(!magickPage.servicesRoute || !magickPage.servicesView)
                return root.fail("MAGICK_SERVICES_ROUTE");
            const view=magickPage.servicesView;
            const dashboard=view.dashboard;
            if(!dashboard || !dashboard.headerItem || !dashboard.metricsItem
               || !dashboard.detailItem || !dashboard.reportItem)
                return root.fail("MAGICK_DASHBOARD_NOT_MOUNTED");
            if(view.directoryRows.length!==18 || view.summaryCards.length!==6)
                return root.fail("MAGICK_SOURCE_INVENTORY_COUNT");
            if(dashboard.detailItem.contentHeight<=dashboard.detailItem.height)
                return root.fail("MAGICK_DOSSIER_NOT_SCROLLABLE");
            if(dashboard.metricsItem.height!==65)
                return root.fail("MAGICK_COMPACT_CARDS_GEOMETRY");
            if(dashboard.primaryStripLabel.indexOf("LIVE FEED")>=0)
                return root.fail("MAGICK_FALSIFIED_LIVE");
            if(!testCard.compactFooterItem || !testCard.compactBodyItem)
                return root.fail("HOME_COMPACT_FOOTER_MISSING");
            const footer=testCard.compactFooterItem;
            const footerBottom=footer.mapToItem(testCard,0,footer.height).y;
            if(footerBottom > testCard.height-1 || footerBottom<0)
                return root.fail("HOME_FOOTER_OVERFLOW // "+footerBottom);
            if(testCard.compactBodyItem.height!==testCard.height-6)
                return root.fail("HOME_CARD_LAYOUT_BOUNDS");
            root.done=true;
            console.log("W7_NATIVE_PASS // MAGICK_SERVICE_INVENTORY_AND_HOME_FOOTER_520X300");
            Qt.quit();
        }
    }
}
