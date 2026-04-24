use crate::utils::capture::{self, CapturedScreen};
use crate::utils::logger;
use base64::engine::general_purpose::STANDARD;
use base64::Engine;
use image::ImageOutputFormat;
use std::io::Cursor;
use std::sync::Mutex;

pub struct FrozenScreenState {
    capture: Mutex<Option<CapturedScreen>>,
}

impl FrozenScreenState {
    pub fn new() -> Self {
        Self {
            capture: Mutex::new(None),
        }
    }

    pub fn store(&self, captured: CapturedScreen) -> Result<(), String> {
        logger::info(
            "region-selector",
            format!(
                "stored frozen screen in memory method={} origin=({}, {}) size={}x{}",
                captured.method,
                captured.origin_x,
                captured.origin_y,
                captured.image.width(),
                captured.image.height()
            ),
        );

        let mut guard = self
            .capture
            .lock()
            .map_err(|_| "Failed to lock frozen screen state".to_string())?;
        *guard = Some(captured);
        Ok(())
    }

    pub fn to_data_url(&self) -> Result<String, String> {
        let captured = self.current()?;
        let mut bytes = Vec::new();
        image::DynamicImage::ImageRgba8(captured.image)
            .write_to(&mut Cursor::new(&mut bytes), ImageOutputFormat::Png)
            .map_err(|e| format!("编码冻结图片失败: {}", e))?;

        logger::info(
            "region-selector",
            format!("encoded frozen screenshot from memory size={}", bytes.len()),
        );

        Ok(format!("data:image/png;base64,{}", STANDARD.encode(bytes)))
    }

    pub fn crop_region(
        &self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
    ) -> Result<image::RgbaImage, String> {
        let captured = self.current()?;
        logger::info(
            "region-selector",
            format!(
                "crop frozen screen region=({}, {}) {}x{} origin=({}, {})",
                x, y, width, height, captured.origin_x, captured.origin_y
            ),
        );
        capture::crop_global(&captured, x, y, width, height)
    }

    fn current(&self) -> Result<CapturedScreen, String> {
        let guard = self
            .capture
            .lock()
            .map_err(|_| "Failed to lock frozen screen state".to_string())?;
        guard
            .as_ref()
            .cloned()
            .ok_or("没有可用的冻结截图，请重新触发框选 OCR".to_string())
    }
}
