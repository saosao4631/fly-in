from dataclasses import dataclass
from zone import Zone


@dataclass(frozen=True)
class Connection:
    """2つのゾーンを結ぶ双方向の接続。

    同じ1本の接続に、用途の違う2つの表現がある。name は画面に
    出すための文字列、key は同一性を判定するための集合。向きを
    保ったまま、向きを無視した比較ができる。"""

    first: Zone
    second: Zone
    capacity: int = 1

    @property
    def name(self) -> str:
        """出力用の名前。'first-second' の形で返す。"""
        return self.first.name + "-" + self.second.name

    @property
    def key(self) -> frozenset[str]:
        """同一性の判定に使う鍵。"""
        return frozenset({self.first.name, self.second.name})

    def other(self, zone: Zone) -> Zone:
        """渡されたゾーンの反対側の端点を返す。"""
        if zone.name == self.first.name:
            return self.second
        if zone.name == self.second.name:
            return self.first
        raise ValueError(
            f"zone {zone.name!r} is not an endpoint of {self.name!r}"
        )
