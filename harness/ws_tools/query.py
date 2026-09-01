#!/usr/bin/env python3
"""Run Python over the game state instead of reading it into context (free).

Reading a 64x64 grid costs ~4KB of context every time you look. Computing over
it costs almost nothing. Use this whenever the question has a small answer:
"where is the avatar", "which cells changed", "what colors exist", "is the
pattern symmetric" — anything you could answer with a loop.

Your snippet runs with these already defined:
  grid              current 64x64 list[list[int]] (None before the first frame)
  status            dict from the daemon (level, win_levels, available_actions, ...)
  events            list of every recorded event (the whole timeline)
  prev              the grid one step back (None if unavailable)
  at(g, x, y)       safe cell read
  cells(g, v)       [(x, y)] of every cell with colour v
  colors(g)         {colour: count}
  bbox(pts)         (x0, y0, x1, y1) of a point list
  diff(a, b)        [(x, y, va, vb)] where two grids differ
  show(g, x0,y0,x1,y1)  render a rectangular window (use for SMALL regions)
  grid_at(i)        the grid recorded at timeline index i

Usage:
  python tools/query.py 'print(colors(grid))'
  python tools/query.py 'print(cells(grid, 9)[:20])'
  python tools/query.py 'print(bbox(cells(grid, 4)))'
  python tools/query.py 'print(len(diff(prev, grid)))'
  python tools/query.py -f probe.py        # run a file instead
"""

from __future__ import annotations

import argparse
import sys

from _lib import HEX, daemon, diff_cells, read_events, render_grid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", nargs="?", default=None)
    ap.add_argument("-f", "--file", default=None)
    args = ap.parse_args()
    src = open(args.file).read() if args.file else args.code
    if not src:
        raise SystemExit("give a snippet or -f FILE")

    st = daemon("/status")
    events = list(read_events())
    grid = st.get("grid")
    prev = None
    for e in reversed(events[:-1]):
        if e.get("grid"):
            prev = e["grid"]
            break

    def at(g, x, y):
        if g is None or not (0 <= y < len(g)) or not (0 <= x < len(g[0])):
            return None
        return g[y][x]

    def cells(g, v):
        return [(x, y) for y, row in enumerate(g or []) for x, c in enumerate(row) if c == v]

    def colors(g):
        out: dict[int, int] = {}
        for row in g or []:
            for c in row:
                out[c] = out.get(c, 0) + 1
        return dict(sorted(out.items()))

    def bbox(pts):
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def diff(a, b):
        return diff_cells(a, b) if a and b else []

    def show(g, x0=0, y0=0, x1=63, y1=63):
        return "\n".join(
            f"{y:>3} " + "".join("." if g[y][x] == 0 else HEX[g[y][x]] for x in range(x0, x1 + 1))
            for y in range(y0, y1 + 1)
        )

    def grid_at(i):
        for e in events:
            if e["i"] == i:
                return e.get("grid")
        return None

    env = dict(
        grid=grid, status=st, events=events, prev=prev,
        at=at, cells=cells, colors=colors, bbox=bbox, diff=diff,
        show=show, grid_at=grid_at, HEX=HEX,
    )
    try:
        exec(compile(src, "<query>", "exec"), env)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
