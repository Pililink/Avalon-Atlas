<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { SearchResult } from "../lib/types";
  import { createEventDispatcher } from "svelte";
  import MapListItem from "./MapListItem.svelte";

  const dispatch = createEventDispatcher();

  let query = "";
  let loading = false;
  let results: SearchResult[] = [];
  let showDropdown = false;
  let searchContainer: HTMLDivElement;

  async function handleInput() {
    if (query.trim().length < 1) {
      results = [];
      showDropdown = false;
      return;
    }

    loading = true;
    showDropdown = true;
    try {
      const res = await invoke("search_maps", { query, maxResults: 10 }) as SearchResult[];
      results = res;
    } catch (e) {
      console.error("Search failed:", e);
    } finally {
      loading = false;
    }
  }

  export async function handleCapture() {
    loading = true;
    query = "正在识别...";
    showDropdown = false;
    try {
      const res = await invoke("capture_and_search") as SearchResult[];
      if (res.length > 0) {
        // For OCR, maybe we just pick the first one or show results?
        // User said: "hit content similar to search result dropdown click" 
        // But for OCR, usually we want immediate action or clarification.
        // Let's verify with dropdown.
        query = res[0].record.name; 
        results = res;
        showDropdown = true;
      } else {
        query = "无匹配结果";
        results = [];
      }
    } catch (e) {
      console.error("OCR failed:", e);
      query = `识别失败: ${e}`;
    } finally {
      loading = false;
    }
  }
  
  function selectItem(item: SearchResult) {
      dispatch('select', item);
      showDropdown = false;
      query = ""; // Clear after select? Or keep? User didn't specify. Clearing is standard for "Add to list".
      results = [];
  }

  // Close dropdown when clicking outside
  function handleWindowClick(event: MouseEvent) {
    if (searchContainer && !searchContainer.contains(event.target as Node)) {
      showDropdown = false;
    }
  }
</script>

<svelte:window on:click={handleWindowClick} />

<div class="search-bar" bind:this={searchContainer}>
  <div class="input-wrapper">
    <span class="search-icon">🔍</span>
    <input
      type="text"
      placeholder="输入地图名称..."
      bind:value={query}
      on:input={handleInput}
      on:focus={() => { if (results.length > 0) showDropdown = true; }}
      class="search-input"
    />
    
    <!-- Dropdown -->
    {#if showDropdown && results.length > 0}
        <div class="dropdown">
            {#each results as result}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <div class="dropdown-item" on:click={() => selectItem(result)}>
                    <MapListItem {result} />
                </div>
            {/each}
        </div>
    {/if}
  </div>
</div>

<style>
  .search-bar {
    display: flex;
    gap: 10px;
    width: 100%;
    align-items: center;
    position: relative; 
    z-index: 100; /* Ensure dropdown is on top */
  }

  .input-wrapper {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 12px;
    font-size: 1.2rem;
    pointer-events: none;
    z-index: 1;
    opacity: 0.5; /* more subtle */
  }

  .search-input {
    width: 100%;
    padding: 0 12px 0 42px;
    height: 48px; 
    font-size: 1.1rem;
    border-radius: 6px;
    border: none; /* Cleaner look */
    background: rgba(255, 255, 255, 0.05); /* Very subtle bg */
    color: var(--text-primary);
    transition: all 0.2s;
  }

  .search-input:focus {
    outline: none;
    background: rgba(255, 255, 255, 0.1);
    box-shadow: 0 0 0 1px var(--accent);
  }

  .dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      width: 100%;
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 0 0 6px 6px;
      margin-top: 4px;
      max-height: 400px;
      overflow-y: auto;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }
  
  .dropdown-item {
      padding: 0;
      cursor: pointer;
  }
  
  .dropdown-item:hover {
      background-color: var(--bg-tertiary);
  }
</style>
