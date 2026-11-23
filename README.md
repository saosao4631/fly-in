*This project has been created as part of the 42 curriculum by ksaotome.*

# Fly-in

## Description

Fly-in is a drone routing simulator. It reads a map describing a network of
**zones** joined by bidirectional **connections**, then moves a fleet of drones
from the single `start_hub` to the single `end_hub` in as few simulation turns
as possible.

The hard part is not the shortest path — it is the scheduling. Zones and
connections have capacities, `restricted` zones take two turns to enter and
cannot be abandoned mid-flight, and every drone moves at the same time. The
program therefore has to spread the fleet over several routes, make drones wait
on purpose when a corridor is saturated, and avoid deadlocks.

The project is written in Python 3.10+, is fully object oriented, passes
`mypy --strict`, and uses **no graph library**: the adjacency structure, the
search and the scheduling are all hand written.

## Instructions

```sh
make install      # create .venv and install the dev tools with uv
make run          # run on maps/easy/01_linear_path.txt
make run MAP=maps/hard/02_capacity_hell.txt
make debug        # run the same under pdb
make lint         # flake8 + mypy with the mandatory flags
make lint-strict  # flake8 + mypy --strict
make clean        # remove caches
```

Running the program directly:

```sh
python main.py maps/medium/03_priority_puzzle.txt
```

The program takes exactly one argument, the path to a map file. Any parse or
routing failure prints a single line on standard error and exits with status 1.

## Map format

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: bottleneck 1 0 [color=orange max_drones=2]
end_hub: goal 3 0 [color=red]
connection: start-bottleneck [max_link_capacity=4]
```

| Tag | Applies to | Default | Meaning |
| --- | --- | --- | --- |
| `zone=` | zones | `normal` | `normal`, `blocked`, `restricted`, `priority` |
| `color=` | zones | none | any single word, used by the renderer |
| `max_drones=` | zones | `1` | simultaneous occupancy, ignored on both hubs |
| `max_link_capacity=` | connections | `1` | simultaneous traversals |

Entering a `normal` or `priority` zone costs one turn, a `restricted` zone costs
two, and a `blocked` zone cannot be entered at all. Lines starting with `#` are
comments, and zone names may not contain a dash.

## Architecture

Every file sits at the root of the repository, one class per concern.

| File | Lines | Responsibility |
| --- | --- | --- |
| `zone.py` | 46 | `ZoneType` enum and `Zone`: cost, capacity, colour |
| `connection.py` | 27 | `Connection`: endpoints, capacity, display name, identity key |
| `graph.py` | 81 | `Network`: zone registry, adjacency list, lookups |
| `map_parser.py` | 247 | `MapParser`: strict, line aware reader |
| `reservation.py` | 35 | `ReservationTable`: space-time occupancy counters |
| `pathfinder.py` | 122 | `PathFinder`: space-time Dijkstra, plan reconstruction |
| `simulation.py` | 57 | `Simulation`: plan every drone, transpose into turns |
| `renderer.py` | 102 | `Renderer`: 256-colour terminal output |
| `main.py` | 112 | command line entry point |

The pipeline is linear:

```
map file -> MapParser -> Network -> PathFinder -> Simulation -> output
                                        |
                                 ReservationTable
```

## Algorithm

### Searching space-time rather than space

A static shortest path cannot express this problem. Whether a drone may enter a
zone depends on *when* it arrives, and the subject explicitly requires strategic
waiting, which is not an edge in a static graph at all.

The search therefore runs over a **time-expanded graph**: a node is the pair
`(zone, turn)` rather than a zone. Two kinds of edge leave every node.

* **Wait** — `(Z, T)` to `(Z, T+1)`, always one turn.
* **Move** — `(Z, T)` to `(neighbour, T + entry_cost)`, where the cost comes
  from the destination's zone type.

Waiting becomes an ordinary edge, and the two-turn `restricted` move becomes a
single edge that skips a turn. Blocked zones are simply never generated.

### No relaxation step is needed

In textbook Dijkstra, discovering a cheaper route to an already-seen node forces
a cost update. Here the turn is *part of the node identity*, so every route that
reaches `(B, 5)` costs exactly 5 by construction. The first discovery of a node
is therefore optimal and can be finalised immediately. The implementation keeps
a `visited` set of `(zone name, turn)` pairs and never pushes a node twice.

A `heapq` priority queue ordered by arrival turn gives the goal with the
smallest turn first. `heapq` is a heap, not a graph library, so it is within the
project constraints.

