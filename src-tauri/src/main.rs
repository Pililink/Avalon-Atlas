// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod models;
mod services;
mod utils;

use std::fs;
use std::sync::Arc;
use tauri::Manager;
use crate::services::search_engine::SearchEngine;
use crate::models::map::MapRecord;

use crate::services::ocr_service::OcrService;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Debug info
            let cwd = std::env::current_dir().unwrap_or_default();
            println!("Current working directory: {:?}", cwd);

            // try multiple paths
            let possible_paths = vec![
                // Production resource
                app.path().resolve("static/data/maps.json", tauri::path::BaseDirectory::Resource).ok(),
                // Dev relative to src-tauri (where cargo runs)
                Some(cwd.join("../public/static/data/maps.json")),
                // Dev relative to root (if CWD is root)
                Some(cwd.join("public/static/data/maps.json")),
                // Hardcoded fallback for known structure
                Some(std::path::PathBuf::from("E:/src/Avalon-Atlas/public/static/data/maps.json")),
            ];

            let mut file_content = String::new();
            let mut found = false;

            for path in possible_paths.into_iter().flatten() {
                println!("Trying to load maps.json from: {:?}", path);
                if path.exists() {
                    if let Ok(content) = fs::read_to_string(&path) {
                        file_content = content;
                        found = true;
                        println!("Successfully loaded maps.json from: {:?}", path);
                        break;
                    }
                }
            }

            if !found {
                 return Err("Could not find maps.json in any checked paths".into());
            }

            let mut records: Vec<MapRecord> = serde_json::from_str(&file_content)
                .map_err(|e| format!("Failed to parse maps.json: {}", e))?;
            
            // Compute slug for each record
            for record in &mut records {
                record.slug = record.name.trim().to_lowercase().replace(" ", "-");
            }
            
            let engine = Arc::new(SearchEngine::new(records));
            // Use RwLock/Mutex if we need internal mutability, but here we just need to set handle once.
            // Actually OcrService struct needs to be thread safe. 
            // We defined it as struct OcrService { ... }
            // Let's wrapping it in a structure that allows setting handle.
            // But Arc<OcrService> is shared. We can use Interior Mutability.
            // Refactoring OcrService to use RwLock or Mutex for app_handle.
            // Wait, for simplicity in Setup, we can just create it with None and then... 
            // no, Arc makes it immutable.
            // Better: initialize OcrService WITH NONE, then wrap in Arc? No.
            // Let's change OcrService definition to include Mutex<Option<AppHandle>>
            // Or simpler: Pass app_handle to new(). But app_handle comes from app...
            let app_handle = app.handle().clone();
            
            let mut service = OcrService::new(engine.clone());
            service.set_app_handle(app_handle);
            
            let ocr_service = Arc::new(service);
            
            app.manage(engine);
            app.manage(ocr_service);
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::search::search_maps,
            commands::ocr::capture_and_search
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
