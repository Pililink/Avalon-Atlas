use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use crate::models::map::{MapRecord, SearchResult};
use crate::utils::fuzzy::{subsequence_match};

pub struct SearchEngine {
    records: Arc<Vec<MapRecord>>,
    cache: Arc<RwLock<HashMap<String, Vec<SearchResult>>>>,
}

impl SearchEngine {
    pub fn new(records: Vec<MapRecord>) -> Self {
        Self {
            records: Arc::new(records),
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn search(&self, query: &str, max_results: usize) -> Vec<SearchResult> {
        let query_lower = query.trim().to_lowercase();
        
        // Cache lookup
        {
            let cache = self.cache.read().unwrap();
            if let Some(results) = cache.get(&query_lower) {
                return results.clone();
            }
        }

        let mut results: Vec<SearchResult> = vec![];

        for record in self.records.iter() {
            if let Some(detail) = subsequence_match(&query_lower, &record.name) {
                results.push(SearchResult {
                    record: record.clone(),
                    score: detail.score,
                    method: "subsequence".to_string(),
                    positions: Some(detail.positions),
                });
            } else if let Some(detail) = subsequence_match(&query_lower, &record.slug) {
                 results.push(SearchResult {
                    record: record.clone(),
                    score: detail.score,
                    method: "slug_subsequence".to_string(),
                    positions: Some(detail.positions),
                });
            }
        }

        // Sort by score desc, then tier desc
        results.sort_by(|a, b| {
            b.score.partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.record.tier.cmp(&b.record.tier))
        });

        results.truncate(max_results);

        // Update cache
        {
            let mut cache = self.cache.write().unwrap();
            // Simple LRU-like behavior protection: if too big, clear it
            if cache.len() > 1000 {
                cache.clear();
            }
            cache.insert(query_lower, results.clone());
        }

        results
    }
}