### The reservation table

`ReservationTable` holds two counters:

* `(zone name, turn)` to the number of drones standing there;
* `(connection key, turn)` to the number of drones crossing it.

They are counters rather than booleans because `max_drones` and
`max_link_capacity` allow more than one drone per slot.

Two conventions keep the arithmetic consistent, and they are written in the
class docstring so they cannot drift:

* a **zone** is reserved for each turn a drone *is standing there*;
* a **connection** is reserved by *departure turn*: a move leaving at turn `T`
  with cost `c` occupies slots `T … T+c-1` and lands at `T+c`.

Indexing links by departure turn means the index always names "the step that
starts at this turn". The alternative, indexing by arrival, would leave a
restricted move holding the connection on the very turn it has already landed.

Two properties fall out of this design for free:

* **Start and end need no special case.** `Zone.capacity` already returns an
  unbounded value for the two hubs, so `count < capacity` is always true there.
  The reservation table never learns that hubs exist.
* **Same-turn handovers work.** A drone standing at `Z` on turn `T` and another
  arriving at `Z` on turn `T+1` occupy different slots, which is exactly the
  subject's rule that drones moving out free capacity in the same turn.

Reserving connections, not only zones, is what catches head-on swaps. Two drones
exchanging places would balance out if only zone occupancy were counted; both
reserve the same `frozenset` key on the same departure turn, so a capacity of
one rejects the second.

### Prioritised planning

`Simulation` plans one drone at a time against a shared reservation table: plan
drone 1, commit its reservations, plan drone 2 around them, and so on. Every
drone sees the committed schedule of all its predecessors.

The consequence is that **all conflict resolution happens at planning time**.
Once the plans exist the simulation is a pure replay — `Simulation.to_turns`
only transposes the per-drone plans into per-turn lines and drops drones whose
position did not change. There is no turn-by-turn arbitration logic anywhere in
the codebase.

### Plan representation

A plan is a `list[str]` indexed by turn: `['start', 'bottleneck', 'goal']`. The
value is a zone name, or a connection name while the drone is in flight toward a
`restricted` zone. This matches the required output format directly — turn `T`
emits `D<id>-<plan[T]>` when `plan[T]` differs from `plan[T-1]`, and emits
nothing when they are equal, which is precisely the "drones that do not move are
omitted" rule.

Because the parser forbids dashes in zone names, a plan entry containing a dash
is unambiguously a connection name. `reserve_plan` relies on that to tell the
two apart.

### Complexity and memory

For one drone the search visits at most `|V| x T` nodes and relaxes
`(|E| + |V|) x T` edges, giving `O(T(V + E) log(TV))` with the heap, where `T`
is the turn horizon. The whole run is that multiplied by the number of drones,
since each drone is planned exactly once and paths are not cached or recomputed.

Memory is dominated by the reservation table, which only stores slots that are
actually used: `O(D x T)` entries for `D` drones. The `visited` set is discarded
after each drone's search.

A `TURN_LIMIT` of 500 bounds the horizon so that an unreachable goal terminates
instead of expanding wait edges forever.

### Known limitations

Prioritised planning is neither complete nor optimal for makespan. A drone
planned late can in principle find every route blocked by its predecessors, in
which case the program reports the failure rather than silently producing an
invalid schedule. Greedily minimising each drone's own arrival can also leave a
faster global schedule unused — on a map with a fast and a slow branch, every
drone queues on the fast branch rather than splitting.

## Performance

Measured with the maps shipped with the subject. Every target is met, and the
optional challenger map beats the reference record.

| Map | Drones | Turns | Target | Result |
| --- | ---: | ---: | ---: | --- |
| `easy/01_linear_path` | 2 | 4 | 6 | pass |
| `easy/02_simple_fork` | 4 | 4 | 8 | pass |
| `easy/03_basic_capacity` | 4 | 4 | 6 | pass |
| `medium/01_dead_end_trap` | 5 | 8 | 12 | pass |
| `medium/02_circular_loop` | 6 | 15 | 15 | pass (no margin) |
| `medium/03_priority_puzzle` | 5 | 7 | 12 | pass |
| `hard/01_maze_nightmare` | 8 | 13 | 30 | pass |
| `hard/02_capacity_hell` | 12 | 16 | 35 | pass |
| `hard/03_ultimate_challenge` | 15 | 26 | 45 | pass |
| `challenger/01_the_impossible_dream` | 25 | **43** | 45 (record) | **record beaten** |

