#[cxx_qt::bridge]
pub mod qobject {
    unsafe extern "C++" {
        include!("cxx-qt-lib/qstring.h");
        type QString = cxx_qt_lib::QString;
    }

    extern "RustQt" {
        #[qobject]
        #[qml_element]
        #[qproperty(QString, active_page)]
        #[qproperty(QString, active_status)]
        #[qproperty(QString, view_mode)]
        #[qproperty(QString, search_term)]
        #[qproperty(bool, loading)]
        #[qproperty(i32, movie_count)]
        #[qproperty(i32, tv_count)]
        #[qproperty(i32, anime_count)]
        #[qproperty(i32, item_count)]
        #[qproperty(QString, sort_field)]
        #[qproperty(QString, sort_dir)]
        #[qproperty(i32, row_height)]
        // Settings
        #[qproperty(QString, tmdb_api_key)]
        #[qproperty(bool, include_adult)]
        type AppController = super::AppControllerRust;

        // Navigation
        #[qinvokable]
        #[cxx_name = "navigateTo"]
        fn navigate_to(self: Pin<&mut Self>, page: &QString);

        #[qinvokable]
        #[cxx_name = "setStatus"]
        fn set_status_filter(self: Pin<&mut Self>, status: &QString);

        #[qinvokable]
        #[cxx_name = "setSearchTerm"]
        fn set_search_term_filter(self: Pin<&mut Self>, term: &QString);

        #[qinvokable]
        #[cxx_name = "setViewMode"]
        fn set_view_mode_pref(self: Pin<&mut Self>, mode: &QString);

        // Item operations
        #[qinvokable]
        #[cxx_name = "saveItem"]
        fn save_item(
            self: Pin<&mut Self>,
            id: i32,
            title: &QString,
            native_title: &QString,
            romaji_title: &QString,
            year: i32,
            status: &QString,
            quality_type: &QString,
            source: &QString,
            notes: &QString,
            poster_url: &QString,
        );

        #[qinvokable]
        #[cxx_name = "deleteItems"]
        fn delete_items(self: Pin<&mut Self>, ids: &QString); // comma-separated

        #[qinvokable]
        #[cxx_name = "moveItems"]
        fn move_items(self: Pin<&mut Self>, ids: &QString, new_status: &QString);

        // Online search
        #[qinvokable]
        #[cxx_name = "searchOnline"]
        fn search_online(self: Pin<&mut Self>, query: &QString, year: i32);

        #[qinvokable]
        #[cxx_name = "addSearchResults"]
        fn add_search_results(self: Pin<&mut Self>, indices: &QString); // comma-separated

        // Settings
        #[qinvokable]
        #[cxx_name = "saveSettings"]
        fn save_settings(self: Pin<&mut Self>, api_key: &QString, include_adult: bool, quality_types: &QString);

        #[qinvokable]
        #[cxx_name = "getQualityTypes"]
        fn get_quality_types(&self) -> QString;

        #[qinvokable]
        #[cxx_name = "getStatusOptions"]
        fn get_status_options(&self) -> QString;

        /// Load saved config values into controller properties (call on startup)
        #[qinvokable]
        #[cxx_name = "loadConfig"]
        fn load_config(self: Pin<&mut Self>);

        #[qinvokable]
        #[cxx_name = "setSortOrder"]
        fn set_sort_order(self: Pin<&mut Self>, field: &QString, dir: &QString);

        #[qinvokable]
        #[cxx_name = "setRowHeight"]
        fn set_row_height_pref(self: Pin<&mut Self>, height: i32);

        // Signals
        #[qsignal]
        #[cxx_name = "itemsChanged"]
        fn items_changed(self: Pin<&mut Self>);

        #[qsignal]
        #[cxx_name = "searchResultsReady"]
        fn search_results_ready(self: Pin<&mut Self>);

        #[qsignal]
        #[cxx_name = "searchingChanged"]
        fn searching_changed(self: Pin<&mut Self>, searching: bool);

        #[qsignal]
        #[cxx_name = "toastMessage"]
        fn toast_message(self: Pin<&mut Self>, message: QString, toast_type: QString);

        #[qsignal]
        #[cxx_name = "countsChanged"]
        fn counts_changed(self: Pin<&mut Self>);

        #[qsignal]
        #[cxx_name = "settingsLoaded"]
        fn settings_loaded(self: Pin<&mut Self>);
    }

