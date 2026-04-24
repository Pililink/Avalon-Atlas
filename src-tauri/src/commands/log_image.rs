use crate::utils::frozen_screen::FrozenScreenState;
use std::sync::Arc;
use tauri::State;

#[tauri::command]
pub async fn read_frozen_screen_data_url(
    state: State<'_, Arc<FrozenScreenState>>,
) -> Result<String, String> {
    state.to_data_url()
}
