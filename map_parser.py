from connection import Connection
from graph import Network
from zone import Zone, ZoneType

ZONE_TAGS = frozenset({"zone", "color", "max_drones"})
LINK_TAGS = frozenset({"max_link_capacity"})

ZONE_PREFIXES = {
    "start_hub:": (True, False),
    "end_hub:": (False, True),
    "hub:": (False, False),
}


class MapParser:
    """マップファイルを読み込んで Network を組み立てる。
    どの問題も行番号つきで落とす。解析を parse_lines に閉じ込めて
    あるので、確認はファイルを作らず文字列のリストで書ける。
    """

    def parse_file(self, path: str) -> Network:
        """ファイルを開いて行のリストにし、本体に渡す。"""
        with open(path, "r", encoding="utf-8") as stream:
            lines = stream.read().splitlines()
        return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> Network:
        """行のリストを解析して Network を返す。"""
        network: Network | None = None
        for number, raw in enumerate(lines, start=1):
            line = self._strip_comment(raw)
            if not line:
                continue
            if network is None:
                network = Network(self._parse_header(line, number))
                continue
            self._parse_entry(network, line, number)
        if network is None:
            raise ValueError("missing 'nb_drones: <positive integer>'")
        self._validate(network)
        return network

    def _parse_entry(
        self, network: Network, line: str, number: int
    ) -> None:
        """ゾーン行か接続行かを見分けて振り分ける。"""
        prefix = "connection:"
        if line.startswith(prefix):
            self._parse_connection(network, line[len(prefix):], number)
            return
        for marker, roles in ZONE_PREFIXES.items():
            if line.startswith(marker):
                body = line[len(marker):]
                self._parse_zone(network, body, number, *roles)
                return
        raise ValueError(f"line {number}: unknown directive in {line!r}")

    def _parse_zone(
        self,
        network: Network,
        body: str,
        number: int,
        is_start: bool,
        is_end: bool,
    ) -> None:
        """hub: / start_hub: / end_hub: の行を読む。"""
        head, tags = self._split_tags(body, number)
        fields = head.split()
        if len(fields) != 3:
            raise ValueError(
                f"line {number}: expected '<name> <x> <y> [metadata]'"
            )
        name, raw_x, raw_y = fields
        if "-" in name:
            raise ValueError(
                f"line {number}: zone name {name!r} contains a dash"
            )
        if network.has_zone(name):
            raise ValueError(f"line {number}: duplicate zone {name!r}")
        if is_start and network.has_start:
            raise ValueError(f"line {number}: more than one start_hub")
        if is_end and network.has_end:
            raise ValueError(f"line {number}: more than one end_hub")
        self._check_tags(tags, ZONE_TAGS, number)
        network.add_zone(
            Zone(
                name=name,
                x=self._parse_int(raw_x, number, "x"),
                y=self._parse_int(raw_y, number, "y"),
                zone_type=self._parse_zone_type(tags, number),
                color=tags.get("color"),
                max_drones=self._parse_capacity(
                    tags, "max_drones", number
                ),
                is_start=is_start,
                is_end=is_end,
            )
        )

    def _parse_connection(
        self, network: Network, body: str, number: int
    ) -> None:
        """connection: の行を読む。"""
        head, tags = self._split_tags(body, number)
        fields = head.split()
        if len(fields) != 1:
            raise ValueError(
                f"line {number}: expected '<zone1>-<zone2> [metadata]'"
            )
        parts = fields[0].split("-")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"line {number}: malformed connection {fields[0]!r}"
            )
        first, second = parts
        if first == second:
            raise ValueError(
                f"line {number}: {first!r} is connected to itself"
            )
        for name in (first, second):
            if not network.has_zone(name):
                raise ValueError(f"line {number}: unknown zone {name!r}")
        if network.has_connection(first, second):
            raise ValueError(
                f"line {number}: duplicate connection {first}-{second}"
            )
        self._check_tags(tags, LINK_TAGS, number)
        network.add_connection(
            Connection(
                network.zone(first),
                network.zone(second),
                self._parse_capacity(tags, "max_link_capacity", number),
            )
        )

    @staticmethod
    def _strip_comment(raw: str) -> str:
        """コメントを落とし、前後の空白を削る。"""
        return raw.split("#", 1)[0].strip()

    @staticmethod
    def _parse_header(line: str, number: int) -> int:
        """nb_drones: の行を読んで機数を返す。"""
        prefix = "nb_drones:"
        if not line.startswith(prefix):
            raise ValueError(
                f"line {number}: expected 'nb_drones: <number>'"
            )
        raw = line[len(prefix):].strip()
        if not raw.isdigit() or int(raw) <= 0:
            raise ValueError(
                f"line {number}: nb_drones must be a positive integer,"
                f" got {raw!r}"
            )
        return int(raw)

    @staticmethod
    def _split_tags(
        body: str, number: int
    ) -> tuple[str, dict[str, str]]:
        """[...] の中身を切り出し、本体と tag の辞書に分ける。"""
        head, marker, rest = body.partition("[")
        if not marker:
            if "]" in head:
                raise ValueError(f"line {number}: ']' without '['")
            return head.strip(), {}
        rest = rest.strip()
        if not rest.endswith("]"):
            raise ValueError(
                f"line {number}: metadata block is not closed"
            )
        tags: dict[str, str] = {}
        for token in rest[:-1].split():
            key, separator, value = token.partition("=")
            if not separator or not key or not value:
                raise ValueError(
                    f"line {number}: bad metadata entry {token!r}"
                )
            if key in tags:
                raise ValueError(
                    f"line {number}: duplicate tag {key!r}"
                )
            tags[key] = value
        return head.strip(), tags

    @staticmethod
    def _check_tags(
        tags: dict[str, str], allowed: frozenset[str], number: int
    ) -> None:
        """課題に無いタグを拒否する。"""
        for key in tags:
            if key not in allowed:
                raise ValueError(f"line {number}: unknown tag {key!r}")

    @staticmethod
    def _parse_int(raw: str, number: int, label: str) -> int:
        """座標を読む。負の値もあるので isdigit は使えない。"""
        try:
            return int(raw)
        except ValueError:
            raise ValueError(
                f"line {number}: {label} must be an integer,"
                f" got {raw!r}"
            ) from None

    @staticmethod
    def _parse_capacity(
        tags: dict[str, str], key: str, number: int
    ) -> int:
        """容量のタグを読む。省略時は 1。"""
        raw = tags.get(key)
        if raw is None:
            return 1
        if not raw.isdigit() or int(raw) <= 0:
            raise ValueError(
                f"line {number}: {key} must be a positive integer,"
                f" got {raw!r}"
            )
        return int(raw)

    @staticmethod
    def _parse_zone_type(
        tags: dict[str, str], number: int
    ) -> ZoneType:
        """zone= のタグを読む。省略時は normal。"""
        raw = tags.get("zone")
        if raw is None:
            return ZoneType.NORMAL
        try:
            return ZoneType(raw)
        except ValueError:
            raise ValueError(
                f"line {number}: unknown zone type {raw!r}"
            ) from None

    @staticmethod
    def _validate(network: Network) -> None:
        """全行を読み終えてから、全体の辻褄を確かめる。"""
        if not network.has_start:
            raise ValueError("the map has no start_hub zone")
        if not network.has_end:
            raise ValueError("the map has no end_hub zone")
        for zone in (network.start, network.end):
            if not zone.zone_type.is_enterable:
                raise ValueError(
                    f"hub {zone.name!r} cannot be a blocked zone"
                )
