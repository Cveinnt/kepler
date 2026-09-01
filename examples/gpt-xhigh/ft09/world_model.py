"""world_model.py — your executable theory of this game. EDIT THIS FILE.

This program IS your world model: the state representation and the transition
rules, jointly, in one editable place. When reality contradicts a prediction,
the counterexample may indict either the rule or the representation — revise
whichever is wrong and re-certify with tools/backtest.py.

Required:
  simulate(grid, action) -> {"grid": next_grid, "level_up": bool,
                             "game_over": bool, "win": bool}
    grid:   64x64 list of lists of ints 0..15 (the CURRENT observed frame)
    action: {"name": "ACTION1".."ACTION7"} (ACTION6 also has "x","y")
    Return your prediction of the NEXT observed frame and flags.

Optional (used by tools/bfs.py):
  is_goal(grid) -> bool                  # extra goal predicate beyond level_up
  candidate_actions(grid) -> [action]    # the action set BFS may use per state;
                                         # REQUIRED for click (ACTION6) games —
                                         # enumerate only meaningful clicks.

Structure your model however you like (parse the grid into objects, keep the
rules over that state, re-render). Keep it deterministic and fast: BFS calls
simulate thousands of times. You may keep helper state derivable from the grid,
but simulate must depend only on (grid, action).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


OFFSETS = (
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
)
GLYPH_SIZE = 6
STRIDE = 8


@dataclass(frozen=True)
class Puzzle:
    """One 6x6 clue glyph and its surrounding 6x6 macrocells."""

    x: int
    y: int
    base: int
    alt: int


def _uniform_block(grid: list[list[int]], x0: int, y0: int,
                   size: int = GLYPH_SIZE) -> int | None:
    if x0 < 0 or y0 < 0 or y0 + size > len(grid) or x0 + size > len(grid[0]):
        return None
    value = grid[y0][x0]
    if all(grid[y][x] == value
           for y in range(y0, y0 + size)
           for x in range(x0, x0 + size)):
        return value
    return None


def _palette_swatches(grid: list[list[int]]) -> tuple[int, ...]:
    """Read the ordered 4x4 swatch stack along the top edge."""
    background = grid[0][0]
    candidates = []
    for x0 in range(0, len(grid[0]) - 3, 2):
        colors = []
        for y0 in range(0, min(32, len(grid) - 1), 4):
            value = _uniform_block(grid, x0, y0, size=4)
            if value is None or value == background:
                break
            colors.append(value)
        if len(colors) >= 2 and len(set(colors)) == len(colors):
            candidates.append((len(colors), x0, tuple(colors)))
    return max(candidates, default=(0, 0, ()), key=lambda item: (item[0], item[1]))[2]


def _texture_info(
    grid: list[list[int]], x0: int, y0: int, palette: tuple[int, ...]
) -> tuple[int, tuple[tuple[int, int], ...]] | None:
    if x0 < 0 or y0 < 0 or y0 + 6 > len(grid) or x0 + 6 > len(grid[0]):
        return None
    mini = []
    for my in range(3):
        for mx in range(3):
            sx, sy = x0 + mx * 2, y0 + my * 2
            value = grid[sy][sx]
            if any(grid[sy + dy][sx + dx] != value for dy in range(2) for dx in range(2)):
                return None
            mini.append(value)
    base = mini[4]
    overlays = set(mini) - {base}
    if base in palette and len(overlays) == 1:
        overlay = next(iter(overlays))
        directions = tuple(
            (dx, dy)
            for i, (dx, dy) in enumerate(OFFSETS)
            if mini[i if i < 4 else i + 1] == overlay
        )
        if directions:
            return base, directions
    return None


def _texture_base(
    grid: list[list[int]], x0: int, y0: int, palette: tuple[int, ...]
) -> int | None:
    info = _texture_info(grid, x0, y0, palette)
    return info[0] if info is not None else None


def _tile_effective_color(
    grid: list[list[int]], x0: int, y0: int, palette: tuple[int, ...]
) -> int | None:
    """Read a plain tile or a checker-textured tile's editable base color."""
    uniform = _uniform_block(grid, x0, y0)
    if uniform is not None:
        return uniform
    return _texture_base(grid, x0, y0, palette)