    // Threading must be outside extern blocks
    impl cxx_qt::Threading for AppController {}
}

use core::pin::Pin;
use cxx_qt::Threading;
use cxx_qt_lib::QString;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use crate::api;
use crate::config;
use crate::db;
use crate::images;
use crate::models::{AppConfig, MediaItem, SearchResult};

/// Shared app state accessible from the bridge
pub struct AppState {
    pub db: Mutex<rusqlite::Connection>,
    pub config: Mutex<AppConfig>,
    pub config_path: PathBuf,
    pub data_dir: PathBuf,
    pub search_results: Mutex<Vec<SearchResult>>,
}

/// Global app state, initialized once
static APP_STATE: std::sync::OnceLock<Arc<AppState>> = std::sync::OnceLock::new();

pub fn init_app_state() -> Arc<AppState> {
    let data_dir = get_data_dir();
    let conn = db::connection::init_db(&data_dir).expect("Failed to initialize database");
    let (cfg, config_path) = config::manager::load_config(&data_dir).expect("Failed to load config");

    let state = Arc::new(AppState {
        db: Mutex::new(conn),
        config: Mutex::new(cfg),
        config_path,
        data_dir,
        search_results: Mutex::new(Vec::new()),
    });

    APP_STATE.set(state.clone()).ok();
    state
}

pub fn get_app_state() -> Arc<AppState> {
    APP_STATE.get().expect("App state not initialized").clone()
}

fn get_data_dir() -> PathBuf {
    let exe_path = std::env::current_exe().expect("Failed to get executable path");
    let exe_dir = exe_path.parent().expect("Failed to get executable directory");
    exe_dir.join("data")
}

#[derive(Default)]
pub struct AppControllerRust {
    active_page: QString,
    active_status: QString,
    view_mode: QString,
    search_term: QString,
    loading: bool,
    movie_count: i32,
    tv_count: i32,
    anime_count: i32,
    item_count: i32,
    sort_field: QString,
    sort_dir: QString,
    row_height: i32,
    tmdb_api_key: QString,
    include_adult: bool,
}

impl qobject::AppController {
    /// Initialize controller with data from DB/config
    pub fn navigate_to(mut self: Pin<&mut Self>, page: &QString) {
        self.as_mut().set_active_page(page.clone());
        self.as_mut().set_active_status(QString::from("On Drive"));
        self.as_mut().set_search_term(QString::from(""));
        self.as_mut().reload_items();
        self.as_mut().reload_counts();
    }

    pub fn set_status_filter(mut self: Pin<&mut Self>, status: &QString) {
        self.as_mut().set_active_status(status.clone());
        self.as_mut().reload_items();
    }

    pub fn set_search_term_filter(mut self: Pin<&mut Self>, term: &QString) {
        self.as_mut().set_search_term(term.clone());
        self.as_mut().reload_items();
    }

    pub fn set_view_mode_pref(mut self: Pin<&mut Self>, mode: &QString) {
        self.as_mut().set_view_mode(mode.clone());
        let state = get_app_state();
        let mut cfg = state.config.lock().unwrap();
        cfg.view_mode = mode.to_string();
        let _ = config::manager::save_config(&cfg, &state.config_path);
    }

