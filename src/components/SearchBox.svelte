<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { SearchResult } from "../lib/types";

  let query = $state("");
  let results = $state<SearchResult[]>([]);
  let loading = $state(false);

  // Debounce helper would be good here, but keeping it simple for now
  async function handleInput() {
    if (query.length < 2) {
      results = [];
      return;
    }

    loading = true;
    try {
      // Assuming command is exposed as 'search_maps'
      results = await invoke("search_maps", { query, maxResults: 20 });
    } catch (e) {
      console.error("Search failed:", e);
    } finally {
      loading = false;
    }
  }
</script>

<div class="search-container">
  <input
    type="text"
    placeholder="在此输入地图名称..."
    bind:value={query}
    oninput={handleInput}
    class="search-input"
  />

  {#if loading}
    <div class="loading">搜索中...</div>
  {/if}

  {#if results.length > 0}
    <div class="results-list">
      {#each results as item}
        <div class="result-item">
          <span class="tier">{item.record.tier}</span>
          <span class="name">{item.record.name}</span>
          <span class="type">{item.record.map_type}</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .search-container {
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
  }

  .search-input {
    width: 100%;
    padding: 12px;
    font-size: 1.2rem;
    border-radius: 8px;
    border: 1px solid #444;
    background: #333;
    color: white;
  }

  .results-list {
    margin-top: 1rem;
    background: #2a2a2a;
    border-radius: 8px;
    overflow: hidden;
  }

  .result-item {
    display: flex;
    align-items: center;
    padding: 10px;
    border-bottom: 1px solid #333;
    gap: 10px;
  }

  .result-item:hover {
    background: #3a3a3a;
  }

  .tier {
    font-weight: bold;
    color: #ffd700;
    width: 30px;
  }

  .name {
    flex: 1;
  }

  .type {
    font-size: 0.8rem;
    color: #888;
  }
</style>
