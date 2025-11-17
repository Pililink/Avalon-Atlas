from pydantic import BaseModel
from typing import Literal


class Chests(BaseModel):
    blue: int # 蓝箱
    green: int # 绿箱子
    highGold: int # 金王座
    lowGold: int # 金箱子


class Dungeons(BaseModel):
    solo: int # 单人洞
    group: int # 蓝洞
    avalon: int # 金洞


class Resources(BaseModel):
    rock: int # 石头
    wood: int # 木头 
    ore: int # 矿石
    fiber: int # 棉花
    hide: int # 兽皮


class MapMdoel(BaseModel):
    name: str
    tier: Literal['T4', 'T6', 'T8'] # 地图阶级
    map_type: Literal[
        'TUNNEL_ROYAL', # 通向
        'TUNNEL_ROYAL_RED',
        'TUNNEL_BLACK_LOW',
        'TUNNEL_BLACK_MEDIUM',
        'TUNNEL_BLACK_HIGH',
        'TUNNEL_DEEP',
        'TUNNEL_LOW',
        'TUNNEL_MEDIUM',
        'TUNNEL_HIGH',
        'TUNNEL_DEEP_RAID',
        'TUNNEL_HIDEOUT',
        'TUNNEL_HIDEOUT_DEEP'
    ]
    chests: Chests
    dungeons: Dungeons
    resources: Resources
    brecilien: int # 显示传送门数量



