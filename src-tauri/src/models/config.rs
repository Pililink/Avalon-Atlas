use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OcrRegion {
    pub width: u32,
    pub height: u32,
    pub vertical_offset: i32,
}

impl Default for OcrRegion {
    fn default() -> Self {
        Self {
            width: 590,
            height: 30,
            vertical_offset: 50,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    #[serde(default = "default_mouse_hotkey")]
    pub mouse_hotkey: String,

    #[serde(default = "default_chat_hotkey")]
    pub chat_hotkey: String,

    #[serde(default = "default_ocr_debug")]
    pub ocr_debug: bool,

    #[serde(default)]
    pub ocr_region: OcrRegion,

    #[serde(default)]
    pub always_on_top: bool,

    #[serde(default = "default_debounce_ms")]
    pub debounce_ms: u32,

    #[serde(default = "default_language")]
    pub language: String,
}

fn default_mouse_hotkey() -> String {
    "ctrl+shift+q".to_string()
}

fn default_chat_hotkey() -> String {
    "ctrl+shift+w".to_string()
}

fn default_debounce_ms() -> u32 {
    200
}

fn default_ocr_debug() -> bool {
    true
}

fn default_language() -> String {
    "zh-CN".to_string()
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            mouse_hotkey: default_mouse_hotkey(),
            chat_hotkey: default_chat_hotkey(),
            ocr_debug: true,
            ocr_region: OcrRegion::default(),
            always_on_top: false,
            debounce_ms: default_debounce_ms(),
            language: default_language(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::AppConfig;

    #[test]
    fn deserializing_partial_config_uses_runtime_defaults() {
        let config: AppConfig =
            serde_json::from_str("{}").expect("empty config should deserialize");

        assert_eq!(config.mouse_hotkey, "ctrl+shift+q");
        assert_eq!(config.chat_hotkey, "ctrl+shift+w");
        assert!(config.ocr_debug);
        assert_eq!(config.ocr_region.width, 590);
        assert_eq!(config.ocr_region.height, 30);
        assert_eq!(config.ocr_region.vertical_offset, 50);
        assert_eq!(config.debounce_ms, 200);
        assert_eq!(config.language, "zh-CN");
    }
}

impl AppConfig {
    /// Load config from file, or create default if not exists
    pub fn load(config_path: &PathBuf) -> Self {
        if config_path.exists() {
            match fs::read_to_string(config_path) {
                Ok(content) => match serde_json::from_str(&content) {
                    Ok(config) => {
                        println!("Loaded config from {:?}", config_path);
                        return config;
                    }
                    Err(e) => {
                        println!("Failed to parse config: {}, using defaults", e);
                    }
                },
                Err(e) => {
                    println!("Failed to read config: {}, using defaults", e);
                }
            }
        }

        let config = Self::default();
        let _ = config.save(config_path);
        config
    }

    /// Save config to file
    pub fn save(&self, config_path: &PathBuf) -> Result<(), String> {
        if let Some(parent) = config_path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }

        let content = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;

        fs::write(config_path, content).map_err(|e| format!("Failed to write config: {}", e))?;

        println!("Saved config to {:?}", config_path);
        Ok(())
    }
}
