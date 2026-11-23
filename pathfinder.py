import heapq

from connection import Connection
from graph import Network
from reservation import ReservationTable
from zone import Zone

# 到達できないマップで無限に探さないための打ち切り。
TURN_LIMIT = 500


class PathFinder:
    """時空間グラフ上のダイクストラで1機ぶんの予定を立てる。
    優先度付きキュー heapq 使用。"""
    def __init__(self, network: Network) -> None:
        """探索対象のネットワークを受け取る。

        Args:
            network: ゾーンと接続を保持するグラフ。
        """
        self._network = network

    def _neighbors(
        self, zone: Zone, turn: int, table: ReservationTable
    ) -> list[tuple[Zone, int]]:
        """いまこの場所から実際に行ける先を列挙する。"""
        results: list[tuple[Zone, int]] = []
        if table.can_enter(zone, turn + 1):
            results.append((zone, turn + 1))
        for link in self._network.links_of(zone):
            neighbour = link.other(zone)
            if not neighbour.zone_type.is_enterable:
                continue
            cost = neighbour.zone_type.entry_cost
            if not table.can_enter(neighbour, turn + cost):
                continue
            if not self._link_free(table, link, turn, cost):
                continue
            results.append((neighbour, turn + cost))
        return results

    @staticmethod
    def _link_free(
        table: ReservationTable, link: Connection, turn: int, cost: int
    ) -> bool:
        """出発ターンから cost 枠ぶん、接続が空いているか。"""
        for step in range(turn, turn + cost):
            if not table.can_use(link, step):
                return False
        return True

    def find(
        self, start: Zone, goal: Zone, table: ReservationTable
    ) -> list[str] | None:
        """start から goal へ、最も早く着く予定表を返す。"""
        queue: list[tuple[int, str]] = [(0, start.name)]
        visited: set[tuple[str, int]] = {(start.name, 0)}
        came_from: dict[tuple[str, int], tuple[str, int]] = {}

        while queue:
            turn, name = heapq.heappop(queue)
            if name == goal.name:
                return self._rebuild(came_from, start, name, turn)
            if turn >= TURN_LIMIT:
                continue
            zone = self._network.zone(name)
            for neighbour, arrival in self._neighbors(zone, turn, table):
                node = (neighbour.name, arrival)
                if node in visited:
                    continue
                visited.add(node)
                came_from[node] = (name, turn)
                heapq.heappush(queue, (arrival, neighbour.name))
        return None

    def reserve_plan(
        self, plan: list[str], table: ReservationTable
    ) -> None:
        """確定した予定表を予約表に書き込む。"""
        for turn, where in enumerate(plan):
            if "-" in where:
                link = self._network.connection_between(
                    *where.split("-")
                )
                table.reserve_link(link, turn - 1)
                table.reserve_link(link, turn)
                continue
            table.reserve_zone(self._network.zone(where), turn)
            if turn == 0 or "-" in plan[turn - 1]:
                continue
            if plan[turn - 1] != where:
                link = self._network.connection_between(
                    plan[turn - 1], where
                )
                table.reserve_link(link, turn - 1)

    def _rebuild(
        self,
        came_from: dict[tuple[str, int], tuple[str, int]],
        start: Zone,
        goal_name: str,
        arrival: int,
    ) -> list[str]:
        """ゴールから逆に辿って、ターンごとの居場所を並べる。"""
        plan = [""] * (arrival + 1)
        node = (goal_name, arrival)
        while True:
            name, turn = node
            plan[turn] = name
            if node == (start.name, 0):
                return plan
            previous_name, previous_turn = came_from[node]
            if turn - previous_turn == 2:
                link = self._network.connection_between(
                    previous_name, name
                )
                plan[previous_turn + 1] = link.name
            node = (previous_name, previous_turn)
