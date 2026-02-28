import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import com.mediatracker


Window {
    id: settingsWin
    title: "Settings"
    width: 500; height: 500
    flags: Qt.Dialog
    modality: Qt.WindowModal
    color: _t.surfaceCard

    property var controller

    palette {
        window: _t.surfaceCard
        windowText: _t.textPrimary
        base: _t.surfaceDark
        alternateBase: _t.surfaceCard
        text: _t.textPrimary
        button: _t.surfaceCard
        buttonText: _t.textPrimary
        highlight: _t.accent
        highlightedText: _t.textWhite
        toolTipBase: _t.surfaceCard
        toolTipText: _t.textPrimary
        placeholderText: _t.textMuted
        light: _t.surfaceElevated
        mid: _t.borderSubtle
        dark: _t.surfaceDark
    }

    // Quality types as a JS array managed in QML
    property var qualityTypes: []

    onVisibleChanged: {
        if (visible) {
            apiKeyField.text = controller.tmdb_api_key
            adultCheck.checked = controller.include_adult
            loadQualityTypes()
        }
    }

    function loadQualityTypes() {
        var raw = controller.getQualityTypes()
        if (raw === "") {
            qualityTypes = []
        } else {
            qualityTypes = raw.split("\n").filter(function(s) { return s.trim() !== "" })
        }
    }

    function addQualityType() {
        var name = newQtField.text.trim()
        if (name === "") return
        // Check for duplicate
        for (var i = 0; i < qualityTypes.length; i++) {
            if (qualityTypes[i].toLowerCase() === name.toLowerCase()) {
                return
            }
        }
        var arr = qualityTypes.slice()
        arr.push(name)
        qualityTypes = arr
        newQtField.text = ""
    }

    function removeQualityType(idx) {
        var arr = qualityTypes.slice()
        arr.splice(idx, 1)
        qualityTypes = arr
    }

    function getQualityTypesString() {
        return qualityTypes.join("\n")
    }

    Theme { id: _t }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: _t.surfaceDark

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 20
                anchors.left: parent.left
                text: "Settings"
                color: _t.textWhite
                font.pixelSize: 17
                font.bold: true
            }
        }

        // Body
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: 16

                Item { Layout.preferredHeight: 4 }

                // TMDB API Key
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 4

                    Text { text: "TMDB API Key"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                    TextField {
                        id: apiKeyField
                        Layout.fillWidth: true
                        color: _t.textPrimary
                        font.pixelSize: 13
                        echoMode: TextInput.Password
                        placeholderText: "Enter your TMDB API key..."
                        placeholderTextColor: _t.textMuted
                        background: Rectangle {
                            color: _t.surfaceDark
                            border.color: apiKeyField.activeFocus ? _t.accent : _t.borderSubtle
                            radius: 8
                        }
                    }
                    Text {
                        text: "Get a free key at themoviedb.org"
                        color: _t.textMuted
                        font.pixelSize: 11
                    }
                }

                // Include Adult
                RowLayout {
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 8

                    CheckBox {
                        id: adultCheck
                        text: "Include adult content in searches"
                        palette.text: _t.textPrimary
                    }
                }

                // Quality Types
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 8

                    Text { text: "Quality Types"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }

                    // List of quality types
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(120, Math.min(200, qtColumn.implicitHeight + 16))
                        color: _t.surfaceDark
                        radius: 8
                        border.color: _t.borderSubtle
                        clip: true

                        Flickable {
                            anchors.fill: parent
                            anchors.margins: 8
                            contentHeight: qtColumn.implicitHeight
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds

                            ColumnLayout {
                                id: qtColumn
                                width: parent.width
                                spacing: 4

                                Repeater {
                                    model: settingsWin.qualityTypes

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 32
                                        radius: 6
                                        color: qtItemMouse.containsMouse ? _t.surfaceCardHover : _t.surfaceCard

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 6
                                            spacing: 8

                                            Text {
                                                text: modelData
                                                color: _t.textPrimary
                                                font.pixelSize: 13
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }

                                            Rectangle {
                                                Layout.preferredWidth: removeText.implicitWidth + 12
                                                Layout.preferredHeight: 24
                                                radius: 4
                                                color: removeMouse.containsMouse ? "#3def4444" : "transparent"

                                                Text {
                                                    id: removeText
                                                    anchors.centerIn: parent
                                                    text: "Remove"
                                                    color: removeMouse.containsMouse ? _t.danger : _t.textMuted
                                                    font.pixelSize: 11
                                                }
                                                MouseArea {
                                                    id: removeMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: settingsWin.removeQualityType(index)
                                                }
                                            }
                                        }

                                        MouseArea {
                                            id: qtItemMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            acceptedButtons: Qt.NoButton
                                        }
                                    }
                                }

                                // Empty state
                                Text {
                                    text: "No quality types defined"
                                    color: _t.textMuted
                                    font.pixelSize: 12
                                    visible: settingsWin.qualityTypes.length === 0
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.topMargin: 20
                                }
                            }
                        }
                    }

                    // Add new quality type
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TextField {
                            id: newQtField
                            Layout.fillWidth: true
                            placeholderText: "New quality type..."
                            placeholderTextColor: _t.textMuted
                            color: _t.textPrimary
                            font.pixelSize: 13
                            background: Rectangle {
                                color: _t.surfaceDark
                                border.color: newQtField.activeFocus ? _t.accent : _t.borderSubtle
                                radius: 8
                            }
                            onAccepted: settingsWin.addQualityType()
                        }

                        Rectangle {
                            Layout.preferredWidth: 50
                            Layout.preferredHeight: 36
                            radius: 8
                            color: addQtMouse.containsMouse ? _t.accentHover : _t.accent

                            Text {
                                anchors.centerIn: parent
                                text: "Add"
                                color: _t.textWhite
                                font.pixelSize: 13
                                font.bold: true
                            }
                            MouseArea {
                                id: addQtMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: settingsWin.addQualityType()
                            }
                        }
                    }
                }

                // Row Height (Table View)
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 8

                    Text { text: "Table Row Height"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Slider {
                            id: rowHeightSlider
                            Layout.fillWidth: true
                            from: 30
                            to: 120
                            stepSize: 2
                            value: controller.row_height > 0 ? controller.row_height : 44
                        }

                        Text {
                            text: Math.round(rowHeightSlider.value) + "px"
                            color: _t.textPrimary
                            font.pixelSize: 13
                            Layout.preferredWidth: 40
                        }
                    }

                    Text {
                        text: "Controls the height of rows in table view (default: 44px)"
                        color: _t.textMuted
                        font.pixelSize: 11
                    }
                }

                Item { Layout.preferredHeight: 8 }
            }
        }

        // Footer
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: _t.surfaceDark

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 60; Layout.preferredHeight: 36
                        color: "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "Cancel"
                            color: sCancelMouse.containsMouse ? _t.textPrimary : _t.textSecondary
                            font.pixelSize: 13
                        }
                        MouseArea {
                            id: sCancelMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: settingsWin.close()
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 80; Layout.preferredHeight: 36
                        radius: 8
                        color: sSaveMouse.containsMouse ? _t.accentHover : _t.accent
                        Text {
                            anchors.centerIn: parent
                            text: "Save"
                            color: _t.textWhite
                            font.pixelSize: 13
                            font.bold: true
                        }
                        MouseArea {
                            id: sSaveMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                controller.saveSettings(apiKeyField.text, adultCheck.checked, settingsWin.getQualityTypesString())
                                controller.setRowHeight(Math.round(rowHeightSlider.value))
                                settingsWin.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
