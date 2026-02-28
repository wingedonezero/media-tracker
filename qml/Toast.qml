import QtQuick
import QtQuick.Controls

Item {
    id: toastRoot
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.rightMargin: 16
    anchors.bottomMargin: 16
    width: 320
    height: toastColumn.height
    z: 1000

    Column {
        id: toastColumn
        anchors.right: parent.right
        width: parent.width
        spacing: 8

        Repeater {
            id: toastRepeater
            model: ListModel { id: toastModel }

            delegate: Rectangle {
                width: toastColumn.width
                height: 44
                radius: 8
                color: model.toastType === "error" ? "#ef4444" :
                       model.toastType === "success" ? "#22c55e" :
                       model.toastType === "warning" ? "#f59e0b" : "#6366f1"
                opacity: 0.95

                Text {
                    anchors.centerIn: parent
                    text: model.message
                    color: "#ffffff"
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    width: parent.width - 24
                    horizontalAlignment: Text.AlignHCenter
                }

                Timer {
                    interval: 3000
                    running: true
                    onTriggered: toastModel.remove(index)
                }

                Behavior on opacity { NumberAnimation { duration: 200 } }
            }
        }
    }

    function show(message, type_) {
        toastModel.append({ message: message, toastType: type_ || "info" })
    }
}
