// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod models;
mod services;
mod utils;

use crate::commands::config::ConfigState;
use crate::models::config::AppConfig;
use crate::models::map::MapRecord;
use crate::services::search_engine::SearchEngine;
use crate::utils::logger;
use std::fs;
use std::sync::{Arc, RwLock};
use tauri::Manager;
use tauri_plugin_global_shortcut::GlobalShortcutExt;

use crate::services::hotkey_service::HotkeyService;
use crate::services::ocr_service::OcrService;
use crate::utils::frozen_screen::FrozenScreenState;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Debug info
            let cwd = std::env::current_dir().unwrap_or_default();
            println!("Current working directory: {:?}", cwd);
            let exe_dir = std::env::current_exe()
                .ok()
                .and_then(|path| path.parent().map(|parent| parent.to_path_buf()))
                .unwrap_or_else(|| cwd.clone());
            let logs_dir = exe_dir.join("logs");
            logger::init(&logs_dir)?;
            logger::info("app", format!("cwd={:?}", cwd));
            logger::info("app", format!("exe_dir={:?}", exe_dir));

            // Load config
            let config_path = cwd.join("config.json");
            let config = AppConfig::load(&config_path);
            println!("Loaded config: {:?}", config);
            logger::info(
                "config",
                format!("loaded from {:?}: {:?}", config_path, config),
            );

            let shared_config = Arc::new(RwLock::new(config.clone()));
            let frozen_screen = Arc::new(FrozenScreenState::new());
            let config_state = Arc::new(ConfigState {
                config: shared_config.clone(),
                config_path,
                logs_dir: logs_dir.clone(),
            });

            // try multiple paths for maps.json
            let possible_paths = vec![
                // Production resource
                app.path()
                    .resolve(
                        "static/data/maps.json",
                        tauri::path::BaseDirectory::Resource,
                    )
                    .ok(),
                // Dev relative to src-tauri (where cargo runs)
                Some(cwd.join("../public/static/data/maps.json")),
                // Dev relative to root (if CWD is root)
                Some(cwd.join("public/static/data/maps.json")),
                // Packaged resource if explicitly mapped by tauri.conf.json.
                app.path()
                    .resolve(
                        "public/static/data/maps.json",
                        tauri::path::BaseDirectory::Resource,
                    )
                    .ok(),
            ];

            let mut file_content = String::new();
            let mut found = false;

            for path in possible_paths.into_iter().flatten() {
                println!("Trying to load maps.json from: {:?}", path);
                logger::info("maps", format!("trying {:?}", path));
                if path.exists() {
                    if let Ok(content) = fs::read_to_string(&path) {
                        file_content = content;
                        found = true;
                        println!("Successfully loaded maps.json from: {:?}", path);
                        logger::info("maps", format!("loaded {:?}", path));
                        break;
                    }
                }
            }

            if !found {
                logger::error("maps", "Could not find maps.json in any checked paths");
                return Err("Could not find maps.json in any checked paths".into());
            }

            let mut records: Vec<MapRecord> = serde_json::from_str(&file_content)
                .map_err(|e| format!("Failed to parse maps.json: {}", e))?;
            logger::info("maps", format!("parsed {} records", records.len()));

            // Compute slug for each record
            for record in &mut records {
                record.slug = record.name.trim().to_lowercase().replace(" ", "-");
            }

            let engine = Arc::new(SearchEngine::new(records));

            let app_handle = app.handle().clone();

            let service = OcrService::new(engine.clone(), shared_config.clone(), logs_dir.clone());
            service.set_app_handle(app_handle.clone());

            let ocr_service = Arc::new(service);

            // Initialize hotkey service with Tauri plugin
            HotkeyService::register_and_listen(
                app_handle.clone(),
                &config,
                logs_dir,
                frozen_screen.clone(),
            )
            .map_err(|e| format!("Failed to setup hotkeys: {}", e))?;
            logger::info("app", "setup completed");

            app.manage(engine);
            app.manage(ocr_service);
            app.manage(config_state);
            app.manage(frozen_screen);

            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .on_window_event(|window, event| {
            if window.label() == "region-selector" {
                return;
            }

            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                let app_handle = window.app_handle();
                let _ = app_handle.global_shortcut().unregister_all();
                app_handle.exit(0);
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::search::search_maps,
            commands::ocr::capture_and_search,
            commands::hotkey_ocr::capture_mouse_ocr,
            commands::hotkey_ocr::capture_region_ocr,
            commands::log_image::read_frozen_screen_data_url,
            commands::config::get_config,
            commands::config::save_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
