<script lang="ts">
  import type { SearchResult, MapRecord } from "../../lib/maps/types";
  import { t } from "../../lib/i18n";

  export let result: SearchResult;
  export let selected: boolean = false;

  type ResourceKey = keyof MapRecord['resources'];
  
  const resourceTypes: { key: ResourceKey; icon: string; labelKey: string }[] = [
    { key: 'wood', icon: '/static/assets/wood.webp', labelKey: 'resource.wood' },
    { key: 'rock', icon: '/static/assets/rock.webp', labelKey: 'resource.rock' },
    { key: 'ore', icon: '/static/assets/ore.webp', labelKey: 'resource.ore' },
    { key: 'hide', icon: '/static/assets/hide.webp', labelKey: 'resource.hide' },
    { key: 'fiber', icon: '/static/assets/fiber.webp', labelKey: 'resource.fiber' },
  ];

  function getHighlightedName(name: string, positions?: number[]): string {
    if (!positions || positions.length === 0) return name;
    
    let html = "";
    let lastIdx = 0;
    for (const pos of positions) {
      if (pos >= name.length) break; 
      html += name.substring(lastIdx, pos);
      html += `<span class="highlight">${name[pos]}</span>`;
      lastIdx = pos + 1;
    }
    html += name.substring(lastIdx);
    return html;
  }
  
  function getTypeName(type: string): string {
      const translated = $t(`mapType.${type}`);
      return translated === `mapType.${type}` ? type : translated;
  }
  
  function getTierColor(tier: string): string {
      const t = tier.toLowerCase();
      if (t === 't4') return 'var(--tier-t4)';
      if (t === 't5') return 'var(--tier-t5)';
      if (t === 't6') return 'var(--tier-t6)';
      if (t === 't7') return 'var(--tier-t7)';
      if (t === 't8') return 'var(--tier-t8)';
      return '#888';
  }
</script>

<div class="map-item {selected ? 'selected' : ''}">
  <!-- Row 1: Tier + Name + Type -->
  <div class="header">
    <div class="title-row">
       <span class="tier-badge" style="background: {getTierColor(result.record.tier)};">{result.record.tier}</span>
       <span class="map-name">{@html getHighlightedName(result.record.name, result.positions)}</span>
       <span class="map-type">{getTypeName(result.record.map_type)}</span>
       {#if result.record.brecilien > 0}
          <span class="brec-icon" title={$t("map.brecilien")}>BR</span>
       {/if}
    </div>
  </div>

  <!-- Row 2: All Resources & Stats -->
  <div class="stats">
    <!-- Chests -->
    {#if result.record.chests.green > 0}
      <div class="stat-item" title={$t("chest.green")}>
         <img src="/static/assets/green-chest.webp" alt="Green" />
         <span class="count">{result.record.chests.green}</span>
      </div>
    {/if}
    {#if result.record.chests.blue > 0}
      <div class="stat-item" title={$t("chest.blue")}>
         <img src="/static/assets/blue-chest.webp" alt="Blue" />
         <span class="count">{result.record.chests.blue}</span>
      </div>
    {/if}
    {#if result.record.chests.highGold > 0 || result.record.chests.lowGold > 0}
      <div class="stat-item" title={$t("chest.gold")}>
         <img src="/static/assets/gold-chest.webp" alt="Gold" />
         <span class="count">{result.record.chests.highGold + result.record.chests.lowGold}</span>
      </div>
    {/if}
    
    <!-- Dungeons -->
    {#if result.record.dungeons.solo > 0}
      <div class="stat-item" title={$t("dungeon.solo")}>
         <img src="/static/assets/dg-solo.webp" alt="Solo" />
         <span class="count">{result.record.dungeons.solo}</span>
      </div>
    {/if}
    {#if result.record.dungeons.group > 0}
      <div class="stat-item" title={$t("dungeon.group")}>
         <img src="/static/assets/dg-group.webp" alt="Group" />
         <span class="count">{result.record.dungeons.group}</span>
      </div>
    {/if}
    {#if result.record.dungeons.avalon > 0}
      <div class="stat-item" title={$t("dungeon.avalon")}>
         <img src="/static/assets/dg-ava.webp" alt="Avalon" />
         <span class="count">{result.record.dungeons.avalon}</span>
      </div>
    {/if}

    <!-- Resources -->
    {#each resourceTypes as res}
      {#if result.record.resources[res.key] > 0}
        <div class="stat-item" title={$t(res.labelKey)}>
          <img src={res.icon} alt={$t(res.labelKey)} />
          <span class="count">{result.record.resources[res.key]}</span>
        </div>
      {/if}
    {/each}
  </div>
</div>

<style>
  .map-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 58px;
    padding: 8px 9px;
    border-radius: 4px;
    cursor: pointer;
    background:
      linear-gradient(90deg, rgba(201, 154, 69, 0.12), transparent 34%),
      linear-gradient(180deg, var(--bg-secondary), var(--bg-panel));
    border: 1px solid var(--border);
    border-left-color: var(--accent-deep);
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    box-shadow: var(--panel-edge);
  }

  .map-item:hover {
    background:
      linear-gradient(90deg, rgba(201, 154, 69, 0.18), transparent 38%),
      var(--bg-tertiary);
    border-color: var(--border-bright);
    box-shadow: var(--shadow-md);
  }

  .map-item.selected {
    background: var(--accent-muted);
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
  }

  /* Header - First Row */
  .header {
    display: flex;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: nowrap;
    flex: 1;
    min-width: 0;
  }

  .tier-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 20px;
    padding: 0 5px;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #000;
    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    flex-shrink: 0;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 1px 3px rgba(0, 0, 0, 0.38);
  }

  .map-name {
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--text-primary);
    flex-shrink: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .map-type {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    font-weight: 500;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .brec-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 23px;
    height: 18px;
    border-radius: 3px;
    border: 1px solid rgba(126, 86, 36, 0.9);
    background: rgba(201, 154, 69, 0.18);
    color: var(--accent-hover);
    font-size: 0.62rem;
    font-weight: 900;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* Stats - Second Row */
  .stats {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    align-items: center;
  }

  .stat-item {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    min-width: 28px;
    height: 20px;
    padding: 1px 4px;
    border-radius: 3px;
    background: var(--bg-inset);
    border: 1px solid var(--border-muted);
    transition: all 0.15s;
  }
  
  .stat-item:hover {
    border-color: var(--border);
    transform: translateY(-1px);
  }

  .stat-item img {
    width: 15px;
    height: 15px;
    object-fit: contain;
    display: block;
  }
  
  .stat-item .count {
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--text-secondary);
    min-width: 10px;
    text-align: center;
  }

  /* Highlight Style */
  :global(.highlight) {
    color: var(--accent);
    font-weight: 700;
    text-shadow: 0 0 8px rgba(201, 154, 69, 0.45);
  }
</style>
