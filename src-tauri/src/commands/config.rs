use tauri::State;
use std::sync::{Arc, RwLock};
use std::path::PathBuf;
use crate::models::config::AppConfig;

pub struct ConfigState {
    pub config: RwLock<AppConfig>,
    pub config_path: PathBuf,
}

#[tauri::command]
pub async fn get_config(
    state: State<'_, Arc<ConfigState>>,
) -> Result<AppConfig, String> {
    let config = state.config.read().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

#[tauri::command]
pub async fn save_config(
    new_config: AppConfig,
    state: State<'_, Arc<ConfigState>>,
) -> Result<(), String> {
    // Update in memory
    {
        let mut config = state.config.write().map_err(|e| e.to_string())?;
        *config = new_config.clone();
    }
    
    // Save to disk
    new_config.save(&state.config_path)?;
    
    Ok(())
}
