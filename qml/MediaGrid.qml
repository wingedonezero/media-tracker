import QtQuick
import QtQuick.Layouts

Item {
    id: gridRoot

    property alias model: gridView.model
    property var selectedIds: []

    signal itemClicked(int row, int modifiers)
    signal itemDoubleClicked(int row)
    signal itemRightClicked(int row, real mx, real my)

    function isSelected(row) {
        var id = model.getItemId(row)
        for (var i = 0; i < selectedIds.length; i++) {
            if (selectedIds[i] === id) return true
        }
        return false
    }

    GridView {
        id: gridView
        anchors.fill: parent
        anchors.margins: 16

        cellWidth: Math.max(160, width / Math.max(1, Math.floor(width / 180)))
        cellHeight: cellWidth * 1.7

        clip: true
        boundsBehavior: Flickable.StopAtBounds

        delegate: Item {
            width: gridView.cellWidth
            height: gridView.cellHeight

            MediaCard {
                anchors.fill: parent
                anchors.margins: 6
                title: model.title
                nativeTitle: model.nativeTitle || ""
                year: model.year
                qualityType: model.qualityType || ""
                posterPath: model.posterPath || ""
                hasPoster: model.hasPoster || false
                selected: gridRoot.isSelected(index)
                onClicked: (modifiers) => gridRoot.itemClicked(index, modifiers)
                onDoubleClicked: gridRoot.itemDoubleClicked(index)
                onRightClicked: (mx, my) => gridRoot.itemRightClicked(index, mx, my)
            }
        }
    }
}
