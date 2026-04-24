use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

static LOG_FILE: OnceLock<Mutex<Option<PathBuf>>> = OnceLock::new();

pub fn init(logs_dir: &Path) -> Result<PathBuf, String> {
    std::fs::create_dir_all(logs_dir)
        .map_err(|e| format!("Failed to create logs directory {:?}: {}", logs_dir, e))?;

    let log_file = logs_dir.join("avalon-atlas.log");
    let state = LOG_FILE.get_or_init(|| Mutex::new(None));
    let mut guard = state
        .lock()
        .map_err(|_| "Failed to lock logger state".to_string())?;
    *guard = Some(log_file.clone());
    drop(guard);

    info("app", format!("logger initialized at {:?}", log_file));
    Ok(log_file)
}

pub fn info(target: &str, message: impl AsRef<str>) {
    write("INFO", target, message.as_ref());
}

pub fn error(target: &str, message: impl AsRef<str>) {
    write("ERROR", target, message.as_ref());
}

fn write(level: &str, target: &str, message: &str) {
    let Some(state) = LOG_FILE.get() else {
        return;
    };

    let Ok(guard) = state.lock() else {
        return;
    };

    let Some(path) = guard.as_ref() else {
        return;
    };

    let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) else {
        return;
    };

    let _ = writeln!(
        file,
        "{} [{}] [{}] {}",
        timestamp(),
        level,
        target,
        message.replace('\n', "\\n").replace('\r', "\\r")
    );
}

fn timestamp() -> String {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();

    format!("{}.{:03}", duration.as_secs(), duration.subsec_millis())
}
