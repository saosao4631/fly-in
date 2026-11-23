from zone import Zone
from connection import Connection


class Network:
    """ゾーンと接続を保持するグラフ。

    台帳2つと隣接表1つの、素の辞書だけで組み立てる。グラフ
    ライブラリは使わない。

    Zone と Connection は不変（frozen）だが、この入れ物は
    パーサが1行ずつ積んでいく間に育つので可変にしてある。
    """

    def __init__(self, nb_drones: int) -> None:
        """空のネットワークを作成"""
        self.nb_drones = nb_drones
        self._zones: dict[str, Zone] = {}
        self._connections: dict[frozenset[str], Connection] = {}
        self._adjacency: dict[str, list[Connection]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        """ゾーンを台帳に登録し、隣接表に空の枠を用意する。"""
        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []
        if zone.is_start:
            self._start = zone
        if zone.is_end:
            self._end = zone

    def add_connection(self, connection: Connection) -> None:
        """接続を台帳に登録し、両端のゾーンの隣接リストに加える。"""
        self._connections[connection.key] = connection
        self._adjacency[connection.first.name].append(connection)
        self._adjacency[connection.second.name].append(connection)

    def has_zone(self, name: str) -> bool:
        """その名前のゾーンが既に登録されているか。"""
        return name in self._zones

    def has_connection(self, a: str, b: str) -> bool:
        """2つのゾーンが既に繋がっているか。順序は問わない。"""
        return frozenset({a, b}) in self._connections

    @property
    def zones(self) -> list[Zone]:
        """登録されている全ゾーン。宣言順。"""
        return list(self._zones.values())

    @property
    def connections(self) -> list[Connection]:
        """登録されている全接続。宣言順。"""
        return list(self._connections.values())

    @property
    def has_start(self) -> bool:
        """始点ハブが登録済みか。"""
        return self._start is not None

    @property
    def has_end(self) -> bool:
        """終点ハブが登録済みか。"""
        return self._end is not None

    def zone(self, name: str) -> Zone:
        """名前からゾーンを取り出す。"""
        return self._zones[name]

    def connection_between(self, first: str, second: str) -> Connection:
        """2つのゾーン名を繋ぐ接続を返す。"""
        return self._connections[frozenset({first, second})]

    def links_of(self, zone: Zone) -> list[Connection]:
        """そのゾーンに繋がっている接続の一覧。"""
        return self._adjacency[zone.name]

    @property
    def start(self) -> Zone:
        """始点ハブ。まだ登録されていなければ例外。"""
        if self._start is None:
            raise ValueError("start_hub zone is not registered")
        return self._start

    @property
    def end(self) -> Zone:
        """終点ハブ。まだ登録されていなければ例外。"""
        if self._end is None:
            raise ValueError("end_hub zone is not registered")
        return self._end
