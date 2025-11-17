from .model import MapMdoel
import json
from pathlib import Path
from typing import List, Optional


def load_map_data() -> List[MapMdoel]:
    """
    加载并验证地图数据
    
    Returns:
        List[MapMdoel]: 验证后的地图数据列表
        
    Raises:
        FileNotFoundError: 如果 maps.json 文件不存在
        json.JSONDecodeError: 如果 JSON 格式错误
        ValidationError: 如果数据验证失败
    """
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    json_file = current_dir / "maps.json"
    
    if not json_file.exists():
        raise FileNotFoundError(f"地图数据文件不存在: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    map_data = json.loads(content)
    
    # 处理字段名映射：JSON中是 "type"，模型中是 "map_type"
    validated_maps = []
    for item in map_data:
        # 将 "type" 字段重命名为 "map_type"
        if "type" in item:
            item["map_type"] = item.pop("type")
        
        # 使用 Pydantic 验证数据
        try:
            map_model = MapMdoel(**item)
            validated_maps.append(map_model)
        except Exception as e:
            # 记录验证失败的地图，但继续处理其他地图
            print(f"警告: 地图数据验证失败 - {item.get('name', 'Unknown')}: {e}")
            continue
    
    return validated_maps


def get_map_by_name(name: str, maps: Optional[List[MapMdoel]] = None) -> Optional[MapMdoel]:
    """
    根据名称查找地图
    
    Args:
        name: 地图名称
        maps: 地图列表，如果为 None 则自动加载
        
    Returns:
        MapMdoel: 找到的地图对象，如果未找到则返回 None
    """
    if maps is None:
        maps = load_map_data()
    
    for map_item in maps:
        if map_item.name == name:
            return map_item
    
    return None


def filter_maps_by_tier(tier: str, maps: Optional[List[MapMdoel]] = None) -> List[MapMdoel]:
    """
    根据等级筛选地图
    
    Args:
        tier: 地图等级 ('T4', 'T6', 'T8')
        maps: 地图列表，如果为 None 则自动加载
        
    Returns:
        List[MapMdoel]: 筛选后的地图列表
    """
    if maps is None:
        maps = load_map_data()
    
    return [m for m in maps if m.tier == tier]


def filter_maps_by_type(map_type: str, maps: Optional[List[MapMdoel]] = None) -> List[MapMdoel]:
    """
    根据类型筛选地图
    
    Args:
        map_type: 地图类型（如 'TUNNEL_ROYAL', 'TUNNEL_BLACK_LOW' 等）
        maps: 地图列表，如果为 None 则自动加载
        
    Returns:
        List[MapMdoel]: 筛选后的地图列表
    """
    if maps is None:
        maps = load_map_data()
    
    return [m for m in maps if m.map_type == map_type]


def get_all_maps() -> List[MapMdoel]:
    """
    获取所有地图数据（便捷函数）
    
    Returns:
        List[MapMdoel]: 所有地图数据列表
    """
    return load_map_data()

