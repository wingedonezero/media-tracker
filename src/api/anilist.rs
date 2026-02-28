use crate::models::SearchResult;
use reqwest::Client;
use serde_json::{json, Value};

const ANILIST_URL: &str = "https://graphql.anilist.co";
const MAX_RETRIES: u32 = 3;

fn strip_html_tags(s: &str) -> String {
    let mut result = String::new();
    let mut in_tag = false;
    for ch in s.chars() {
        match ch {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => result.push(ch),
            _ => {}
        }
    }
    result
}

fn resolve_title(title: &Value) -> (String, Option<String>, Option<String>) {
    let english = title["english"].as_str().map(|s| s.to_string());
    let romaji = title["romaji"].as_str().map(|s| s.to_string());
    let native = title["native"].as_str().map(|s| s.to_string());

    let display_title = english
        .clone()
        .or_else(|| romaji.clone())
        .unwrap_or_default();

    (display_title, native, romaji)
}

async fn make_request(
    client: &Client,
    query: &str,
    variables: &Value,
) -> Result<Value, String> {
    let body = json!({
        "query": query,
        "variables": variables,
    });

    for retry in 0..=MAX_RETRIES {
        let resp = client
            .post(ANILIST_URL)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("AniList request failed: {}", e))?;

        if resp.status().as_u16() == 429 && retry < MAX_RETRIES {
            let delay = 5 * (1 << retry); // 5s, 10s, 20s
            tokio::time::sleep(std::time::Duration::from_secs(delay)).await;
            continue;
        }

        if !resp.status().is_success() {
            return Err(format!("AniList error: HTTP {}", resp.status()));
        }

        let data: Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse AniList response: {}", e))?;

        return Ok(data);
    }

    Err("AniList: max retries exceeded".into())
}

pub async fn search_anime(
    client: &Client,
    query: &str,
    year: Option<i32>,
    include_adult: bool,
) -> Result<Vec<SearchResult>, String> {
    let gql = if !include_adult {
        r#"
            query ($search: String, $seasonYear: Int) {
                Page(page: 1, perPage: 50) {
                    media(search: $search, seasonYear: $seasonYear, type: ANIME, sort: SEARCH_MATCH, isAdult: false) {
                        id
                        title {
                            english
                            romaji
                            native
                        }
                        seasonYear
                        description
                        coverImage {
                            large
                        }
                    }
                }
            }
        "#
    } else {
        r#"
            query ($search: String, $seasonYear: Int) {
                Page(page: 1, perPage: 50) {
                    media(search: $search, seasonYear: $seasonYear, type: ANIME, sort: SEARCH_MATCH) {
                        id
                        title {
                            english
                            romaji
                            native
                        }
                        seasonYear
                        description
                        coverImage {
                            large
                        }
                    }
                }
            }
        "#
    };

    let mut variables = json!({ "search": query });
    if let Some(y) = year {
        variables["seasonYear"] = json!(y);
    }

    let data = make_request(client, gql, &variables).await?;

    let results = data["data"]["Page"]["media"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|m| {
            let (title, native_title, romaji_title) = resolve_title(&m["title"]);
            SearchResult {
                api_id: m["id"].as_i64().unwrap_or(0),
                title,
                native_title,
                romaji_title,
                year: m["seasonYear"].as_i64().map(|y| y as i32),
                overview: m["description"]
                    .as_str()
                    .map(|d| strip_html_tags(d)),
                poster_url: m["coverImage"]["large"]
                    .as_str()
                    .map(|s| s.to_string()),
            }
        })
        .collect();

    Ok(results)
}
