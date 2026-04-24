use crate::models::map::SearchResult;
use crate::services::ocr_service::OcrService;
use crate::utils::frozen_screen::FrozenScreenState;
use crate::utils::logger;
use std::sync::Arc;
use tauri::State;

#[cfg(target_os = "windows")]
fn global_cursor_position() -> Result<(i32, i32), String> {
    let mut point = windows_sys::Win32::Foundation::POINT { x: 0, y: 0 };
    let ok = unsafe { windows_sys::Win32::UI::WindowsAndMessaging::GetCursorPos(&mut point) };

    if ok == 0 {
        return Err("Failed to read global cursor position".to_string());
    }

    Ok((point.x, point.y))
}

#[cfg(not(target_os = "windows"))]
fn global_cursor_position() -> Result<(i32, i32), String> {
    Err("Global cursor position is only implemented on Windows".to_string())
}

#[tauri::command]
pub async fn capture_mouse_ocr(
    width: u32,
    height: u32,
    vertical_offset: Option<i32>,
    ocr: State<'_, Arc<OcrService>>,
) -> Result<Vec<SearchResult>, String> {
    let (x, y) = global_cursor_position()?;
    let vertical_offset = vertical_offset.unwrap_or(0);
    logger::info(
        "ocr.mouse",
        format!(
            "invoke cursor=({}, {}) region={}x{} vertical_offset={}",
            x, y, width, height, vertical_offset
        ),
    );

    match ocr.capture_mouse_region(x, y, width, height, vertical_offset) {
        Ok(results) => {
            logger::info("ocr.mouse", format!("completed results={}", results.len()));
            Ok(results)
        }
        Err(error) => {
            logger::error("ocr.mouse", format!("failed: {}", error));
            Err(error)
        }
    }
}

#[tauri::command]
pub async fn capture_region_ocr(
    x: i32,
    y: i32,
    width: u32,
    height: u32,
    ocr: State<'_, Arc<OcrService>>,
    frozen_screen: State<'_, Arc<FrozenScreenState>>,
) -> Result<Vec<SearchResult>, String> {
    logger::info(
        "ocr.region",
        format!("invoke region=({}, {}) {}x{}", x, y, width, height),
    );

    let cropped = match frozen_screen.crop_region(x, y, width, height) {
        Ok(cropped) => cropped,
        Err(error) => {
            logger::error(
                "ocr.region",
                format!("failed to crop frozen screen: {}", error),
            );
            return Err(error);
        }
    };

    match ocr.ocr_region_image(cropped, x, y, width, height, "frozen") {
        Ok(results) => {
            logger::info("ocr.region", format!("completed results={}", results.len()));
            Ok(results)
        }
        Err(error) => {
            logger::error("ocr.region", format!("failed: {}", error));
            Err(error)
        }
    }
}
