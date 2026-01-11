use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_global_shortcut::{Code, Modifiers, ShortcutState, GlobalShortcutExt};

pub struct HotkeyService;

impl HotkeyService {
    pub fn new() -> Result<Self, String> {
        Ok(Self)
    }

    pub fn register_and_listen(app_handle: AppHandle) -> Result<(), String> {
        println!("HotkeyService: Registering Ctrl+Shift+Q using Tauri plugin...");
        
        // Register shortcut using Tauri's plugin
        app_handle
            .global_shortcut()
            .on_shortcut("Ctrl+Shift+Q", move |app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    println!("HotkeyService: Ctrl+Shift+Q pressed!");
                    let _ = app.emit("hotkey-mouse-ocr", ());
                }
            })
            .map_err(|e| format!("Failed to register shortcut: {}", e))?;
        
        println!("HotkeyService: Ctrl+Shift+Q registered successfully");
        Ok(())
    }
}
