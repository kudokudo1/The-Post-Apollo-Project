import QtQuick
import QtQuick.Window
import Quickshell
import "components" as Components
import "widgets/weather" as Weather

// Disposable renderer for two real ActionButton spatial rows plus the
// actual HOME top-navigation rail. No Sway, stores or external providers.
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool completed: false
    property int safeCount: 0
    property int unsafeCount: 0
    property int dangerCount: 0
    property string externalRoute: ""
    function fail(reason) {
        if(completed) return;
        completed=true;
        console.error("CONTENT_SPATIAL_NATIVE_FAIL // "+reason);
        Qt.quit();
    }
    Window {
        id: window
        width: 600
        height: 645
        visible: true
        color: "black"

        Item {
            id: testPanel
            width: parent.width
            height: 265
            Components.ActionButton {
                id: first
                x: 16; y: 10; width: 120; height: 45
                label: "SAFE READ"
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.safeCount++
            }
            Components.ActionButton {
                id: second
                x: 170; y: 10; width: 120; height: 45
                label: "SECOND"
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.safeCount++
            }
            Components.ActionButton {
                id: third
                x: 16; y: 115; width: 120; height: 45
                label: "THIRD"
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.safeCount++
            }
            Components.ActionButton {
                id: danger
                x: 170; y: 115; width: 120; height: 45
                label: "DELETE"
                destructive: true
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.dangerCount++
            }
            Components.ActionButton {
                id: notApproved
                x: 16; y: 205; width: 120; height: 40
                label: "SAVE?"
                onLeftClicked: root.unsafeCount++
            }
            Components.WidgetContentKeyboardNavigator {
                id: localKeys
                anchors.fill: parent
                contentRoot: testPanel
                navigationActive: true
            }
        }

        Item {
            id: homePanel
            x: 0; y: testPanel.height+7
            width: parent.width
            height: 355
            Weather.StationHome {
                id: home
                anchors.fill: parent
                subjectRoute: ""
                workspaceSection: "overview"
                runtimeNowMs: 1794397200000
                weatherService: ({
                    latitude:38.9,longitude:-77.03,ready:false,
                    aqiReady:false,hourlyForecast:[]
                })
                spaceService: null
                nwsAlertSource: null
                historyService: null
                liveHistoryStore: null
                homeFavoritesStore: null
                onRouteRequested: function(path) { root.externalRoute=path; }
            }
            Components.WidgetContentKeyboardNavigator {
                id: homeKeys
                anchors.fill: home
                contentRoot: home
                navigationActive: true
            }
        }
    }
    Timer {
        interval: 160
        running: !root.completed
        repeat: true
        onTriggered: {
            if(++root.ticks>65)return root.fail("TIMEOUT");
            if(root.phase===0) {
                if(!localKeys.selectInitial()
                   || localKeys.selectedItem!==first
                   || !localKeys.hasContentSelection
                   || !localKeys.keyboardPrimaryActive
                   || !first.contentKeyboardPrimary
                   || second.contentKeyboardPrimary
                   || first.foregroundColor!==first.keyboardSelectedForegroundColor)
                    return root.fail("NO_VISIBLE_INITIAL_CONTENT_SELECTOR");
                root.phase++;
                return;
            }
            if(root.phase===1) {
                if(!localKeys.handleDirectionKey(Qt.Key_Right,Qt.NoModifier)
                    || localKeys.selectedItem!==second
                    || !second.contentKeyboardPrimary
                    || first.contentKeyboardPrimary)
                    return root.fail("RIGHT_NOT_SPATIAL");
                // Exercise the exact method that the real mouse-position
                // signal calls. This does NOT claim physical pointer delivery.
                if(!localKeys.followPointer(second)
                    || localKeys.keyboardPrimaryActive
                    || second.contentKeyboardPrimary
                    || first.contentKeyboardNavigationActive)
                    return root.fail("POINTER_RECOMBINATION_FAILED");
                root.phase++;
                return;
            }
            if(root.phase===2) {
                if(!localKeys.handleDirectionKey(Qt.Key_J,Qt.NoModifier)
                    || localKeys.selectedItem!==third
                    || !localKeys.keyboardPrimaryActive
                    || !third.contentKeyboardPrimary)
                    return root.fail("J_NOT_DOWN_OR_DANGEROUS_TARGET_REACHED");
                root.phase++;
                return;
            }
            if(root.phase===3) {
                if(!localKeys.activate() || root.safeCount!==1
                    || root.unsafeCount!==0 || root.dangerCount!==0)
                    return root.fail("ENTER_FAILED_SAFE_ACTION");
                root.phase++;
                return;
            }
            if(root.phase===4) {
                if(!localKeys.selectInitial()
                    || !localKeys.handleDirectionKey(Qt.Key_L,Qt.NoModifier)
                    || localKeys.selectedItem!==second
                    || !localKeys.handleDirectionKey(Qt.Key_H,Qt.NoModifier)
                    || localKeys.selectedItem!==first)
                    return root.fail("HJKL_DIRECTION_PARITY");
                localKeys.navigationActive=false;
                if(localKeys.handleDirectionKey(Qt.Key_Down,Qt.NoModifier)
                    || localKeys.hasContentSelection
                    || first.contentKeyboardNavigationActive
                    || second.contentKeyboardPrimary
                    || localKeys.activate())
                    return root.fail("INACTIVE_OWNER_STOLE_INPUT");
                root.phase++;
                return;
            }
            if(root.phase===5) {
                if(!homeKeys.selectInitial())return root.fail("HOME_NO_TARGET");
                const firstTab=home.homeOverviewRailItem.buttonRepeater.itemAt(0);
                if(homeKeys.selectedItem!==firstTab
                    || homeKeys.selectedItem.label!=="LIVE")
                    return root.fail("HOME_FIRST_SELECTION_NOT_LIVE");
                if(!homeKeys.handleDirectionKey(Qt.Key_Right,Qt.NoModifier)
                    || homeKeys.selectedItem.label!=="AUTO")
                    return root.fail("HOME_ARROW_NOT_TO_AUTO");
                root.phase++;
                return;
            }
            if(root.phase===6) {
                if(!homeKeys.activate() || home.homeInlineMode!=="auto"
                    || root.externalRoute!=="")
                    return root.fail("HOME_ENTER_NOT_LOCAL_VIEW_SWITCH");
                root.phase++;
                return;
            }
            if(root.phase===7) {
                homeKeys.reset();
                if(!homeKeys.selectInitial()
                    || !homeKeys.handleDirectionKey(Qt.Key_L,Qt.NoModifier)
                    || !homeKeys.handleDirectionKey(Qt.Key_L,Qt.NoModifier)
                    || homeKeys.selectedItem.label!=="QUICK")
                    return root.fail("HOME_HJKL_QUICK_SELECTION");
                root.phase++;
                return;
            }
            if(root.phase===8) {
                window.contentItem.grabToImage(function(image) {
                    if(!image || !image.saveToFile("/tmp/widget-content-keyboard-native.png"))
                        return root.fail("PREVIEW_MISSING");
                    if(!homeKeys.activate() || home.homeInlineMode!=="quick"
                        || root.externalRoute!=="")
                        return root.fail("HOME_QUICK_ACTIVATION_FAILED");
                    root.completed=true;
                    console.log("CONTENT_SPATIAL_NATIVE_PASS // REAL_HOME_HJKL_ARROW_SELECTOR_SAFE_ENTER");
                    Qt.quit();
                },Qt.size(1200,1290));
                root.phase++;
            }
        }
    }
}
