use crate::models::SearchResult;
use reqwest::Client;
use serde_json::Value;

const BASE_URL: &str = "https://api.themoviedb.org/3";
const IMAGE_BASE_URL: &str = "https://image.tmdb.org/t/p/w500";

fn extract_year(date_str: &str) -> Option<i32> {
    if date_str.len() >= 4 {
        date_str[..4].parse().ok()
    } else {
        None
    }
}

fn poster_url(path: Option<&str>) -> Option<String> {
    path.map(|p| format!("{}{}", IMAGE_BASE_URL, p))
}

fn parse_movie_results(data: &Value) -> Vec<SearchResult> {
    data["results"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|r| SearchResult {
            api_id: r["id"].as_i64().unwrap_or(0),
            title: r["title"].as_str().unwrap_or("").to_string(),
            native_title: None,
            romaji_title: None,
            year: r["release_date"].as_str().and_then(|d| extract_year(d)),
            overview: r["overview"].as_str().map(|s| s.to_string()),
            poster_url: poster_url(r["poster_path"].as_str()),
        })
        .collect()
}

fn parse_tv_results(data: &Value) -> Vec<SearchResult> {
    data["results"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|r| SearchResult {
            api_id: r["id"].as_i64().unwrap_or(0),
            title: r["name"].as_str().unwrap_or("").to_string(),
            native_title: None,
            romaji_title: None,
            year: r["first_air_date"].as_str().and_then(|d| extract_year(d)),
            overview: r["overview"].as_str().map(|s| s.to_string()),
            poster_url: poster_url(r["poster_path"].as_str()),
        })
        .collect()
}

async fn tmdb_search(
    client: &Client,
    endpoint: &str,
    params: &[(&str, String)],
) -> Result<(Value, i64), String> {
    let resp = client
        .get(&format!("{}/{}", BASE_URL, endpoint))
        .query(params)
        .send()
        .await
        .map_err(|e| format!("TMDB request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("TMDB error: HTTP {}", resp.status()));
    }

    let data: Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse TMDB response: {}", e))?;

    let total_pages = data["total_pages"].as_i64().unwrap_or(1);
    Ok((data, total_pages))
}

pub async fn search_movie(
    client: &Client,
    api_key: &str,
    query: &str,
    year: Option<i32>,
    include_adult: bool,
) -> Result<Vec<SearchResult>, String> {
    let mut base_params = vec![
        ("api_key", api_key.to_string()),
        ("query", query.to_string()),
        ("language", "en-US".to_string()),
        ("include_adult", include_adult.to_string()),
        ("page", "1".to_string()),
    ];
    if let Some(y) = year {
        base_params.push(("year", y.to_string()));
    }

    // Fetch page 1
    let (data1, total_pages) = tmdb_search(client, "search/movie", &base_params).await?;
    let mut results = parse_movie_results(&data1);

    // Fetch page 2 if available
    if total_pages > 1 {
        let mut params2 = base_params.clone();
        for p in params2.iter_mut() {
            if p.0 == "page" { p.1 = "2".to_string(); }
        }
        if let Ok((data2, _)) = tmdb_search(client, "search/movie", &params2).await {
            results.extend(parse_movie_results(&data2));
        }
    }

    Ok(results)
}

pub async fn search_tv(
    client: &Client,
    api_key: &str,
    query: &str,
    year: Option<i32>,
    include_adult: bool,
) -> Result<Vec<SearchResult>, String> {
    let mut base_params = vec![
        ("api_key", api_key.to_string()),
        ("query", query.to_string()),
        ("language", "en-US".to_string()),
        ("include_adult", include_adult.to_string()),
        ("page", "1".to_string()),
    ];
    if let Some(y) = year {
        base_params.push(("first_air_date_year", y.to_string()));
    }

    // Fetch page 1
    let (data1, total_pages) = tmdb_search(client, "search/tv", &base_params).await?;
    let mut results = parse_tv_results(&data1);

    // Fetch page 2 if available
    if total_pages > 1 {
        let mut params2 = base_params.clone();
        for p in params2.iter_mut() {
            if p.0 == "page" { p.1 = "2".to_string(); }
        }
        if let Ok((data2, _)) = tmdb_search(client, "search/tv", &params2).await {
            results.extend(parse_tv_results(&data2));
        }
    }

    Ok(results)
}
