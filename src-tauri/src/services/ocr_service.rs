use crate::models::config::AppConfig;
use crate::models::map::SearchResult;
use crate::services::search_engine::SearchEngine;
use crate::utils::capture;
use crate::utils::logger;
use image::{DynamicImage, GrayImage, Luma};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::{Mutex, RwLock};
use tauri::{AppHandle, Manager};

pub struct OcrService {
    search_engine: Arc<SearchEngine>,
    app_handle: Mutex<Option<AppHandle>>,
    config: Arc<RwLock<AppConfig>>,
    logs_dir: PathBuf,
}

/// OCR character correction mapping (same as Python version)
/// Maps commonly misrecognized characters to their correct equivalents
fn apply_ocr_char_fixes(text: &str) -> String {
    text.chars()
        .map(|c| match c {
            '0' => 'o',
            '1' | '|' | '¡' => 'l',
            '2' => 'z',
            '3' => 'e',
            '4' => 'a',
            '5' => 's',
            '6' | '8' => 'b',
            '7' => 't',
            '9' => 'g',
            _ => c,
        })
        .collect()
}

/// Preprocess image to improve OCR accuracy (same as Python version)
/// Steps: Convert to grayscale, enhance contrast, sharpen
fn preprocess_image(img: DynamicImage) -> DynamicImage {
    // 1. Convert to grayscale
    let gray = img.to_luma8();

    // 2. Enhance contrast (simple linear stretch)
    let contrast_enhanced = enhance_contrast(&gray, 2.0);

    // 3. Sharpen (using a simple unsharp mask approximation)
    let sharpened = sharpen_image(&contrast_enhanced);

    DynamicImage::ImageLuma8(sharpened)
}

/// Enhance contrast by a factor
fn enhance_contrast(img: &GrayImage, factor: f32) -> GrayImage {
    let (width, height) = img.dimensions();
    let mut result = GrayImage::new(width, height);

    for (x, y, pixel) in img.enumerate_pixels() {
        let value = pixel[0] as f32;
        // Center around 128, apply factor, then shift back
        let new_value = ((value - 128.0) * factor + 128.0).clamp(0.0, 255.0) as u8;
        result.put_pixel(x, y, Luma([new_value]));
    }

    result
}

/// Simple sharpen filter using 3x3 kernel
fn sharpen_image(img: &GrayImage) -> GrayImage {
    let (width, height) = img.dimensions();
    let mut result = GrayImage::new(width, height);

    // Sharpen kernel: center = 5, edges = -1
    // [0, -1, 0]
    // [-1, 5, -1]
    // [0, -1, 0]

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let center = img.get_pixel(x, y)[0] as i32 * 5;
            let top = img.get_pixel(x, y - 1)[0] as i32;
            let bottom = img.get_pixel(x, y + 1)[0] as i32;
            let left = img.get_pixel(x - 1, y)[0] as i32;
            let right = img.get_pixel(x + 1, y)[0] as i32;

            let value = (center - top - bottom - left - right).clamp(0, 255) as u8;
            result.put_pixel(x, y, Luma([value]));
        }
    }

    // Copy edges
    for x in 0..width {
        result.put_pixel(x, 0, *img.get_pixel(x, 0));
        result.put_pixel(x, height - 1, *img.get_pixel(x, height - 1));
    }
    for y in 0..height {
        result.put_pixel(0, y, *img.get_pixel(0, y));
        result.put_pixel(width - 1, y, *img.get_pixel(width - 1, y));
    }

    result
}

fn tesseract_compatible_path(path: PathBuf) -> PathBuf {
    let text = path.to_string_lossy();

    #[cfg(target_os = "windows")]
    {
        if let Some(stripped) = text.strip_prefix(r"\\?\UNC\") {
            return PathBuf::from(format!(r"\\{}", stripped));
        }

        if let Some(stripped) = text.strip_prefix(r"\\?\") {
            return PathBuf::from(stripped);
        }
    }

    path
}

fn looks_like_map_name_candidate(candidate: &str) -> bool {
    let Some((left, right)) = candidate.split_once('-') else {
        return false;
    };

    left.chars().filter(|ch| ch.is_ascii_alphanumeric()).count() >= 3
        && right
            .chars()
            .filter(|ch| ch.is_ascii_alphanumeric())
            .count()
            >= 3
}

