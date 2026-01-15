<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import { invoke } from "@tauri-apps/api/core";

  const dispatch = createEventDispatcher();

  export let show = false;
  export let config: AppConfig = {
    mouseHotkey: "ctrl+shift+q",
    regionHotkey: "ctrl+shift+w",
    ocrDebug: true,
    ocrRegion: {
      width: 600,
      height: 80,
      verticalOffset: 0
    }
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
  }

  let recordingKey: "mouse" | "region" | null = null;
  let tempMouseHotkey = config.mouseHotkey;
  let tempRegionHotkey = config.regionHotkey;
  let tempOcrDebug = config.ocrDebug;

  $: if (show) {
    tempMouseHotkey = config.mouseHotkey;
    tempRegionHotkey = config.regionHotkey;
    tempOcrDebug = config.ocrDebug;
  }

  function close() {
    recordingKey = null;
    dispatch("close");
  }

  function save() {
    if (!tempMouseHotkey.trim()) {
      alert("鼠标 OCR 热键不能为空");
      return;
    }
    if (!tempRegionHotkey.trim()) {
      alert("框选 OCR 热键不能为空");
      return;
    }
    if (tempMouseHotkey === tempRegionHotkey) {
      alert("两个热键不能相同");
      return;
    }

    const newConfig: AppConfig = {
      ...config,
      mouseHotkey: tempMouseHotkey,
      regionHotkey: tempRegionHotkey,
      ocrDebug: tempOcrDebug
    };

    dispatch("save", newConfig);
    close();
  }

  function startRecording(type: "mouse" | "region") {
    recordingKey = type;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!recordingKey) return;
    
    event.preventDefault();
    event.stopPropagation();

    const modifiers: string[] = [];
    if (event.ctrlKey) modifiers.push("ctrl");
    if (event.altKey) modifiers.push("alt");
    if (event.shiftKey) modifiers.push("shift");
    if (event.metaKey) modifiers.push("win");

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
        <h2>设置</h2>
        <button class="close-btn" on:click={close}>×</button>
      </header>

      <div class="settings-body">
        <!-- Hotkey Settings -->
        <section class="settings-group">
          <h3>热键设置</h3>
          
          <div class="setting-row">
            <span class="setting-label">鼠标 OCR 热键:</span>
            <div class="hotkey-input-group">
              <input 
                type="text" 
                readonly
                value={recordingKey === "mouse" ? "请按下组合键..." : tempMouseHotkey}
                class="hotkey-input"
                class:recording={recordingKey === "mouse"}
              />
              <button 
                class="record-btn"
                class:recording={recordingKey === "mouse"}
                on:click={() => startRecording("mouse")}
                disabled={recordingKey !== null}
              >
                {recordingKey === "mouse" ? "录制中..." : "录制"}
              </button>
            </div>
            <span class="help-text">触发鼠标位置上方的 OCR 识别</span>
          </div>

          <div class="setting-row">
            <span class="setting-label">框选 OCR 热键:</span>
            <div class="hotkey-input-group">
              <input 
                type="text" 
                readonly
                value={recordingKey === "region" ? "请按下组合键..." : tempRegionHotkey}
                class="hotkey-input"
                class:recording={recordingKey === "region"}
              />
              <button 
                class="record-btn"
                class:recording={recordingKey === "region"}
                on:click={() => startRecording("region")}
                disabled={recordingKey !== null}
              >
                {recordingKey === "region" ? "录制中..." : "录制"}
              </button>
            </div>
            <span class="help-text">拖动选择屏幕区域进行 OCR 识别</span>
          </div>
        </section>

        <!-- Other Settings -->
        <section class="settings-group">
          <h3>其他设置</h3>
          
          <div class="setting-row checkbox-row">
            <label class="checkbox-label">
              <input type="checkbox" bind:checked={tempOcrDebug} />
              <span>启用 OCR 调试模式</span>
            </label>
            <span class="help-text">保存 OCR 截图到 debug 目录</span>
          </div>
        </section>
      </div>

      <footer>
        <button class="btn btn-secondary" on:click={close}>取消</button>
        <button class="btn btn-primary" on:click={save}>保存</button>
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
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--bg-secondary);
    border-radius: 12px;
    width: 500px;
    max-width: 90vw;
    max-height: 80vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    border: 1px solid var(--border);
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }

  header h2 {
    margin: 0;
    font-size: 1.2rem;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
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
    padding: 20px;
    overflow-y: auto;
    flex: 1;
  }

  .settings-group {
    margin-bottom: 24px;
  }

  .settings-group:last-child {
    margin-bottom: 0;
  }

  .settings-group h3 {
    font-size: 1rem;
    color: var(--text-primary);
    margin: 0 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  .setting-row {
    margin-bottom: 16px;
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
    padding: 8px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    font-family: monospace;
    font-size: 0.95rem;
  }

  .hotkey-input.recording {
    border-color: var(--accent);
    background: var(--accent-muted);
  }

  .record-btn {
    padding: 8px 16px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .record-btn:hover:not(:disabled) {
    background: var(--bg-elevated);
    border-color: var(--text-tertiary);
  }

  .record-btn.recording {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
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
    width: 18px;
    height: 18px;
    accent-color: var(--accent);
  }

  .checkbox-label span {
    color: var(--text-primary);
  }

  footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 16px 20px;
    border-top: 1px solid var(--border);
  }

  .btn {
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-secondary {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
  }

  .btn-secondary:hover {
    background: var(--bg-elevated);
  }

  .btn-primary {
    background: var(--accent);
    border: 1px solid var(--accent);
    color: white;
  }

  .btn-primary:hover {
    filter: brightness(1.1);
  }
</style>
