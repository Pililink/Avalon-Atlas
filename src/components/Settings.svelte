<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { locales, setLocale, t, type Locale } from "../lib/i18n";

  const dispatch = createEventDispatcher();

  export let show = false;
  export let config: AppConfig = {
    mouseHotkey: "ctrl+shift+q",
    regionHotkey: "ctrl+shift+w",
    ocrDebug: true,
    ocrRegion: {
      width: 590,
      height: 30,
      verticalOffset: 50
    },
    language: "zh-CN"
  };

  interface AppConfig {
    mouseHotkey: string;
    regionHotkey: string;
    ocrDebug: boolean;
    ocrRegion: {
      width: number;
      height: number;
      verticalOffset: number;
    };
    language: Locale;
  }

  let recordingKey: "mouse" | "region" | null = null;
  let tempMouseHotkey = config.mouseHotkey;
  let tempRegionHotkey = config.regionHotkey;
  let tempOcrDebug = config.ocrDebug;
  let tempLanguage: Locale = config.language;

  $: if (show) {
    tempMouseHotkey = config.mouseHotkey;
    tempRegionHotkey = config.regionHotkey;
    tempOcrDebug = config.ocrDebug;
    tempLanguage = config.language;
  }

  function close(revertLanguage = true) {
    recordingKey = null;
    if (revertLanguage) {
      setLocale(config.language);
    }
    dispatch("close");
  }

  function save() {
    if (!tempMouseHotkey.trim()) {
      alert($t("settings.errorMouseHotkeyRequired"));
      return;
    }
    if (!tempRegionHotkey.trim()) {
      alert($t("settings.errorRegionHotkeyRequired"));
      return;
    }
    if (tempMouseHotkey === tempRegionHotkey) {
      alert($t("settings.errorHotkeyConflict"));
      return;
    }

    const newConfig: AppConfig = {
      ...config,
      mouseHotkey: tempMouseHotkey,
      regionHotkey: tempRegionHotkey,
      ocrDebug: tempOcrDebug,
      language: tempLanguage
    };

    dispatch("save", newConfig);
    close(false);
  }

  function startRecording(type: "mouse" | "region") {
    recordingKey = type;
  }

  function handleLanguageChange(event: Event) {
    tempLanguage = (event.currentTarget as HTMLSelectElement).value as Locale;
    setLocale(tempLanguage);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!recordingKey) return;
    
    event.preventDefault();
    event.stopPropagation();

    const modifiers: string[] = [];
    if (event.ctrlKey) modifiers.push("ctrl");
    if (event.altKey) modifiers.push("alt");
    if (event.shiftKey) modifiers.push("shift");
    if (event.metaKey) modifiers.push("super");

    let key = event.key.toLowerCase();
    
    // Skip if only modifier keys pressed
    if (["control", "alt", "shift", "meta"].includes(key)) {
      return;
    }

    // Normalize key names
    if (key === " ") key = "space";
    if (key === "escape") {
      recordingKey = null;
      return;
    }

    modifiers.sort();
    const combo = [...modifiers, key].join("+");

    if (recordingKey === "mouse") {
      tempMouseHotkey = combo;
    } else {
      tempRegionHotkey = combo;
    }
    
    recordingKey = null;
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      close();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="modal-backdrop" on:click={handleBackdropClick}>
    <div class="modal-content">
      <header>
        <h2>{$t("settings.title")}</h2>
        <button class="close-btn" on:click={() => close()}>×</button>
      </header>

      <div class="settings-body">
        <!-- Hotkey Settings -->
        <section class="settings-group">
          <h3>{$t("settings.hotkeys")}</h3>

          <div class="setting-row">
            <span class="setting-label">{$t("settings.mouseHotkey")}</span>
            <div class="hotkey-input-group">
              <input 
                type="text" 
                readonly
                value={recordingKey === "mouse" ? $t("settings.pressCombo") : tempMouseHotkey}
                class="hotkey-input"
                class:recording={recordingKey === "mouse"}
              />
              <button 
                class="record-btn"
                class:recording={recordingKey === "mouse"}
                on:click={() => startRecording("mouse")}
                disabled={recordingKey !== null}
              >
                {recordingKey === "mouse" ? $t("settings.recording") : $t("settings.record")}
              </button>
            </div>
            <span class="help-text">{$t("settings.mouseHotkeyHelp")}</span>
          </div>

          <div class="setting-row">
            <span class="setting-label">{$t("settings.regionHotkey")}</span>
            <div class="hotkey-input-group">
              <input 
                type="text" 
                readonly
                value={recordingKey === "region" ? $t("settings.pressCombo") : tempRegionHotkey}
                class="hotkey-input"
                class:recording={recordingKey === "region"}
              />
              <button 
                class="record-btn"
                class:recording={recordingKey === "region"}
                on:click={() => startRecording("region")}
                disabled={recordingKey !== null}
              >
                {recordingKey === "region" ? $t("settings.recording") : $t("settings.record")}
              </button>
            </div>
            <span class="help-text">{$t("settings.regionHotkeyHelp")}</span>
          </div>
        </section>

        <!-- Other Settings -->
        <section class="settings-group">
          <h3>{$t("settings.other")}</h3>

          <div class="setting-row">
            <span class="setting-label">{$t("settings.language")}</span>
            <select class="language-select" bind:value={tempLanguage} on:change={handleLanguageChange}>
              {#each locales as localeCode}
                <option value={localeCode}>{$t(`locale.${localeCode}`)}</option>
              {/each}
            </select>
          </div>
          
          <div class="setting-row checkbox-row">
            <label class="checkbox-label">
              <input type="checkbox" bind:checked={tempOcrDebug} />
              <span>{$t("settings.debugOcr")}</span>
            </label>
            <span class="help-text">{$t("settings.debugOcrHelp")}</span>
          </div>
        </section>
      </div>

      <footer>
        <button class="btn btn-secondary" on:click={() => close()}>{$t("settings.cancel")}</button>
        <button class="btn btn-primary" on:click={save}>{$t("settings.save")}</button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(8, 6, 4, 0.72);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background:
      linear-gradient(180deg, rgba(201, 154, 69, 0.12), transparent 72px),
      var(--bg-panel);
    border-radius: 5px;
    width: 500px;
    max-width: 90vw;
    max-height: 80vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: var(--panel-edge), 0 18px 42px rgba(0, 0, 0, 0.62);
    border: 1px solid var(--border-bright);
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  header h2 {
    margin: 0;
    font-size: 1rem;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .settings-body {
    padding: 14px;
    overflow-y: auto;
    flex: 1;
  }

  .settings-group {
    margin-bottom: 16px;
  }

  .settings-group:last-child {
    margin-bottom: 0;
  }

  .settings-group h3 {
    font-size: 0.82rem;
    color: var(--text-primary);
    margin: 0 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
  }

  .setting-row {
    margin-bottom: 12px;
  }

  .setting-row label {
    display: block;
    font-size: 0.9rem;
    color: var(--text-primary);
    margin-bottom: 6px;
  }

  .hotkey-input-group {
    display: flex;
    gap: 8px;
  }

  .hotkey-input {
    flex: 1;
    height: 34px;
    padding: 0 10px;
    background: var(--bg-inset);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-primary);
    font-family: monospace;
    font-size: 0.86rem;
    box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.45);
  }

  .language-select {
    width: 100%;
    height: 36px;
    padding: 0 10px;
    background: var(--bg-inset);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 0.92rem;
    box-shadow: var(--panel-edge);
  }

  .language-select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 1px rgba(201, 154, 69, 0.28);
  }

  .hotkey-input.recording {
    border-color: var(--accent);
    background: var(--bg-primary);
  }

  .record-btn {
    height: 34px;
    padding: 0 12px;
    background: linear-gradient(180deg, var(--bg-elevated), var(--bg-tertiary));
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
    box-shadow: var(--panel-edge);
  }

  .record-btn:hover:not(:disabled) {
    background: var(--bg-elevated);
    border-color: var(--text-tertiary);
  }

  .record-btn.recording {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--text-dark);
    font-weight: 800;
  }

  .record-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .help-text {
    display: block;
    font-size: 0.8rem;
    color: var(--text-tertiary);
    margin-top: 4px;
  }

  .checkbox-row {
    display: flex;
    flex-direction: column;
  }

  .checkbox-label {
    display: flex !important;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .checkbox-label input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent);
  }

  .checkbox-label span {
    color: var(--text-primary);
  }

  footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 10px 14px;
    border-top: 1px solid var(--border);
    background: var(--bg-secondary);
  }

  .btn {
    min-width: 76px;
    height: 34px;
    padding: 0 14px;
    border-radius: 4px;
    font-size: 0.88rem;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: var(--panel-edge);
  }

  .btn-secondary {
    background: linear-gradient(180deg, var(--bg-elevated), var(--bg-tertiary));
    border: 1px solid var(--border);
    color: var(--text-primary);
  }

  .btn-secondary:hover {
    background: var(--bg-elevated);
  }

  .btn-primary {
    background: linear-gradient(180deg, var(--accent-hover), var(--accent));
    border: 1px solid var(--accent);
    color: var(--text-dark);
    font-weight: 800;
  }

  .btn-primary:hover {
    filter: brightness(1.1);
  }
</style>
