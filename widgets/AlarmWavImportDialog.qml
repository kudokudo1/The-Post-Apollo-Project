import QtQuick
import QtQuick.Dialogs

// Loaded only after explicit IMPORT WAV. If the optional dialog module is
// missing, Clock and the alarm timer must still be able to start.
Item {
    id: pickerHost
    signal fileSelected(string fileUrl)
    function openChooser() { wavPicker.open(); }
    FileDialog {
        id: wavPicker
        title: "IMPORT WAV INTO POST-APOLLO SOUND LIBRARY"
        fileMode: FileDialog.OpenFile
        nameFilters: ["PCM WAV audio (*.wav)"]
        onAccepted: pickerHost.fileSelected(selectedFile.toString())
    }
}
