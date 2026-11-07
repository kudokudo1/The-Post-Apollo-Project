import QtQuick
import QtQuick.Window
import Quickshell
import qs.services.location
import "widgets/weather"

// Isolated native test of actual MAGICK QML date, location and transit panes.
// No PanelWindow, no real compositor, no JPL calls, no user's HOME.
ShellRoot {
    id: root
    property bool complete: false
    property string stage: "BOOT"

    Window {
        id: testSurface
        visible: true
        width: 650
        height: 550
    StationMagickUtcDateField {
        id: dateField
        width: 360
        dateValue: "2024-02-29"
        onDateEdited: function(date) { dateField.dateValue = date; }
    }
    StationMagickEventChartSetupPane {
        id: natalForm
        width: 450
        height: 360
        visible: false
    }
    StationMagickTransitChartPane {
        id: transitForm
        width: 450
        height: 360
        visible: false
    }
    }
    function fail(code) {
        if(complete)return;
        complete=true;
        console.error("M8E_NATIVE_FAIL // "+stage+" // "+code);
        Qt.quit();
    }
    function check(cond,code) {
        if(!cond)fail(code);
        return cond;
    }
    Timer {
        interval: 250
        repeat: false
        running: true
        onTriggered: {
            root.stage="TASKS_STEPPER";
            dateField.stepPart("year",1);
            if(!root.check(dateField.dateValue==="2025-02-28",
                "LEAP_YEAR_STEP_INCORRECT"))return;
            dateField.editPart("month","03");
            if(!root.check(dateField.dateValue==="2025-03-28",
                "MONTH_EDIT_INCORRECT"))return;
            dateField.today();
            const utcNow=(new Date()).toISOString().slice(0,10);
            if(!root.check(dateField.dateValue===utcNow,
                "TODAY_NOT_UTC"))return;

            root.stage="NATAL_AUTO_DATE";
            natalForm.visible=true;
            if(!root.check(natalForm.utcDate===utcNow,
                "NATAL_DATE_NOT_DEFAULTED"))return;
            if(!root.check(natalForm.place.source==="UNAVAILABLE",
                "EMPTY_HOME_NOT_FAIL_CLOSED"))return;

            root.stage="SAVED_HOME";
            PlaceRegistry.document={
                schema:"post-apollo.places.v1",revision:0,
                home:{label:"NATIVE TEST HOME",source:"MANUAL",
                    latitude:38.9,longitude:-76.8},
                explore:null,savedPlaces:[],nextSavedPlaceId:1
            };
            PlaceRegistry.storageState="ready";
            if(!root.check(natalForm.place.source==="HOME",
                "HOME_NOT_DETECTED"))return;
            if(!root.check(natalForm.draft.valid===false,
                "TIME_EMPTY_SHOULD_BE_INVALID"))return;
            natalForm.utcTime="15:42";
            if(!root.check(natalForm.draft.valid===true,
                "HOME_UTC_NATAL_VALIDATION_FAILED"))return;

            root.stage="MANUAL_OVERRIDE";
            natalForm.latitudeText="0";
            if(!root.check(natalForm.place.source==="INCOMPLETE",
                "ONE_SIDED_COORDINATES_NOT_REJECTED"))return;
            natalForm.longitudeText="0";
            if(!root.check(natalForm.place.source==="MANUAL",
                "MANUAL_SOURCE_NOT_SELECTED"))return;
            if(!root.check(natalForm.draft.valid===true,
                "ZERO_COORDINATES_NOT_ACCEPTED"))return;
            natalForm.latitudeText="bad";
            if(!root.check(!natalForm.draft.valid,
                "BAD_MANUAL_COORDINATES_NOT_REJECTED"))return;

            root.stage="TRANSIT_AUTO_DATE";
            transitForm.visible=true;
            if(!root.check(transitForm.dateText===utcNow,
                "TRANSIT_DATE_NOT_DEFAULTED"))return;
            if(!root.check(!transitForm.comparison.ready,
                "TRANSIT_SHOWED_UNVERIFIED_DATA"))return;
            transitForm.setCurrentInstant();
            if(!root.check(transitForm.dateText===utcNow,
                "TRANSIT_NOW_NOT_UTC"))return;

            root.stage="SESSION_CLEAR";
            natalForm.visible=false;
            transitForm.visible=false;
            if(!root.check(natalForm.utcTime===""&&natalForm.latitudeText===""
                  &&natalForm.longitudeText==="",
                  "NATAL_PRIVATE_FIELDS_NOT_CLEARED"))return;
            if(!root.check(transitForm.timeText==="",
                "TRANSIT_TIME_NOT_CLEARED"))return;

            root.complete=true;
            console.log("M8E_NATIVE_PASS // REAL_QML_DATE_HOME_TRANSIT_COMPONENTS");
            Qt.quit();
        }
    }
    Timer {
        interval: 9000
        repeat:false
        running:true
        onTriggered: root.fail("TIMEOUT")
    }
}
