import sys

from graph import Network
from zone import Zone

RESET = "\033[0m"

# マップに現れる色名を 256 色番号に対応づける。
# ここに無い名前は着色せずそのまま出す（'rainbow' など）。
COLOR_CODES: dict[str, int] = {
    "black": 240,
    "blue": 33,
    "brown": 130,
    "crimson": 160,
    "cyan": 51,
    "darkred": 88,
    "gold": 220,
    "gray": 244,
    "grey": 244,
    "green": 40,
    "lime": 118,
    "magenta": 201,
    "maroon": 52,
    "orange": 208,
    "purple": 93,
    "red": 196,
    "violet": 177,
    "white": 255,
    "yellow": 226,
}

# 機体の識別用に順番に使う色。
DRONE_CODES = [51, 213, 220, 118, 208, 147, 203, 85]


class Renderer:
    """色付きターミナル出力。

    幅を揃えてから色で包む。逆にするとエスケープシーケンスが
    文字数に数えられて、列が崩れる。
    """

    def __init__(self, enabled: bool | None = None) -> None:
        """色を使うかどうか。省略時は端末かどうかで決める。"""
        if enabled is None:
            enabled = sys.stdout.isatty()
        self.enabled = enabled

    def paint(self, text: str, code: int | None) -> str:
        """text を 256 色で包む。無効時や未知の色はそのまま返す。"""
        if not self.enabled or code is None:
            return text
        return f"\033[38;5;{code}m{text}{RESET}"

    def zone_label(self, zone: Zone, width: int = 0) -> str:
        """ゾーン名を幅を揃えてから、その color タグで着色する。"""
        padded = f"{zone.name:<{width}}"
        if zone.color is None:
            return padded
        return self.paint(padded, COLOR_CODES.get(zone.color.lower()))

    def drone_label(self, index: int) -> str:
        """D1 のような機体名を、機体ごとに違う色で返す。"""
        code = DRONE_CODES[(index - 1) % len(DRONE_CODES)]
        return self.paint(f"D{index}", code)

    def move(self, network: Network, index: int, where: str) -> str:
        """1件の動きを D1-zone の形で色付きにする。"""
        if "-" in where and not network.has_zone(where):
            return f"{self.drone_label(index)}-{where}"
        zone = network.zone(where)
        return f"{self.drone_label(index)}-{self.zone_label(zone)}"

    def turn_line(
        self, network: Network, moves: list[str]
    ) -> str:
        """1ターンぶんの動きを1行にまとめる。"""
        painted = []
        for item in moves:
            index_text, where = item.split("-", 1)
            painted.append(
                self.move(network, int(index_text[1:]), where)
            )
        return " ".join(painted)

    def occupancy(
        self, network: Network, plans: list[list[str]], turn: int
    ) -> str:
        """そのターンに各ゾーンへ何機いるかを1行で表す。"""
        counts: dict[str, list[int]] = {}
        for index, plan in enumerate(plans, start=1):
            if turn >= len(plan):
                continue
            counts.setdefault(plan[turn], []).append(index)
        cells = []
        for zone in network.zones:
            here = counts.get(zone.name, [])
            if not here:
                continue
            tags = ",".join(self.drone_label(i) for i in here)
            cells.append(f"{self.zone_label(zone)}[{tags}]")
        return " ".join(cells)
