from dataclasses import dataclass
from zone import Zone


@dataclass(frozen=True)
class Connection:
    first: Zone
    second: Zone
    capacity: int = 1

    @property
    def name(self) -> str:
        """出力用の名前。first の名前 + - + second の名前を返す"""
        return self.first.name + "-" + self.second.name

    @property
    def key(self) -> frozenset[str]:
        """a-b と b-a を同じ道だと判定するための判定用値、forzensetだと前後の順番を分けずに同一とみなす"""
        return frozenset({self.first.name, self.second.name})

    def other(self, zone: Zone) -> Zone:
        if zone.name == self.first.name:
            return self.second
        elif zone.name == self.second.name:
            return self.first
        else:
            raise ValueError("Error-Conneccion.other")