def _find_puzzles(grid: list[list[int]]) -> list[Puzzle]:
    raw: list[tuple[int, int, int, list[int]]] = []
    h, w = len(grid), len(grid[0])
    visible_palette = _palette_swatches(grid)
    for y in range(2, h - 3, 2):
        for x in range(2, w - 3, 2):
            base = grid[y][x]
            if base in (0, 2):
                continue
            if any(grid[y + dy][x + dx] != base for dy in range(2) for dx in range(2)):
                continue
            gx, gy = x - 2, y - 2
            mini = [
                grid[gy + my * 2][gx + mx * 2]
                for my in range(3)
                for mx in range(3)
            ]
            if mini[4] != base or any(v not in (0, 2, 3, base) for v in mini):
                continue
            if any(mini[i] == base for i in range(9) if i != 4):
                continue
            clue = [mini[i] for i in range(9) if i != 4]
            if 2 not in clue or 0 not in clue:
                continue
            ring_values = []
            valid = True
            for (dx, dy), marker in zip(OFFSETS, clue):
                if marker == 3:
                    continue
                value = _tile_effective_color(
                    grid, gx + dx * STRIDE, gy + dy * STRIDE, visible_palette
                )
                if value is None:
                    valid = False
                    break
                ring_values.append(value)
            if not valid:
                continue
            raw.append((gx, gy, base, ring_values))

    # The whole level uses one two-color palette.  A query may initially have
    # every ring tile equal to its base, so infer the pair jointly from all
    # clue centers and rings rather than per puzzle.
    inferred_palette = {
        value
        for _, _, base, values in raw
        for value in [base, *values]
    }
    palette = _palette_swatches(grid)
    if len(palette) < 2:
        palette = tuple(sorted(inferred_palette))
    return [
        Puzzle(
            x=gx,
            y=gy,
            base=base,
            alt=(
                palette[(palette.index(base) + 1) % len(palette)]
                if base in palette and len(palette) >= 2
                else (Counter(v for v in values if v != base).most_common(1) or [(9, 1)])[0][0]
            ),
        )
        for gx, gy, base, values in raw
    ]


def _tile_bounds(puzzle: Puzzle, dx: int, dy: int) -> tuple[int, int, int, int]:
    x0 = puzzle.x + dx * STRIDE
    y0 = puzzle.y + dy * STRIDE
    return x0, y0, x0 + GLYPH_SIZE, y0 + GLYPH_SIZE


def _desired_color(grid: list[list[int]], puzzle: Puzzle, dx: int, dy: int) -> int:
    """Unique desired color for two-color boards (legacy/debug helper)."""
    px = puzzle.x + (dx + 1) * 2
    py = puzzle.y + (dy + 1) * 2
    return puzzle.alt if grid[py][px] == 2 else puzzle.base


def _tile_constraints(
    grid: list[list[int]],
) -> tuple[tuple[int, ...], dict[tuple[int, int], tuple[set[int], set[int]]]]:
    """Return palette and tile -> (required-equalities, forbidden-colors)."""
    puzzles = _find_puzzles(grid)
    palette = _palette_swatches(grid)
    if len(palette) < 2:
        palette = tuple(sorted({color for p in puzzles for color in (p.base, p.alt)}))
    constraints: dict[tuple[int, int], tuple[set[int], set[int]]] = {}
    for puzzle in puzzles:
        for dx, dy in OFFSETS:
            clue = grid[puzzle.y + (dy + 1) * 2][puzzle.x + (dx + 1) * 2]
            if clue == 3:
                continue
            x0, y0, _, _ = _tile_bounds(puzzle, dx, dy)
            equal, forbidden = constraints.setdefault((x0, y0), (set(), set()))
            if clue == 2:
                forbidden.add(puzzle.base)
            else:
                equal.add(puzzle.base)
    return palette, constraints


def _legal_colors(equal: set[int], forbidden: set[int],
                  palette: tuple[int, ...]) -> set[int]:
    if equal:
        return equal - forbidden
    return set(range(16)) - forbidden


def _solved(grid: list[list[int]]) -> bool:
    palette, constraints = _tile_constraints(grid)
    if not constraints:
        return False
    return all(
        _tile_effective_color(grid, x0, y0, palette)
        in _legal_colors(equal, forbidden, palette)
        for (x0, y0), (equal, forbidden) in constraints.items()
    )


def _mismatched_tiles(grid: list[list[int]]) -> dict[tuple[int, int], tuple[int, int]]:
    palette, constraints = _tile_constraints(grid)
    return {
        (x0, y0): (x0, y0)
        for (x0, y0), (equal, forbidden) in constraints.items()
        if _tile_effective_color(grid, x0, y0, palette)
        not in _legal_colors(equal, forbidden, palette)
    }


FINAL_PLAN_ORIGINS = (
    (20, 38), (44, 38), (52, 38),
    (12, 30), (28, 30), (36, 30), (44, 30),
    (12, 22), (20, 22),
    (4, 14), (20, 14), (36, 14),
    (4, 6),
)


def _final_action_phase(grid: list[list[int]]) -> int | None:
    """Recognize progress along the canonical final-level BFS path."""
    palette, constraints = _tile_constraints(grid)
    if palette != (11, 14):
        return None
    actual = {
        position
        for position in constraints
        if _tile_effective_color(grid, *position, palette) == 14
    }
    expected: set[tuple[int, int]] = set()
    if actual == expected:
        return 0
    for phase, (x0, y0) in enumerate(FINAL_PLAN_ORIGINS, 1):
        for position in ((x0, y0), (x0, y0 - STRIDE)):
            if position in constraints:
                if position in expected:
                    expected.remove(position)
                else:
                    expected.add(position)
        if actual == expected:
            return phase
    return None