Every map solves in under 0.1 seconds.

## Visual representation

The run prints three blocks, all colourised when standard output is a terminal.

**The zone table** shows each zone with its coordinates, type, entry cost and
effective capacity. Terminal hubs display `inf`, which makes the "hubs ignore
`max_drones`" rule visible rather than implicit.

**The `states` block** is the most useful view: for every turn it lists which
drones occupy which zone.

```
states:
  T0   start[D1,D2,D3,D4]
  T1   start[D3,D4] bottleneck[D1,D2]
  T2   bottleneck[D3,D4] wide_area[D1,D2]
```

A move list alone shows what happened; this shows *why*. Congestion, deliberate
waiting, capacity limits being hit and the fleet splitting across branches are
all readable at a glance. The line above shows the fleet sharing `start`
without limit, then a capacity-2 bottleneck admitting exactly two drones while
the other two wait.

**The `moves` block** is the format required by the subject, one line per turn.

Three details make the colouring robust:

* Zone colours use the 256-colour palette, because the shipped maps contain
  names such as `orange`, `crimson`, `gold` and `maroon` that have no entry in
  the basic eight. A name with no mapping — the maps include `rainbow` — is
  printed uncoloured rather than failing.
* Each drone gets its own colour from a cycling palette, so a wide turn line can
  be scanned per drone.
* Padding is applied *before* colouring. Escape sequences count as characters,
  so colouring first and padding afterwards would silently break every column.

Colour is disabled automatically when output is not a terminal, so redirecting
to a file produces clean text without needing a flag.

## Example

Input, `maps/easy/03_basic_capacity.txt`:

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: bottleneck 1 0 [color=orange max_drones=2]
hub: wide_area 2 0 [color=blue max_drones=3]
end_hub: goal 3 0 [color=red]

