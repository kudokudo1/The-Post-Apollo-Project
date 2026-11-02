import QtQuick
import "../../components"
import "StationSubjectNavigationPolicy.js" as SubjectRoutes

// M1 separate subject rail: WeatherStationW retains its canonical one
// legacy Main Mode delegate. This component is visible in index mode only.
Column {
    id: subjectRail
    property var navigator: null
    spacing: 6

    Repeater {
        model: SubjectRoutes.SUBJECTS
        delegate: ModeButton {
            required property var modelData
            width: subjectRail.width
            height: 48
            textOnly: true
            horizontalContent: true
            labelFontSize: 17
            bordered: false
            selected: subjectRail.navigator
                      && subjectRail.navigator.currentRoute
                      && subjectRail.navigator.currentRoute.subject
                         === modelData.id
            labelText: modelData.label
            onTriggered: {
                if (subjectRail.navigator)
                    subjectRail.navigator.selectSubject(modelData.id);
            }
        }
    }
}
