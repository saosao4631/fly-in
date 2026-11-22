import sys

from graph import Network
from map_parser import MapParser
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


def print_summary(network: Network) -> None:
    """マップ全体の数をまとめて表示する。"""
    print(f"drones      : {network.nb_drones}")
    print(f"zones       : {len(network.zones)}")
    print(f"connections : {len(network.connections)}")
    print(f"start       : {network.start.name}")
    print(f"end         : {network.end.name}")


def print_zones(network: Network) -> None:
    """ゾーンを1行ずつ表示する。"""
    print("zones:")
    for zone in network.zones:
        cells = [
            role_mark(zone),
            f"{zone.name:<20}",
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


def main() -> int:
    """引数で指定されたマップを読み込んで表示する。"""
    if len(sys.argv) != 2:
        print("usage: python main.py <map file>", file=sys.stderr)
        return 1

    try:
        network = MapParser().parse_file(sys.argv[1])
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print_summary(network)
    print()
    print_zones(network)
    print()
    print_connections(network)
    return 0


if __name__ == "__main__":
    sys.exit(main())