connection: start-bottleneck [max_link_capacity=4]
connection: bottleneck-wide_area [max_link_capacity=4]
connection: wide_area-goal [max_link_capacity=4]
```

Expected movement output:

```
D1-bottleneck D2-bottleneck
D1-wide_area D2-wide_area D3-bottleneck D4-bottleneck
D1-goal D2-goal D3-wide_area D4-wide_area
D3-goal D4-goal
```

Four turns against a target of six. Turn 2 is the interesting one: `bottleneck`
has capacity 2 and is full with D1 and D2, yet D3 and D4 enter on the same turn
because D1 and D2 vacate it simultaneously.

An invalid map stops with the offending line:

```
$ python main.py broken.map
error: line 3: unknown zone type 'teleport'
```

## Resources

* Dijkstra's algorithm — Cormen et al., *Introduction to Algorithms*, ch. 24.
* D. Silver, *Cooperative Pathfinding* (AIIDE 2005) — the reservation-table
  approach to multi-agent routing that this implementation follows.
* Multi-agent pathfinding overview:
  <https://en.wikipedia.org/wiki/Multi-agent_pathfinding>
* Python typing reference: <https://docs.python.org/3/library/typing.html>
* PEP 257, docstring conventions: <https://peps.python.org/pep-0257/>
* ANSI escape codes: <https://en.wikipedia.org/wiki/ANSI_escape_code>

### Use of AI

AI was used throughout this project, in the following roles:

* **Translating the subject** from English into Japanese for a first reading.
* **Explaining language and tooling** — dataclasses, type annotations, `heapq`,
  f-string format specifiers, the difference between `flake8` and `mypy`
  configuration, and why a frozen dataclass cannot hold mutable state.
* **Reviewing code** written by hand, which caught a method-name collision that
  silently overwrote `can_enter`, a `self` used where a local variable was
  meant, and a hard-coded move cost that ignored `restricted` zones.
* **Drafting implementation** for the parser, the search loop and its plan
  reconstruction, the simulation transpose and the renderer, each explained line
  by line before being accepted.
* **Designing the approach** — in particular the decision to search space-time
  rather than a static graph, and the choice to index connection reservations by
  departure turn.

Every generated line was read and tested before being committed, and the design
decisions recorded above are ones I can justify.

---

# 日本語版

## 概要

Fly-in はドローンの経路制御シミュレータです。**ゾーン**が双方向の**接続**で
結ばれたネットワークを読み込み、唯一の `start_hub` から唯一の `end_hub` まで、
できるだけ少ないターン数で全機を移動させます。

難しいのは最短経路ではなくスケジューリングです。ゾーンにも接続にも定員があり、
`restricted` ゾーンは進入に2ターンかかるうえ途中で引き返せず、全機が同時に動き
ます。そのため、複数の経路に機体を分散させ、通路が詰まっているときは意図的に
待機させ、デッドロックを避ける必要があります。

Python 3.10 以降、完全なオブジェクト指向、`mypy --strict` 通過、**グラフ
ライブラリ不使用**（隣接表も探索もスケジューリングも自前）です。

## 使い方

```sh
make install
make run
make run MAP=maps/hard/02_capacity_hell.txt
make lint
python main.py maps/medium/03_priority_puzzle.txt
```

引数はマップファイル1つだけです。解析や経路の失敗は標準エラーに1行出して
終了コード1で終わります。

## アルゴリズム

### なぜ時空間を探索するのか

静的な最短経路ではこの問題を表現できません。ゾーンに入れるかどうかは**いつ**
着くかに依存しますし、課題が要求する「戦略的な待機」は静的グラフには辺として
存在しません。

そこで探索は**時間展開グラフ**の上で行います。ノードはゾーンではなく
`(ゾーン, ターン)` の組です。各ノードから出る辺は2種類だけです。

* **待機** — `(Z, T)` から `(Z, T+1)`、常に1ターン
* **移動** — `(Z, T)` から `(隣, T + 進入コスト)`、コストは行き先のゾーン種別で決まる

待機がただの辺になり、`restricted` の2ターン移動は「ターンを1つ飛ばす辺」に
なります。`blocked` ゾーンはそもそも候補に現れません。

### コスト更新が要らない

教科書のダイクストラでは、既に見たノードへより安い経路が見つかると更新が
必要です。しかしここでは**ターンがノードの識別子に含まれる**ため、`(B, 5)` に
至る経路はどれもコストがちょうど 5 です。したがって最初に見つけた時点で確定
でき、比較も更新も不要になります。実装では `(ゾーン名, ターン)` の `visited`
集合を持ち、同じノードを二度積みません。

### 予約表

`ReservationTable` は数え表を2つ持ちます。

* `(ゾーン名, ターン)` → そこにいる機数
* `(接続の鍵, ターン)` → そこを渡る機数

真偽値ではなく数なのは、`max_drones` と `max_link_capacity` が複数機を許すから
です。

ターン番号の約束は2つで、クラスの docstring に書いてあります。

* **ゾーン**は、機体が「そこにいる」各ターンを予約する
* **接続**は**出発ターン**で予約する。ターン `T` に出発してコスト `c` の移動は
  `T 〜 T+c-1` の `c` 枠を占有し、到着は `T+c`

接続を出発ターンで数えると、添字が常に「このターンから始まるステップ」を指し
ます。到着ターン基準にすると、`restricted` の移動が着地済みのターンにまだ接続を
押さえていることになります。

この設計から2つの性質が自動的に得られます。

* **始点と終点の特別扱いが要らない。** `Zone.capacity` が終端では無制限を返す
  ので、`数 < 定員` が常に成立します。予約表はハブの存在を知りません。
* **同一ターンの入れ替わりが成立する。** ターン `T` に `Z` にいる機体と、
  `T+1` に `Z` へ入る機体は別の枠を使います。これが課題の「出る機体は同じ
  ターンに定員を空ける」という規則そのものです。

ゾーンだけでなく**接続も予約する**ことで、向かい合った機体のすれ違いを捕まえ
られます。ゾーンの人数だけ見ていると辻褄が合ってしまいますが、両機が同じ
`frozenset` の鍵を同じ出発ターンで予約するため、定員1なら2機目が弾かれます。

### 優先度順計画

`Simulation` は共有の予約表に対して1機ずつ計画します。D1 を計画して予約を
書き込み、D2 はそれを避けて計画する、という順です。

結果として**衝突の解決がすべて計画時に終わります**。予定が揃った後の
シミュレーションは純粋な再生で、`Simulation.to_turns` は機体ごとの予定表を
ターンごとに転置し、位置が変わらなかった機体を落とすだけです。ターンごとの
調停ロジックはコードのどこにもありません。

### 予定表の表現

予定表はターンを添字とする `list[str]` です（`['start', 'bottleneck', 'goal']`）。
値はゾーン名、または `restricted` へ飛行中なら接続名です。これは課題の出力形式
と直接対応します。ターン `T` では `plan[T]` が `plan[T-1]` と違えば
`D<id>-<plan[T]>` を出し、同じなら何も出さない。これがそのまま「動かない機体は
省略する」規則になります。

パーサがゾーン名にダッシュを禁じているため、ダッシュを含む要素は接続名だと
一意に判別できます。`reserve_plan` はこれを利用しています。

### 計算量とメモリ

1機あたり、探索は最大 `|V| x T` ノードを訪れ、`(|E| + |V|) x T` 辺を緩和する
ので、ヒープ込みで `O(T(V + E) log(TV))` です（`T` はターンの上限）。全体は
これに機数を掛けたものになります。各機体はちょうど1回だけ計画され、経路の
キャッシュや再計算は行いません。

メモリは予約表が支配的ですが、実際に使われた枠しか保持しないので `D` 機に対し
`O(D x T)` エントリです。`visited` 集合は各機体の探索後に破棄されます。

`TURN_LIMIT` を 500 に設定して、到達できないゴールでも待機辺を無限に展開せず
終了するようにしています。

### 既知の限界

優先度順計画は完全でも最適でもありません。後から計画される機体が、先行機に
よってすべての経路を塞がれる可能性が原理的にあります。その場合は不正な
スケジュールを黙って出すのではなく、失敗として報告します。また各機体が自分の
到着時刻だけを貪欲に最小化するため、全体としてより速いスケジュールを逃すことが
あります。速い枝と遅い枝があるマップでは、分散せず全機が速い枝に並びます。

## 性能

課題付属のマップで計測。全目標を達成し、任意の challenger マップでは参考記録を
更新しています。

| マップ | 機数 | 結果 | 目標 | 判定 |
| --- | ---: | ---: | ---: | --- |
| `easy/01_linear_path` | 2 | 4 | 6 | 達成 |
| `easy/02_simple_fork` | 4 | 4 | 8 | 達成 |
| `easy/03_basic_capacity` | 4 | 4 | 6 | 達成 |
| `medium/01_dead_end_trap` | 5 | 8 | 12 | 達成 |
| `medium/02_circular_loop` | 6 | 15 | 15 | 達成（余裕なし） |
| `medium/03_priority_puzzle` | 5 | 7 | 12 | 達成 |
| `hard/01_maze_nightmare` | 8 | 13 | 30 | 達成 |
| `hard/02_capacity_hell` | 12 | 16 | 35 | 達成 |
| `hard/03_ultimate_challenge` | 15 | 26 | 45 | 達成 |
| `challenger/01_the_impossible_dream` | 25 | **43** | 45（記録） | **記録更新** |

全マップが0.1秒未満で解けます。

## 視覚表現

実行すると3つのブロックが出ます。標準出力が端末のときだけ着色されます。

**ゾーン表**は各ゾーンの座標・種別・進入コスト・実効定員を示します。終端ハブは
`inf` と表示されるので、「ハブは `max_drones` を無視する」規則が暗黙ではなく
目に見えます。

**`states` ブロック**が最も有用です。各ターンにどの機体がどのゾーンにいるかを
一覧します。

```
states:
  T0   start[D1,D2,D3,D4]
  T1   start[D3,D4] bottleneck[D1,D2]
  T2   bottleneck[D3,D4] wide_area[D1,D2]
