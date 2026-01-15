<script lang="ts">
  import type { SearchResult, MapRecord } from "../lib/types";

  export let result: SearchResult;
  export let selected: boolean = false;

  type ResourceKey = keyof MapRecord['resources'];
  
  const resourceTypes: { key: ResourceKey; icon: string; label: string }[] = [
    { key: 'wood', icon: '/static/assets/wood.webp', label: '木材' },
    { key: 'rock', icon: '/static/assets/rock.webp', label: '石材' },
    { key: 'ore', icon: '/static/assets/ore.webp', label: '矿石' },
    { key: 'hide', icon: '/static/assets/hide.webp', label: '皮革' },
    { key: 'fiber', icon: '/static/assets/fiber.webp', label: '纤维' },
  ];

  const TYPE_MAP: Record<string, string> = {
      'TUNNEL_ROYAL': '通向外界-皇家大陆(蓝/黄区)',
      'TUNNEL_ROYAL_RED': '通向外界-皇家大陆(红区)',
      'TUNNEL_BLACK_LOW': '通向外界-黑区外圈',
      'TUNNEL_BLACK_MEDIUM': '通向外界-黑区中圈',
      'TUNNEL_BLACK_HIGH': '通向外界-黑区内圈',
      'TUNNEL_DEEP': '阿瓦隆通道-深层',
      'TUNNEL_LOW': '阿瓦隆通道-外层',
      'TUNNEL_MEDIUM': '阿瓦隆通道-中层',
      'TUNNEL_HIGH': '阿瓦隆通道-内层',
      'TUNNEL_DEEP_RAID': '金门',
      'TUNNEL_HIDEOUT': '地堡-普通',
      'TUNNEL_HIDEOUT_DEEP': '地堡-深层',
  };

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
      return TYPE_MAP[type] || type;
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
          <span class="brec-icon" title="Brecilien Access">🍄</span>
       {/if}
    </div>
  </div>

  <!-- Row 2: All Resources & Stats -->
  <div class="stats">
    <!-- Chests -->
    {#if result.record.chests.green > 0}
      <div class="stat-item" title="绿宝箱">
         <img src="/static/assets/green-chest.webp" alt="Green" />
         <span class="count">{result.record.chests.green}</span>
      </div>
    {/if}
    {#if result.record.chests.blue > 0}
      <div class="stat-item" title="蓝宝箱">
         <img src="/static/assets/blue-chest.webp" alt="Blue" />
         <span class="count">{result.record.chests.blue}</span>
      </div>
    {/if}
    {#if result.record.chests.highGold > 0 || result.record.chests.lowGold > 0}
      <div class="stat-item" title="金宝箱">
         <img src="/static/assets/gold-chest.webp" alt="Gold" />
         <span class="count">{result.record.chests.highGold + result.record.chests.lowGold}</span>
      </div>
    {/if}
    
    <!-- Dungeons -->
    {#if result.record.dungeons.solo > 0}
      <div class="stat-item" title="单人地牢">
         <img src="/static/assets/dg-solo.webp" alt="Solo" />
         <span class="count">{result.record.dungeons.solo}</span>
      </div>
    {/if}
    {#if result.record.dungeons.group > 0}
      <div class="stat-item" title="组队地牢">
         <img src="/static/assets/dg-group.webp" alt="Group" />
         <span class="count">{result.record.dungeons.group}</span>
      </div>
    {/if}
    {#if result.record.dungeons.avalon > 0}
      <div class="stat-item" title="阿瓦隆地牢">
         <img src="/static/assets/dg-ava.webp" alt="Avalon" />
         <span class="count">{result.record.dungeons.avalon}</span>
      </div>
    {/if}

    <!-- Resources -->
    {#each resourceTypes as res}
      {#if result.record.resources[res.key] > 0}
        <div class="stat-item" title={res.label}>
          <img src={res.icon} alt={res.label} />
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
    gap: 8px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
  }

  .map-item:hover {
    background: var(--bg-tertiary);
    border-color: var(--text-tertiary);
    transform: translateY(-1px);
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
    gap: 8px;
    flex-wrap: wrap;
    flex: 1;
  }

  .tier-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 18px;
    padding: 0 5px;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #000;
    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    flex-shrink: 0;
  }

  .map-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    flex-shrink: 1;
    min-width: 0;
  }
  
  .map-type {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    font-weight: 500;
    flex-shrink: 0;
  }
  
  .brec-icon {
    font-size: 1rem;
    filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.3));
    flex-shrink: 0;
    margin-left: auto;
  }

  /* Stats - Second Row */
  .stats {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }

  .stat-item {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 5px;
    border-radius: 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border-muted);
    transition: all 0.15s;
  }
  
  .stat-item:hover {
    border-color: var(--border);
    transform: translateY(-1px);
  }

  .stat-item img {
    width: 14px;
    height: 14px;
    object-fit: contain;
    display: block;
  }
  
  .stat-item .count {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary);
    min-width: 10px;
    text-align: center;
  }

  /* Highlight Style */
  :global(.highlight) {
    color: var(--accent);
    font-weight: 700;
    text-shadow: 0 0 8px rgba(88, 166, 255, 0.4);
  }
</style>
