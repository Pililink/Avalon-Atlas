import { derived, writable } from "svelte/store";

export const locales = ["zh-CN", "en-US"] as const;
export type Locale = (typeof locales)[number];

type Dictionary = Record<string, string>;

const dictionaries: Record<Locale, Dictionary> = {
  "zh-CN": {
    "app.subtitle": "Road scout panel",
    "app.settings": "设置",
    "app.alwaysOnTop": "窗口置顶",
    "app.emptyTitle": "等待地图情报",
    "app.emptyHint": "搜索或使用 OCR 添加通道",
    "app.selected": "已选",
    "app.mouseOcr": "鼠标 OCR",
    "app.regionOcr": "框选 OCR",
    "app.pinned": "置顶",
    "app.mapPreviewAlt": "地图预览",
    "app.remove": "移除",
    "app.clear": "清空",
    "app.clearSelection": "清空已选地图",
    "app.copyMap": "双击复制地图信息",
    "app.copied": "已复制",
    "app.copyFailed": "复制失败",

    "copy.name": "地图",
    "copy.tier": "等级",
    "copy.type": "类型",
    "copy.chests": "宝箱",
    "copy.dungeons": "地牢",
    "copy.resources": "资源",
    "copy.brecilien": "布雷希林",
    "copy.yes": "有",

    "search.placeholder": "搜索地图名 / OCR 结果",
    "search.recognizing": "正在识别...",
    "search.noMatches": "无匹配结果",
    "search.failed": "识别失败: {error}",
    "search.matches": "匹配结果",

    "settings.title": "设置",
    "settings.hotkeys": "热键设置",
    "settings.mouseHotkey": "鼠标 OCR 热键:",
    "settings.mouseHotkeyHelp": "触发鼠标位置上方的 OCR 识别",
    "settings.regionHotkey": "框选 OCR 热键:",
    "settings.regionHotkeyHelp": "拖动选择屏幕区域进行 OCR 识别",
    "settings.other": "其他设置",
    "settings.language": "语言:",
    "settings.debugOcr": "启用 OCR 调试模式",
    "settings.debugOcrHelp": "保存 OCR 截图到 debug 目录",
    "settings.pressCombo": "请按下组合键...",
    "settings.recording": "录制中...",
    "settings.record": "录制",
    "settings.cancel": "取消",
    "settings.save": "保存",
    "settings.errorMouseHotkeyRequired": "鼠标 OCR 热键不能为空",
    "settings.errorRegionHotkeyRequired": "框选 OCR 热键不能为空",
    "settings.errorHotkeyConflict": "两个热键不能相同",

    "locale.zh-CN": "中文",
    "locale.en-US": "English",

    "region.hint": "拖动鼠标选择区域 · ESC 取消",

    "resource.wood": "木材",
    "resource.rock": "石材",
    "resource.ore": "矿石",
    "resource.hide": "皮革",
    "resource.fiber": "纤维",
    "chest.green": "绿宝箱",
    "chest.blue": "蓝宝箱",
    "chest.gold": "金宝箱",
    "dungeon.solo": "单人地牢",
    "dungeon.group": "组队地牢",
    "dungeon.avalon": "阿瓦隆地牢",
    "map.brecilien": "布雷希林入口",

    "mapType.TUNNEL_ROYAL": "通向外界-皇家大陆(蓝/黄区)",
    "mapType.TUNNEL_ROYAL_RED": "通向外界-皇家大陆(红区)",
    "mapType.TUNNEL_BLACK_LOW": "通向外界-黑区外圈",
    "mapType.TUNNEL_BLACK_MEDIUM": "通向外界-黑区中圈",
    "mapType.TUNNEL_BLACK_HIGH": "通向外界-黑区内圈",
    "mapType.TUNNEL_DEEP": "阿瓦隆通道-深层",
    "mapType.TUNNEL_LOW": "阿瓦隆通道-外层",
    "mapType.TUNNEL_MEDIUM": "阿瓦隆通道-中层",
    "mapType.TUNNEL_HIGH": "阿瓦隆通道-内层",
    "mapType.TUNNEL_DEEP_RAID": "金门",
    "mapType.TUNNEL_HIDEOUT": "地堡-普通",
    "mapType.TUNNEL_HIDEOUT_DEEP": "地堡-深层",
  },
  "en-US": {
    "app.subtitle": "Road scout panel",
    "app.settings": "Settings",
    "app.alwaysOnTop": "Always on top",
    "app.emptyTitle": "Waiting for map intel",
    "app.emptyHint": "Search or use OCR to add a road",
    "app.selected": "Selected",
    "app.mouseOcr": "Mouse OCR",
    "app.regionOcr": "Region OCR",
    "app.pinned": "Pinned",
    "app.mapPreviewAlt": "Map preview",
    "app.remove": "Remove",
    "app.clear": "Clear",
    "app.clearSelection": "Clear selected maps",
    "app.copyMap": "Double-click to copy map info",
    "app.copied": "Copied",
    "app.copyFailed": "Copy failed",

    "copy.name": "Map",
    "copy.tier": "Tier",
    "copy.type": "Type",
    "copy.chests": "Chests",
    "copy.dungeons": "Dungeons",
    "copy.resources": "Resources",
    "copy.brecilien": "Brecilien",
    "copy.yes": "Yes",

    "search.placeholder": "Search map name / OCR text",
    "search.recognizing": "Recognizing...",
    "search.noMatches": "No matches",
    "search.failed": "Recognition failed: {error}",
    "search.matches": "Matches",

    "settings.title": "Settings",
    "settings.hotkeys": "Hotkeys",
    "settings.mouseHotkey": "Mouse OCR:",
    "settings.mouseHotkeyHelp": "Runs OCR above the current mouse position",
    "settings.regionHotkey": "Region OCR:",
    "settings.regionHotkeyHelp": "Drag a screen region and run OCR on it",
    "settings.other": "Other",
    "settings.language": "Language:",
    "settings.debugOcr": "Enable OCR debug mode",
    "settings.debugOcrHelp": "Save OCR captures to the debug directory",
    "settings.pressCombo": "Press a key combo...",
    "settings.recording": "Recording...",
    "settings.record": "Record",
    "settings.cancel": "Cancel",
    "settings.save": "Save",
    "settings.errorMouseHotkeyRequired": "Mouse OCR hotkey is required",
    "settings.errorRegionHotkeyRequired": "Region OCR hotkey is required",
    "settings.errorHotkeyConflict": "Hotkeys must be different",

    "locale.zh-CN": "中文",
    "locale.en-US": "English",

    "region.hint": "Drag to select an area · ESC to cancel",

    "resource.wood": "Wood",
    "resource.rock": "Stone",
    "resource.ore": "Ore",
    "resource.hide": "Hide",
    "resource.fiber": "Fiber",
    "chest.green": "Green chest",
    "chest.blue": "Blue chest",
    "chest.gold": "Gold chest",
    "dungeon.solo": "Solo dungeon",
    "dungeon.group": "Group dungeon",
    "dungeon.avalon": "Avalonian dungeon",
    "map.brecilien": "Brecilien access",

    "mapType.TUNNEL_ROYAL": "Royal continent tunnel (Blue/Yellow)",
    "mapType.TUNNEL_ROYAL_RED": "Royal continent tunnel (Red)",
    "mapType.TUNNEL_BLACK_LOW": "Outlands tunnel - outer ring",
    "mapType.TUNNEL_BLACK_MEDIUM": "Outlands tunnel - middle ring",
    "mapType.TUNNEL_BLACK_HIGH": "Outlands tunnel - inner ring",
    "mapType.TUNNEL_DEEP": "Avalonian road - deep",
    "mapType.TUNNEL_LOW": "Avalonian road - outer",
    "mapType.TUNNEL_MEDIUM": "Avalonian road - middle",
    "mapType.TUNNEL_HIGH": "Avalonian road - inner",
    "mapType.TUNNEL_DEEP_RAID": "Golden portal",
    "mapType.TUNNEL_HIDEOUT": "Hideout - normal",
    "mapType.TUNNEL_HIDEOUT_DEEP": "Hideout - deep",
  },
};

export const locale = writable<Locale>("zh-CN");

export function normalizeLocale(value: string | undefined | null): Locale {
  return locales.includes(value as Locale) ? (value as Locale) : "zh-CN";
}

export function setLocale(value: string | undefined | null) {
  locale.set(normalizeLocale(value));
}

function format(template: string, values?: Record<string, string | number>): string {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? `{${key}}`));
}

export const t = derived(locale, ($locale) => {
  const dictionary = dictionaries[$locale];
  const fallback = dictionaries["zh-CN"];

  return (key: string, values?: Record<string, string | number>) =>
    format(dictionary[key] ?? fallback[key] ?? key, values);
});
