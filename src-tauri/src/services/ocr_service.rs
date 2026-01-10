use screenshots::Screen;
use std::sync::Arc;
use crate::models::map::SearchResult;
use crate::services::search_engine::SearchEngine;
use std::sync::Mutex;
use tauri::{AppHandle, Manager};
use std::os::windows::process::CommandExt;

pub struct OcrService {
    search_engine: Arc<SearchEngine>,
    app_handle: Mutex<Option<AppHandle>>,
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
        text.lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<&str>>()
            .join(" ")
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace() || *c == '-')
            .collect()
    }
}
