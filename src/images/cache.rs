use reqwest::Client;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

fn url_to_filename(url: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(url.as_bytes());
    let hash = hex::encode(hasher.finalize());
    // Extract extension from URL
    let ext = url
        .rsplit('/')
        .next()
        .and_then(|s| s.rsplit('.').next())
        .unwrap_or("jpg");
    format!("{}.{}", &hash[..16], ext)
}

pub async fn cache_poster(
    client: &Client,
    cache_dir: &Path,
    url: &str,
) -> Result<PathBuf, String> {
    std::fs::create_dir_all(cache_dir).map_err(|e| format!("Failed to create cache dir: {}", e))?;

    let filename = url_to_filename(url);
    let file_path = cache_dir.join(&filename);

    // Return cached file if it exists
    if file_path.exists() {
        return Ok(file_path);
    }

    // Download the image
    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Failed to download poster: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Poster download failed: HTTP {}", resp.status()));
    }

    let bytes = resp
        .bytes()
        .await
        .map_err(|e| format!("Failed to read poster data: {}", e))?;

    std::fs::write(&file_path, &bytes)
        .map_err(|e| format!("Failed to save poster: {}", e))?;

    Ok(file_path)
}

/// Delete a cached poster file by its local path.
pub fn delete_cached_poster(path: &str) {
    let p = Path::new(path);
    if p.exists() && p.components().any(|c| c.as_os_str() == "image_cache") {
        let _ = std::fs::remove_file(p);
    }
}
