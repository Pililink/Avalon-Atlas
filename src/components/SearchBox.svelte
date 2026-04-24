<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { SearchResult } from "../lib/types";
  import { createEventDispatcher } from "svelte";
  import MapListItem from "./MapListItem.svelte";
  import { t } from "../lib/i18n";

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
    query = $t("search.recognizing");
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
        query = $t("search.noMatches");
        results = [];
      }
    } catch (e) {
      console.error("OCR failed:", e);
      query = $t("search.failed", { error: String(e) });
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
    <span class="search-icon" class:loading aria-hidden="true">⌕</span>
    <input
      type="text"
      placeholder={$t("search.placeholder")}
      bind:value={query}
      on:input={handleInput}
      on:focus={() => { if (results.length > 0) showDropdown = true; }}
      class="search-input"
    />
    
    <!-- Dropdown -->
    {#if showDropdown && results.length > 0}
        <div class="dropdown">
            <div class="dropdown-meta">{$t("search.matches")}</div>
            {#each results as result}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
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
    z-index: 100;
  }

  .input-wrapper {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 11px;
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    font-size: 1rem;
    font-weight: 800;
    pointer-events: none;
    z-index: 1;
    opacity: 0.9;
  }

  .search-icon.loading {
    animation: pulse 0.8s ease-in-out infinite alternate;
  }

  .search-input {
    width: 100%;
    padding: 0 10px 0 36px;
    height: 36px;
    font-size: 0.94rem;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.22), rgba(0, 0, 0, 0.04)), var(--bg-inset);
    color: var(--text-primary);
    transition: all 0.2s;
    box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.55), var(--panel-edge);
  }

  .search-input:focus {
    outline: none;
    border-color: var(--accent);
    background: var(--bg-primary);
    box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(201, 154, 69, 0.28);
  }

  .search-input::placeholder {
    color: var(--text-tertiary);
  }

  .dropdown {
      position: absolute;
      top: calc(100% + 5px);
      left: 0;
      width: calc(100vw - 16px);
      background: var(--bg-panel);
      border: 1px solid var(--border-bright);
      border-radius: 4px;
      max-height: min(390px, calc(100vh - 126px));
      overflow-y: auto;
      box-shadow: var(--panel-edge), 0 12px 28px rgba(0,0,0,0.56);
      z-index: 20;
  }

  .dropdown-meta {
      padding: 5px 8px 4px;
      color: var(--text-tertiary);
      font-size: 0.68rem;
      font-weight: 800;
      text-transform: uppercase;
      border-bottom: 1px solid var(--border-muted);
      background: var(--bg-secondary);
  }
  
  .dropdown-item {
      padding: 4px;
      cursor: pointer;
  }
  
  .dropdown-item:hover {
      background-color: rgba(201, 154, 69, 0.1);
  }

  @keyframes pulse {
    from {
      opacity: 0.45;
      transform: scale(0.94);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
