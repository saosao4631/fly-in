from graph import Network
from pathfinder import PathFinder
from reservation import ReservationTable


class Simulation:
    """全機ぶんの予定を立て、ターンごとの動きに並べ替える。

    衝突の解決は計画の段階で済ませる。ここでは立てた予定を
    再生するだけなので、ターンごとの判定ロジックを持たない。
    """

    def __init__(self, network: Network) -> None:
        """ネットワークと、それを探索する PathFinder を用意する。

        Args:
            network: 走らせる対象のマップ。
        """
        self._network = network
        self._finder = PathFinder(network)
        self._table = ReservationTable()

    @property
    def table(self) -> ReservationTable:
        """計画の結果として積み上がった予約表。

        どのゾーン・どの接続が、どのターンに何機ぶん使われたかが
        入っている。計画後の集計や表示から参照する。
        """
        return self._table

    def plan_all(self) -> list[list[str]]:
        """機体を1機ずつ順に計画し、予約表に積んでいく。

        Raises:
            ValueError: どれか1機でも経路が見つからないとき。
        """
        table = self._table
        plans: list[list[str]] = []
        for index in range(1, self._network.nb_drones + 1):
            plan = self._finder.find(
                self._network.start, self._network.end, table
            )
            if plan is None:
                raise ValueError(f"D{index} の経路が見つかりません")
            self._finder.reserve_plan(plan, table)
            plans.append(plan)
        return plans

    @staticmethod
    def to_turns(plans: list[list[str]]) -> list[list[str]]:
        """予定表をターンごとの動きに並べ替える。

        ターンT の居場所が T-1 と同じ機体は、待機したので
        その行から省く。到着済みの機体も追跡しない。
        """
        longest = max(len(plan) for plan in plans)
        turns: list[list[str]] = []
        for turn in range(1, longest):
            moves: list[str] = []
            for index, plan in enumerate(plans, start=1):
                if turn >= len(plan):
                    continue
                if plan[turn] == plan[turn - 1]:
                    continue
                moves.append(f"D{index}-{plan[turn]}")
            turns.append(moves)
        return turns

    def run(self) -> list[list[str]]:
        """計画してターンごとの動きを返す。"""
        return self.to_turns(self.plan_all())
