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
use crate::services::hotkey_service::HotkeyService;

fn main() {
    tauri::Builder::default()
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
            
            let app_handle = app.handle().clone();
            
            let mut service = OcrService::new(engine.clone());
            service.set_app_handle(app_handle.clone());
            
            let ocr_service = Arc::new(service);
            
            // Initialize hotkey service with Tauri plugin
            HotkeyService::register_and_listen(app_handle.clone())
                .map_err(|e| format!("Failed to setup hotkeys: {}", e))?;
            
            app.manage(engine);
            app.manage(ocr_service);
            
            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            commands::search::search_maps,
            commands::ocr::capture_and_search,
            commands::hotkey_ocr::capture_mouse_ocr,
            commands::hotkey_ocr::capture_region_ocr,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
