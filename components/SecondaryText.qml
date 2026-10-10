import QtQuick

// Supporting but readily legible information. No automatic glow.
// For promoted white text with cyan glow, attach TextHashGlow explicitly.
GohuText {
    property real secondaryOpacity: VisualLanguage.secondaryTextOpacity
    font.pixelSize: 11
    color: Colors.white
    opacity: secondaryOpacity
}
