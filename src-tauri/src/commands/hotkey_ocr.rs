use tauri::State;
use std::sync::Arc;
use crate::services::ocr_service::OcrService;
use crate::models::map::SearchResult;

#[tauri::command]
pub async fn capture_mouse_ocr(
    x: i32,
    y: i32,
    width: u32,
    height: u32,
    ocr: State<'_, Arc<OcrService>>,
) -> Result<Vec<SearchResult>, String> {
    ocr.capture_mouse_region(x, y, width, height)
}

#[tauri::command]
pub async fn capture_region_ocr(
    x: i32,
    y: i32,
    width: u32,
    height: u32,
    ocr: State<'_, Arc<OcrService>>,
) -> Result<Vec<SearchResult>, String> {
    ocr.capture_custom_region(x, y, width, height)
}
