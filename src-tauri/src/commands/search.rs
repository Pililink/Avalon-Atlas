use crate::models::map::SearchResult;
use crate::services::search_engine::SearchEngine;
use std::sync::Arc;
use tauri::State;

#[tauri::command]
pub async fn search_maps(
    query: String,
    max_results: Option<usize>,
    engine: State<'_, Arc<SearchEngine>>,
) -> Result<Vec<SearchResult>, String> {
    if query.len() < 2 {
        return Ok(vec![]);
    }

    let results = engine.search(&query, max_results.unwrap_or(25));
    Ok(results)
}
