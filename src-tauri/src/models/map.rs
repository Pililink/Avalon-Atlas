use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapRecord {
    pub name: String,
    #[serde(skip, default)]
    pub slug: String,
    pub tier: String,
    #[serde(rename = "type")]
    pub map_type: String,
    pub chests: Chests,
    pub dungeons: Dungeons,
    pub resources: Resources,
    pub brecilien: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chests {
    pub blue: u32,
    pub green: u32,
    #[serde(rename = "highGold")]
    pub high_gold: u32,
    #[serde(rename = "lowGold")]
    pub low_gold: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dungeons {
    pub solo: u32,
    pub group: u32,
    pub avalon: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Resources {
    pub rock: u32,
    pub wood: u32,
    pub ore: u32,
    pub fiber: u32,
    pub hide: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub record: MapRecord,
    pub score: f64,
    pub method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub positions: Option<Vec<usize>>,
}
