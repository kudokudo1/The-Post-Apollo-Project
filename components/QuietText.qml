import QtQuick

// Contextual/low-priority information, NOT an unavailable control.
// White at low opacity appears gray against Post-Apollo's dark surfaces.
// No automatic glow: quiet words should not outshine their primary content.
GohuText {
    property real quietOpacity: VisualLanguage.quietTextOpacity
    font.pixelSize: 10
    color: Colors.white
    opacity: quietOpacity
}
