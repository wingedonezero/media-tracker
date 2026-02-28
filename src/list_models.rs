#[cxx_qt::bridge]
pub mod qobject {
    unsafe extern "C++Qt" {
        include!(<QtCore/QAbstractListModel>);
        #[qobject]
        type QAbstractListModel;
    }

    unsafe extern "C++" {
        include!("cxx-qt-lib/qhash.h");
        type QHash_i32_QByteArray = cxx_qt_lib::QHash<cxx_qt_lib::QHashPair_i32_QByteArray>;

        include!("cxx-qt-lib/qvariant.h");
        type QVariant = cxx_qt_lib::QVariant;

        include!("cxx-qt-lib/qmodelindex.h");
        type QModelIndex = cxx_qt_lib::QModelIndex;

        include!("cxx-qt-lib/qstring.h");
        type QString = cxx_qt_lib::QString;
    }

    // ── MediaModel ──────────────────────────────────────────────────────
    extern "RustQt" {
        #[qobject]
        #[base = QAbstractListModel]
        #[qml_element]
        type MediaModel = super::MediaModelRust;

        #[qinvokable]
        #[cxx_override]
        fn data(self: &MediaModel, index: &QModelIndex, role: i32) -> QVariant;

        #[qinvokable]
        #[cxx_override]
        #[cxx_name = "roleNames"]
        fn role_names(self: &MediaModel) -> QHash_i32_QByteArray;

        #[qinvokable]
        #[cxx_override]
        #[cxx_name = "rowCount"]
        fn row_count(self: &MediaModel, parent: &QModelIndex) -> i32;

        #[qinvokable]
        fn reload(self: Pin<&mut MediaModel>, page: &QString, status: &QString, search: &QString, sort_field: &QString, sort_dir: &QString);

        #[qinvokable]
        #[cxx_name = "getItemId"]
        fn get_item_id(self: &MediaModel, row: i32) -> i32;

        #[qinvokable]
        #[cxx_name = "getItemTitle"]
        fn get_item_title(self: &MediaModel, row: i32) -> QString;

        #[qinvokable]
        #[cxx_name = "getItemNativeTitle"]
        fn get_item_native_title(self: &MediaModel, row: i32) -> QString;

        #[qinvokable]
        #[cxx_name = "getItemRomajiTitle"]
        fn get_item_romaji_title(self: &MediaModel, row: i32) -> QString;
    }

    extern "RustQt" {
        #[inherit]
        #[cxx_name = "beginResetModel"]
        unsafe fn begin_reset_model_media(self: Pin<&mut MediaModel>);
        #[inherit]
        #[cxx_name = "endResetModel"]
        unsafe fn end_reset_model_media(self: Pin<&mut MediaModel>);
    }

    // ── SearchModel ─────────────────────────────────────────────────────
    extern "RustQt" {
        #[qobject]
        #[base = QAbstractListModel]
        #[qml_element]
        #[qproperty(i32, selected_count)]
        type SearchModel = super::SearchModelRust;

        #[qinvokable]
        #[cxx_override]
        fn data(self: &SearchModel, index: &QModelIndex, role: i32) -> QVariant;

        #[qinvokable]
        #[cxx_override]
        #[cxx_name = "roleNames"]
        fn role_names(self: &SearchModel) -> QHash_i32_QByteArray;

        #[qinvokable]
        #[cxx_override]
        #[cxx_name = "rowCount"]
        fn row_count(self: &SearchModel, parent: &QModelIndex) -> i32;

        #[qinvokable]
        #[cxx_name = "loadFromState"]
        fn load_from_state(self: Pin<&mut SearchModel>);

        #[qinvokable]
        #[cxx_name = "toggleSelection"]
        fn toggle_selection(self: Pin<&mut SearchModel>, row: i32);

        #[qinvokable]
        #[cxx_name = "getSelectedIndices"]
        fn get_selected_indices(self: &SearchModel) -> QString;

        #[qinvokable]
        fn clear(self: Pin<&mut SearchModel>);
    }

    extern "RustQt" {
        #[inherit]
        #[cxx_name = "beginResetModel"]
        unsafe fn begin_reset_model_search(self: Pin<&mut SearchModel>);
        #[inherit]
        #[cxx_name = "endResetModel"]
        unsafe fn end_reset_model_search(self: Pin<&mut SearchModel>);
    }
}

use core::pin::Pin;
use cxx_qt::CxxQtType;
use cxx_qt_lib::{QByteArray, QHash, QHashPair_i32_QByteArray, QModelIndex, QString, QVariant};

