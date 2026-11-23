import argparse
import sys
from typing import NoReturn

from graph import Network
from map_parser import MapParser
from renderer import Renderer
from simulation import Simulation
from zone import Zone


def role_mark(zone: Zone) -> str:
    """始点なら S、終点なら E、それ以外は空白を返す。"""
    if zone.is_start:
        return "S"
    if zone.is_end:
        return "E"
    return " "


def capacity_text(zone: Zone) -> str:
    """定員を文字列にする。始点と終点は無制限なので inf。"""
    if zone.is_start or zone.is_end:
        return "inf"
    return str(zone.capacity)


def print_summary(network: Network, screen: Renderer) -> None:
    """マップ全体の数をまとめて表示する。"""
    print(f"drones      : {network.nb_drones}")
    print(f"zones       : {len(network.zones)}")
    print(f"connections : {len(network.connections)}")
    print(f"start       : {screen.zone_label(network.start)}")
    print(f"end         : {screen.zone_label(network.end)}")


def print_zones(network: Network, screen: Renderer) -> None:
    """ゾーンを1行ずつ表示する。"""
    print("zones:")
    for zone in network.zones:
        cells = [
            role_mark(zone),
            screen.zone_label(zone, 20),
            f"({zone.x:>3},{zone.y:>3})",
            f"{zone.zone_type.value:<10}",
            f"cost={zone.zone_type.entry_cost}",
            f"cap={capacity_text(zone):<4}",
            f"color={zone.color}",
        ]
        print("  " + " ".join(cells))


def print_connections(network: Network) -> None:
    """接続を1行ずつ表示する。"""
    print("connections:")
    for link in network.connections:
        print(f"  {link.name:<34} capacity={link.capacity}")


def print_turns(
    network: Network, turns: list[list[str]], screen: Renderer
) -> None:
    """ターンごとの動きを課題の形式で表示する。"""
    for moves in turns:
        print(screen.turn_line(network, moves))


def print_states(
    network: Network, plans: list[list[str]], screen: Renderer
) -> None:
    """ターンごとに、どのゾーンに誰がいるかを表示する。"""
    print("states:")
    longest = max(len(plan) for plan in plans)
    for turn in range(longest):
        line = screen.occupancy(network, plans, turn)
        print(f"  T{turn:<3} {line}")


class Cli(argparse.ArgumentParser):
    """引数の誤りも、他の失敗と同じ終了コード 1 で終える。

    argparse の既定は 2 だが、このプログラムの失敗は
    すべて 1 に揃える。
    """

    def error(self, message: str) -> NoReturn:
        """使い方を表示して終了コード 1 で終わる。"""
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        sys.exit(1)


def build_cli() -> argparse.ArgumentParser:
    """コマンドライン引数の定義を組み立てる。"""
    parser = Cli(prog="main.py", add_help=False)
    parser.add_argument("map_file", help="path to the map file")
    return parser


def main() -> int:
    """引数で指定されたマップを読み込んで走らせる。"""
    args = build_cli().parse_args()

    # 色は出力先が端末のときだけ有効になる。
    screen = Renderer()
    try:
        network = MapParser().parse_file(args.map_file)
        simulation = Simulation(network)
        plans = simulation.plan_all()
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    turns = simulation.to_turns(plans)
    print_summary(network, screen)
    print()
    print_zones(network, screen)
    print()
    print_connections(network)
    print()
    print_states(network, plans, screen)
    print()
    print("moves:")
    print_turns(network, turns, screen)
    print()
    print(f"total turns : {len(turns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