    pub fn save_item(
        mut self: Pin<&mut Self>,
        id: i32,
        title: &QString,
        native_title: &QString,
        romaji_title: &QString,
        year: i32,
        status: &QString,
        quality_type: &QString,
        source: &QString,
        notes: &QString,
        poster_url: &QString,
    ) {
        let state = get_app_state();
        let conn = state.db.lock().unwrap();
        let media_type = self.active_page().to_string();

        let item = MediaItem {
            id: if id >= 0 { Some(id as i64) } else { None },
            title: title.to_string(),
            native_title: opt_string(native_title),
            romaji_title: opt_string(romaji_title),
            year: if year > 0 { Some(year) } else { None },
            media_type,
            status: status.to_string(),
            quality_type: opt_string(quality_type),
            source: opt_string(source),
            notes: opt_string(notes),
            tmdb_id: None,
            anilist_id: None,
            poster_url: opt_string(poster_url),
            created_at: None,
            updated_at: None,
        };

        let result = if id >= 0 {
            db::queries::update_item(&conn, &item).map(|_| "Item updated".to_string())
        } else {
            db::queries::add_item(&conn, &item).map(|_| "Item added".to_string())
        };

        drop(conn);

        match result {
            Ok(msg) => {
                self.as_mut().toast_message(QString::from(&msg), QString::from("success"));
                self.as_mut().reload_items();
                self.as_mut().reload_counts();
            }
            Err(e) => {
                self.as_mut().toast_message(
                    QString::from(&format!("Error: {}", e)),
                    QString::from("error"),
                );
            }
        }
    }

    pub fn delete_items(mut self: Pin<&mut Self>, ids: &QString) {
        let id_vec: Vec<i64> = ids
            .to_string()
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect();

        if id_vec.is_empty() {
            return;
        }

        let state = get_app_state();
        let conn = state.db.lock().unwrap();

        // Collect poster paths before deleting so we can clean up cached images
        let poster_paths = db::queries::get_poster_urls(&conn, &id_vec).unwrap_or_default();

        match db::queries::delete_items_batch(&conn, &id_vec) {
            Ok(_) => {
                drop(conn);
                for path in &poster_paths {
                    images::cache::delete_cached_poster(path);
                }
                let count = id_vec.len();
                self.as_mut().toast_message(
                    QString::from(&format!("Deleted {} item(s)", count)),
                    QString::from("success"),
                );
                self.as_mut().reload_items();
                self.as_mut().reload_counts();
            }
            Err(e) => {
                drop(conn);
                self.as_mut().toast_message(
                    QString::from(&format!("Delete failed: {}", e)),
                    QString::from("error"),
                );
            }
        }
    }

    pub fn move_items(mut self: Pin<&mut Self>, ids: &QString, new_status: &QString) {
        let id_vec: Vec<i64> = ids
            .to_string()
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect();

        if id_vec.is_empty() {
            return;
        }

        let state = get_app_state();
        let conn = state.db.lock().unwrap();
        match db::queries::move_items(&conn, &id_vec, &new_status.to_string()) {
            Ok(_) => {
                drop(conn);
                self.as_mut().toast_message(
                    QString::from(&format!("Moved {} item(s)", id_vec.len())),
                    QString::from("success"),
                );
                self.as_mut().reload_items();
            }
            Err(e) => {
                drop(conn);
                self.as_mut().toast_message(
                    QString::from(&format!("Move failed: {}", e)),
                    QString::from("error"),
                );
            }
        }
    }

