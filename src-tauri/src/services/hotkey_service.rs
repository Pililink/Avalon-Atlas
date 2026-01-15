use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_global_shortcut::{ShortcutState, GlobalShortcutExt};

pub struct HotkeyService;

impl HotkeyService {
    pub fn register_and_listen(app_handle: AppHandle) -> Result<(), String> {
        println!("HotkeyService: Registering hotkeys using Tauri plugin...");
        
        // Register mouse OCR shortcut: Ctrl+Shift+Q
        let app1 = app_handle.clone();
        app_handle
            .global_shortcut()
            .on_shortcut("Ctrl+Shift+Q", move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    println!("HotkeyService: Ctrl+Shift+Q pressed!");
                    let _ = app1.emit("hotkey-mouse-ocr", ());
                }
            })
            .map_err(|e| format!("Failed to register Ctrl+Shift+Q: {}", e))?;
        
        println!("HotkeyService: Ctrl+Shift+Q registered successfully");
        
        // Register region select OCR shortcut: Ctrl+Shift+W
        let app2 = app_handle.clone();
        app_handle
            .global_shortcut()
            .on_shortcut("Ctrl+Shift+W", move |_app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    println!("HotkeyService: Ctrl+Shift+W pressed!");
                    // Create fullscreen transparent overlay window for region selection
                    if let Err(e) = Self::create_region_selector_window(&app2) {
                        eprintln!("Failed to create region selector window: {}", e);
                    }
                }
            })
            .map_err(|e| format!("Failed to register Ctrl+Shift+W: {}", e))?;
        
        println!("HotkeyService: Ctrl+Shift+W registered successfully");
        
        Ok(())
    }
    
    /// Create a fullscreen transparent overlay window for region selection
    fn create_region_selector_window(app_handle: &AppHandle) -> Result<(), String> {
        // Check if window already exists - close it first
        if let Some(existing) = app_handle.get_webview_window("region-selector") {
            println!("Region selector window already exists, closing it first");
            let _ = existing.close();
        }
        
        println!("Creating region selector overlay window...");
        
        // Get primary monitor dimensions
        let monitors = app_handle.available_monitors()
            .map_err(|e| format!("Failed to get monitors: {}", e))?;
        
        let primary = monitors.into_iter().next()
            .ok_or("No monitor found")?;
        
        let size = primary.size();
        let position = primary.position();
        
        println!("Monitor: {}x{} at ({}, {})", size.width, size.height, position.x, position.y);
        
        // Create fullscreen transparent window
        let window = WebviewWindowBuilder::new(
            app_handle,
            "region-selector",
            WebviewUrl::App("region-selector.html".into())
        )
        .title("")
        .inner_size(size.width as f64, size.height as f64)
        .position(position.x as f64, position.y as f64)
        .decorations(false)
        .transparent(true)
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
        
        Ok(())
    }
}
