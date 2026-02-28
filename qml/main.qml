import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import com.mediatracker

ApplicationWindow {
    id: root
    visible: true
    width: 1200; height: 700
    minimumWidth: 800; minimumHeight: 500
    title: "Media Tracker"
    color: _t.surface

    Theme { id: _t }

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

    // ---- Dark-themed inline components for controls ----
    component DarkMenu: Menu {
        background: Rectangle {
            implicitWidth: 200
            color: _t.surfaceCard
            border.color: _t.borderSubtle
            border.width: 1
            radius: 8
        }
    }
    component DarkItem: MenuItem {
        id: _di
        background: Rectangle {
            implicitWidth: 200
            implicitHeight: 32
            color: _di.highlighted ? _t.surfaceCardHover : "transparent"
        }
        contentItem: Text {
            leftPadding: 12
            rightPadding: 12
            text: _di.text
            font.pixelSize: 13
            color: _di.enabled ? _t.textPrimary : _t.textMuted
            verticalAlignment: Text.AlignVCenter
        }
    }
    component DarkSep: MenuSeparator {
        contentItem: Rectangle {
            implicitHeight: 1
            color: _t.borderSubtle
        }
        background: Item {}
    }

    property string activePage: "Movie"
    property string activeStatus: "On Drive"
    property string viewMode: "grid"
    property string searchTerm: ""
    property var selectedIds: []
    property int lastClickedRow: -1

    // ---- Clipboard helper (uses Qt's native clipboard) ----
    TextInput {
        id: clipboardHelper
        visible: false
    }
    function copyToClipboard(text) {
        clipboardHelper.text = text
        clipboardHelper.selectAll()
        clipboardHelper.copy()
    }

    // ---- Backend Objects ----
    AppController {
        id: controller
        onItemsChanged: mediaModel.reload(activePage, activeStatus, searchTerm, controller.sort_field, controller.sort_dir)
        onSearchResultsReady: {
            searchModel.loadFromState()
            if (editDialog.visible) editDialog.onSearchDone()
        }
        onSearchingChanged: (searching) => {
            if (editDialog.visible) editDialog.searching = searching
        }
        onToastMessage: (message, type_) => toast.show(message, type_)
        onCountsChanged: {} // counts are properties, auto-update
        Component.onCompleted: {
            controller.loadConfig()
            activePage = "Movie"
            activeStatus = "On Drive"
            viewMode = controller.view_mode !== "" ? controller.view_mode : "grid"
            controller.navigateTo("Movie")
        }
    }

    MediaModel { id: mediaModel }
    SearchModel { id: searchModel }

    // ---- Main Layout ----
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ======== SIDEBAR ========
        Rectangle {
            Layout.preferredWidth: _t.sidebarWidth
            Layout.fillHeight: true
            color: _t.surfaceDark

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                // App title
                Text {
                    text: "Media Tracker"
                    color: _t.textWhite
                    font.pixelSize: 18
                    font.bold: true
                    Layout.bottomMargin: 12
                }

                // Nav items
                Repeater {
                    model: [
                        { page: "Movie", icon: "🎬", label: "Movies" },
                        { page: "TV", icon: "📺", label: "TV Shows" },
                        { page: "Anime", icon: "⛩", label: "Anime" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        radius: _t.borderRadius
                        color: activePage === modelData.page ? _t.accent : (navMouse.containsMouse ? _t.surfaceCardHover : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 10

                            Text {
                                text: modelData.icon
                                font.pixelSize: 16
                            }
                            Text {
                                text: modelData.label
                                color: activePage === modelData.page ? _t.textWhite : _t.textSecondary
                                font.pixelSize: 14
                                Layout.fillWidth: true
                            }
                            Text {
                                text: modelData.page === "Movie" ? controller.movie_count :
                                      modelData.page === "TV" ? controller.tv_count :
                                      controller.anime_count
                                color: _t.textMuted
                                font.pixelSize: 12
                            }
                        }

                        MouseArea {
                            id: navMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                activePage = modelData.page
                                activeStatus = "On Drive"
                                searchTerm = ""
                                selectedIds = []
                                lastClickedRow = -1
                                controller.navigateTo(modelData.page)
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // Settings button
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    radius: _t.borderRadius
                    color: settingsMouse.containsMouse ? _t.surfaceCardHover : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        spacing: 10
                        Text { text: "⚙"; font.pixelSize: 16 }
                        Text { text: "Settings"; color: _t.textSecondary; font.pixelSize: 14 }
                    }
                    MouseArea {
                        id: settingsMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: settingsDialog.show()
                    }
                }
            }

            // Right border
            Rectangle {
                width: 1
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                color: _t.borderSubtle
            }
        }

        // ======== MAIN CONTENT ========
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // ---- Top Bar ----
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: _t.surface

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    spacing: 12

                    // Page title
                    Text {
                        text: activePage === "Movie" ? "Movies" : activePage === "TV" ? "TV Shows" : "Anime"
                        color: _t.textWhite
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text {
                        text: controller.item_count + " items"
                        color: _t.textMuted
                        font.pixelSize: 13
                        Layout.leftMargin: 4
                    }

                    Item { Layout.fillWidth: true }

                    // Search box
                    Rectangle {
                        Layout.preferredWidth: 220
                        Layout.preferredHeight: 36
                        radius: _t.borderRadius
                        color: _t.surfaceDark
                        border.color: searchInput.activeFocus ? _t.accent : _t.borderSubtle
                        border.width: 1

                        TextField {
                            id: searchInput
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            placeholderText: "Search..."
                            placeholderTextColor: _t.textMuted
                            color: _t.textPrimary
                            font.pixelSize: 13
                            background: null
                            onTextChanged: {
                                searchTerm = text
                                controller.setSearchTerm(text)
                            }
                        }
                    }

                    // View mode toggle
                    Row {
                        spacing: 0
                        Rectangle {
                            width: 36; height: 36
                            radius: 6
                            color: viewMode === "grid" ? _t.accent : (gridMouse.containsMouse ? _t.surfaceCardHover : "transparent")
                            Text { anchors.centerIn: parent; text: "▦"; color: _t.textWhite; font.pixelSize: 16 }
                            MouseArea {
                                id: gridMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { viewMode = "grid"; controller.setViewMode("grid") }
                            }
                        }
                        Rectangle {
                            width: 36; height: 36
                            radius: 6
                            color: viewMode === "table" ? _t.accent : (tableMouse.containsMouse ? _t.surfaceCardHover : "transparent")
                            Text { anchors.centerIn: parent; text: "☰"; color: _t.textWhite; font.pixelSize: 16 }
                            MouseArea {
                                id: tableMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { viewMode = "table"; controller.setViewMode("table") }
                            }
                        }
                    }

                    // Add button
                    Rectangle {
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 36
                        radius: _t.borderRadius
                        color: addMouse.containsMouse ? _t.accentHover : _t.accent

                        Text {
                            anchors.centerIn: parent
                            text: "+ Add"
                            color: _t.textWhite
                            font.pixelSize: 13
                            font.bold: true
                        }
                        MouseArea {
                            id: addMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: editDialog.openAdd()
                        }
                    }
                }

                // Bottom border
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 1
                    color: _t.borderSubtle
                }
            }

            // ---- Status Tabs ----
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: _t.surface

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    spacing: 4

                    Repeater {
                        model: ["On Drive", "To Download", "To Work On"]
                        delegate: Rectangle {
                            Layout.preferredHeight: 32
                            Layout.preferredWidth: statusText.implicitWidth + 24
                            radius: 6
                            color: activeStatus === modelData ? _t.accent : (statusMouse.containsMouse ? _t.surfaceCardHover : "transparent")

                            Text {
                                id: statusText
                                anchors.centerIn: parent
                                text: modelData
                                color: activeStatus === modelData ? _t.textWhite : _t.textSecondary
                                font.pixelSize: 13
                            }
                            MouseArea {
                                id: statusMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    activeStatus = modelData
                                    selectedIds = []
                                    lastClickedRow = -1
                                    controller.setStatus(modelData)
                                }
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 1
                    color: _t.borderSubtle
                }
            }

            // ---- Content Area ----
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // Grid View
                MediaGrid {
                    id: mediaGrid
                    anchors.fill: parent
                    visible: viewMode === "grid"
                    model: mediaModel
                    selectedIds: root.selectedIds
                    onItemClicked: (row, modifiers) => handleItemClick(row, modifiers)
                    onItemDoubleClicked: (row) => handleItemDoubleClick(row)
                    onItemRightClicked: (row, mx, my) => showContextMenu(row, mx, my)
                }

                // Table View
                MediaTable {
                    id: mediaTable
                    anchors.fill: parent
                    visible: viewMode === "table"
                    model: mediaModel
                    selectedIds: root.selectedIds
                    rowHeight: controller.row_height
                    sortField: controller.sort_field
                    sortDir: controller.sort_dir
                    onItemClicked: (row, modifiers) => handleItemClick(row, modifiers)
                    onItemDoubleClicked: (row) => handleItemDoubleClick(row)
                    onItemRightClicked: (row, mx, my) => showContextMenu(row, mx, my)
                    onSortRequested: (field, dir) => controller.setSortOrder(field, dir)
                }

                // Empty state
                Text {
                    anchors.centerIn: parent
                    text: "No items found"
                    color: _t.textMuted
                    font.pixelSize: 16
                    visible: controller.item_count === 0
                }
            }
        }
    }

    // ---- Single Item Context Menu ----
    DarkMenu {
        id: contextMenu
        property int targetRow: -1

        DarkItem {
            text: "Edit"
            onTriggered: handleItemDoubleClick(contextMenu.targetRow)
        }

        // Copy Name — simple for Movie/TV
        DarkItem {
            text: "Copy Name"
            visible: activePage !== "Anime"
            onTriggered: copyToClipboard(mediaModel.getItemTitle(contextMenu.targetRow))
        }

        // Copy Name — submenu for Anime (English, Romaji, Japanese)
        DarkMenu {
            title: "Copy Name"
            visible: activePage === "Anime"

            DarkItem {
                text: {
                    var t = mediaModel.getItemTitle(contextMenu.targetRow)
                    return "English: " + (t.length > 35 ? t.substring(0, 35) + "..." : t)
                }
                onTriggered: copyToClipboard(mediaModel.getItemTitle(contextMenu.targetRow))
            }
            DarkItem {
                text: {
                    var t = mediaModel.getItemRomajiTitle(contextMenu.targetRow)
                    if (t === "") return ""
                    return "Romaji: " + (t.length > 35 ? t.substring(0, 35) + "..." : t)
                }
                visible: mediaModel.getItemRomajiTitle(contextMenu.targetRow) !== ""
                onTriggered: copyToClipboard(mediaModel.getItemRomajiTitle(contextMenu.targetRow))
            }
            DarkItem {
                text: {
                    var t = mediaModel.getItemNativeTitle(contextMenu.targetRow)
                    if (t === "") return ""
                    return "Japanese: " + (t.length > 35 ? t.substring(0, 35) + "..." : t)
                }
                visible: mediaModel.getItemNativeTitle(contextMenu.targetRow) !== ""
                onTriggered: copyToClipboard(mediaModel.getItemNativeTitle(contextMenu.targetRow))
            }
        }

        DarkSep {}
        DarkMenu {
            title: "Move to..."
            DarkItem { text: "On Drive"; onTriggered: controller.moveItems(String(mediaModel.getItemId(contextMenu.targetRow)), "On Drive") }
            DarkItem { text: "To Download"; onTriggered: controller.moveItems(String(mediaModel.getItemId(contextMenu.targetRow)), "To Download") }
            DarkItem { text: "To Work On"; onTriggered: controller.moveItems(String(mediaModel.getItemId(contextMenu.targetRow)), "To Work On") }
        }
        DarkSep {}
        DarkItem {
            text: "Delete"
            onTriggered: {
                deleteDialog.itemIds = [mediaModel.getItemId(contextMenu.targetRow)]
                deleteDialog.open()
            }
        }
    }

    // ---- Bulk Context Menu (multiple items selected) ----
    DarkMenu {
        id: bulkContextMenu

        DarkItem {
            text: selectedIds.length + " items selected"
            enabled: false
        }
        DarkSep {}
        DarkMenu {
            title: "Move all to..."
            DarkItem {
                text: "On Drive"
                onTriggered: { controller.moveItems(selectedIds.join(","), "On Drive"); selectedIds = [] }
            }
            DarkItem {
                text: "To Download"
                onTriggered: { controller.moveItems(selectedIds.join(","), "To Download"); selectedIds = [] }
            }
            DarkItem {
                text: "To Work On"
                onTriggered: { controller.moveItems(selectedIds.join(","), "To Work On"); selectedIds = [] }
            }
        }
        DarkSep {}
        DarkItem {
            text: "Delete " + selectedIds.length + " items"
            onTriggered: {
                deleteDialog.itemIds = selectedIds.slice()
                deleteDialog.open()
            }
        }
    }

    // ---- Delete Confirmation Dialog ----
    Dialog {
        id: deleteDialog
        modal: true
        anchors.centerIn: parent

        property var itemIds: []

        background: Rectangle {
            color: _t.surfaceCard
            border.color: _t.borderSubtle
            radius: 12
        }

        header: Rectangle {
            color: "transparent"
            height: 44
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: "Confirm Delete"
                color: _t.textPrimary
                font.pixelSize: 15
                font.bold: true
            }
        }

        Label {
            text: "Delete " + deleteDialog.itemIds.length + " item(s)? This cannot be undone."
            color: _t.textPrimary
        }

        footer: Rectangle {
            color: "transparent"
            height: 52
            RowLayout {
                anchors.fill: parent
                anchors.rightMargin: 12
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 60; Layout.preferredHeight: 32
                    color: "transparent"
                    Text {
                        anchors.centerIn: parent; text: "Cancel"
                        color: dlgCancelMouse.containsMouse ? _t.textPrimary : _t.textSecondary
                        font.pixelSize: 13
                    }
                    MouseArea {
                        id: dlgCancelMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: deleteDialog.reject()
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 70; Layout.preferredHeight: 32
                    radius: 8
                    color: dlgOkMouse.containsMouse ? _t.dangerHover : _t.danger
                    Text {
                        anchors.centerIn: parent; text: "Delete"
                        color: _t.textWhite; font.pixelSize: 13; font.bold: true
                    }
                    MouseArea {
                        id: dlgOkMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: deleteDialog.accept()
                    }
                }
            }
        }

        onAccepted: {
            controller.deleteItems(itemIds.join(","))
            selectedIds = []
        }
    }

    // ---- Edit Dialog (real OS window) ----
    EditDialog {
        id: editDialog
        controller: controller
        searchModel: searchModel
        mediaModel: mediaModel
        activePage: root.activePage
        activeStatus: root.activeStatus
    }

    // ---- Settings Dialog (real OS window) ----
    SettingsDialog {
        id: settingsDialog
        controller: controller
    }

    // ---- Toast ----
    Toast { id: toast }

    // ---- Helper Functions ----
    function handleItemClick(row, modifiers) {
        var id = mediaModel.getItemId(row)

        if (modifiers & Qt.ControlModifier) {
            // Ctrl+Click: toggle this item
            var arr = selectedIds.slice()
            var idx = arr.indexOf(id)
            if (idx >= 0) {
                arr.splice(idx, 1)
            } else {
                arr.push(id)
            }
            selectedIds = arr
            lastClickedRow = row
        } else if (modifiers & Qt.ShiftModifier) {
            // Shift+Click: range select from last clicked
            if (lastClickedRow < 0) lastClickedRow = 0
            var start = Math.min(lastClickedRow, row)
            var end = Math.max(lastClickedRow, row)
            var rangeIds = []
            for (var i = start; i <= end; i++) {
                rangeIds.push(mediaModel.getItemId(i))
            }
            selectedIds = rangeIds
        } else {
            // Plain click: select only this item
            selectedIds = [id]
            lastClickedRow = row
        }
    }

    function handleItemDoubleClick(row) {
        editDialog.openEdit(row)
    }

    function showContextMenu(row, mx, my) {
        // If right-clicked item is not in current selection, select it alone
        var id = mediaModel.getItemId(row)
        if (selectedIds.indexOf(id) < 0) {
            selectedIds = [id]
            lastClickedRow = row
        }

        if (selectedIds.length > 1) {
            bulkContextMenu.popup()
        } else {
            contextMenu.targetRow = row
            contextMenu.popup()
        }
    }
}