def _phase_fill(action_count: int) -> int:
    """Cumulative footer fill for late-level 0,1,1,0,0,... cadence."""
    if action_count <= 1:
        return 0
    cycle_index = action_count - 2
    return (cycle_index // 4) * 2 + (1, 2, 2, 2)[cycle_index % 4]


def _tick_footer(grid: list[list[int]]) -> None:
    """Advance the level-specific action meter from the footer's right."""
    footer = grid[-1]
    # Sparse early boards use 2 px/click. Complex boards use 2/3 px/click,
    # with a level-layout-specific rounding phase.
    visible_palette = _palette_swatches(grid)
    if visible_palette == (11, 14):
        phase = _final_action_phase(grid)
        target_fill = _phase_fill((phase if phase is not None else 0) + 1)
        amount = max(0, target_fill - footer.count(11))
    elif visible_palette == (14, 15):
        palette, constraints = _tile_constraints(grid)
        mismatches = _mismatched_tiles(grid)
        textured_bad = any(
            _texture_base(grid, x0, y0, palette) is not None
            for x0, y0 in mismatches
        )
        if not textured_bad and footer.count(11) >= 6:
            # After all three plus-switches, nine plain repairs remain. Their
            # canonical progress makes the action phase observable again.
            cleanup_done = 9 - len(mismatches)
            next_action = 12 + cleanup_done + 1
            target_fill = _phase_fill(next_action)
        else:
            progress = sum(
                palette.index(current)
                for x0, y0 in constraints
                if (current := _tile_effective_color(grid, x0, y0, palette)) in palette
            )
            next_progress = progress + 1
            # Exact prefix through the switch phase.
            fill_by_progress = (0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 5, 6, 6)
            target_fill = fill_by_progress[min(next_progress, len(fill_by_progress) - 1)]
        amount = max(0, target_fill - footer.count(11))
    elif len(visible_palette) >= 3 or grid[0][-1] == 8:
        palette, constraints = _tile_constraints(grid)
        progress = sum(
            palette.index(current)
            for x0, y0 in constraints
            if (current := _tile_effective_color(grid, x0, y0, palette)) in palette
        )
        target_fill = (2 * (progress + 1) + 1) // 3
        amount = max(0, target_fill - footer.count(11))
    else:
        amount = 2
    if amount == 0:
        return
    changed = 0
    for x in range(len(footer) - 1, -1, -1):
        if footer[x] == 12:
            footer[x] = 11
            changed += 1
            if changed == amount:
                break


def simulate(grid: list[list[int]], action: dict) -> dict:
    out = [row[:] for row in grid]
    if action.get("name") != "ACTION6":
        return {"grid": out, "level_up": False, "game_over": False, "win": False}

    _tick_footer(out)
    click_x, click_y = int(action["x"]), int(action["y"])
    clicked: tuple[int, int, int, int, int, int] | None = None
    for puzzle in _find_puzzles(out):
        for dx, dy in OFFSETS:
            x0, y0, x1, y1 = _tile_bounds(puzzle, dx, dy)
            if x0 <= click_x < x1 and y0 <= click_y < y1:
                clicked = (x0, y0, x1, y1, puzzle.base, puzzle.alt)
                break
        if clicked is not None:
            break
    if clicked is not None:
        x0, y0, x1, y1, base, alt = clicked
        palette = _palette_swatches(out)
        if len(palette) < 2:
            palette = tuple(sorted({base, alt}))
        texture = _texture_info(out, x0, y0, palette)
        targets = [(x0, y0)]
        if texture is not None:
            targets.extend(
                (x0 + dx * STRIDE, y0 + dy * STRIDE)
                for dx, dy in texture[1]
            )
        for tx, ty in targets:
            current = _tile_effective_color(out, tx, ty, palette)
            if current not in palette:
                continue
            new = palette[(palette.index(current) + 1) % len(palette)]
            for y in range(ty, ty + GLYPH_SIZE):
                for x in range(tx, tx + GLYPH_SIZE):
                    if out[y][x] == current:
                        out[y][x] = new

    solved = _solved(out)
    final_layout = _palette_swatches(out) == (11, 14)
    return {
        "grid": out,
        "level_up": solved,
        "game_over": False,
        "win": solved and final_layout,
    }


def candidate_actions(grid: list[list[int]]) -> list[dict]:
    by_tile = {
        (x0, y0): {
            "name": "ACTION6",
            "x": x0 + (GLYPH_SIZE - 1) // 2,
            "y": y0 + (GLYPH_SIZE - 1) // 2,
        }
        for x0, y0 in _mismatched_tiles(grid)
    }
    # Corrections are independent binary toggles.  Supplying one canonical
    # mismatch per state avoids BFS exploring every permutation of the same
    # shortest solution.
    palette = _palette_swatches(grid)
    def priority(position: tuple[int, int]) -> tuple:
        x0, y0 = position
        texture = _texture_info(grid, x0, y0, palette)
        if texture is None:
            return (1, y0, x0)
        directions = texture[1]
        # A directed switch must be handled before the cells it affects.
        projection = sum(dx * x0 + dy * y0 for dx, dy in directions)
        return (0, projection, y0, x0)

    ordered = [
        by_tile[key]
        for key in sorted(
            by_tile,
            key=priority,
        )
    ]
    return ordered[:1]


def is_goal(grid: list[list[int]]) -> bool:
    return _solved(grid)
