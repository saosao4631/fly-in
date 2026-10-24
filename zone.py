import sys
from enum import Enum
from dataclasses import dataclass


class ZoneType(Enum):
    """ゾーンの種類。進入コストと進入可否を決める。"""
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
    """ゾーンの情報・状態。"""
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def capacity(self) -> int:
        """同時に滞在できるドローンの最大数。"""
        if self.is_start or self.is_end:
            return sys.maxsize
        return self.max_drones