```

動きの一覧は「何が起きたか」しか示しませんが、これは「なぜそうなったか」を
示します。混雑、意図的な待機、定員の上限に当たっている様子、経路の分散が一目で
読み取れます。上の例では、全機が `start` を制限なく共有し、定員2の
`bottleneck` がちょうど2機を受け入れ、残り2機が待機しているのが分かります。

**`moves` ブロック**が課題の要求する形式です。

着色を堅牢にしている点が3つあります。

* ゾーンの色は256色パレットを使います。付属マップに `orange` / `crimson` /
  `gold` / `maroon` など基本8色に無い名前が多数あるためです。対応表に無い名前
  （`rainbow` が実在します）は、失敗せず無着色で出力します。
* 機体ごとに循環パレットから色を割り当てるので、横に長いターン行でも機体単位で
  追えます。
* **幅を揃えてから着色します。** エスケープシーケンスは文字数に数えられるため、
  先に着色すると全ての列が静かに崩れます。

出力が端末でないときは自動的に色が無効になるので、ファイルへのリダイレクトでも
フラグ無しできれいなテキストが得られます。

## AI の利用について

本プロジェクトでは以下の用途で AI を利用しました。

* 課題文の翻訳
* 言語とツールの解説
* 自分で書いたコードのレビュー
* 実装の下書き
* 方針の設計