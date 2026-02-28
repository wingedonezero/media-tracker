use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MediaItem {
    pub id: Option<i64>,
    pub title: String,
    pub native_title: Option<String>,
    pub romaji_title: Option<String>,
    pub year: Option<i32>,
    pub media_type: String,
    pub status: String,
    pub quality_type: Option<String>,
    pub source: Option<String>,
    pub notes: Option<String>,
    pub tmdb_id: Option<i64>,
    pub anilist_id: Option<i64>,
    pub poster_url: Option<String>,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub api_id: i64,
    pub title: String,
    pub native_title: Option<String>,
    pub romaji_title: Option<String>,
    pub year: Option<i32>,
    pub overview: Option<String>,
    pub poster_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchAddResult {
    pub added: i32,
    pub skipped: i32,
    pub errors: i32,
    pub added_items: Vec<String>,
    pub skipped_items: Vec<String>,
    pub error_items: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub tmdb_api_key: String,
    pub quality_types: Vec<String>,
    pub view_mode: String,
    #[serde(default)]
    pub include_adult: bool,
    #[serde(default = "default_row_height")]
    pub row_height: i32,
}

fn default_row_height() -> i32 {
    44
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            tmdb_api_key: String::new(),
            quality_types: vec![
                "BluRay".into(),
                "BluRay 1080p".into(),
                "BluRay 2160p".into(),
                "Remux".into(),
                "Remux 1080p".into(),
                "Remux 2160p".into(),
                "WEB-DL 1080p".into(),
                "WEB-DL 2160p".into(),
                "WebDL".into(),
            ],
            view_mode: "grid".into(),
            include_adult: false,
            row_height: 44,
        }
    }
}
