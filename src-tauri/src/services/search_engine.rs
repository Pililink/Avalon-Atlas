use crate::models::map::{MapRecord, SearchResult};
use crate::utils::fuzzy::subsequence_match;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub struct SearchEngine {
    records: Arc<Vec<MapRecord>>,
    cache: Arc<RwLock<HashMap<(String, usize), Vec<SearchResult>>>>,
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
        if query_lower.chars().count() < 2 || max_results == 0 {
            return vec![];
        }

        let cache_key = (query_lower.clone(), max_results);

        // Cache lookup
        {
            let cache = self.cache.read().unwrap();
            if let Some(results) = cache.get(&cache_key) {
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
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| b.record.tier.cmp(&a.record.tier))
                .then_with(|| a.record.name.cmp(&b.record.name))
        });

        results.truncate(max_results);

        // Update cache
        {
            let mut cache = self.cache.write().unwrap();
            // Simple LRU-like behavior protection: if too big, clear it
            if cache.len() > 1000 {
                cache.clear();
            }
            cache.insert(cache_key, results.clone());
        }

        results
    }

    pub fn search_ocr_candidate(&self, query: &str) -> Option<SearchResult> {
        let query = query.trim().to_lowercase();
        if !looks_like_full_map_query(&query) {
            return None;
        }

        let mut best: Option<SearchResult> = None;
        let mut second_best_score: f64 = 0.0;

        for record in self.records.iter() {
            let candidate = record.slug.trim().to_lowercase();
            let distance = levenshtein_distance(&query, &candidate);
            let max_len = query.chars().count().max(candidate.chars().count()) as f64;
            if max_len == 0.0 {
                continue;
            }

            let similarity = 1.0 - (distance as f64 / max_len);
            let accepted = if query == candidate {
                true
            } else {
                distance <= 2 && similarity >= 0.84
            };

            if !accepted {
                continue;
            }

            if best
                .as_ref()
                .map(|current| similarity > current.score)
                .unwrap_or(true)
            {
                if let Some(current) = best.replace(SearchResult {
                    record: record.clone(),
                    score: similarity,
                    method: "ocr_exact".to_string(),
                    positions: None,
                }) {
                    second_best_score = second_best_score.max(current.score);
                }
            } else {
                second_best_score = second_best_score.max(similarity);
            }
        }

        let best = best?;
        if best.score < 1.0 && best.score - second_best_score < 0.06 {
            return None;
        }

        Some(best)
    }
}

fn looks_like_full_map_query(query: &str) -> bool {
    let Some((left, right)) = query.split_once('-') else {
        return false;
    };

    left.chars().filter(|ch| ch.is_ascii_alphanumeric()).count() >= 3
        && right
            .chars()
            .filter(|ch| ch.is_ascii_alphanumeric())
            .count()
            >= 3
}

fn levenshtein_distance(left: &str, right: &str) -> usize {
    let left: Vec<char> = left.chars().collect();
    let right: Vec<char> = right.chars().collect();

    let mut previous: Vec<usize> = (0..=right.len()).collect();
    let mut current = vec![0; right.len() + 1];

    for (i, left_ch) in left.iter().enumerate() {
        current[0] = i + 1;

        for (j, right_ch) in right.iter().enumerate() {
            let substitution = previous[j] + usize::from(left_ch != right_ch);
            let insertion = current[j] + 1;
            let deletion = previous[j + 1] + 1;
            current[j + 1] = substitution.min(insertion).min(deletion);
        }

        std::mem::swap(&mut previous, &mut current);
    }

    previous[right.len()]
}

#[cfg(test)]
mod tests {
    use super::SearchEngine;
    use crate::models::map::{Chests, Dungeons, MapRecord, Resources};

    fn record(name: &str) -> MapRecord {
        MapRecord {
            name: name.to_string(),
            slug: name.to_string(),
            tier: "T4".to_string(),
            map_type: "TUNNEL_ROYAL".to_string(),
            chests: Chests {
                blue: 0,
                green: 0,
                high_gold: 0,
                low_gold: 0,
            },
            dungeons: Dungeons {
                solo: 0,
                group: 0,
                avalon: 0,
            },
            resources: Resources {
                rock: 0,
                wood: 0,
                ore: 0,
                fiber: 0,
                hide: 0,
            },
            brecilien: 0,
        }
    }

    #[test]
    fn cache_keeps_queries_with_different_limits_separate() {
        let engine = SearchEngine::new(vec![
            record("casos-aiagsum"),
            record("casos-aximam"),
            record("casos-ayosrom"),
        ]);

        let limited = engine.search("casos", 1);
        let expanded = engine.search("casos", 3);

        assert_eq!(limited.len(), 1);
        assert_eq!(expanded.len(), 3);
    }

    #[test]
    fn search_ignores_trimmed_queries_shorter_than_two_chars() {
        let engine = SearchEngine::new(vec![record("casos-aiagsum")]);

        assert!(engine.search(" c ", 10).is_empty());
    }

    #[test]
    fn ocr_candidate_requires_full_map_shape() {
        let engine = SearchEngine::new(vec![record("Oynites-Araosum")]);

        assert!(engine.search_ocr_candidate("oynites-araosum").is_some());
        assert!(engine.search_ocr_candidate("oynites-araosurn").is_some());
        assert!(engine.search_ocr_candidate("bes").is_none());
        assert!(engine.search_ocr_candidate("s-obayal").is_none());
    }
}