impl OcrService {
    pub fn new(
        search_engine: Arc<SearchEngine>,
        config: Arc<RwLock<AppConfig>>,
        logs_dir: PathBuf,
    ) -> Self {
        Self {
            search_engine,
            app_handle: Mutex::new(None),
            config,
            logs_dir,
        }
    }

    pub fn set_app_handle(&self, app_handle: AppHandle) {
        let mut handle = self.app_handle.lock().unwrap();
        *handle = Some(app_handle);
    }

    fn get_tesseract_paths(&self) -> Result<(String, String), String> {
        let handle_guard = self.app_handle.lock().unwrap();
        let app = handle_guard.as_ref().ok_or("App handle not set")?;

        let binary_path = app
            .path()
            .resolve(
                "binaries/tesseract/tesseract.exe",
                tauri::path::BaseDirectory::Resource,
            )
            .map_err(|e| e.to_string())?;

        let tessdata_path = app
            .path()
            .resolve("binaries/tessdata", tauri::path::BaseDirectory::Resource)
            .map_err(|e| e.to_string())?;

        // Handle dev environment fallback if needed
        let binary_path = if binary_path.exists() {
            binary_path
        } else {
            // Fallback for dev: assume running from src-tauri root
            let cwd = std::env::current_dir().map_err(|e| e.to_string())?;
            cwd.join("binaries/tesseract/tesseract.exe")
        };

        let tessdata_path = if tessdata_path.exists() {
            tessdata_path
        } else {
            let cwd = std::env::current_dir().map_err(|e| e.to_string())?;
            cwd.join("binaries/tessdata")
        };

        if !binary_path.exists() {
            logger::error(
                "ocr.paths",
                format!("tesseract binary not found at {:?}", binary_path),
            );
            return Err(format!("Tesseract binary not found at {:?}", binary_path));
        }

        let binary_path = tesseract_compatible_path(binary_path);
        let tessdata_path = tesseract_compatible_path(tessdata_path);

        logger::info(
            "ocr.paths",
            format!("tesseract={:?} tessdata={:?}", binary_path, tessdata_path),
        );

        Ok((
            binary_path.to_string_lossy().to_string(),
            tessdata_path.to_string_lossy().to_string(),
        ))
    }

    fn ocr_debug_enabled(&self) -> bool {
        self.config
            .read()
            .map(|config| config.ocr_debug)
            .unwrap_or(false)
    }

    fn capture_path(&self, filename: String) -> Result<PathBuf, String> {
        if self.ocr_debug_enabled() {
            std::fs::create_dir_all(&self.logs_dir)
                .map_err(|e| format!("Failed to create OCR debug directory: {}", e))?;
            Ok(self.logs_dir.join(filename))
        } else {
            let mut path = std::env::temp_dir();
            path.push(filename);
            Ok(path)
        }
    }

