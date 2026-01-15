use screenshots::Screen;
use std::sync::Arc;
use crate::models::map::SearchResult;
use crate::services::search_engine::SearchEngine;
use std::sync::Mutex;
use tauri::{AppHandle, Manager};
use std::os::windows::process::CommandExt;
use image::{DynamicImage, GrayImage, Luma};

pub struct OcrService {
    search_engine: Arc<SearchEngine>,
    app_handle: Mutex<Option<AppHandle>>,
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

impl OcrService {
    pub fn new(search_engine: Arc<SearchEngine>) -> Self {
        Self { 
            search_engine,
            app_handle: Mutex::new(None),
        }
    }

    pub fn set_app_handle(&self, app_handle: AppHandle) {
        let mut handle = self.app_handle.lock().unwrap();
        *handle = Some(app_handle);
    }

    fn get_tesseract_paths(&self) -> Result<(String, String), String> {
        let handle_guard = self.app_handle.lock().unwrap();
        let app = handle_guard.as_ref().ok_or("App handle not set")?;
        
        let binary_path = app.path().resolve("binaries/tesseract/tesseract.exe", tauri::path::BaseDirectory::Resource)
            .map_err(|e| e.to_string())?;
            
        let tessdata_path = app.path().resolve("binaries/tessdata", tauri::path::BaseDirectory::Resource)
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
            return Err(format!("Tesseract binary not found at {:?}", binary_path));
        }
        
        Ok((
            binary_path.to_string_lossy().to_string(), 
            tessdata_path.to_string_lossy().to_string()
        ))
    }

    pub fn capture_and_search(&self) -> Result<Vec<SearchResult>, String> {
        let (tess_path, tess_data) = self.get_tesseract_paths()?;

        // 1. Capture Screen
        let screens = Screen::all().map_err(|e| e.to_string())?;
        let screen = screens.first().ok_or("No screen found")?;
        
        let image = screen.capture().map_err(|e| e.to_string())?;
        
        // Convert to dynamic image for processing (optional later)
        // let dynamic_image = DynamicImage::ImageRgba8(image);

        // 2. Save to temp file (robust way for Tesseract)
        let mut temp_path = std::env::temp_dir();
        temp_path.push("avalon_atlas_ocr.png");
        
        // Use image struct's save method directly (it is an ImageBuffer)
        if let Err(e) = image.save(&temp_path) {
             return Err(format!("Failed to save screenshot to temp file: {}", e));
        }
        
        // 3. OCR 
        // Use path instead of in-memory data for better compatibility
        let temp_path_str = temp_path.to_str().ok_or("Invalid temp path")?;
        
        // Execute tesseract directly to have full control over binary path and env
        println!("Executing Tesseract: {} on {}", tess_path, temp_path_str);
        
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
            return Err(format!("Tesseract execution failed: {}", stderr));
        }

        let text = String::from_utf8(output.stdout)
            .map_err(|e| format!("Invalid UTF-8 output: {}", e))?;

        // 4. Search with the recognized text
        let clean_text = self.normalize_text(&text);
        
        if clean_text.len() < 3 {
             return Err(format!("Recognized text too short: {}", clean_text));
        }

        println!("OCR Text: {}", clean_text);
        
        let results = self.search_engine.search(&clean_text, 5);
        Ok(results)
    }

    fn normalize_text(&self, text: &str) -> String {
        let cleaned: String = text.lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<&str>>()
            .join(" ")
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace() || *c == '-')
            .collect();
        
        // Apply OCR character fixes (0→o, 1→l, etc.)
        apply_ocr_char_fixes(&cleaned.to_lowercase())
    }

    /// Capture a region with mouse at bottom center (consistent with Python version)
    /// 
    /// Python logic:
    /// - left = mouse_x - width / 2
    /// - top = mouse_y - height - vertical_offset
    /// - Mouse is at the bottom center of the region
    pub fn capture_mouse_region(
        &self,
        mouse_x: i32,
        mouse_y: i32,
        width: u32,
        height: u32,
    ) -> Result<Vec<SearchResult>, String> {
        // Mouse at bottom center: region is above the mouse
        let x = mouse_x - (width as i32 / 2);
        let y = mouse_y - height as i32;  // Region is ABOVE mouse position
        
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
        let (tess_path, tess_data) = self.get_tesseract_paths()?;

        // Capture the specific screen region
        let screens = Screen::all().map_err(|e| e.to_string())?;
        let screen = screens.first().ok_or("No screen found")?;
        
        // Capture full screen first, then crop
        let full_image = screen.capture().map_err(|e| e.to_string())?;
        
        // Ensure coordinates are within bounds
        let x = x.max(0) as u32;
        let y = y.max(0) as u32;
        let width = width.min(full_image.width().saturating_sub(x));
        let height = height.min(full_image.height().saturating_sub(y));
        
        if width == 0 || height == 0 {
            return Err("Invalid capture region dimensions".to_string());
        }
        
        // Crop the image
        let cropped = image::DynamicImage::ImageRgba8(full_image).crop_imm(x, y, width, height);
        
        // Apply preprocessing (grayscale, contrast enhancement, sharpen)
        let processed = preprocess_image(cropped);
        
        // Save processed image to temp file
        let mut temp_path = std::env::temp_dir();
        temp_path.push(format!("avalon_atlas_region_{}_{}.png", x, y));
        
        processed.save(&temp_path)
            .map_err(|e| format!("Failed to save region screenshot: {}", e))?;
        
        let temp_path_str = temp_path.to_str().ok_or("Invalid temp path")?;
        
        // Execute tesseract
        println!("OCR region ({},{} {}x{}): {}", x, y, width, height, temp_path_str);
        
        let output = std::process::Command::new(&tess_path)
            .arg(temp_path_str)
            .arg("stdout")
            .arg("-l")
            .arg("eng")
            .arg("--tessdata-dir")
            .arg(&tess_data)
            .arg("-c")
            .arg("load_system_dawg=0")
            .arg("-c")
            .arg("load_freq_dawg=0")
            .creation_flags(0x08000000)
            .output()
            .map_err(|e| format!("Failed to execute tesseract: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Tesseract execution failed: {}", stderr));
        }

        let text = String::from_utf8(output.stdout)
            .map_err(|e| format!("Invalid UTF-8 output: {}", e))?;

        // Extract all possible map names from text
        self.extract_all_map_names(&text)
    }

    /// Extract multiple map names from OCR text
    fn extract_all_map_names(&self, text: &str) -> Result<Vec<SearchResult>, String> {
        let clean_text = self.normalize_text(text);
        
        if clean_text.len() < 3 {
            return Err(format!("Recognized text too short: {}", clean_text));
        }

        println!("OCR Text: {}", clean_text);
        
        // Try to find all map names in the text
        // Split by common delimiters and search each part
        let mut all_results = Vec::new();
        let mut seen_names = std::collections::HashSet::new();
        
        // Split text into potential map names
        for part in clean_text.split(&['\n', ',', ';', '|']) {
            let trimmed = part.trim();
            if trimmed.len() >= 3 {
                let results = self.search_engine.search(trimmed, 5);
                for result in results {
                    let key = format!("{}_{}", result.record.name, result.record.tier);
                    if !seen_names.contains(&key) {
                        seen_names.insert(key);
                        all_results.push(result);
                    }
                }
            }
        }
        
        if all_results.is_empty() {
            // Fallback: try the entire text as one query
            all_results = self.search_engine.search(&clean_text, 5);
        }
        
        Ok(all_results)
    }
}
