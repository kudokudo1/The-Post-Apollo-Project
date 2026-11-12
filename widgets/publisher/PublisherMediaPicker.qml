import QtQuick
import QtQuick.Dialogs

// Optional system file chooser. Loaded only after a deliberate IMPORT click.
// Selection does not copy, modify, queue or upload the chosen file.
Item {
    id: picker
    signal fileSelected(string fileUrl)
    signal cancelled()
    function openChooser() { dialog.open(); }
    FileDialog {
        id: dialog
        title: "POST-APOLLO PUBLISHER // LINK LOCAL MEDIA"
        fileMode: FileDialog.OpenFile
        options: FileDialog.ReadOnly
        nameFilters: [
            "Images / videos (*.png *.jpg *.jpeg *.webp *.mp4 *.webm *.mov)",
            "Images (*.png *.jpg *.jpeg *.webp)",
            "Videos (*.mp4 *.webm *.mov)"
        ]
        onAccepted: picker.fileSelected(selectedFile.toString())
        onRejected: picker.cancelled()
    }
}
