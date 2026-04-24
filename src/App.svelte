<script lang="ts">
  import SearchBox from "./components/search/SearchBox.svelte";
  import MapListItem from "./components/map/MapListItem.svelte";
  import Settings from "./components/settings/Settings.svelte";
  import type { SearchResult } from "./lib/maps/types";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { listen } from "@tauri-apps/api/event";
  import { onMount, onDestroy } from "svelte";
  import { normalizeLocale, setLocale, t, type Locale } from "./lib/i18n";
  import { callCommand } from "./lib/tauri/client";

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
    language: string;
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
  let copyStatus = "";

  // Config state (frontend format)
  let config = {
    mouseHotkey: "ctrl+shift+q",
    regionHotkey: "ctrl+shift+w",
    ocrDebug: true,
    ocrRegion: {
      width: 590,
      height: 30,
      verticalOffset: 50
    },
    language: "zh-CN" as Locale
  };

  const appWindow = getCurrentWindow();
  let unlistenMouseOcr: (() => void) | null = null;
  let unlistenRegionSelected: (() => void) | null = null;

  // Load config from backend on mount
  async function loadConfig() {
    try {
      const backendConfig = await callCommand<BackendConfig>('get_config');
      const language = normalizeLocale(backendConfig.language);
      config = {
        mouseHotkey: backendConfig.mouse_hotkey,
        regionHotkey: backendConfig.chat_hotkey,  // Renamed: region select OCR
        ocrDebug: backendConfig.ocr_debug,
        ocrRegion: {
          width: backendConfig.ocr_region.width,
          height: backendConfig.ocr_region.height,
          verticalOffset: backendConfig.ocr_region.vertical_offset
        },
        language
      };
      setLocale(language);
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

  function clearSelectedMaps() {
      selectedMaps = [];
      hoveredMap = null;
      copyStatus = "";
  }

  function handleMouseEnter(record: any) {
      hoveredMap = record.slug;
  }

  function handleMouseLeave() {
      hoveredMap = null;
  }
  
  function handleMouseMove(event: MouseEvent) {
      mouseX = event.clientX;
      mouseY = event.clientY;
  }

  function getPreviewStyle(): string {
      const padding = 10;
      const offset = 18;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const width = Math.min(340, viewportWidth - padding * 2);
      const height = Math.min(260, viewportHeight - padding * 2);

      let left = mouseX + offset;
      if (left + width > viewportWidth - padding) {
          left = Math.max(padding, mouseX - width - offset);
      }

      let top = mouseY + offset;
      if (top + height > viewportHeight - padding) {
          top = Math.max(padding, mouseY - height - offset);
      }

      return `top: ${top}px; left: ${left}px;`;
  }

  function getMapTypeName(type: string): string {
      const translated = $t(`mapType.${type}`);
      return translated === `mapType.${type}` ? type : translated;
  }

  function formatCounts(items: Array<[string, number]>): string {
      return items
          .filter(([, count]) => count > 0)
          .map(([label, count]) => `${label} x${count}`)
          .join(", ");
  }

  function buildMapDescription(result: SearchResult): string {
      const { record } = result;
      const chests = formatCounts([
          [$t("chest.green"), record.chests.green],
          [$t("chest.blue"), record.chests.blue],
          [$t("chest.gold"), record.chests.highGold + record.chests.lowGold],
      ]);
      const dungeons = formatCounts([
          [$t("dungeon.solo"), record.dungeons.solo],
          [$t("dungeon.group"), record.dungeons.group],
          [$t("dungeon.avalon"), record.dungeons.avalon],
      ]);
      const resources = formatCounts([
          [$t("resource.wood"), record.resources.wood],
          [$t("resource.rock"), record.resources.rock],
          [$t("resource.ore"), record.resources.ore],
          [$t("resource.hide"), record.resources.hide],
          [$t("resource.fiber"), record.resources.fiber],
      ]);
      const lines = [
          `${$t("copy.name")}: ${record.name}`,
          `${$t("copy.tier")}: ${record.tier}`,
          `${$t("copy.type")}: ${getMapTypeName(record.map_type)}`,
      ];

      if (chests) lines.push(`${$t("copy.chests")}: ${chests}`);
      if (dungeons) lines.push(`${$t("copy.dungeons")}: ${dungeons}`);
      if (resources) lines.push(`${$t("copy.resources")}: ${resources}`);
      if (record.brecilien > 0) lines.push(`${$t("copy.brecilien")}: ${$t("copy.yes")}`);

      return lines.join("\n");
  }

  async function copyMapDescription(result: SearchResult) {
      const text = buildMapDescription(result);
      try {
          await navigator.clipboard.writeText(text);
          copyStatus = $t("app.copied");
      } catch (error) {
          console.error("Failed to copy map description:", error);
          copyStatus = $t("app.copyFailed");
      }
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
      const results = await callCommand<SearchResult[]>('capture_mouse_ocr', {
        width: config.ocrRegion.width,
        height: config.ocrRegion.height,
        verticalOffset: config.ocrRegion.verticalOffset
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
      const results = await callCommand<SearchResult[]>('capture_region_ocr', {
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
    setLocale(newConfig.language);
    
    // Save to backend
    try {
      await callCommand('save_config', {
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
          debounce_ms: 200,
          language: newConfig.language
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
  <header class="panel-header">
    <div class="panel-title">
      <span class="crest" aria-hidden="true">A</span>
      <div>
        <h1>Avalon Atlas</h1>
        <span>{$t("app.subtitle")}</span>
      </div>
    </div>
    <div class="search-area">
      <SearchBox bind:this={searchBox} on:select={handleSelect} />
      <button class="icon-btn" on:click={openSettings} title={$t("app.settings")} aria-label={$t("app.settings")}>
        ⚙
      </button>
      <button class="icon-btn pin-btn" on:click={toggleAlwaysOnTop} class:active={alwaysOnTop} title={$t("app.alwaysOnTop")} aria-label={$t("app.alwaysOnTop")}>
        ◆
      </button>
    </div>
  </header>

  <div class="content-area">
    {#if selectedMaps.length === 0}
      <div class="empty-state">
        <div class="empty-mark">A</div>
        <p>{$t("app.emptyTitle")}</p>
        <span>{$t("app.emptyHint")}</span>
      </div>
    {:else}
      <div class="results-list">
        {#each selectedMaps as result, i}
          <!-- Wrap explicitly to capture hover events here for the preview -->
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div 
            class="list-item-wrapper"
            on:mouseenter={() => handleMouseEnter(result.record)}
            on:mouseleave={handleMouseLeave}
            on:dblclick={() => copyMapDescription(result)}
            title={$t("app.copyMap")}
          >
            <MapListItem {result} selected={false} />
            <button class="delete-btn" on:click|stopPropagation={() => removeMap(i)} title={$t("app.remove")}>×</button>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <footer>
    <div class="footer-content">
      <button class="status-pill selected-pill" on:click={clearSelectedMaps} disabled={selectedMaps.length === 0} title={$t("app.clearSelection")}>
        <span>{$t("app.selected")}</span>
        <strong>{selectedMaps.length}</strong>
        {#if selectedMaps.length > 0}
          <span class="clear-mark" aria-hidden="true">×</span>
        {/if}
      </button>
      {#if copyStatus}
        <span class="status-item">{copyStatus}</span>
      {/if}
      <span class="status-item">{$t("app.mouseOcr")} <kbd>{config.mouseHotkey}</kbd></span>
      <span class="status-item">{$t("app.regionOcr")} <kbd>{config.regionHotkey}</kbd></span>
      <span class="status-dot" class:active={alwaysOnTop}>{$t("app.pinned")}</span>
    </div>
  </footer>
  
  <!-- Map Preview Float -->
  {#if hoveredMap}
    <div 
        class="map-preview"
        style={getPreviewStyle()}
    >
        <img 
            src="/static/maps/{hoveredMap}.webp" 
            alt={$t("app.mapPreviewAlt")}
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
    min-width: 320px;
    background:
      linear-gradient(180deg, rgba(255, 231, 166, 0.06), transparent 90px),
      var(--bg-primary);
    border: 1px solid var(--border);
    box-shadow: var(--panel-edge), var(--shadow-lg);
  }

  .panel-header {
    background:
      linear-gradient(180deg, rgba(201, 154, 69, 0.14), rgba(0, 0, 0, 0)),
      var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    padding: 8px;
    box-shadow: var(--panel-edge), var(--shadow-sm);
    z-index: 50;
  }

  .panel-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    min-height: 30px;
  }

  .crest {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: 1px solid var(--border-bright);
    border-radius: 4px;
    background: linear-gradient(180deg, var(--accent-hover), var(--accent-deep));
    color: var(--text-dark);
    font-weight: 900;
    font-size: 0.92rem;
    box-shadow: var(--panel-edge);
  }

  .panel-title h1 {
    margin: 0;
    color: var(--text-primary);
    font-size: 0.96rem;
    line-height: 1.1;
    letter-spacing: 0;
  }

  .panel-title span:not(.crest) {
    display: block;
    color: var(--text-tertiary);
    font-size: 0.68rem;
    line-height: 1.1;
    text-transform: uppercase;
  }
  
  .search-area {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  
  .icon-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(180deg, var(--bg-elevated), var(--bg-tertiary));
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-secondary);
    font-size: 1rem;
    font-weight: 800;
    cursor: pointer;
    transition: all 0.2s;
    flex-shrink: 0;
    box-shadow: var(--panel-edge);
  }
  
  .icon-btn:hover {
    background: var(--bg-elevated);
    border-color: var(--border-bright);
    color: var(--text-primary);
  }
  
  .icon-btn.active {
    background: var(--accent-muted);
    border-color: var(--accent);
    color: var(--accent-hover);
  }
  
  .pin-btn.active {
    transform: rotate(45deg);
  }

  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    background:
      linear-gradient(90deg, rgba(201, 154, 69, 0.04), transparent 22%, transparent 78%, rgba(201, 154, 69, 0.04)),
      var(--bg-panel);
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: 760px;
    margin: 0 auto;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--text-secondary);
    gap: 4px;
    text-align: center;
  }

  .empty-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    margin-bottom: 4px;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--bg-inset);
    color: var(--accent);
    font-size: 1.2rem;
    font-weight: 900;
    opacity: 0.82;
  }

  .empty-state p {
    color: var(--text-primary);
    font-size: 0.92rem;
    font-weight: 700;
  }

  .empty-state span {
    color: var(--text-tertiary);
    font-size: 0.78rem;
  }

  footer {
    background:
      linear-gradient(180deg, rgba(255, 231, 166, 0.06), transparent),
      var(--bg-secondary);
    border-top: 1px solid var(--border);
    padding: 6px 8px;
    font-size: 0.76rem;
    margin-top: auto;
    box-shadow: var(--panel-edge);
  }

  .footer-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      flex-wrap: wrap;
      max-width: 760px;
      margin: 0 auto;
      color: var(--text-secondary);
  }

  .status-pill,
  .status-item,
  .status-dot {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      min-height: 22px;
      white-space: nowrap;
  }

  .status-pill {
      padding: 1px 7px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--bg-inset);
      color: var(--text-secondary);
  }

  .status-pill strong {
      color: var(--accent-hover);
  }

  .selected-pill {
      min-width: 58px;
      justify-content: center;
      transition: color 0.2s, border-color 0.2s, background 0.2s;
  }

  .selected-pill:disabled {
      cursor: default;
  }

  .selected-pill:hover:not(:disabled) {
      background: var(--bg-primary);
      border-color: var(--border-bright);
      color: var(--text-primary);
  }

  .clear-mark {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 0;
      overflow: hidden;
      color: var(--danger);
      font-size: 1rem;
      line-height: 1;
      opacity: 0;
      transition: width 0.18s ease, opacity 0.18s ease;
  }

  .selected-pill:hover .clear-mark {
      width: 12px;
      opacity: 1;
  }

  .status-dot::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--text-tertiary);
      box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.35);
  }

  .status-dot.active::before {
      background: var(--success);
      box-shadow: 0 0 8px rgba(127, 159, 90, 0.55);
  }

  /* Map Preview */
  .map-preview {
      position: fixed;
      z-index: 1000;
      pointer-events: none; /* Let mouse events pass through */
      background: var(--bg-inset);
      padding: 5px;
      border-radius: 4px;
      border: 1px solid var(--border-bright);
      box-shadow: var(--panel-edge), 0 10px 26px rgba(0,0,0,0.62);
      width: min(340px, calc(100vw - 20px));
      height: min(260px, calc(100vh - 20px));
      display: flex;
      align-items: center;
      justify-content: center;
  }
  
  .map-preview img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
      border-radius: 2px;
  }
  
  .list-item-wrapper {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 24px;
      gap: 4px;
      align-items: stretch;
      transition: filter 0.2s;
  }
  
  .list-item-wrapper:hover {
      filter: brightness(1.06);
  }

  .delete-btn {
      align-self: stretch;
      background: rgba(15, 12, 9, 0.82);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      width: 24px;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.72;
      transition: opacity 0.2s, background 0.2s;
      font-size: 1.2rem;
      line-height: 1;
      padding-bottom: 2px;
  }

  .list-item-wrapper:hover .delete-btn {
      opacity: 1;
  }

  .delete-btn:hover {
      background: var(--danger);
      border-color: #e18874;
      color: #fff;
  }
</style>
