import QtQuick
import QtQuick.Dialogs

// Loaded only after explicit WAV/MP3 import. If the optional dialog module is
// missing, Clock and the alarm timer must still be able to start.
Item {
    id: pickerHost
    signal fileSelected(string fileUrl)
    signal cancelled()
    function openChooser() { wavPicker.open(); }
    FileDialog {
        id: wavPicker
        title: "IMPORT WAV OR MP3 INTO POST-APOLLO SOUND LIBRARY"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Sound files (*.wav *.mp3)", "WAV audio (*.wav)", "MP3 audio (*.mp3)"]
        onAccepted: pickerHost.fileSelected(selectedFile.toString())
        onRejected: pickerHost.cancelled()
    }
}
