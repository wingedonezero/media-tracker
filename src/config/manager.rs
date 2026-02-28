use crate::models::AppConfig;
use std::path::Path;

pub fn load_config(data_dir: &Path) -> Result<(AppConfig, std::path::PathBuf), Box<dyn std::error::Error>> {
    let config_path = data_dir.join("config.json");
    if config_path.exists() {
        let data = std::fs::read_to_string(&config_path)?;
        let config: AppConfig = serde_json::from_str(&data).unwrap_or_default();
        Ok((config, config_path))
    } else {
        let config = AppConfig::default();
        std::fs::create_dir_all(data_dir)?;
        let data = serde_json::to_string_pretty(&config)?;
        std::fs::write(&config_path, data)?;
        Ok((config, config_path))
    }
}

pub fn save_config(config: &AppConfig, config_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let data = serde_json::to_string_pretty(config)?;
    std::fs::write(config_path, data)?;
    Ok(())
}
