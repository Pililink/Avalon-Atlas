<script lang="ts">
  import SearchBox from "./components/SearchBox.svelte";
  import MapListItem from "./components/MapListItem.svelte";
  import Settings from "./components/Settings.svelte";
  import type { SearchResult } from "./lib/types";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { listen } from "@tauri-apps/api/event";
  import { invoke } from "@tauri-apps/api/core";
  import { onMount, onDestroy } from "svelte";

  interface BackendConfig {
    mouse_hotkey: string;
    chat_hotkey: string;
    ocr_debug: boolean;
    ocr_region: {
      width: number;
      height: number;
      vertical_offset: number;
    };
    always_on_top: boolean;
    debounce_ms: number;
  }

  // Region selection event payload from overlay window
  interface RegionSelectedPayload {
    x: number;
    y: number;
    width: number;
    height: number;
  }

  let selectedMaps: SearchResult[] = [];
  let hoveredMap: string | null = null;
  let mouseX = 0;
  let mouseY = 0;
  let alwaysOnTop = false;
  let showSettings = false;

  // Config state (frontend format)
  let config = {
    mouseHotkey: "ctrl+shift+q",
    regionHotkey: "ctrl+shift+w",
    ocrDebug: true,
    ocrRegion: {
      width: 600,
      height: 80,
      verticalOffset: 0
    }
  };

  const appWindow = getCurrentWindow();
  let unlistenMouseOcr: (() => void) | null = null;
  let unlistenRegionSelected: (() => void) | null = null;

  // Load config from backend on mount
  async function loadConfig() {
    try {
      const backendConfig = await invoke<BackendConfig>('get_config');
      config = {
        mouseHotkey: backendConfig.mouse_hotkey,
        regionHotkey: backendConfig.chat_hotkey,  // Renamed: region select OCR
        ocrDebug: backendConfig.ocr_debug,
        ocrRegion: {
          width: backendConfig.ocr_region.width,
          height: backendConfig.ocr_region.height,
          verticalOffset: backendConfig.ocr_region.vertical_offset
        }
      };
      alwaysOnTop = backendConfig.always_on_top;
      if (alwaysOnTop) {
        await appWindow.setAlwaysOnTop(true);
      }
      console.log('Loaded config:', config);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  }

  function handleSelect(event: CustomEvent<SearchResult>) {
    // Add to list if not already present (by ID)
    const newItem = event.detail;
    // Check if map name and tier match (simple uniqueness check)
    if (!selectedMaps.some(m => m.record.name === newItem.record.name && m.record.tier === newItem.record.tier)) {
         selectedMaps = [...selectedMaps, newItem];
    }
  }

  function removeMap(index: number) {
      selectedMaps = selectedMaps.filter((_, i) => i !== index);
      hoveredMap = null; // Clear preview immediately
  }

  function handleMouseEnter(event: MouseEvent, record: any) {
      hoveredMap = record.slug;
  }

  function handleMouseLeave() {
      hoveredMap = null;
  }
  
  function handleMouseMove(event: MouseEvent) {
      mouseX = event.clientX;
      mouseY = event.clientY;
  }
  let searchBox: SearchBox;

  function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'F4') {
          searchBox.handleCapture();
      }
  }
  
  async function toggleAlwaysOnTop() {
      alwaysOnTop = !alwaysOnTop;
      await appWindow.setAlwaysOnTop(alwaysOnTop);
  }

  // Hotkey OCR handler - Ctrl+Shift+Q
  // Uses parameters from config (same as Python version)
  async function handleMouseOcr() {
    try {
      console.log('Mouse OCR triggered at:', mouseX, mouseY);
      // Python version: mouse at bottom center of region
      const results = await invoke<SearchResult[]>('capture_mouse_ocr', {
        x: mouseX,
        y: mouseY,
        width: config.ocrRegion.width,
        height: config.ocrRegion.height
      });
      
      // Add results to selected maps
      for (const result of results) {
        if (!selectedMaps.some(m => m.record.name === result.record.name && m.record.tier === result.record.tier)) {
          selectedMaps = [...selectedMaps, result];
        }
      }
    } catch (error) {
      console.error('Mouse OCR failed:', error);
    }
  }

  onMount(async () => {
    // Load config from backend
    await loadConfig();
    
    // Listen for mouse OCR hotkey from backend
    unlistenMouseOcr = await listen('hotkey-mouse-ocr', () => {
      handleMouseOcr();
    });
    
    // Listen for region selection from overlay window
    unlistenRegionSelected = await listen<RegionSelectedPayload>('region-selected', async (event) => {
      console.log('Region selected from overlay:', event.payload);
      await handleRegionOcr(event.payload);
    });
  });

  onDestroy(() => {
    if (unlistenMouseOcr) unlistenMouseOcr();
    if (unlistenRegionSelected) unlistenRegionSelected();
  });

  function openSettings() {
    showSettings = true;
  }

  // Handle region OCR - called when overlay window sends region-selected event
  async function handleRegionOcr(region: RegionSelectedPayload) {
    const { x, y, width, height } = region;
    console.log('Performing OCR on region:', x, y, width, height);
    
    try {
      const results = await invoke<SearchResult[]>('capture_region_ocr', {
        x, y, width, height
      });
      
      // Add results to selected maps
      for (const result of results) {
        if (!selectedMaps.some(m => m.record.name === result.record.name && m.record.tier === result.record.tier)) {
          selectedMaps = [...selectedMaps, result];
        }
      }
    } catch (error) {
      console.error('Region OCR failed:', error);
    }
  }

  // Legacy handler for in-window region selector (no longer used)
  async function handleRegionComplete(event: CustomEvent<{ x: number; y: number; width: number; height: number }>) {
    await handleRegionOcr(event.detail);
  }

  async function handleSettingsSave(event: CustomEvent) {
    const newConfig = event.detail;
    config = newConfig;
    
    // Save to backend
    try {
      await invoke('save_config', {
        newConfig: {
          mouse_hotkey: newConfig.mouseHotkey,
          chat_hotkey: newConfig.regionHotkey,  // Backend uses chat_hotkey field
          ocr_debug: newConfig.ocrDebug,
          ocr_region: {
            width: newConfig.ocrRegion.width,
            height: newConfig.ocrRegion.height,
            vertical_offset: newConfig.ocrRegion.verticalOffset
          },
          always_on_top: alwaysOnTop,
          debounce_ms: 200
        }
      });
      console.log('Settings saved:', config);
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  }
</script>

<svelte:window on:mousemove={handleMouseMove} on:contextmenu|preventDefault={() => {}} on:keydown={handleKeydown}/>

<main>
  <header>
    <div class="search-area">
      <SearchBox bind:this={searchBox} on:select={handleSelect} />
      <button class="icon-btn" on:click={openSettings} title="设置">
        ⚙️
      </button>
      <button class="icon-btn" on:click={toggleAlwaysOnTop} class:active={alwaysOnTop} title="窗口置顶">
        📌
      </button>
    </div>
  </header>

  <div class="content-area">
    {#if selectedMaps.length === 0}
      <div class="empty-state">
        <p>搜索添加地图以构建你的图集</p>
      </div>
    {:else}
      <div class="results-list">
        {#each selectedMaps as result, i}
          <!-- Wrap explicitly to capture hover events here for the preview -->
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div 
            class="list-item-wrapper"
            on:mouseenter={(e) => handleMouseEnter(e, result.record)}
            on:mouseleave={handleMouseLeave}
          >
            <MapListItem {result} selected={false} />
            <button class="delete-btn" on:click|stopPropagation={() => removeMap(i)} title="移除">×</button>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <footer>
    <div class="footer-content">
      <div class="hotkey-section">
        <h3>⌨️ 热键</h3>
        <div class="hotkey-row">
           <span class="hotkey-label">鼠标 OCR:</span>
           <div class="key-bind">{config.mouseHotkey}</div>
        </div>
        <div class="hotkey-row">
           <span class="hotkey-label">框选 OCR:</span>
           <div class="key-bind">{config.regionHotkey}</div>
        </div>
      </div>
      
      <div class="help-section">
         <h3>❓ 使用说明</h3>
         <p>1. 搜索或热键 OCR 添加地图</p>
         <p>2. 鼠标悬停查看地图预览</p>
         <p>3. 点击 × 移除地图</p>
      </div>
    </div>
  </footer>
  
  <!-- Map Preview Float -->
  {#if hoveredMap}
    <div 
        class="map-preview" 
        style="top: {mouseY + 20}px; left: {mouseX + 20}px;" 
    >
        <img 
            src="/static/maps/{hoveredMap}.webp" 
            alt="Map Preview" 
            on:error={() => console.error('Failed to load map image:', hoveredMap)}
        />
    </div>
  {/if}
  
  <!-- Settings Dialog -->
  <Settings 
    bind:show={showSettings} 
    {config} 
    on:close={() => showSettings = false}
    on:save={handleSettingsSave}
  />
</main>

<style>
  main {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background-color: var(--bg-primary);
  }

  header {
    background-color: var(--bg-secondary);
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    z-index: 50;
  }
  
  .search-area {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  
  .icon-btn {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 1.2rem;
    cursor: pointer;
    transition: all 0.2s;
    flex-shrink: 0;
  }
  
  .icon-btn:hover {
    background: var(--bg-elevated);
    border-color: var(--text-tertiary);
  }
  
  .icon-btn.active {
    background: var(--accent-muted);
    border-color: var(--accent);
  }
  
  .icon-btn.active[title="窗口置顶"] {
    transform: rotate(45deg);
  }

  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 800px;
    margin: 0 auto;
  }

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--text-secondary);
    font-size: 1.1rem;
    opacity: 0.5;
  }

  footer {
    background-color: var(--bg-secondary);
    border-top: 1px solid var(--border);
    padding: 16px;
    font-size: 0.9rem;
    margin-top: auto;
  }

  .footer-content {
      display: flex;
      justify-content: space-around;
      max-width: 800px;
      margin: 0 auto;
      color: var(--text-secondary);
  }
  
  .footer-content h3 {
      font-size: 1rem;
      margin-bottom: 8px;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 6px;
  }
  
  .hotkey-row {
      display: flex;
      gap: 10px;
      align-items: center;
  }
  
  .key-bind {
      background: #444;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: monospace;
      color: #fff;
      border: 1px solid #666;
  }
  
  .help-section p {
      margin: 4px 0;
      font-size: 0.85rem;
  }

  /* Map Preview */
  .map-preview {
      position: fixed;
      z-index: 1000;
      pointer-events: none; /* Let mouse events pass through */
      background: rgba(0, 0, 0, 0.8);
      padding: 4px;
      border-radius: 4px;
      border: 1px solid var(--border);
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      max-width: 400px;
      transform: translateY(10px); /* Offset slightly */
  }
  
  .map-preview img {
      display: block;
      max-width: 100%;
      height: auto;
      border-radius: 2px;
  }
  
  .list-item-wrapper {
      position: relative;
      transition: transform 0.2s;
  }
  
  .list-item-wrapper:hover {
      transform: translateX(4px);
  }

  .delete-btn {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      background: rgba(0, 0, 0, 0.5);
      border: none;
      color: #fff;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.2s, background 0.2s;
      font-size: 1.2rem;
      line-height: 1;
      padding-bottom: 2px;
  }

  .list-item-wrapper:hover .delete-btn {
      opacity: 1;
  }

  .delete-btn:hover {
      background: #ff5252;
  }
</style>
