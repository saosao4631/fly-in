import heapq

from connection import Connection
from graph import Network
from reservation import ReservationTable
from zone import Zone

# 到達できないマップで無限に探さないための打ち切り。
TURN_LIMIT = 500


class PathFinder:
    """時空間グラフ上のダイクストラで1機ぶんの予定を立てる。

    探索するノードはゾーンではなく (ゾーン, ターン) の組。出る辺は
    「待機」と「隣へ移動」の2種類だけで、待機が辺になることで
    「動けないときは待つ」が特別扱い無しに表現できる。

    ターンがノードの識別子に含まれるため、あるノードに至る経路は
    どれもコストが等しい。したがって最初に見つけた時点で確定でき、
    教科書のダイクストラにあるコスト更新が要らない。

    優先度付きキューには heapq を使う。ヒープはデータ構造であって
    グラフ処理ライブラリではないので、課題の禁止には当たらない。
    """

    def __init__(self, network: Network) -> None:
        """探索対象のネットワークを受け取る。

        Args:
            network: ゾーンと接続を保持するグラフ。
        """
        self._network = network

    def _neighbors(
        self, zone: Zone, turn: int, table: ReservationTable
    ) -> list[tuple[Zone, int]]:
        """いまこの場所から実際に行ける先を列挙する。

        候補は「その場で待つ」と「隣へ移動する」の2種類。blocked
        ゾーンと、予約表に照らして入れない先は除く。

        Args:
            zone: いまいるゾーン。
            turn: いまのターン。
            table: 先行機がすでに確保している枠。

        Returns:
            (行き先ゾーン, 到着ターン) の組の一覧。
        """
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
        """出発ターンから cost 枠ぶん、接続が空いているか。

        接続は出発ターン基準で予約するので、見るのは
        turn から turn + cost - 1 まで。restricted への移動なら
        2枠を続けて確認することになる。

        Args:
            table: 予約表。
            link: 渡ろうとしている接続。
            turn: 出発するターン。
            cost: 移動にかかるターン数。

        Returns:
            全ての枠に空きがあれば True。
        """
        for step in range(turn, turn + cost):
            if not table.can_use(link, step):
                return False
        return True

    def find(
        self, start: Zone, goal: Zone, table: ReservationTable
    ) -> list[str] | None:
        """start から goal へ、最も早く着く予定表を返す。

        キューから取り出せた最初のゴールが最短になる。より早い
        経路があればそちらが先に取り出されているため。

        Args:
            start: 出発ゾーン。
            goal: 目的ゾーン。
            table: 先行機がすでに確保している枠。

        Returns:
            添字をターン番号とする居場所の並び。TURN_LIMIT まで
            探して届かなければ None。
        """
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
        """確定した予定表を予約表に書き込む。

        ゾーン名にダッシュは使えないとパーサが保証しているので、
        '-' を含む要素は接続名、それ以外はゾーン名と判別できる。

        接続は出発ターン基準で予約する。要素が接続名なら飛行中
        なので turn-1 と turn の2枠、ゾーン名が前のターンと違う
        なら通常の移動なので turn-1 の1枠を確保する。

        Args:
            plan: find が返した予定表。
            table: 書き込み先の予約表。
        """
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
        """ゴールから逆に辿って、ターンごとの居場所を並べる。

        restricted への移動はターンが2つ飛ぶので、間の1ターンが
        空のまま残る。そこは機体が接続の上を飛んでいる最中なので、
        接続の表示名で埋める。

        Args:
            came_from: ノードから直前のノードへの対応。
            start: 出発ゾーン。
            goal_name: 到達したゴールの名前。
            arrival: ゴールに着いたターン。

        Returns:
            添字をターン番号とする居場所の並び。
        """
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
