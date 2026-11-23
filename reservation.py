from zone import Zone
from connection import Connection


class ReservationTable:
    """時空間の占有を数える表。

    予約のターン番号は次の約束に従う。

    - ゾーン: そのドローンが「そこにいる」ターン。
    - 接続: 出発したターン。コスト c の移動は T から T+c-1 まで
      c 枠を占有し、到着は T+c。
    """

    def __init__(self) -> None:
        self._zone_use: dict[tuple[str, int], int] = {}
        self._link_use: dict[tuple[frozenset[str], int], int] = {}

    def zone_count(self, zone: Zone, turn: int) -> int:
        return self._zone_use.get((zone.name, turn), 0)

    def can_enter(self, zone: Zone, turn: int) -> bool:
        return self.zone_count(zone, turn) < zone.capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        self._zone_use[(zone.name, turn)] = self.zone_count(zone, turn) + 1

    def link_count(self, link: Connection, turn: int) -> int:
        return self._link_use.get((link.key, turn), 0)

    def can_use(self, link: Connection, turn: int) -> bool:
        return self.link_count(link, turn) < link.capacity

    def reserve_link(self, link: Connection, turn: int) -> None:
        self._link_use[(link.key, turn)] = self.link_count(link, turn) + 1
