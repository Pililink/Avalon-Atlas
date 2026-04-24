export interface MapRecord {
    name: string;
    slug: string;
    tier: string;
    map_type: string;
    chests: {
        blue: number;
        green: number;
        highGold: number;
        lowGold: number;
    };
    dungeons: {
        solo: number;
        group: number;
        avalon: number;
    };
    resources: {
        rock: number;
        wood: number;
        ore: number;
        fiber: number;
        hide: number;
    };
    brecilien: number;
}

export interface SearchResult {
    record: MapRecord;
    score: number;
    method: string;
    positions?: number[];
}
