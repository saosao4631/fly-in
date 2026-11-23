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
        """何も予約されていない状態で始める。"""
        self._zone_use: dict[tuple[str, int], int] = {}
        self._link_use: dict[tuple[frozenset[str], int], int] = {}

    def zone_count(self, zone: Zone, turn: int) -> int:
        """そのゾーン・そのターンにいる機数。未予約なら 0。"""
        return self._zone_use.get((zone.name, turn), 0)

    def can_enter(self, zone: Zone, turn: int) -> bool:
        """そのターンに、もう1機そのゾーンへ入れるか。"""
        return self.zone_count(zone, turn) < zone.capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """そのゾーン・そのターンの枠を1つ使う。"""
        self._zone_use[(zone.name, turn)] = self.zone_count(zone, turn) + 1

    def link_count(self, link: Connection, turn: int) -> int:
        """その接続・そのターンを渡る機数。未予約なら 0。"""
        return self._link_use.get((link.key, turn), 0)

    def can_use(self, link: Connection, turn: int) -> bool:
        """そのターンに、もう1機その接続を渡れるか。"""
        return self.link_count(link, turn) < link.capacity

    def reserve_link(self, link: Connection, turn: int) -> None:
        """その接続・そのターンの枠を1つ使う。"""
        self._link_use[(link.key, turn)] = self.link_count(link, turn) + 1
