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
      results = await invoke("search_maps", { query, maxResults: 20 });
    } catch (e) {
      console.error("Search failed:", e);
    } finally {
      loading = false;
    }
  }

  async function handleCapture() {
    loading = true;
    query = "正在识别...";
    try {
      results = await invoke("capture_and_search");
      if (results.length > 0) {
        query = results[0].record.name; // Use first match name as query
      } else {
        query = "无匹配结果";
      }
    } catch (e) {
      console.error("OCR failed:", e);
      query = `识别失败: ${e}`;
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
  
  <button class="capture-btn" onclick={handleCapture} disabled={loading} title="截图识别">
    📷
  </button>

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
    position: relative;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .search-input {
    flex: 1;
    padding: 12px;
    font-size: 1.2rem;
    border-radius: 8px;
    border: 1px solid #444;
    background: #333;
    color: white;
  }

  .capture-btn {
    padding: 0 20px;
    font-size: 1.5rem;
    background: #4ecdc4;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .capture-btn:hover:not(:disabled) {
    background: #45b7af;
  }

  .capture-btn:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  .results-list {
    width: 100%;
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
