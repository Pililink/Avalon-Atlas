from __future__ import annotations

from dataclasses import dataclass

from ..maps.model import Chests, Dungeons, MapMdoel, Resources


@dataclass(slots=True)
class MapRecord:
    name: str
    slug: str
    tier: str
    map_type: str
    chests: Chests
    dungeons: Dungeons
    resources: Resources
    brecilien: int

    @classmethod
    def from_model(cls, model: MapMdoel) -> "MapRecord":
        slug = model.name.strip().lower()
        return cls(
            name=model.name,
            slug=slug,
            tier=model.tier,
            map_type=model.map_type,
            chests=model.chests,
            dungeons=model.dungeons,
            resources=model.resources,
            brecilien=model.brecilien,
        )