use crate::bridge::get_app_state;
use crate::db;

// ═══════════════════════════════════════════════════════════════════════
// MediaModel roles & types
// ═══════════════════════════════════════════════════════════════════════

// Qt::UserRole = 0x0100 = 256
const MEDIA_ROLE_ID: i32 = 256;
const MEDIA_ROLE_TITLE: i32 = 257;
const MEDIA_ROLE_NATIVE_TITLE: i32 = 258;
const MEDIA_ROLE_ROMAJI_TITLE: i32 = 259;
const MEDIA_ROLE_YEAR: i32 = 260;
const MEDIA_ROLE_MEDIA_TYPE: i32 = 261;
const MEDIA_ROLE_STATUS: i32 = 262;
const MEDIA_ROLE_QUALITY_TYPE: i32 = 263;
const MEDIA_ROLE_SOURCE: i32 = 264;
const MEDIA_ROLE_NOTES: i32 = 265;
const MEDIA_ROLE_POSTER_PATH: i32 = 266;
const MEDIA_ROLE_HAS_POSTER: i32 = 267;

struct DisplayItem {
    id: i32,
    title: String,
    native_title: String,
    romaji_title: String,
    year: i32,
    media_type: String,
    status: String,
    quality_type: String,
    source: String,
    notes: String,
    poster_path: String,
    has_poster: bool,
}

#[derive(Default)]
pub struct MediaModelRust {
    items: Vec<DisplayItem>,
}

impl qobject::MediaModel {
    pub fn data(&self, index: &QModelIndex, role: i32) -> QVariant {
        let row = index.row() as usize;
        if let Some(item) = self.items.get(row) {
            return match role {
                MEDIA_ROLE_ID => QVariant::from(&item.id),
                MEDIA_ROLE_TITLE => QVariant::from(&QString::from(&item.title)),
                MEDIA_ROLE_NATIVE_TITLE => QVariant::from(&QString::from(&item.native_title)),
                MEDIA_ROLE_ROMAJI_TITLE => QVariant::from(&QString::from(&item.romaji_title)),
                MEDIA_ROLE_YEAR => QVariant::from(&item.year),
                MEDIA_ROLE_MEDIA_TYPE => QVariant::from(&QString::from(&item.media_type)),
                MEDIA_ROLE_STATUS => QVariant::from(&QString::from(&item.status)),
                MEDIA_ROLE_QUALITY_TYPE => QVariant::from(&QString::from(&item.quality_type)),
                MEDIA_ROLE_SOURCE => QVariant::from(&QString::from(&item.source)),
                MEDIA_ROLE_NOTES => QVariant::from(&QString::from(&item.notes)),
                MEDIA_ROLE_POSTER_PATH => QVariant::from(&QString::from(&item.poster_path)),
                MEDIA_ROLE_HAS_POSTER => QVariant::from(&item.has_poster),
                _ => QVariant::default(),
            };
        }
        QVariant::default()
    }

    pub fn role_names(&self) -> QHash<QHashPair_i32_QByteArray> {
        let mut roles = QHash::<QHashPair_i32_QByteArray>::default();
        roles.insert(MEDIA_ROLE_ID, QByteArray::from("itemId"));
        roles.insert(MEDIA_ROLE_TITLE, QByteArray::from("title"));
        roles.insert(MEDIA_ROLE_NATIVE_TITLE, QByteArray::from("nativeTitle"));
        roles.insert(MEDIA_ROLE_ROMAJI_TITLE, QByteArray::from("romajiTitle"));
        roles.insert(MEDIA_ROLE_YEAR, QByteArray::from("year"));
        roles.insert(MEDIA_ROLE_MEDIA_TYPE, QByteArray::from("mediaType"));
        roles.insert(MEDIA_ROLE_STATUS, QByteArray::from("status"));
        roles.insert(MEDIA_ROLE_QUALITY_TYPE, QByteArray::from("qualityType"));
        roles.insert(MEDIA_ROLE_SOURCE, QByteArray::from("source"));
        roles.insert(MEDIA_ROLE_NOTES, QByteArray::from("notes"));
        roles.insert(MEDIA_ROLE_POSTER_PATH, QByteArray::from("posterPath"));
        roles.insert(MEDIA_ROLE_HAS_POSTER, QByteArray::from("hasPoster"));
        roles
    }

    pub fn row_count(&self, _parent: &QModelIndex) -> i32 {
        self.items.len() as i32
    }

