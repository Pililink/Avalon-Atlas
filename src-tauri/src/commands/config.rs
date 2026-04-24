use crate::models::config::AppConfig;
use crate::services::hotkey_service::HotkeyService;
use crate::utils::frozen_screen::FrozenScreenState;
use crate::utils::logger;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};
use tauri::{AppHandle, State};

pub struct ConfigState {
    pub config: Arc<RwLock<AppConfig>>,
    pub config_path: PathBuf,
    pub logs_dir: PathBuf,
}

#[tauri::command]
pub async fn get_config(state: State<'_, Arc<ConfigState>>) -> Result<AppConfig, String> {
    let config = state.config.read().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

#[tauri::command]
pub async fn save_config(
    new_config: AppConfig,
    app_handle: AppHandle,
    state: State<'_, Arc<ConfigState>>,
    frozen_screen: State<'_, Arc<FrozenScreenState>>,
) -> Result<(), String> {
    logger::info("config", format!("save requested: {:?}", new_config));
    HotkeyService::register_and_listen(
        app_handle,
        &new_config,
        state.logs_dir.clone(),
        frozen_screen.inner().clone(),
    )?;

    // Update in memory
    {
        let mut config = state.config.write().map_err(|e| e.to_string())?;
        *config = new_config.clone();
    }

    // Save to disk
    new_config.save(&state.config_path)?;
    logger::info("config", format!("saved to {:?}", state.config_path));

    Ok(())
}
