from graph import Network
from zone import Zone
import heapq


class PathFinder:
    def __init__(self, network: Network) -> None:
        self._network = network

    def _neighbors(self, zone: Zone, turn: int) -> list[tuple[Zone, int]]:
        results: list[tuple[Zone, int]] = []
        results.append((zone, turn + 1))
        for link in self._network.links_of(zone):
            neighbour = link.other(zone)
            if not neighbour.zone_type.is_enterable:
                continue
            results.append((neighbour, turn + neighbour.zone_type.entry_cost))
        return results

    def find(self, start: Zone, goal: Zone) -> list[str] | None:

