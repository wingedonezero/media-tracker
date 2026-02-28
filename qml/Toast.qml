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

    property int _nextId: 0

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
                opacity: 0.95

                required property int toastId
                required property string message
                required property string toastType

                color: toastType === "error" ? "#ef4444" :
                       toastType === "success" ? "#22c55e" :
                       toastType === "warning" ? "#f59e0b" : "#6366f1"

                Text {
                    anchors.centerIn: parent
                    text: message
                    color: "#ffffff"
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    width: parent.width - 24
                    horizontalAlignment: Text.AlignHCenter
                }

                Timer {
                    interval: 3000
                    running: true
                    onTriggered: removeById(toastId)
                }

                Behavior on opacity { NumberAnimation { duration: 200 } }
            }
        }
    }

    function removeById(id) {
        for (var i = 0; i < toastModel.count; i++) {
            if (toastModel.get(i).toastId === id) {
                toastModel.remove(i)
                return
            }
        }
    }

    function show(message, type_) {
        toastModel.append({ message: message, toastType: type_ || "info", toastId: _nextId })
        _nextId++
    }
}
