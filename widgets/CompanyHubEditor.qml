import QtQuick
import "../components"

// Operator-entered, non-personal HUB CLAIM form.
// No action here establishes authenticated organization membership
// or verified geographic/program coverage.
Rectangle {
    id: editor
    color: Colors.black
    border.color: Colors.blue
    border.width: 1

    property real longitude: 0
    property real latitude: 0
    property bool hasLocation: false
    property string storeState: "loading"
    property string storeError: ""
    property string defaultRegionCode: ""
    property string countryCode: "US"
    property string serviceFamily: "BENEFITS"
    property bool saving: false
    property string saveError: ""
    property string localError: ""
    signal saveRequested(var hub)
    signal cancelRequested()
    signal pickLocationRequested()
    signal retryStoreRequested()

    // + HUB opens the form immediately. Map placement is a separate,
    // visible action and MUST NOT be silently inferred from the viewport.
    function begin(region) {
        hasLocation = false;
        longitude = 0;
        latitude = 0;
        defaultRegionCode = String(region || "");
        regionInput.text = defaultRegionCode;
        labelInput.text = "";
        organizationInput.text = "";
        cityInput.text = "";
        countryCode = "US";
        serviceFamily = "BENEFITS";
        localError = "";
    }

    function setCoordinates(lon, lat) {
        const x = Number(lon), y = Number(lat);
        if (!isFinite(x) || !isFinite(y) || x < -180 || x > 180
                || y < -90 || y > 90) {
            localError = "INVALID MAP LOCATION";
            return false;
        }
        longitude = x;
        latitude = y;
        hasLocation = true;
        localError = "";
        return true;
    }

    // Backward compatible entry point for existing map-picked callers.
    function prepare(lon, lat, region) {
        begin(region);
        setCoordinates(lon, lat);
    }

    function save() {
        if (!hasLocation) {
            localError = "PICK A LOCATION ON THE MAP BEFORE SAVING";
            return;
        }
        if (storeState !== "ready") {
            localError = "HUB DIRECTORY NOT READY: " + (storeError || storeState);
            return;
        }
        const label = labelInput.text.trim();
        const organization = organizationInput.text.trim();
        const city = cityInput.text.trim();
        const region = regionInput.text.trim().toUpperCase();
        if (!label || !organization || !city
                || !/^[A-Z]{2,3}$/.test(region)) {
            localError = "ENTER HUB, ORGANIZATION, CITY AND 2–3 LETTER REGION";
            return;
        }
        if (!isFinite(longitude) || !isFinite(latitude)) {
            localError = "MAP COORDINATES UNAVAILABLE";
            return;
        }
        localError = "";
        saveRequested({
            label:label,
            organizationLabel:organization,
            city:city,
            regionCode:region,
            countryCode:countryCode,
            longitude:longitude,
            latitude:latitude,
            serviceFamily:serviceFamily
        });
    }

    Keys.onEscapePressed: function(event) {
        if (!saving) cancelRequested();
        event.accepted = true;
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 12
        clip: true
        contentWidth: width
        contentHeight: contentColumn.height
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: 10

            Row {
                width: parent.width
                height: 32
                spacing: 8

                GohuText {
                    width: parent.width - 45
                    anchors.verticalCenter: parent.verticalCenter
                    text: "NEW HUB // OPERATOR-REPORTED"
                    font.pixelSize: 17
                    font.bold: true
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                ActionButton {
                    width: 34
                    height: 30
                    label: "×"
                    labelPixelSize: 20
                    accentColor: Colors.red
                    destructive: true
                    available: !editor.saving
                    onLeftClicked: editor.cancelRequested()
                }
            }

            GohuText {
                width: parent.width
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                color: Colors.white
                text: "Enter the hub information, then use PICK LOCATION to mark its "
                    + "position on the map. Operator-reported only, NOT verified "
                    + "service coverage. No client or employee details."
            }

            Row {
                width: parent.width
                height: 38
                spacing: 8
                ModeButton {
                    width: 200
                    height: 36
                    textOnly: true
                    bordered: false
                    labelText: editor.hasLocation ? "CHANGE MAP LOCATION" : "PICK LOCATION ON MAP"
                    labelFontSize: 11
                    selected: !editor.hasLocation
                    onTriggered: editor.pickLocationRequested()
                }
                GohuText {
                    width: parent.width - 208
                    anchors.verticalCenter: parent.verticalCenter
                    text: editor.hasLocation ? "COORDINATES SET" : "LOCATION REQUIRED"
                    color: editor.hasLocation ? Colors.cyan : Colors.yellow
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }

            Row {
                width: parent.width
                height: editor.storeState==="ready" ? 0 : 32
                visible: editor.storeState !== "ready"
                spacing: 8
                GohuText {
                    width: Math.max(110,parent.width - 110)
                    anchors.verticalCenter: parent.verticalCenter
                    text: "STORE: " + editor.storeState.toUpperCase()
                        + (editor.storeError ? " // "+editor.storeError : "")
                    color: Colors.red
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
                ModeButton {
                    width: 96
                    height: 30
                    textOnly: true
                    labelText: "RETRY LOAD"
                    labelFontSize: 10
                    bordered: false
                    onTriggered: editor.retryStoreRequested()
                }
            }

            // Named inputs ensure the view reads exactly what the user typed.
            Rectangle {
                width: parent.width
                height: 40
                color: Colors.dark
                border.color: Colors.blue
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: "HUB NAME"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                TextInput {
                    id: labelInput
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 15
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    color: Colors.white
                    selectByMouse: true
                    clip: true
                    maximumLength: 90
                }
            }

            Rectangle {
                width: parent.width
                height: 40
                color: Colors.dark
                border.color: Colors.blue
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: "ORGANIZATION LABEL"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                TextInput {
                    id: organizationInput
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 15
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    color: Colors.white
                    selectByMouse: true
                    clip: true
                    maximumLength: 90
                }
            }

            Rectangle {
                width: parent.width
                height: 40
                color: Colors.dark
                border.color: Colors.blue
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: "CITY / LOCALITY"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                TextInput {
                    id: cityInput
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 15
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    color: Colors.white
                    selectByMouse: true
                    clip: true
                    maximumLength: 80
                }
            }

            Rectangle {
                width: parent.width
                height: 40
                color: Colors.dark
                border.color: Colors.blue
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: "STATE / REGION CODE"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                TextInput {
                    id: regionInput
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 15
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    color: Colors.white
                    selectByMouse: true
                    clip: true
                    maximumLength: 3
                    inputMethodHints: Qt.ImhUppercaseOnly
                }
            }

            GohuText {
                text: "COUNTRY"
                color: Colors.yellow
                font.pixelSize: 11
            }
            Row {
                width: parent.width
                height: 35
                spacing: 5
                Repeater {
                    model: [
                        {name:"USA",code:"US"},
                        {name:"CANADA",code:"CAN"},
                        {name:"MEXICO",code:"MEX"}
                    ]
                    ModeButton {
                        required property var modelData
                        width: (contentColumn.width - 10) / 3
                        height: 35
                        textOnly: true
                        labelFontSize: 11
                        labelText: modelData.name
                        selected: editor.countryCode===modelData.code
                        bordered: false
                        onTriggered: editor.countryCode=modelData.code
                    }
                }
            }

            GohuText {
                text: "SERVICE FAMILY // ONE PER ENTRY"
                color: Colors.yellow
                font.pixelSize: 11
            }
            Flow {
                width: parent.width
                spacing: 5
                Repeater {
                    model: [
                        "BENEFITS","HEALTHCARE","EDUCATION",
                        "EMPLOYMENT","REINTEGRATION","HOUSING"
                    ]
                    ModeButton {
                        required property string modelData
                        width: Math.max(118,Math.floor((contentColumn.width-10)/3))
                        height: 35
                        textOnly: true
                        labelFontSize: 10
                        labelText: modelData
                        selected: editor.serviceFamily===modelData
                        bordered: false
                        onTriggered: editor.serviceFamily=modelData
                    }
                }
            }

            GohuText {
                width: parent.width
                text: editor.hasLocation
                    ? "MAP POINT // "
                        + Number(editor.latitude).toFixed(4) + "° latitude  // "
                        + Number(editor.longitude).toFixed(4) + "° longitude"
                    : "MAP POINT // NOT SELECTED"
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }

            GohuText {
                visible: !!editor.localError || !!editor.saveError
                width: parent.width
                font.pixelSize: 10
                color: Colors.red
                wrapMode: Text.WordWrap
                text: editor.localError || editor.saveError
            }

            Row {
                width: parent.width
                height: 42
                spacing: 8
                ModeButton {
                    width: 164
                    height: 40
                    textOnly: true
                    bordered: false
                    labelText: editor.saving ? "SAVING..." : "SAVE LOCAL HUB"
                    selected: true
                    interactive: !editor.saving
                    onTriggered: editor.save()
                }
                ModeButton {
                    width: 120
                    height: 40
                    textOnly: true
                    bordered: false
                    labelText: "CANCEL"
                    interactive: !editor.saving
                    onTriggered: editor.cancelRequested()
                }
            }
        }
    }
}
