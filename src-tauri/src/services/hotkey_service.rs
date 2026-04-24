use crate::models::config::AppConfig;
use crate::utils::capture;
use crate::utils::frozen_screen::FrozenScreenState;
use crate::utils::logger;
use std::path::PathBuf;
use std::str::FromStr;
use std::sync::Arc;
use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

pub struct HotkeyService;

impl HotkeyService {
    pub fn register_and_listen(
        app_handle: AppHandle,
        config: &AppConfig,
        logs_dir: PathBuf,
        frozen_screen: Arc<FrozenScreenState>,
    ) -> Result<(), String> {
        let mouse_hotkey = Self::normalize_hotkey(&config.mouse_hotkey)?;
        let region_hotkey = Self::normalize_hotkey(&config.chat_hotkey)?;
        let ocr_debug = config.ocr_debug;

        if mouse_hotkey.eq_ignore_ascii_case(&region_hotkey) {
            return Err("Mouse OCR hotkey and region OCR hotkey cannot be the same".to_string());
        }

        // Validate before replacing existing registrations.
        Shortcut::from_str(&mouse_hotkey)
            .map_err(|e| format!("Invalid mouse OCR hotkey '{}': {}", config.mouse_hotkey, e))?;
        Shortcut::from_str(&region_hotkey)
            .map_err(|e| format!("Invalid region OCR hotkey '{}': {}", config.chat_hotkey, e))?;

        println!(
            "HotkeyService: Registering hotkeys using Tauri plugin: mouse={}, region={}",
            mouse_hotkey, region_hotkey
        );
        logger::info(
            "hotkey",
            format!(
                "register mouse={} region={} logs_dir={:?}",
                mouse_hotkey, region_hotkey, logs_dir
            ),
        );

        app_handle
            .global_shortcut()
            .unregister_all()
            .map_err(|e| format!("Failed to clear existing shortcuts: {}", e))?;

        // Register mouse OCR shortcut
        let app1 = app_handle.clone();
        app_handle
            .global_shortcut()
            .on_shortcut(mouse_hotkey.as_str(), move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    println!("HotkeyService: mouse OCR hotkey pressed!");
                    logger::info("hotkey", "mouse OCR hotkey pressed");
                    let _ = app1.emit("hotkey-mouse-ocr", ());
                }
            })
            .map_err(|e| {
                format!(
                    "Failed to register mouse OCR hotkey '{}': {}",
                    mouse_hotkey, e
                )
            })?;

        println!("HotkeyService: mouse OCR hotkey registered successfully");

        // Register region select OCR shortcut
        let app2 = app_handle.clone();
        let region_logs_dir = logs_dir.clone();
        let region_frozen_screen = frozen_screen.clone();
        app_handle
            .global_shortcut()
            .on_shortcut(region_hotkey.as_str(), move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    println!("HotkeyService: region OCR hotkey pressed!");
                    logger::info("hotkey", "region OCR hotkey pressed");
                    // Create fullscreen transparent overlay window for region selection
                    if let Err(e) = Self::create_region_selector_window(
                        &app2,
                        &region_logs_dir,
                        &region_frozen_screen,
                        ocr_debug,
                    ) {
                        eprintln!("Failed to create region selector window: {}", e);
                        logger::error("hotkey", format!("region selector failed: {}", e));
                    }
                }
            })
            .map_err(|e| {
                format!(
                    "Failed to register region OCR hotkey '{}': {}",
                    region_hotkey, e
                )
            })?;

        println!("HotkeyService: region OCR hotkey registered successfully");

        Ok(())
    }

    fn normalize_hotkey(hotkey: &str) -> Result<String, String> {
        let parts: Vec<String> = hotkey
            .split('+')
            .map(|part| part.trim().to_lowercase())
            .filter(|part| !part.is_empty())
            .map(|part| match part.as_str() {
                "control" => "ctrl".to_string(),
                "cmd" | "command" | "meta" | "win" | "windows" => "super".to_string(),
                other => other.to_string(),
            })
            .collect();

        if parts.is_empty() {
            return Err("hotkey cannot be empty".to_string());
        }

        Ok(parts.join("+"))
    }

    /// Create a fullscreen transparent overlay window for region selection
    fn create_region_selector_window(
        app_handle: &AppHandle,
        logs_dir: &PathBuf,
        frozen_screen: &FrozenScreenState,
        ocr_debug: bool,
    ) -> Result<(), String> {
        // Check if window already exists - close it first
        if let Some(existing) = app_handle.get_webview_window("region-selector") {
            println!("Region selector window already exists, closing it first");
            let _ = existing.close();
        }

        println!("Creating region selector overlay window...");
        logger::info("region-selector", "creating overlay window");

        // Get primary monitor dimensions
        let monitors = app_handle
            .available_monitors()
            .map_err(|e| format!("Failed to get monitors: {}", e))?;

        let primary = monitors.into_iter().next().ok_or("No monitor found")?;

        let size = primary.size();
        let position = primary.position();

        println!(
            "Monitor: {}x{} at ({}, {})",
            size.width, size.height, position.x, position.y
        );
        logger::info(
            "region-selector",
            format!(
                "monitor={}x{} at ({}, {})",
                size.width, size.height, position.x, position.y
            ),
        );

        Self::capture_frozen_screen(logs_dir, frozen_screen, ocr_debug)?;
        let url = format!(
            "region-selector.html?originX={}&originY={}",
            position.x, position.y
        );

        // Create fullscreen transparent window
        let window =
            WebviewWindowBuilder::new(app_handle, "region-selector", WebviewUrl::App(url.into()))
                .title("")
                .inner_size(size.width as f64, size.height as f64)
                .position(position.x as f64, position.y as f64)
                .decorations(false)
                .transparent(false)
                .always_on_top(true)
                .skip_taskbar(true)
                .resizable(false)
                .focused(true)
                .visible(true)
                .build()
                .map_err(|e| format!("Failed to create region selector window: {}", e))?;

        // Explicitly set focus after creation
        let _ = window.set_focus();

        println!("Region selector window created: {:?}", window.label());
        logger::info(
            "region-selector",
            format!("window created label={:?}", window.label()),
        );

        Ok(())
    }

    fn capture_frozen_screen(
        logs_dir: &PathBuf,
        frozen_screen: &FrozenScreenState,
        ocr_debug: bool,
    ) -> Result<(), String> {
        let captured = capture::capture_primary_screen()?;
        logger::info(
            "region-selector",
            format!(
                "captured frozen screen method={} origin=({}, {}) size={}x{}",
                captured.method,
                captured.origin_x,
                captured.origin_y,
                captured.image.width(),
                captured.image.height()
            ),
        );

        if ocr_debug {
            std::fs::create_dir_all(logs_dir)
                .map_err(|e| format!("Failed to create logs directory: {}", e))?;
            let mut path = logs_dir.clone();
            path.push("avalon_atlas_region_frozen.png");

            captured
                .image
                .save(&path)
                .map_err(|e| format!("Failed to save frozen screenshot: {}", e))?;
            logger::info(
                "region-selector",
                format!("saved frozen screenshot debug copy {:?}", path),
            );
        } else {
            logger::info(
                "region-selector",
                "ocr_debug disabled; frozen screenshot kept in memory only",
            );
        }

        frozen_screen.store(captured)?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::HotkeyService;

    #[test]
    fn normalize_hotkey_accepts_frontend_modifier_names() {
        assert_eq!(
            HotkeyService::normalize_hotkey("Ctrl+Shift+Q").unwrap(),
            "ctrl+shift+q"
        );
        assert_eq!(
            HotkeyService::normalize_hotkey("ctrl+win+w").unwrap(),
            "ctrl+super+w"
        );
    }
}
