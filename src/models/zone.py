from enum import Enum
from dataclasses import dataclass

class ZoneType(Enum):
    NORMAL = "normal"
    PRIORITY = "priority"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"

    @property
    def entry_cost(self) -> int:
        """このゾーンに進入するのに必要なターン数。"""
        return 2 if self is ZoneType.RESTRICTED else 1

    @property
    def is_enterable(self) -> bool:
        """ドローンが進入できるか。"""
        return self is not ZoneType.BLOCKED

    @property
    def is_preferred(self) -> bool:
        """経路探索で優先されるべきか。"""
        return self is ZoneType.PRIORITY

@dataclass(frozen=True)
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1