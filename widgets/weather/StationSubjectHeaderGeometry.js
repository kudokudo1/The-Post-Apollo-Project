.pragma library

// C44 // Stable SUBJECTS header geometry. The content beneath can change,
// but every adopting page keeps the same horizontal boundaries and
// title / tab / rule / instrument vertical stages.
var inset = 6;
var titleHeight = 18;
var titleToTabs = 4;
var tabHeight = 27;
var tabSpacing = 4;
var tabsToRule = 5;
var ruleHeight = 2;
var ruleToContent = 3;

function buttonWidth(availableWidth, count) {
    var width = Number(availableWidth);
    var n = Number(count);
    if (!isFinite(width) || width < 0 || !isFinite(n) || n < 1)
        return 1;
    n = Math.floor(n);
    return Math.max(1,(width - (n-1)*tabSpacing)/n);
}
function titleTop() {return inset;}
function tabsTop() {return inset + titleHeight + titleToTabs;}
function ruleTop() {return tabsTop() + tabHeight + tabsToRule;}
function contentTop() {return ruleTop() + ruleHeight + ruleToContent;}

// For Column-based panes with spacing = ruleToContent:
// title → 1px spacer → tabs → 4px slot (2px leading + 2px rule).
function columnHeaderGap() {
    return titleToTabs-ruleToContent;
}
function columnRuleSlotHeight() {
    return tabsToRule-ruleToContent+ruleHeight;
}
