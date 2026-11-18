import QtQuick
import "WidgetContentSpatialPolicy.js" as Spatial

// Visual cursor for REAL controls in a widget's content area. The owner
// retains Qt focus and all Tab / Shift / Ctrl submode routes. This Item
// has NO input handlers, MouseArea, FocusScope or Sway focus requirement.
Item {
    id: navigator
    property Item contentRoot: null
    property bool navigationActive: false
    property var selectedItem: null
    property rect selectedBounds: Qt.rect(0,0,0,0)
    readonly property bool hasContentSelection:
        selectedItem !== null && selectedBounds.width > 0
    z: 500
    focus: false

    function reset() {
        selectedItem = null;
        selectedBounds = Qt.rect(0,0,0,0);
    }
    onContentRootChanged: reset()
    onNavigationActiveChanged: {
        if(!navigationActive) reset();
    }

    function collect(node, active, result, depth) {
        if(!node || !active || depth > 70 || result.length >= 300)
            return;
        try {
            if(node.visible === false || node.enabled === false
                    || node.opacity <= 0.01)
                return;
            // ActionButton is a semantic navigable control. ModeButton and
            // the separate main-mode rails are NOT inside contentRoot.
            if(node.keyboardNavTarget === true
                    && node.interactive === true
                    && node.available === true
                    && node.destructive !== true
                    && node.width > 4 && node.height > 4) {
                const mapped = node.mapToItem(navigator,0,0);
                const x=Number(mapped.x),y=Number(mapped.y);
                if(isFinite(x) && isFinite(y))
                    result.push({item:node,x:x,y:y,width:node.width,
                        height:node.height,
                        visible:x+node.width>0 && y+node.height>0
                            && x<navigator.width && y<navigator.height});
            }
            const children=node.children || [];
            for(let i=0;i<children.length && result.length<300;i++)
                collect(children[i],true,result,depth+1);
        } catch(error) {
            // Removed repeater delegates or native actors are not a reason
            // to take keyboard control away from the current application.
        }
    }

    function candidates() {
        const result=[];
        if(!navigationActive || !contentRoot || !contentRoot.visible)
            return result;
        collect(contentRoot,true,result,0);
        return result;
    }

    function scrollIntoView(target) {
        // Scroll only a genuine interactive Flickable enclosing the button.
        // Fixed-height HOME and read-only widgets retain their scroll state.
        try {
            var owner=target.parent;
            while(owner && owner!==contentRoot) {
                if(owner.contentItem
                        && typeof owner.contentY === "number"
                        && typeof owner.contentHeight === "number"
                        && owner.interactive !== false
                        && owner.contentHeight > owner.height + 1) {
                    const pos=target.mapToItem(owner.contentItem,0,0);
                    let next=owner.contentY;
                    if(pos.y < next+3) next=pos.y-3;
                    else if(pos.y+target.height > next+owner.height-3)
                        next=pos.y+target.height-owner.height+3;
                    owner.contentY=Math.max(0,
                        Math.min(owner.contentHeight-owner.height,next));
                }
                owner=owner.parent;
            }
        } catch(error) {
            // A deleted delegate/hidden panel must not mutate scroll state.
        }
    }

    function refreshBounds() {
        if(!navigationActive || !selectedItem) {
            selectedBounds=Qt.rect(0,0,0,0);
            return;
        }
        try {
            const p=selectedItem.mapToItem(navigator,0,0);
            const w=selectedItem.width,h=selectedItem.height;
            if(!selectedItem.visible || w<4 || h<4
                    || p.x+w <= 0 || p.y+h <= 0
                    || p.x >= width || p.y >= height) {
                selectedBounds=Qt.rect(0,0,0,0);
            } else selectedBounds=Qt.rect(p.x,p.y,w,h);
        } catch(error) { reset(); }
    }

    function selectInitial() {
        if(!navigationActive) return false;
        const controls=candidates();
        const next=Spatial.initialIndex(controls);
        if(next<0) {reset();return false;}
        selectedItem=controls[next].item;
        refreshBounds();
        return hasContentSelection;
    }

    function move(dx,dy) {
        if(!navigationActive) return false;
        const current=candidates();
        if(current.length===0) {reset();return false;}
        let index=-1;
        for(let i=0;i<current.length;i++)
            if(current[i].item===selectedItem) {index=i;break;}
        const next=Spatial.nextIndex(current,index,dx,dy);
        if(next<0) return false;
        selectedItem=current[next].item;
        scrollIntoView(selectedItem);
        refreshBounds();
        return true;
    }

    function handleDirectionKey(key,modifiers) {
        if(!navigationActive || modifiers!==Qt.NoModifier) return false;
        const direction=Spatial.directionForKey(key);
        return direction ? move(direction[0],direction[1]) : false;
    }

    function activate() {
        if(!navigationActive || !selectedItem) return false;
        const button=selectedItem;
        try {
            if(!button.visible || !button.available || !button.interactive
                    || button.destructive)
                return false;
            // An arbitrary action is NOT safe merely because it has a
            // clickable surface. Navigation-only owners opt in explicitly.
            const kind=button.keyboardActivationSignal;
            if(kind!=="leftClicked" && kind!=="triggered"
                    && kind!=="clicked")
                return false;
            reset();  // route changes may destroy this delegate synchronously
            if(kind==="leftClicked") button.leftClicked(null);
            else if(kind==="clicked") button.clicked(null);
            else button.triggered(null);
            return true;
        } catch(error) { reset();return false; }
    }

    // Visual overlay is never a mouse target and never modifies the button's
    // own keyboardSelected binding, preserving other current QML contracts.
    Rectangle {
        id: selectionFrame
        objectName: "widget-content-keyboard-selection"
        visible: navigator.navigationActive && navigator.hasContentSelection
        x: navigator.selectedBounds.x-3
        y: navigator.selectedBounds.y-3
        width: navigator.selectedBounds.width+6
        height: navigator.selectedBounds.height+6
        color: "transparent"
        border.color: Colors.yellow
        border.width: 2
        radius: 0
        z: 500
        Rectangle {
            width: 5
            height: 5
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            color: Colors.magenta
        }
    }
}
