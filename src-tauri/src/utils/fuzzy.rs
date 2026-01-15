use std::f64;

#[derive(Debug, Clone)]
pub struct MatchDetail {
    pub score: f64,
    pub positions: Vec<usize>,
}

const BASE_SCORE: f64 = 10.0;
const ADJACENT_BONUS: f64 = 14.0;
const WORD_START_BONUS: f64 = 8.0;
const START_OF_STRING_BONUS: f64 = 4.0;
const GAP_PENALTY: f64 = 2.0;

/// similar chars mapping
fn chars_match(ch1: char, ch2: char) -> bool {
    if ch1 == ch2 {
        return true;
    }
    match ch1 {
        'i' | 'l' | '1' | '|' => matches!(ch2, 'i' | 'l' | '1' | '|'),
        'o' | '0' => matches!(ch2, 'o' | '0'),
        's' | '5' => matches!(ch2, 's' | '5'),
        'z' | '2' => matches!(ch2, 'z' | '2'),
        _ => false,
    }
}

pub fn subsequence_match(query: &str, candidate: &str) -> Option<MatchDetail> {
    let query = query.trim().to_lowercase();
    let candidate = candidate.to_lowercase();
    
    if query.is_empty() || candidate.is_empty() {
        return None;
    }
    
    if query.len() > candidate.len() {
        return None;
    }

    let m = query.len();
    let n = candidate.len();
    let query_chars: Vec<char> = query.chars().collect();
    let target_chars: Vec<char> = candidate.chars().collect();
    let original_chars: Vec<char> = candidate.chars().collect(); // For is_word_start check if needed

    // dp[i][j] stores the best score matching query[0..=i] ending at candidate[j]
    let mut dp = vec![vec![f64::NEG_INFINITY; n]; m];
    let mut backtrack = vec![vec![-1i32; n]; m];

    // Initialize first row
    for j in 0..n {
        if chars_match(query_chars[0], target_chars[j]) {
            dp[0][j] = score_position(&original_chars, j, None);
        }
    }

    // Check if first char matched at all
    // Optimization: if max(dp[0]) is NEG_INFINITY, return None early

    for i in 1..m {
        for j in i..n {
             if !chars_match(query_chars[i], target_chars[j]) {
                continue;
            }
            
            let mut best_score = f64::NEG_INFINITY;
            let mut best_prev = -1;
            
            // Try to extend from any valid previous position k < j
            for k in 0..j {
                let prev_score = dp[i-1][k];
                if prev_score == f64::NEG_INFINITY {
                    continue;
                }
                
                let current_score = prev_score + score_position(&original_chars, j, Some(k));
                if current_score > best_score {
                    best_score = current_score;
                    best_prev = k as i32;
                }
            }
            
            dp[i][j] = best_score;
            backtrack[i][j] = best_prev;
        }
    }

    // Find best end position
    let mut best_final_score = f64::NEG_INFINITY;
    let mut best_final_idx = -1;
    
    for j in 0..n {
        let s = dp[m-1][j];
        if s > best_final_score {
            best_final_score = s;
            best_final_idx = j as i32;
        }
    }

    if best_final_score == f64::NEG_INFINITY {
        return None;
    }

    // Backtrack to find positions
    let mut positions = vec![0; m];
    let mut curr_idx = best_final_idx as usize;
    
    for i in (0..m).rev() {
        positions[i] = curr_idx;
        if i > 0 {
            let prev = backtrack[i][curr_idx];
            if prev == -1 {
                return None; // Should not happen if score is valid
            }
            curr_idx = prev as usize;
        }
    }

    Some(MatchDetail {
        score: best_final_score,
        positions,
    })
}

fn score_position(text: &[char], idx: usize, prev_idx: Option<usize>) -> f64 {
    let mut score = BASE_SCORE;
    
    if is_word_start(text, idx) {
        score += WORD_START_BONUS;
    }
    if idx == 0 {
        score += START_OF_STRING_BONUS;
    }

    match prev_idx {
        None => {
            score -= (idx as f64) * GAP_PENALTY;
        }
        Some(prev) => {
            let gap = (idx as i32) - (prev as i32) - 1;
            if gap <= 0 {
                score += ADJACENT_BONUS;
            } else {
                score -= (gap as f64) * GAP_PENALTY;
            }
        }
    }
    
    score
}

fn is_word_start(text: &[char], idx: usize) -> bool {
    if idx == 0 {
        return true;
    }
    let prev = text[idx - 1];
    if prev == '-' || prev == '_' || prev == ' ' || prev == '/' {
        return true;
    }
    let curr = text[idx];
    if prev.is_lowercase() && curr.is_uppercase() {
        return true;
    }
    false
}