    pub fn reload(mut self: Pin<&mut Self>, page: &QString, status: &QString, search: &QString, sort_field: &QString, sort_dir: &QString) {
        let page_str = page.to_string();
        let status_str = status.to_string();
        let search_str = search.to_string();
        let sort_f = sort_field.to_string();
        let sort_d = sort_dir.to_string();

        let state = get_app_state();
        let conn = state.db.lock().unwrap();

        let db_items = if search_str.is_empty() {
            db::queries::get_items_sorted(&conn, Some(&page_str), Some(&status_str), &sort_f, &sort_d).unwrap_or_default()
        } else {
            db::queries::search_items(&conn, &search_str, Some(&page_str)).unwrap_or_default()
        };
        drop(conn);

        let data_dir = &state.data_dir;
        let display_items: Vec<DisplayItem> = db_items
            .iter()
            .map(|item| {
                let (poster_path, has_poster) = resolve_poster(item.poster_url.as_deref(), data_dir);
                DisplayItem {
                    id: item.id.unwrap_or(-1) as i32,
                    title: item.title.clone(),
                    native_title: item.native_title.clone().unwrap_or_default(),
                    romaji_title: item.romaji_title.clone().unwrap_or_default(),
                    year: item.year.unwrap_or(0),
                    media_type: item.media_type.clone(),
                    status: item.status.clone(),
                    quality_type: item.quality_type.clone().unwrap_or_default(),
                    source: item.source.clone().unwrap_or_default(),
                    notes: item.notes.clone().unwrap_or_default(),
                    poster_path,
                    has_poster,
                }
            })
            .collect();

        unsafe {
            self.as_mut().begin_reset_model_media();
            self.as_mut().rust_mut().items = display_items;
            self.as_mut().end_reset_model_media();
        }
    }

    pub fn get_item_id(&self, row: i32) -> i32 {
        self.items.get(row as usize).map(|i| i.id).unwrap_or(-1)
    }

    pub fn get_item_title(&self, row: i32) -> QString {
        self.items
            .get(row as usize)
            .map(|i| QString::from(&i.title))
            .unwrap_or_default()
    }

    pub fn get_item_native_title(&self, row: i32) -> QString {
        self.items
            .get(row as usize)
            .map(|i| QString::from(&i.native_title))
            .unwrap_or_default()
    }

    pub fn get_item_romaji_title(&self, row: i32) -> QString {
        self.items
            .get(row as usize)
            .map(|i| QString::from(&i.romaji_title))
            .unwrap_or_default()
    }
}

fn resolve_poster(poster_url: Option<&str>, _data_dir: &std::path::Path) -> (String, bool) {
    if let Some(url) = poster_url {
        if !url.is_empty() {
            let path = if url.starts_with("asset://localhost/") {
                url.replace("asset://localhost/", "")
            } else if url.starts_with('/') || url.contains("image_cache") {
                url.to_string()
            } else {
                url.to_string()
            };
            if std::path::Path::new(&path).exists() {
                return (format!("file://{}", path), true);
            }
        }
    }
    (String::new(), false)
}

// ═══════════════════════════════════════════════════════════════════════
// SearchModel roles & types
// ═══════════════════════════════════════════════════════════════════════

const SEARCH_ROLE_TITLE: i32 = 256;
const SEARCH_ROLE_NATIVE_TITLE: i32 = 257;
const SEARCH_ROLE_ROMAJI_TITLE: i32 = 258;
const SEARCH_ROLE_YEAR: i32 = 259;
const SEARCH_ROLE_OVERVIEW: i32 = 260;
const SEARCH_ROLE_POSTER_PATH: i32 = 261;
const SEARCH_ROLE_HAS_POSTER: i32 = 262;
const SEARCH_ROLE_SELECTED: i32 = 263;
const SEARCH_ROLE_INDEX: i32 = 264;

struct SearchItem {
    title: String,
    native_title: String,
    romaji_title: String,
    year: i32,
    overview: String,
    poster_path: String,
    has_poster: bool,
    selected: bool,
    index: i32,
}

#[derive(Default)]
pub struct SearchModelRust {
    items: Vec<SearchItem>,
    selected_count: i32,
}

