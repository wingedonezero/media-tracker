import QtQuick
import QtQuick.Layouts

Item {
    id: tableRoot
    Theme { id: _t }

    property alias model: listView.model
    property var selectedIds: []
    property int rowHeight: 44
    property string sortField: "title"
    property string sortDir: "ASC"

    signal itemClicked(int row, int modifiers)
    signal itemDoubleClicked(int row)
    signal itemRightClicked(int row, real mx, real my)
    signal sortRequested(string field, string dir)

    function isSelected(row) {
        var id = model.getItemId(row)
        for (var i = 0; i < selectedIds.length; i++) {
            if (selectedIds[i] === id) return true
        }
        return false
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Table header (sortable)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: _t.surfaceDark

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 8

                // Title header (sortable)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: titleHeaderMouse.containsMouse ? _t.surfaceCardHover : "transparent"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        spacing: 4
                        Text { text: "Title"; color: _t.textMuted; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: tableRoot.sortField === "title" ? (tableRoot.sortDir === "ASC" ? "↑" : "↓") : ""
                            color: _t.accent; font.pixelSize: 12
                        }
                        Item { Layout.fillWidth: true }
                    }
                    MouseArea {
                        id: titleHeaderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: toggleSort("title")
                    }
                }

                // Year header (sortable)
                Rectangle {
                    Layout.preferredWidth: 60
                    Layout.fillHeight: true
                    color: yearHeaderMouse.containsMouse ? _t.surfaceCardHover : "transparent"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        spacing: 4
                        Text { text: "Year"; color: _t.textMuted; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: tableRoot.sortField === "year" ? (tableRoot.sortDir === "ASC" ? "↑" : "↓") : ""
                            color: _t.accent; font.pixelSize: 12
                        }
                    }
                    MouseArea {
                        id: yearHeaderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: toggleSort("year")
                    }
                }

                // Quality header (sortable)
                Rectangle {
                    Layout.preferredWidth: 120
                    Layout.fillHeight: true
                    color: qualityHeaderMouse.containsMouse ? _t.surfaceCardHover : "transparent"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        spacing: 4
                        Text { text: "Quality"; color: _t.textMuted; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: tableRoot.sortField === "quality_type" ? (tableRoot.sortDir === "ASC" ? "↑" : "↓") : ""
                            color: _t.accent; font.pixelSize: 12
                        }
                    }
                    MouseArea {
                        id: qualityHeaderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: toggleSort("quality_type")
                    }
                }

                // Source header (sortable)
                Rectangle {
                    Layout.preferredWidth: 100
                    Layout.fillHeight: true
                    color: sourceHeaderMouse.containsMouse ? _t.surfaceCardHover : "transparent"
                    radius: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        spacing: 4
                        Text { text: "Source"; color: _t.textMuted; font.pixelSize: 12; font.bold: true }
                        Text {
                            text: tableRoot.sortField === "source" ? (tableRoot.sortDir === "ASC" ? "↑" : "↓") : ""
                            color: _t.accent; font.pixelSize: 12
                        }
                    }
                    MouseArea {
                        id: sourceHeaderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: toggleSort("source")
                    }
                }
            }
        }

        // Table rows
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            spacing: 1

            delegate: Rectangle {
                width: listView.width
                height: tableRoot.rowHeight

                property bool isSelected: tableRoot.isSelected(index)

                color: isSelected ? _t.accentBg : (rowMouse.containsMouse ? _t.surfaceCardHover : (index % 2 === 0 ? _t.surfaceDark : _t.surface))
                border.width: isSelected ? 1 : 0
                border.color: isSelected ? _t.accent : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 8

                    // Poster thumbnail
                    Rectangle {
                        Layout.preferredWidth: Math.round(tableRoot.rowHeight * 0.64)
                        Layout.preferredHeight: tableRoot.rowHeight - 8
                        radius: 4
                        color: _t.surfaceElevated
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: model.hasPoster ? model.posterPath : ""
                            fillMode: Image.PreserveAspectCrop
                            visible: model.hasPoster || false
                            asynchronous: true
                        }
                    }

                    // Title
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: model.title
                            color: _t.textPrimary
                            font.pixelSize: 13
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: model.nativeTitle || ""
                            color: _t.textMuted
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            visible: (model.nativeTitle || "") !== ""
                        }
                    }

                    Text { text: model.year > 0 ? String(model.year) : ""; color: _t.textSecondary; font.pixelSize: 13; Layout.preferredWidth: 60 }
                    Text { text: model.qualityType || ""; color: _t.accentLight; font.pixelSize: 13; Layout.preferredWidth: 120 }
                    Text { text: model.source || ""; color: _t.textSecondary; font.pixelSize: 13; Layout.preferredWidth: 100 }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: (mouse) => {
                        if (mouse.button === Qt.RightButton) {
                            tableRoot.itemRightClicked(index, mouse.x, mouse.y)
                        } else {
                            tableRoot.itemClicked(index, mouse.modifiers)
                        }
                    }
                    onDoubleClicked: tableRoot.itemDoubleClicked(index)
                }
            }
        }
    }

    function toggleSort(field) {
        if (sortField === field) {
            // Toggle direction
            var newDir = sortDir === "ASC" ? "DESC" : "ASC"
            sortRequested(field, newDir)
        } else {
            sortRequested(field, "ASC")
        }
    }
}
