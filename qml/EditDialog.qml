import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import com.mediatracker


Window {
    id: editWin
    title: isEditing ? "Edit Item" : "Add Item"
    width: 720; height: 620
    flags: Qt.Dialog
    modality: Qt.WindowModal
    color: _t.surfaceCard

    property var controller
    property var searchModel
    property var mediaModel
    property string activePage: "Movie"
    property string activeStatus: "On Drive"

    property bool isEditing: false
    property int editingId: -1
    property bool searching: false

    // ---- QML-side selection state (avoids model resets & scroll jumps) ----
    property var selectedIndices: ({})   // { rowIndex: true, ... }
    property int selectedCount: 0
    property int lastClickedIndex: -1
    property bool hasSearched: false     // true after first search in this session

    function clearSelection() {
        selectedIndices = ({})
        selectedCount = 0
        lastClickedIndex = -1
    }

    function selectOnly(idx) {
        var sel = {}
        sel[idx] = true
        selectedIndices = sel
        selectedCount = 1
        lastClickedIndex = idx
    }

    function toggleSelect(idx) {
        var sel = {}
        var keys = Object.keys(selectedIndices)
        for (var i = 0; i < keys.length; i++) {
            if (parseInt(keys[i]) !== idx) {
                sel[keys[i]] = true
            }
        }
        if (!selectedIndices[idx]) {
            sel[idx] = true
        }
        selectedIndices = sel
        selectedCount = Object.keys(sel).length
        lastClickedIndex = idx
    }

    function rangeSelect(idx) {
        if (lastClickedIndex < 0) {
            selectOnly(idx)
            return
        }
        var start = Math.min(lastClickedIndex, idx)
        var end = Math.max(lastClickedIndex, idx)
        var sel = {}
        for (var i = start; i <= end; i++) {
            sel[i] = true
        }
        selectedIndices = sel
        selectedCount = Object.keys(sel).length
        // keep lastClickedIndex as the anchor
    }

    function getSelectedResultIndices() {
        return Object.keys(selectedIndices).join(",")
    }

    function openAdd() {
        isEditing = false
        editingId = -1
        titleField.text = ""
        nativeTitleField.text = ""
        romajiTitleField.text = ""
        yearField.text = ""
        statusCombo.currentIndex = 0
        qualityCombo.currentIndex = 0
        sourceField.text = ""
        notesField.text = ""
        posterUrlField.text = ""
        searchQuery.text = ""
        searchYear.text = ""
        searchModel.clear()
        clearSelection()
        hasSearched = false
        show()
    }

    function openEdit(row) {
        isEditing = true
        hasSearched = false
        clearSelection()
        searchModel.clear()

        // Load item data from MediaModel using role numbers
        // MediaModel roles: ID=256, Title=257, NativeTitle=258, RomajiTitle=259,
        //   Year=260, MediaType=261, Status=262, QualityType=263,
        //   Source=264, Notes=265, PosterPath=266, HasPoster=267
        var mi = mediaModel.index(row, 0)
        editingId = mediaModel.data(mi, 256) || -1  // ID
        titleField.text = mediaModel.data(mi, 257) || ""
        nativeTitleField.text = mediaModel.data(mi, 258) || ""
        romajiTitleField.text = mediaModel.data(mi, 259) || ""
        var yr = mediaModel.data(mi, 260) || 0
        yearField.text = yr > 0 ? String(yr) : ""

        // Status combo
        var status = mediaModel.data(mi, 262) || "On Drive"
        var statusIdx = statusCombo.find(status)
        statusCombo.currentIndex = statusIdx >= 0 ? statusIdx : 0

        // Quality combo
        var quality = mediaModel.data(mi, 263) || ""
        var qualIdx = qualityCombo.find(quality)
        qualityCombo.currentIndex = qualIdx >= 0 ? qualIdx : 0

        // Source, Notes
        sourceField.text = mediaModel.data(mi, 264) || ""
        notesField.text = mediaModel.data(mi, 265) || ""

        // Poster path (model already returns file:// prefixed)
        var pp = mediaModel.data(mi, 266) || ""
        if (pp.toString().startsWith("file://")) pp = pp.toString().substring(7)
        posterUrlField.text = pp

        show()
    }

    function onSearchDone() {
        clearSelection()
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

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 16

                Text {
                    text: editWin.isEditing ? "Edit Item" : "Add Item"
                    color: _t.textWhite
                    font.pixelSize: 17
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
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

                // ---- Online Search (add mode only) ----
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 8
                    visible: !editWin.isEditing

                    Text {
                        text: "Search Online"
                        color: _t.textPrimary
                        font.pixelSize: 13
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TextField {
                            id: searchQuery
                            Layout.fillWidth: true
                            placeholderText: "Search title..."
                            placeholderTextColor: _t.textMuted
                            color: _t.textPrimary
                            font.pixelSize: 13
                            background: Rectangle {
                                color: _t.surfaceDark
                                border.color: searchQuery.activeFocus ? _t.accent : _t.borderSubtle
                                radius: 8
                            }
                            onAccepted: doSearch()
                        }

                        TextField {
                            id: searchYear
                            Layout.preferredWidth: 60
                            placeholderText: "Year"
                            placeholderTextColor: _t.textMuted
                            color: _t.textPrimary
                            font.pixelSize: 13
                            validator: IntValidator { bottom: 1900; top: 2099 }
                            background: Rectangle {
                                color: _t.surfaceDark
                                border.color: searchYear.activeFocus ? _t.accent : _t.borderSubtle
                                radius: 8
                            }
                            onAccepted: doSearch()
                        }

                        Rectangle {
                            Layout.preferredWidth: 70
                            Layout.preferredHeight: 36
                            radius: 8
                            color: searchBtnMouse.containsMouse ? _t.accentHover : _t.accent

                            Text {
                                anchors.centerIn: parent
                                text: editWin.searching ? "..." : "Search"
                                color: _t.textWhite
                                font.pixelSize: 13
                                font.bold: true
                            }
                            MouseArea {
                                id: searchBtnMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: doSearch()
                            }
                        }
                    }

                    // Search results (always visible after first search)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        visible: editWin.hasSearched
                        color: _t.surfaceDark
                        radius: 8
                        border.color: _t.borderSubtle
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: searchResultsList.count > 0
                                        ? searchResultsList.count + " results — Click to select, Ctrl+Click multi, Shift+Click range"
                                        : "No results"
                                    color: _t.textMuted
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: editWin.selectedCount > 0 ? editWin.selectedCount + " selected" : ""
                                    color: _t.accent
                                    font.pixelSize: 11
                                }
                            }

                            ListView {
                                id: searchResultsList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 4
                                model: searchModel

                                delegate: Rectangle {
                                    id: resultDelegate
                                    width: searchResultsList.width
                                    height: 56
                                    radius: 8

                                    property bool isSelected: editWin.selectedIndices[index] === true

                                    color: isSelected ? _t.accentBg : (srMouse.containsMouse ? "#0dffffff" : "transparent")
                                    border.width: isSelected ? 1 : 0
                                    border.color: isSelected ? _t.accent : "transparent"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 10

                                        // Poster thumb
                                        Rectangle {
                                            Layout.preferredWidth: 36
                                            Layout.preferredHeight: 48
                                            radius: 4
                                            color: _t.surface
                                            clip: true

                                            Image {
                                                anchors.fill: parent
                                                source: model.hasPoster ? model.posterPath : ""
                                                fillMode: Image.PreserveAspectCrop
                                                visible: model.hasPoster || false
                                                asynchronous: true
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            Text {
                                                text: model.title
                                                color: _t.textPrimary
                                                font.pixelSize: 13
                                                font.bold: true
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                            Text {
                                                text: model.year > 0 ? String(model.year) : "Unknown year"
                                                color: _t.textMuted
                                                font.pixelSize: 11
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

                                        Text {
                                            text: resultDelegate.isSelected ? "✓" : ""
                                            color: _t.accent
                                            font.pixelSize: 18
                                            font.bold: true
                                        }
                                    }

                                    MouseArea {
                                        id: srMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: (mouse) => {
                                            if (mouse.modifiers & Qt.ShiftModifier) {
                                                editWin.rangeSelect(index)
                                            } else if (mouse.modifiers & Qt.ControlModifier) {
                                                editWin.toggleSelect(index)
                                            } else {
                                                editWin.selectOnly(index)
                                            }
                                            // Auto-fill form when exactly 1 selected
                                            if (editWin.selectedCount === 1) {
                                                var selIdx = parseInt(Object.keys(editWin.selectedIndices)[0])
                                                autoFillFromResult(selIdx)
                                            }
                                        }
                                    }
                                }
                            }

                            // Placeholder when no results
                            Text {
                                anchors.centerIn: parent
                                text: editWin.searching ? "Searching..." : "Search above to find titles online"
                                color: _t.textMuted
                                font.pixelSize: 13
                                visible: searchResultsList.count === 0
                            }
                        }
                    }

                    // Batch add button
                    RowLayout {
                        Layout.fillWidth: true
                        visible: editWin.selectedCount > 1

                        Text {
                            text: editWin.selectedCount + " items selected"
                            color: _t.accent
                            font.pixelSize: 12
                        }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            Layout.preferredWidth: addAllText.implicitWidth + 24
                            Layout.preferredHeight: 32
                            radius: 8
                            color: addAllMouse.containsMouse ? _t.accentHover : _t.accent

                            Text {
                                id: addAllText
                                anchors.centerIn: parent
                                text: "Add All Selected"
                                color: _t.textWhite
                                font.pixelSize: 13
                                font.bold: true
                            }
                            MouseArea {
                                id: addAllMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    controller.addSearchResults(editWin.getSelectedResultIndices())
                                    editWin.close()
                                }
                            }
                        }
                    }
                }

                // ---- Form Fields ----
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    spacing: 16

                    // Poster preview
                    Rectangle {
                        Layout.preferredWidth: 140
                        Layout.preferredHeight: 210
                        radius: 8
                        color: _t.surfaceDark
                        clip: true
                        visible: posterUrlField.text !== ""

                        Image {
                            anchors.fill: parent
                            source: posterUrlField.text !== "" ? "file://" + posterUrlField.text : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                    }

                    // Form
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        // Title
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Text { text: "Title"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                            TextField {
                                id: titleField; Layout.fillWidth: true
                                color: _t.textPrimary; font.pixelSize: 13
                                background: Rectangle { color: _t.surfaceDark; border.color: titleField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                            }
                        }

                        // Romaji + Native (anime)
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12
                            visible: activePage === "Anime"

                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Romaji Title"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                TextField {
                                    id: romajiTitleField; Layout.fillWidth: true
                                    color: _t.textPrimary; font.pixelSize: 13
                                    background: Rectangle { color: _t.surfaceDark; border.color: romajiTitleField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Native Title"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                TextField {
                                    id: nativeTitleField; Layout.fillWidth: true
                                    color: _t.textPrimary; font.pixelSize: 13
                                    background: Rectangle { color: _t.surfaceDark; border.color: nativeTitleField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                                }
                            }
                        }

                        // Year + Status
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Year"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                TextField {
                                    id: yearField; Layout.fillWidth: true
                                    color: _t.textPrimary; font.pixelSize: 13
                                    validator: IntValidator { bottom: 1900; top: 2099 }
                                    background: Rectangle { color: _t.surfaceDark; border.color: yearField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Status"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                ComboBox {
                                    id: statusCombo; Layout.fillWidth: true
                                    model: ["On Drive", "To Download", "To Work On"]
                                }
                            }
                        }

                        // Quality + Source
                        RowLayout {
                            Layout.fillWidth: true; spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Quality Type"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                ComboBox {
                                    id: qualityCombo; Layout.fillWidth: true
                                    model: {
                                        var types = controller.getQualityTypes().split("\n").filter(s => s !== "")
                                        return [""].concat(types)
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { text: "Source"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                                TextField {
                                    id: sourceField; Layout.fillWidth: true
                                    color: _t.textPrimary; font.pixelSize: 13
                                    background: Rectangle { color: _t.surfaceDark; border.color: sourceField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                                }
                            }
                        }

                        // Notes
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Text { text: "Notes"; color: _t.textSecondary; font.pixelSize: 12; font.bold: true }
                            TextArea {
                                id: notesField; Layout.fillWidth: true; Layout.preferredHeight: 80
                                color: _t.textPrimary; font.pixelSize: 13
                                wrapMode: TextEdit.Wrap
                                background: Rectangle { color: _t.surfaceDark; border.color: notesField.activeFocus ? _t.accent : _t.borderSubtle; radius: 8 }
                            }
                        }

                        // Hidden poster URL
                        TextField {
                            id: posterUrlField
                            visible: false
                        }
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
                            color: cancelMouse.containsMouse ? _t.textPrimary : _t.textSecondary
                            font.pixelSize: 13
                        }
                        MouseArea {
                            id: cancelMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: editWin.close()
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 80; Layout.preferredHeight: 36
                        radius: 8
                        color: saveMouse.containsMouse ? _t.accentHover : _t.accent
                        Text {
                            anchors.centerIn: parent
                            text: editWin.isEditing ? "Update" : "Add"
                            color: _t.textWhite
                            font.pixelSize: 13
                            font.bold: true
                        }
                        MouseArea {
                            id: saveMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: saveItem()
                        }
                    }
                }
            }
        }
    }

    function doSearch() {
        var q = searchQuery.text.trim()
        if (q === "") return
        hasSearched = true
        clearSelection()
        var y = parseInt(searchYear.text) || 0
        controller.searchOnline(q, y)
    }

    function autoFillFromResult(idx) {
        // Read from searchModel roles
        var mi = searchModel.index(idx, 0)
        titleField.text = searchModel.data(mi, 256) || "" // Title role
        nativeTitleField.text = searchModel.data(mi, 257) || ""
        romajiTitleField.text = searchModel.data(mi, 258) || ""
        var yr = searchModel.data(mi, 259) || 0
        yearField.text = yr > 0 ? String(yr) : ""
        // poster path
        var pp = searchModel.data(mi, 261) || ""
        if (pp.startsWith("file://")) pp = pp.substring(7)
        posterUrlField.text = pp
    }

    function saveItem() {
        controller.saveItem(
            editWin.editingId,
            titleField.text,
            nativeTitleField.text,
            romajiTitleField.text,
            parseInt(yearField.text) || 0,
            statusCombo.currentText,
            qualityCombo.currentText,
            sourceField.text,
            notesField.text,
            posterUrlField.text
        )
        editWin.close()
    }
}
