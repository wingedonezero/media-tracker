import QtQuick
import QtQuick.Layouts

Rectangle {
    id: card
    radius: _t.borderRadius
    color: card.selected ? _t.accentBg : (cardMouse.containsMouse ? _t.surfaceCardHover : _t.surfaceCard)
    border.color: card.selected ? _t.accent : (cardMouse.containsMouse ? _t.borderSubtle : "transparent")
    border.width: card.selected ? 2 : 1
    clip: true

    signal clicked(int modifiers)
    signal doubleClicked()
    signal rightClicked(real mx, real my)

    property string title: ""
    property string nativeTitle: ""
    property int year: 0
    property string qualityType: ""
    property string posterPath: ""
    property bool hasPoster: false
    property bool selected: false

    Theme { id: _t }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Poster
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: _t.surfaceDark
            clip: true

            Image {
                anchors.fill: parent
                source: card.hasPoster ? card.posterPath : ""
                fillMode: Image.PreserveAspectCrop
                visible: card.hasPoster
                asynchronous: true
            }

            // No-poster placeholder
            Text {
                anchors.centerIn: parent
                text: "🎬"
                font.pixelSize: 32
                visible: !card.hasPoster
            }
        }

        // Info
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 2

                Text {
                    text: card.title
                    color: _t.textPrimary
                    font.pixelSize: 13
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    spacing: 6
                    Text {
                        text: card.year > 0 ? String(card.year) : ""
                        color: _t.textMuted
                        font.pixelSize: 11
                        visible: card.year > 0
                    }
                    Text {
                        text: card.qualityType
                        color: _t.accentLight
                        font.pixelSize: 11
                        visible: card.qualityType !== ""
                    }
                }
            }
        }
    }

    MouseArea {
        id: cardMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (mouse) => {
            if (mouse.button === Qt.RightButton) {
                card.rightClicked(mouse.x, mouse.y)
            } else {
                card.clicked(mouse.modifiers)
            }
        }
        onDoubleClicked: card.doubleClicked()
    }
}