    pub fn capture_and_search(&self) -> Result<Vec<SearchResult>, String> {
        let (tess_path, tess_data) = self.get_tesseract_paths()?;
        logger::info("ocr.full", "capture_and_search started");

        // 1. Capture Screen
        let captured = capture::capture_primary_screen()?;
        let image = captured.image;
        logger::info(
            "ocr.full",
            format!(
                "captured method={} origin=({}, {}) size={}x{}",
                captured.method,
                captured.origin_x,
                captured.origin_y,
                image.width(),
                image.height()
            ),
        );

        // Convert to dynamic image for processing (optional later)
        // let dynamic_image = DynamicImage::ImageRgba8(image);

        // 2. Save to temp file (robust way for Tesseract)
        let temp_path = self.capture_path("avalon_atlas_ocr.png".to_string())?;

        // Use image struct's save method directly (it is an ImageBuffer)
        if let Err(e) = image.save(&temp_path) {
            logger::error(
                "ocr.full",
                format!("failed to save screenshot {:?}: {}", temp_path, e),
            );
            return Err(format!("Failed to save screenshot to temp file: {}", e));
        }
        logger::info("ocr.full", format!("saved screenshot {:?}", temp_path));

        // 3. OCR
        // Use path instead of in-memory data for better compatibility
        let temp_path_str = temp_path.to_str().ok_or("Invalid temp path")?;

        // Execute tesseract directly to have full control over binary path and env
        println!("Executing Tesseract: {} on {}", tess_path, temp_path_str);
        logger::info(
            "ocr.full",
            format!(
                "executing tesseract image={} tessdata={}",
                temp_path_str, tess_data
            ),
        );

        // Windows: ensure we don't pop up a console window? Tauri handles this for sidecars,
        // but for Command we might need creation_flags if it weren't a console app.
        // But tesseract is a console app.
        // Since we are running from backend, it should be fine.

        let output = std::process::Command::new(&tess_path)
            .arg(temp_path_str)
            .arg("stdout") // Output to stdout
            .arg("-l")
            .arg("eng")
            .arg("--tessdata-dir")
            .arg(&tess_data)
            // config to disable dictionary
            .arg("-c")
            .arg("load_system_dawg=0")
            .arg("-c")
            .arg("load_freq_dawg=0")
            // Hide window on Windows
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output()
            .map_err(|e| format!("Failed to execute tesseract: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            logger::error("ocr.full", format!("tesseract failed: {}", stderr));
            return Err(format!("Tesseract execution failed: {}", stderr));
        }

        let text =
            String::from_utf8(output.stdout).map_err(|e| format!("Invalid UTF-8 output: {}", e))?;

        // 4. Search with the recognized text
        let clean_text = self.normalize_text(&text);
        logger::info("ocr.full", format!("raw_text={:?}", text));
        logger::info("ocr.full", format!("normalized_text={}", clean_text));

        if clean_text.len() < 3 {
            logger::error(
                "ocr.full",
                format!("recognized text too short: {}", clean_text),
            );
            return Err(format!("Recognized text too short: {}", clean_text));
        }

        println!("OCR Text: {}", clean_text);

        let results = self.search_engine.search(&clean_text, 5);
        logger::info("ocr.full", format!("results={}", results.len()));
        Ok(results)
    }

    fn normalize_text(&self, text: &str) -> String {
        let fixed = apply_ocr_char_fixes(&text.to_lowercase());
        let mut normalized = String::new();
        let mut last_was_separator = false;

        for ch in fixed.chars() {
            if ch.is_ascii_alphanumeric() {
                normalized.push(ch);
                last_was_separator = false;
            } else if !normalized.is_empty() && !last_was_separator {
                normalized.push('-');
                last_was_separator = true;
            }
        }

        normalized.trim_matches('-').to_string()
    }

    /// Capture a region with mouse at bottom center (consistent with Python version)
    ///
    /// Python logic:
    /// - left = mouse_x - width / 2
    /// - top = mouse_y - height - vertical_offset
    /// - With the default 590x30 region and 50px offset, this captures
    ///   the band 50..80 pixels above the cursor, 295px on each side.
    pub fn capture_mouse_region(
        &self,
        mouse_x: i32,
        mouse_y: i32,
        width: u32,
        height: u32,
        vertical_offset: i32,
    ) -> Result<Vec<SearchResult>, String> {
        // Mouse at bottom center: region is above the mouse
        let x = mouse_x - (width as i32 / 2);
        let y = mouse_y - height as i32 - vertical_offset; // Region is ABOVE mouse position
        logger::info(
            "ocr.mouse",
            format!(
                "computed capture region=({}, {}) {}x{} from cursor=({}, {}) vertical_offset={}",
                x, y, width, height, mouse_x, mouse_y, vertical_offset
            ),
        );

        self.capture_custom_region(x, y, width, height)
    }

    /// Capture a specific rectangular region
    pub fn capture_custom_region(
        &self,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
    ) -> Result<Vec<SearchResult>, String> {
        logger::info(
            "ocr.region",
            format!(
                "capture_custom_region requested=({}, {}) {}x{}",
                x, y, width, height
            ),
        );

        let captured = capture::capture_screen_containing_point(x, y)?;
        logger::info(
            "ocr.region",
            format!(
                "captured method={} origin=({}, {}) size={}x{}",
                captured.method,
                captured.origin_x,
                captured.origin_y,
                captured.image.width(),
                captured.image.height()
            ),
        );

        // Crop the image
        let cropped = capture::crop_global(&captured, x, y, width, height).map_err(|e| {
            logger::error("ocr.region", format!("failed to crop region: {}", e));
            e
        })?;

        self.ocr_region_image(cropped, x, y, width, height, captured.method)
    }

    pub fn ocr_region_image(
        &self,
        cropped: image::RgbaImage,
        x: i32,
        y: i32,
        width: u32,
        height: u32,
        source: &str,
    ) -> Result<Vec<SearchResult>, String> {
        let (tess_path, tess_data) = self.get_tesseract_paths()?;
        logger::info(
            "ocr.region",
            format!(
                "ocr_region_image source={} region=({}, {}) {}x{} image={}x{}",
                source,
                x,
                y,
                width,
                height,
                cropped.width(),
                cropped.height()
            ),
        );

        // Apply preprocessing (grayscale, contrast enhancement, sharpen)
        let processed = preprocess_image(image::DynamicImage::ImageRgba8(cropped));

        // Save processed image to temp file
        let temp_path = self.capture_path(format!("avalon_atlas_region_{}_{}.png", x, y))?;

        processed
            .save(&temp_path)
            .map_err(|e| format!("Failed to save region screenshot: {}", e))?;
        logger::info(
            "ocr.region",
            format!("saved processed screenshot {:?}", temp_path),
        );

        let temp_path_str = temp_path.to_str().ok_or("Invalid temp path")?;

        // Execute tesseract
        println!(
            "OCR region ({},{} {}x{}): {}",
            x, y, width, height, temp_path_str
        );
        logger::info(
            "ocr.region",
            format!(
                "executing tesseract image={} tessdata={} psm=6",
                temp_path_str, tess_data
            ),
        );

        let output = std::process::Command::new(&tess_path)
            .arg(temp_path_str)
            .arg("stdout")
            .arg("-l")
            .arg("eng")
            .arg("--tessdata-dir")
            .arg(&tess_data)
            .arg("--psm")
            .arg("6")
            .arg("-c")
            .arg("load_system_dawg=0")
            .arg("-c")
            .arg("load_freq_dawg=0")
            .creation_flags(0x08000000)
            .output()
            .map_err(|e| format!("Failed to execute tesseract: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            logger::error("ocr.region", format!("tesseract failed: {}", stderr));
            return Err(format!("Tesseract execution failed: {}", stderr));
        }

        let text =
            String::from_utf8(output.stdout).map_err(|e| format!("Invalid UTF-8 output: {}", e))?;
        logger::info("ocr.region", format!("raw_text={:?}", text));

        // Extract all possible map names from text
        self.extract_all_map_names(&text)
    }

    /// Extract multiple map names from OCR text
    fn extract_all_map_names(&self, text: &str) -> Result<Vec<SearchResult>, String> {
        // Try to find all map names in the text. Split the raw OCR text first so
        // multi-line chat OCR does not get collapsed into one oversized query.
        let mut all_results = Vec::new();
        let mut seen_names = std::collections::HashSet::new();
        let raw_parts: Vec<String> = text
            .split(|c: char| c.is_whitespace() || matches!(c, ',' | ';' | '|'))
            .map(|part| self.normalize_text(part))
            .filter(|part| part.len() >= 3)
            .collect();
        let mut candidates: Vec<String> = raw_parts
            .iter()
            .filter(|candidate| looks_like_map_name_candidate(candidate))
            .cloned()
            .collect();

        for pair in raw_parts.windows(2) {
            let joined = format!("{}-{}", pair[0], pair[1]);
            if looks_like_map_name_candidate(&joined) {
                candidates.push(joined);
            }
        }

        if candidates.is_empty() {
            logger::info(
                "ocr.extract",
                format!("no map-shaped candidates from raw_text={:?}", text),
            );
            return Ok(Vec::new());
        }

        candidates.sort();
        candidates.dedup();

        println!("OCR candidates: {:?}", candidates);
        logger::info("ocr.extract", format!("candidates={:?}", candidates));

        for candidate in candidates {
            let result = self.search_engine.search_ocr_candidate(&candidate);
            logger::info(
                "ocr.extract",
                format!(
                    "candidate={} accepted={}",
                    candidate,
                    result
                        .as_ref()
                        .map(|result| format!("{} score={:.3}", result.record.name, result.score))
                        .unwrap_or_else(|| "none".to_string())
                ),
            );
            if let Some(result) = result {
                let key = format!("{}_{}", result.record.name, result.record.tier);
                if !seen_names.contains(&key) {
                    seen_names.insert(key);
                    all_results.push(result);
                }
            }
        }

        logger::info(
            "ocr.extract",
            format!("final_results={}", all_results.len()),
        );

        Ok(all_results)
    }
}

#[cfg(test)]
mod tests {
    use super::{looks_like_map_name_candidate, tesseract_compatible_path, OcrService};
    use crate::models::config::AppConfig;
    use crate::models::map::{Chests, Dungeons, MapRecord, Resources};
    use crate::services::search_engine::SearchEngine;
    use std::sync::{Arc, RwLock};

    fn record(name: &str) -> MapRecord {
        MapRecord {
            name: name.to_string(),
            slug: name.to_string(),
            tier: "T4".to_string(),
            map_type: "TUNNEL_ROYAL".to_string(),
            chests: Chests {
                blue: 0,
                green: 0,
                high_gold: 0,
                low_gold: 0,
            },
            dungeons: Dungeons {
                solo: 0,
                group: 0,
                avalon: 0,
            },
            resources: Resources {
                rock: 0,
                wood: 0,
                ore: 0,
                fiber: 0,
                hide: 0,
            },
            brecilien: 0,
        }
    }

    fn service_with_records(records: Vec<MapRecord>) -> OcrService {
        OcrService::new(
            Arc::new(SearchEngine::new(records)),
            Arc::new(RwLock::new(AppConfig::default())),
            std::env::temp_dir(),
        )
    }

    fn service() -> OcrService {
        service_with_records(Vec::new())
    }

    #[test]
    fn normalize_text_converts_delimiters_and_common_ocr_digits() {
        let service = service();

        assert_eq!(service.normalize_text("C4S0S_AIAGSUM"), "casos-aiagsum");
        assert_eq!(service.normalize_text(" casos   aiagsum "), "casos-aiagsum");
    }

    #[test]
    fn tesseract_compatible_path_removes_windows_extended_prefix() {
        let path = tesseract_compatible_path(r"\\?\E:\app\binaries\tessdata".into());

        assert_eq!(path.to_string_lossy(), r"E:\app\binaries\tessdata");
    }

    #[test]
    fn map_name_candidate_filter_rejects_short_ocr_noise() {
        assert!(looks_like_map_name_candidate("oynites-araosum"));
        assert!(!looks_like_map_name_candidate("lao"));
        assert!(!looks_like_map_name_candidate("tsp"));
    }

    #[test]
    fn extract_all_map_names_handles_noisy_single_line_mouse_ocr() {
        let service = service_with_records(vec![
            record("Oynites-Araosum"),
            record("Lao-Noise"),
            record("Tsp-Noise"),
        ]);

        let results = service
            .extract_all_map_names("@ <> Oynites-Araosum VS eo oy")
            .expect("noisy OCR line should still produce candidates");

        assert_eq!(results.len(), 1);
        assert_eq!(results[0].record.name, "Oynites-Araosum");
    }

    #[test]
    fn extract_all_map_names_returns_empty_for_uncertain_noise() {
        let service = service_with_records(vec![
            record("Oynites-Araosum"),
            record("Casos-Aiagsum"),
            record("Lao-Noise"),
            record("Tsp-Noise"),
        ]);

        let results = service
            .extract_all_map_names("Di bes.\nfonos- m re bal\n[\ns-Obayal\npy <> es\n?")
            .expect("uncertain OCR should not be treated as an error");

        assert!(results.is_empty());
    }

    #[test]
    fn extract_all_map_names_can_join_adjacent_ocr_words() {
        let service = service_with_records(vec![record("Oynites-Araosum")]);

        let results = service
            .extract_all_map_names("Oynites Araosum")
            .expect("space separated OCR map name should be matched");

        assert_eq!(results.len(), 1);
        assert_eq!(results[0].record.name, "Oynites-Araosum");
    }
}
