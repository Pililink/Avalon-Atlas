<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let active = false;

  const dispatch = createEventDispatcher<{
    complete: { x: number; y: number; width: number; height: number };
    cancel: void;
  }>();

  let startX = 0;
  let startY = 0;
  let currentX = 0;
  let currentY = 0;
  let isSelecting = false;

  $: selectionRect = {
    x: Math.min(startX, currentX),
    y: Math.min(startY, currentY),
    width: Math.abs(currentX - startX),
    height: Math.abs(currentY - startY),
  };

  function handleMouseDown(e: MouseEvent) {
    if (!active) return;
    
    isSelecting = true;
    startX = e.clientX;
    startY = e.clientY;
    currentX = e.clientX;
    currentY = e.clientY;
  }

  function handleMouseMove(e: MouseEvent) {
    if (!active || !isSelecting) return;
    
    currentX = e.clientX;
    currentY = e.clientY;
  }

  function handleMouseUp(e: MouseEvent) {
    if (!active || !isSelecting) return;
    
    isSelecting = false;
    
    if (selectionRect.width > 10 && selectionRect.height > 10) {
      dispatch('complete', selectionRect);
      active = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!active) return;
    
    if (e.key === 'Escape') {
      isSelecting = false;
      dispatch('cancel');
      active = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if active}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div 
    class="region-selector-overlay"
    on:mousedown={handleMouseDown}
    on:mousemove={handleMouseMove}
    on:mouseup={handleMouseUp}
  >
    {#if isSelecting}
      <div 
        class="selection-rect"
        style="
          left: {selectionRect.x}px;
          top: {selectionRect.y}px;
          width: {selectionRect.width}px;
          height: {selectionRect.height}px;
        "
      >
        <div class="size-label">
          {selectionRect.width} × {selectionRect.height}
        </div>
      </div>
    {/if}
    
    <div class="hint">
      拖动鼠标选择区域 · ESC 取消
    </div>
  </div>
{/if}

<style>
  .region-selector-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.5);
    cursor: crosshair;
    z-index: 9999;
  }

  .selection-rect {
    position: absolute;
    border: 2px solid var(--accent, #58a6ff);
    background: rgba(88, 166, 255, 0.1);
    pointer-events: none;
  }

  .size-label {
    position: absolute;
    bottom: -25px;
    right: 0;
    background: var(--accent, #58a6ff);
    color: #000;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .hint {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    pointer-events: none;
  }
</style>
