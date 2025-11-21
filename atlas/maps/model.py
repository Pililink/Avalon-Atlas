from typing import Literal

from pydantic import BaseModel


class Chests(BaseModel):
    blue: int  # 蓝箱
    green: int  # 绿箱
    highGold: int  # 金王座
    lowGold: int  # 蓝箱


class Dungeons(BaseModel):
    solo: int  # 绿洞
    group: int  # 蓝洞
    avalon: int  # 金洞


class Resources(BaseModel):
    rock: int  # 石点
    wood: int  # 木点
    ore: int  # 矿点
    fiber: int  # 棉点
    hide: int  # 皮点


class MapMdoel(BaseModel):
    name: str
    tier: Literal["T4", "T6", "T8"]  # 地图阶级
    map_type: Literal[
        "TUNNEL_ROYAL",  # 通向外界-皇家大陆(蓝/黄区)
        "TUNNEL_ROYAL_RED",  # 通向外界-皇家大陆(红区)
        "TUNNEL_BLACK_LOW",  # 通向外界-黑区外圈
        "TUNNEL_BLACK_MEDIUM",  # 通向外界-黑区中圈
        "TUNNEL_BLACK_HIGH",  # 通向外界-黑区内圈
        "TUNNEL_DEEP",  # 阿瓦隆通道-深层
        "TUNNEL_LOW",  # 阿瓦隆通道-外层
        "TUNNEL_MEDIUM",  # 阿瓦隆通道-中层
        "TUNNEL_HIGH",  # 阿瓦隆通道-内层
        "TUNNEL_DEEP_RAID",  # 金门
        "TUNNEL_HIDEOUT",  # 地堡-普通
        "TUNNEL_HIDEOUT_DEEP",  # 地堡-深层
    ]
    chests: Chests  # 箱子信息
    dungeons: Dungeons
    resources: Resources  # 资源信息
    brecilien: int  # 兔子洞数
