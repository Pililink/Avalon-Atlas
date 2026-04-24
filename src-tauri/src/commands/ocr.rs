use crate::models::map::SearchResult;
use crate::services::ocr_service::OcrService;
use std::sync::Arc;
use tauri::State;

#[tauri::command]
pub async fn capture_and_search(
    service: State<'_, Arc<OcrService>>,
) -> Result<Vec<SearchResult>, String> {
    service.capture_and_search()
}
