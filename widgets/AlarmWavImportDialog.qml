import QtQuick
import QtQuick.Dialogs

// Loaded only when the user selects IMPORT WAV. Missing optional
// QtQuick.Dialogs must not prevent Clock or its scheduler from loading.
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
