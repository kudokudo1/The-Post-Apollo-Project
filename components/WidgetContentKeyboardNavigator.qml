import QtQuick
import "WidgetContentSpatialPolicy.js" as Spatial

// Coordinates one REAL button selector. Keyboard movement separates it
// from a stationary secondary mouse hover, while actual pointer movement
// recombines it. Existing Qt/key ownership and Tab/Sub Mode routes stay with
// the window. This Item has NO input handlers, MouseArea or FocusScope.
Item {
    id: navigator
    property Item contentRoot: null
    property bool navigationActive: false
    property var selectedItem: null
    property bool keyboardPrimaryActive: false
    // Never replace a button's pre-existing keyboardSelected QML binding.
    // The content-specific flags below are owned only while registered here.
    property var registeredControls: []
    property rect selectedBounds: Qt.rect(0,0,0,0)
    readonly property bool hasContentSelection:
        selectedItem !== null && selectedBounds.width > 0
    z: 500
    focus: false

    function clearContentFlags(item) {
        try {
            if (item && item.contentNavigator === navigator) {
                item.contentKeyboardPrimary = false;
                item.contentKeyboardNavigationActive = false;
                item.contentNavigator = null;
            }
        } catch(error) {
            // A removed delegate cannot retain focus or input authority.
        }
    }

    function reset() {
        for (let i=0;i<registeredControls.length;i++)
            clearContentFlags(registeredControls[i]);
        registeredControls = [];
        selectedItem = null;
        keyboardPrimaryActive = false;
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

    function synchronizeButtonCursor(controls) {
        const live=controls.map(function(entry) { return entry.item; });
        for(let i=0;i<registeredControls.length;i++) {
            const old=registeredControls[i];
            if(live.indexOf(old)<0) clearContentFlags(old);
        }
        // Only ActionButton descendants expose these new flags. Unknown
        // controls retain a bounded fallback outline below.
        for(let i=0;i<live.length;i++) {
            const item=live[i];
            try {
                if(typeof item.contentKeyboardPrimary !== "boolean"
                        || typeof item.contentKeyboardNavigationActive !== "boolean")
                    continue;
                item.contentNavigator=navigator;
                item.contentKeyboardNavigationActive=keyboardPrimaryActive;
                item.contentKeyboardPrimary=keyboardPrimaryActive
                    && selectedItem===item;
            } catch(error) {
                // Disappearing delegates are excluded on next collection.
            }
        }
        registeredControls=live;
    }

    // Called only from a real ActionButton pointer-position event. Neither
    // passive hover, keyboard movement nor focus restoration may steal
    // the keyboard-primary cursor.
    function followPointer(item) {
        if(!navigationActive || !item || !item.available
                || !item.interactive || !item.keyboardNavTarget)
            return false;
        if(registeredControls.indexOf(item)<0)
            return false;
        selectedItem=item;
        keyboardPrimaryActive=false;
        const controls=candidates();
        synchronizeButtonCursor(controls);
        refreshBounds();
        return true;
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
        let next=controls.findIndex(function(entry) {
            return entry.item.hovered === true && entry.visible;
        });
        if(next<0) next=Spatial.initialIndex(controls);
        if(next<0) {reset();return false;}
        selectedItem=controls[next].item;
        keyboardPrimaryActive=true;
        synchronizeButtonCursor(controls);
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
        if(index<0) index=current.findIndex(function(entry) {
            return entry.item.hovered === true && entry.visible;
        });
        const next=Spatial.nextIndex(current,index,dx,dy);
        if(next<0) return false;
        selectedItem=current[next].item;
        keyboardPrimaryActive=true;
        scrollIntoView(selectedItem);
        synchronizeButtonCursor(current);
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

    // ActionButton draws the primary orange preview / activated magenta
    // artwork, border and sampled glows itself. Never add a disconnected
    // second yellow rectangle around a real ActionButton.
    // Fallback only for a future non-ActionButton keyboard target.
    Rectangle {
        id: selectionFrame
        objectName: "widget-content-keyboard-selection"
        visible: navigator.navigationActive && navigator.keyboardPrimaryActive
                 && navigator.hasContentSelection
                 && (!navigator.selectedItem
                     || typeof navigator.selectedItem.contentKeyboardPrimary
                        !== "boolean")
        x: navigator.selectedBounds.x-3
        y: navigator.selectedBounds.y-3
        width: navigator.selectedBounds.width+6
        height: navigator.selectedBounds.height+6
        color: "transparent"
        border.color: navigator.selectedItem && navigator.selectedItem.selected
                      ? Colors.magenta : Colors.orange
        border.width: 2
        radius: 0
        z: 500
    }
}