impl qobject::SearchModel {
    pub fn data(&self, index: &QModelIndex, role: i32) -> QVariant {
        let row = index.row() as usize;
        if let Some(item) = self.items.get(row) {
            return match role {
                SEARCH_ROLE_TITLE => QVariant::from(&QString::from(&item.title)),
                SEARCH_ROLE_NATIVE_TITLE => QVariant::from(&QString::from(&item.native_title)),
                SEARCH_ROLE_ROMAJI_TITLE => QVariant::from(&QString::from(&item.romaji_title)),
                SEARCH_ROLE_YEAR => QVariant::from(&item.year),
                SEARCH_ROLE_OVERVIEW => QVariant::from(&QString::from(&item.overview)),
                SEARCH_ROLE_POSTER_PATH => QVariant::from(&QString::from(&item.poster_path)),
                SEARCH_ROLE_HAS_POSTER => QVariant::from(&item.has_poster),
                SEARCH_ROLE_SELECTED => QVariant::from(&item.selected),
                SEARCH_ROLE_INDEX => QVariant::from(&item.index),
                _ => QVariant::default(),
            };
        }
        QVariant::default()
    }

    pub fn role_names(&self) -> QHash<QHashPair_i32_QByteArray> {
        let mut roles = QHash::<QHashPair_i32_QByteArray>::default();
        roles.insert(SEARCH_ROLE_TITLE, QByteArray::from("title"));
        roles.insert(SEARCH_ROLE_NATIVE_TITLE, QByteArray::from("nativeTitle"));
        roles.insert(SEARCH_ROLE_ROMAJI_TITLE, QByteArray::from("romajiTitle"));
        roles.insert(SEARCH_ROLE_YEAR, QByteArray::from("year"));
        roles.insert(SEARCH_ROLE_OVERVIEW, QByteArray::from("overview"));
        roles.insert(SEARCH_ROLE_POSTER_PATH, QByteArray::from("posterPath"));
        roles.insert(SEARCH_ROLE_HAS_POSTER, QByteArray::from("hasPoster"));
        roles.insert(SEARCH_ROLE_SELECTED, QByteArray::from("selected"));
        roles.insert(SEARCH_ROLE_INDEX, QByteArray::from("resultIndex"));
        roles
    }

    pub fn row_count(&self, _parent: &QModelIndex) -> i32 {
        self.items.len() as i32
    }

    pub fn load_from_state(mut self: Pin<&mut Self>) {
        let state = get_app_state();
        let results = state.search_results.lock().unwrap();
        let poster_paths = state.cached_poster_paths.lock().unwrap();

        let items: Vec<SearchItem> = results
            .iter()
            .enumerate()
            .map(|(i, r)| {
                let poster_path = poster_paths
                    .get(i)
                    .and_then(|p| p.as_ref())
                    .map(|p| {
                        if std::path::Path::new(p).exists() {
                            format!("file://{}", p)
                        } else {
                            String::new()
                        }
                    })
                    .unwrap_or_default();
                let has_poster = !poster_path.is_empty();

                SearchItem {
                    title: r.title.clone(),
                    native_title: r.native_title.clone().unwrap_or_default(),
                    romaji_title: r.romaji_title.clone().unwrap_or_default(),
                    year: r.year.unwrap_or(0),
                    overview: r.overview.clone().unwrap_or_default(),
                    poster_path,
                    has_poster,
                    selected: false,
                    index: i as i32,
                }
            })
            .collect();

        drop(results);
        drop(poster_paths);

        unsafe {
            self.as_mut().begin_reset_model_search();
            self.as_mut().rust_mut().items = items;
            self.as_mut().set_selected_count(0);
            self.as_mut().end_reset_model_search();
        }
    }

    pub fn toggle_selection(mut self: Pin<&mut Self>, row: i32) {
        if let Some(item) = self.as_mut().rust_mut().items.get_mut(row as usize) {
            item.selected = !item.selected;
        }
        let count = self.items.iter().filter(|i| i.selected).count() as i32;
        self.as_mut().set_selected_count(count);

        // Notify QML the data changed - trigger full reset for simplicity
        unsafe {
            self.as_mut().begin_reset_model_search();
            self.as_mut().end_reset_model_search();
        }
    }

    pub fn get_selected_indices(&self) -> QString {
        let indices: Vec<String> = self
            .items
            .iter()
            .filter(|i| i.selected)
            .map(|i| i.index.to_string())
            .collect();
        QString::from(&indices.join(","))
    }

    pub fn clear(mut self: Pin<&mut Self>) {
        unsafe {
            self.as_mut().begin_reset_model_search();
            self.as_mut().rust_mut().items.clear();
            self.as_mut().set_selected_count(0);
            self.as_mut().end_reset_model_search();
        }
    }
}
