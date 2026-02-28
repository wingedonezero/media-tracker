use cxx_qt_build::{CxxQtBuilder, QmlModule};

fn main() {
    CxxQtBuilder::new_qml_module(
        QmlModule::new("com.mediatracker")
            .qml_file("qml/main.qml")
            .qml_file("qml/Theme.qml")
            .qml_file("qml/MediaCard.qml")
            .qml_file("qml/MediaGrid.qml")
            .qml_file("qml/MediaTable.qml")
            .qml_file("qml/EditDialog.qml")
            .qml_file("qml/SettingsDialog.qml")
            .qml_file("qml/Toast.qml")
    )
    .qt_module("Network")
    .files([
        "src/bridge.rs",
        "src/list_models.rs",
    ])
    .build();
}
