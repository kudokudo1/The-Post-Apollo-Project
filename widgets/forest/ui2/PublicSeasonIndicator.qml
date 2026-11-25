import QtQuick
import QtQuick.Shapes
import "PublicHistoryDisplay.js" as ShapeCheck

// S1 isolated, fixed-public presentation only. Scope tokens identify local
// example slots, not real entities, parent graphs or lifecycle evidence.
Item {
    id: root
    implicitWidth: 16
    implicitHeight: 16
    width: 16
    height: 16
    clip: true
    property bool syntheticOwner: false
    property var ownerScope: null
    property var _accepted: null
    property string _season: "UNKNOWN"
    readonly property bool eligible: visible && syntheticOwner && validScope(ownerScope)
    readonly property string season: eligible && sameScope(_accepted,ownerScope)
        ? _season : "UNKNOWN"
    readonly property string seasonLabel: ({
        SPRING:"Spring Cleaning", SUMMER:"Summer Growing", FALL:"Fall Shedding",
        WINTER:"Winter Dormant", UNKNOWN:"Season unknown"
    })[season]
    readonly property color seasonColor: ({
        SPRING:"#9ECE6A", SUMMER:"#EAC846", FALL:"#ED981A",
        WINTER:"#62B5F5", UNKNOWN:"#999999"
    })[season]
    // Local vector shapes: no font/emoji fallback, image fetch or input text.
    readonly property string glyphPath: ({
        SPRING:"M 8 14 L 8 8 M 8 10 C 3 10 2 6 2 3 C 6 3 8 5 8 9 M 8 8 C 8 4 11 2 14 2 C 14 6 12 9 8 9",
        SUMMER:"M 8 5 A 3 3 0 1 0 8 11 A 3 3 0 1 0 8 5 M 8 1 L 8 3 M 8 13 L 8 15 M 1 8 L 3 8 M 13 8 L 15 8 M 3 3 L 4.5 4.5 M 11.5 11.5 L 13 13 M 3 13 L 4.5 11.5 M 11.5 4.5 L 13 3",
        FALL:"M 2 14 L 10 6 M 4 12 C 1 4 8 2 14 2 C 14 10 10 15 4 12 M 7 9 L 7 5 M 7 9 L 11 9",
        WINTER:"M 8 1 L 8 15 M 2 4.5 L 14 11.5 M 2 11.5 L 14 4.5 M 5.5 3 L 8 5 L 10.5 3 M 5.5 13 L 8 11 L 10.5 13 M 2.5 7.5 L 5 6.2 L 5 3.5 M 13.5 8.5 L 11 9.8 L 11 12.5 M 2.5 8.5 L 5 9.8 L 5 12.5 M 13.5 7.5 L 11 6.2 L 11 3.5",
        UNKNOWN:"M 8 1.5 A 6.5 6.5 0 1 0 8 14.5 A 6.5 6.5 0 1 0 8 1.5 M 6 5 C 6 2.8 10.8 3 10.8 5.5 C 10.8 7 8 7.5 8 9.5 M 8 12 L 8 12.2"
    })[season]
    Accessible.role: Accessible.Graphic
    Accessible.name: seasonLabel
    focus: false
    activeFocusOnTab: false
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false
    readonly property bool productionAuthority: false
    readonly property bool restorationEnabled: false
    function token(v) {
        return typeof v==="string" && v.length===32 && /^[0-9a-f]{32}$/.test(v);
    }
    function validScope(s) {
        return ShapeCheck.exact(s,["kind","entityAlias","viewKey","revision"])
            && ["TREE","COLONY","CLONE","ASSIGNMENT"].indexOf(s.kind)>=0
            && token(s.entityAlias) && token(s.viewKey) && s.entityAlias!==s.viewKey
            && ShapeCheck.integer(s.revision,1);
    }
    function sameScope(a,b) {
        return validScope(a) && validScope(b) && a.kind===b.kind
            && a.entityAlias===b.entityAlias && a.viewKey===b.viewKey
            && a.revision===b.revision;
    }
    function clear() {
        _accepted=null;
        _season="UNKNOWN";
    }
    onOwnerScopeChanged: clear()
    onEligibleChanged: if (!eligible) clear()
    // Owner pins the whole example scope independently. A stale event is
    // ignored; a malformed value for the current scope clears that slot.
    function receive(ref,value) {
        if (!eligible || !sameScope(ref,ownerScope)) return false;
        if (["SPRING","SUMMER","FALL","WINTER","UNKNOWN"].indexOf(value)<0) {
            clear();
            return false;
        }
        _accepted={kind:ref.kind,entityAlias:ref.entityAlias,
            viewKey:ref.viewKey,revision:ref.revision};
        _season=value;
        return true;
    }
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: root.seasonColor
            strokeWidth: 1.25
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg { path: root.glyphPath }
        }
    }
}
