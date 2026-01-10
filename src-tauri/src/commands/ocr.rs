use tauri::State;
use std::sync::Arc;
use crate::services::ocr_service::OcrService;
use crate::models::map::SearchResult;

#[tauri::command]
pub async fn capture_and_search(
    service: State<'_, Arc<OcrService>>,
) -> Result<Vec<SearchResult>, String> {
    service.capture_and_search()
}
