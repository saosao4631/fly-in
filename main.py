import sys

from graph import Network
from map_parser import MapParser
from zone import Zone

USAGE = "usage: python main.py <map file>"


def describe_zone(zone: Zone) -> str:
    """ゾーン1件を1行の文字列にまとめる。"""
    role = "S" if zone.is_start else ("E" if zone.is_end else " ")
    unlimited = zone.is_start or zone.is_end
    capacity = "inf" if unlimited else str(zone.capacity)
    return (
        f"{role} {zone.name:<20}"
        f" ({zone.x:>3},{zone.y:>3})"
        f" {zone.zone_type.value:<10}"
        f" cost={zone.zone_type.entry_cost}"
        f" cap={capacity:<4}"
        f" color={zone.color}"
    )


def show(network: Network) -> None:
    """読み込んだマップの中身を表示する。"""
    print(f"drones      : {network.nb_drones}")
    print(f"zones       : {len(network.zones)}")
    print(f"connections : {len(network.connections)}")
    print(f"start       : {network.start.name}")
    print(f"end         : {network.end.name}")
    print()
    print("zones:")
    for zone in network.zones:
        print(f"  {describe_zone(zone)}")
    print()
    print("connections:")
    for link in network.connections:
        print(f"  {link.name:<34} capacity={link.capacity}")


def main() -> int:
    """引数で指定されたマップを読み込んで表示する。"""
    if len(sys.argv) != 2:
        print(USAGE, file=sys.stderr)
        return 1
    try:
        network = MapParser().parse_file(sys.argv[1])
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    show(network)
    return 0


if __name__ == "__main__":
    sys.exit(main())
