use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapRecord {
    pub name: String,
    #[serde(default)]
    pub slug: String,
    pub tier: String,
    #[serde(alias = "type")]
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

#[cfg(test)]
mod tests {
    use super::MapRecord;
    use serde_json::json;

    #[test]
    fn map_record_accepts_legacy_type_and_serializes_map_type() {
        let record: MapRecord = serde_json::from_value(json!({
            "name": "casos-aiagsum",
            "tier": "T4",
            "type": "TUNNEL_ROYAL",
            "chests": {
                "blue": 1,
                "green": 2,
                "highGold": 3,
                "lowGold": 4
            },
            "dungeons": {
                "solo": 1,
                "group": 0,
                "avalon": 0
            },
            "resources": {
                "rock": 1,
                "wood": 2,
                "ore": 3,
                "fiber": 4,
                "hide": 5
            },
            "brecilien": 0
        }))
        .expect("legacy type field should deserialize");

        let serialized = serde_json::to_value(record).expect("record should serialize");

        assert_eq!(serialized["map_type"], "TUNNEL_ROYAL");
        assert!(serialized.get("type").is_none());
        assert_eq!(serialized["chests"]["highGold"], 3);
    }
}