    pub fn search_online(mut self: Pin<&mut Self>, query: &QString, year: i32) {
        let query_str = query.to_string().trim().to_string();
        if query_str.is_empty() {
            return;
        }

        let media_type = self.active_page().to_string();
        let state = get_app_state();
        let (api_key, include_adult) = {
            let cfg = state.config.lock().unwrap();
            (cfg.tmdb_api_key.clone(), cfg.include_adult)
        };

        self.as_mut().searching_changed(true);

        let qt_thread = self.qt_thread();
        let year_opt = if year > 0 { Some(year) } else { None };

        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let client = reqwest::Client::builder()
                    .timeout(std::time::Duration::from_secs(15))
                    .build()
                    .unwrap_or_default();

                let results = match media_type.as_str() {
                    "Movie" => {
                        if api_key.is_empty() {
                            Err("TMDB API key not set. Configure in Settings.".to_string())
                        } else {
                            api::tmdb::search_movie(&client, &api_key, &query_str, year_opt, include_adult).await
                        }
                    }
                    "TV" => {
                        if api_key.is_empty() {
                            Err("TMDB API key not set. Configure in Settings.".to_string())
                        } else {
                            api::tmdb::search_tv(&client, &api_key, &query_str, year_opt, include_adult).await
                        }
                    }
                    "Anime" => {
                        api::anilist::search_anime(&client, &query_str, year_opt, include_adult).await
                    }
                    _ => Err("Unknown media type".to_string()),
                };

                match results {
                    Ok(results) => {
                        let count = results.len();

                        // Store results in global state (posters are NOT cached yet —
                        // they're only downloaded when the user actually adds items)
                        let state = get_app_state();
                        *state.search_results.lock().unwrap() = results;

                        qt_thread.queue(move |mut ctrl: Pin<&mut qobject::AppController>| {
                            ctrl.as_mut().searching_changed(false);
                            ctrl.as_mut().toast_message(
                                QString::from(&format!("Found {} results", count)),
                                QString::from("success"),
                            );
                            ctrl.as_mut().search_results_ready();
                        }).unwrap();
                    }
                    Err(e) => {
                        qt_thread.queue(move |mut ctrl: Pin<&mut qobject::AppController>| {
                            ctrl.as_mut().searching_changed(false);
                            ctrl.as_mut().toast_message(
                                QString::from(&format!("Search failed: {}", e)),
                                QString::from("error"),
                            );
                        }).unwrap();
                    }
                }
            });
        });
    }

    pub fn add_search_results(self: Pin<&mut Self>, indices: &QString) {
        let idx_vec: Vec<usize> = indices
            .to_string()
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect();

        if idx_vec.is_empty() {
            return;
        }

        let state = get_app_state();
        let results = state.search_results.lock().unwrap();
        let media_type = self.active_page().to_string();
        let active_status = self.active_status().to_string();

        // Collect items and their poster URLs (not yet cached)
        let mut items_to_add: Vec<MediaItem> = Vec::new();
        let mut poster_urls: Vec<Option<String>> = Vec::new();
        for &idx in &idx_vec {
            if let Some(r) = results.get(idx) {
                poster_urls.push(r.poster_url.clone());
                let item = MediaItem {
                    id: None,
                    title: r.title.clone(),
                    native_title: r.native_title.clone(),
                    romaji_title: r.romaji_title.clone(),
                    year: r.year,
                    media_type: media_type.clone(),
                    status: active_status.clone(),
                    quality_type: None,
                    source: None,
                    notes: None,
                    tmdb_id: if media_type != "Anime" { Some(r.api_id) } else { None },
                    anilist_id: if media_type == "Anime" { Some(r.api_id) } else { None },
                    poster_url: None, // will be set after caching
                    created_at: None,
                    updated_at: None,
                };
                items_to_add.push(item);
            }
        }
        drop(results);

        // Cache posters synchronously (they're small images, and we only
        // download for the items actually being added)
        let cache_dir = state.data_dir.join("image_cache");
        let qt_thread = self.qt_thread();

        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let client = reqwest::Client::builder()
                    .timeout(std::time::Duration::from_secs(15))
                    .build()
                    .unwrap_or_default();

                for (i, url_opt) in poster_urls.iter().enumerate() {
                    if let Some(url) = url_opt {
                        if !url.is_empty() {
                            if let Ok(path) = images::cache::cache_poster(&client, &cache_dir, url).await {
                                items_to_add[i].poster_url = Some(path.to_string_lossy().to_string());
                            }
                        }
                    }
                }

                let state = get_app_state();
                let conn = state.db.lock().unwrap();
                match db::queries::add_items_batch(&conn, &items_to_add, true) {
                    Ok(result) => {
                        drop(conn);
                        let msg = format!(
                            "Added {}, skipped {} duplicates",
                            result.added, result.skipped
                        );
                        qt_thread.queue(move |mut ctrl: Pin<&mut qobject::AppController>| {
                            ctrl.as_mut().toast_message(QString::from(&msg), QString::from("success"));
                            ctrl.as_mut().reload_items();
                            ctrl.as_mut().reload_counts();
                        }).unwrap();
                    }
                    Err(e) => {
                        drop(conn);
                        let msg = format!("Error: {}", e);
                        qt_thread.queue(move |mut ctrl: Pin<&mut qobject::AppController>| {
                            ctrl.as_mut().toast_message(
                                QString::from(&msg),
                                QString::from("error"),
                            );
                        }).unwrap();
                    }
                }
            });
        });
    }

    pub fn save_settings(mut self: Pin<&mut Self>, api_key: &QString, include_adult: bool, quality_types: &QString) {
        let state = get_app_state();
        let mut cfg = state.config.lock().unwrap();
        cfg.tmdb_api_key = api_key.to_string();
        cfg.include_adult = include_adult;
        cfg.row_height = *self.row_height();
        cfg.quality_types = quality_types
            .to_string()
            .split('\n')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        match config::manager::save_config(&cfg, &state.config_path) {
            Ok(_) => {
                self.as_mut().set_tmdb_api_key(api_key.clone());
                self.as_mut().set_include_adult(include_adult);
                self.as_mut().toast_message(
                    QString::from("Settings saved"),
                    QString::from("success"),
                );
            }
            Err(e) => {
                self.as_mut().toast_message(
                    QString::from(&format!("Save failed: {}", e)),
                    QString::from("error"),
                );
            }
        }
    }

    pub fn get_quality_types(&self) -> QString {
        let state = get_app_state();
        let cfg = state.config.lock().unwrap();
        QString::from(&cfg.quality_types.join("\n"))
    }

    pub fn get_status_options(&self) -> QString {
        QString::from("On Drive\nTo Download\nTo Work On")
    }

    pub fn load_config(mut self: Pin<&mut Self>) {
        let state = get_app_state();
        let cfg = state.config.lock().unwrap();
        self.as_mut().set_view_mode(QString::from(&cfg.view_mode));
        self.as_mut().set_tmdb_api_key(QString::from(&cfg.tmdb_api_key));
        self.as_mut().set_include_adult(cfg.include_adult);
        self.as_mut().set_row_height(if cfg.row_height > 0 { cfg.row_height } else { 44 });
        self.as_mut().set_sort_field(QString::from("title"));
        self.as_mut().set_sort_dir(QString::from("ASC"));
    }

    pub fn set_sort_order(mut self: Pin<&mut Self>, field: &QString, dir: &QString) {
        self.as_mut().set_sort_field(field.clone());
        self.as_mut().set_sort_dir(dir.clone());
        self.as_mut().reload_items();
    }

    pub fn set_row_height_pref(mut self: Pin<&mut Self>, height: i32) {
        let h = height.clamp(30, 200);
        self.as_mut().set_row_height(h);
        let state = get_app_state();
        let mut cfg = state.config.lock().unwrap();
        cfg.row_height = h;
        let _ = config::manager::save_config(&cfg, &state.config_path);
    }

    // ---- Internal helpers ----

    fn reload_items(mut self: Pin<&mut Self>) {
        let page = self.active_page().to_string();
        let status = self.active_status().to_string();
        let search = self.search_term().to_string();

        let state = get_app_state();
        let conn = state.db.lock().unwrap();

        let search_opt = if search.is_empty() { None } else { Some(search.as_str()) };
        let count = db::queries::count_filtered_items(
            &conn, Some(&page), Some(&status), search_opt,
        ).unwrap_or(0);

        self.as_mut().set_item_count(count as i32);
        drop(conn);

        // Signal QML to reload MediaModel (which does its own query for the actual rows)
        self.as_mut().items_changed();
    }

    fn reload_counts(mut self: Pin<&mut Self>) {
        let state = get_app_state();
        let conn = state.db.lock().unwrap();
        if let Ok(counts) = db::queries::get_counts(&conn) {
            self.as_mut().set_movie_count(*counts.get("Movie").unwrap_or(&0) as i32);
            self.as_mut().set_tv_count(*counts.get("TV").unwrap_or(&0) as i32);
            self.as_mut().set_anime_count(*counts.get("Anime").unwrap_or(&0) as i32);
        }
        self.as_mut().counts_changed();
    }
}

fn opt_string(s: &QString) -> Option<String> {
    let st = s.to_string();
    if st.is_empty() {
        None
    } else {
        Some(st)
    }
}
