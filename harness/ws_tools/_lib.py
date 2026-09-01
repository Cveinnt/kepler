"""Shared helpers for workspace tools. Stdlib only."""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterator, Optional

WS = Path(__file__).resolve().parent.parent
EVENTS = WS / "events.jsonl"

HEX = "0123456789abcdef"


def daemon(path: str, payload: Optional[dict] = None) -> dict:
    cfg = json.loads((WS / ".daemon.json").read_text())
    url = f"http://127.0.0.1:{cfg['port']}{path}"
    if payload is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def load_world_model() -> Any:
    path = WS / "world_model.py"
    if not path.exists():
        sys.exit("world_model.py not found in workspace")
    spec = importlib.util.spec_from_file_location("world_model", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["world_model"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if not hasattr(mod, "simulate"):
        sys.exit("world_model.py must define simulate(grid, action) -> dict")
    return mod


def read_events() -> Iterator[dict]:
    if not EVENTS.exists():
        return
    with open(EVENTS) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def render_grid(grid: list[list[int]]) -> str:
    """Hex render: one char per cell, row-indexed. '.' for color 0 to expose shape."""
    lines = []
    w = len(grid[0]) if grid else 0
    header = "    " + "".join(str(c // 10) if c % 10 == 0 and c else " " for c in range(w))
    header2 = "    " + "".join(str(c % 10) for c in range(w))
    lines.append(header)
    lines.append(header2)
    for y, row in enumerate(grid):
        cells = "".join("." if v == 0 else HEX[v] for v in row)
        lines.append(f"{y:>3} {cells}")
    return "\n".join(lines)


def diff_cells(a: list[list[int]], b: list[list[int]]) -> list[tuple[int, int, int, int]]:
    """[(x, y, val_a, val_b)] where grids differ.

    A predicted cell of None means the model ABSTAINS on that cell (partial
    prediction, after Tycho's UNKNOWN cells and Retrodict's sparse `expect`
    lists). Abstained cells are never counted as mismatches — but see
    claimed_fraction(): a model that abstains everywhere has proven nothing.
    """
    out = []
    for y, (r1, r2) in enumerate(zip(a, b)):
        for x, (v1, v2) in enumerate(zip(r1, r2)):
            if v1 is None:
                continue
            if v1 != v2:
                out.append((x, y, v1, v2))
    return out


def claimed_fraction(pred: list[list[int]]) -> float:
    """Share of cells the prediction actually claims (non-None)."""
    total = claimed = 0
    for row in pred:
        for v in row:
            total += 1
            if v is not None:
                claimed += 1
    return claimed / total if total else 0.0


def objects(grid: list[list[int]], colors=None, connectivity: int = 4):
    """Connected components as a scene graph. Ported in spirit from Retrodict's
    arclog.objects() (github.com/ryanbbrown/Retrodict, workspace_template/arclog.py)
    and Tycho's wmlib.segment (github.com/NIMI-research/Tycho) — both open source,
    both credited. Returns dicts: color, cells, bbox (x0,y0,x1,y1), size,
    centroid, and a translation-invariant shape hash so the same object is
    recognisable anywhere on the board.
    """
    H = len(grid); W = len(grid[0]) if H else 0
    seen = [[False] * W for _ in range(H)]
    out = []
    for y0 in range(H):
        for x0 in range(W):
            if seen[y0][x0]:
                continue
            c = grid[y0][x0]
            if colors is not None and c not in colors:
                seen[y0][x0] = True
                continue
            stack = [(x0, y0)]; seen[y0][x0] = True; cells = []
            while stack:
                x, y = stack.pop(); cells.append((x, y))
                steps = ((1,0),(-1,0),(0,1),(0,-1)) if connectivity == 4 else                         ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
                for dx, dy in steps:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and grid[ny][nx] == c:
                        seen[ny][nx] = True; stack.append((nx, ny))
            xs = [x for x, _ in cells]; ys = [y for _, y in cells]
            mnx, mny = min(xs), min(ys)
            shape = tuple(sorted((x - mnx, y - mny) for x, y in cells))
            out.append({
                "color": c, "cells": cells, "size": len(cells),
                "bbox": (mnx, mny, max(xs), max(ys)),
                "centroid": (sum(xs) / len(xs), sum(ys) / len(ys)),
                "hash": hash((c, shape)),
                "shape_hash": hash(shape),   # colour-blind: same shape, any colour
            })
    return out


def normalize_action(a: dict) -> dict:
    out = {"name": a["name"]}
    if a["name"] == "ACTION6":
        out["x"] = int(a["x"])
        out["y"] = int(a["y"])
    return out


def action_str(a: dict) -> str:
    if a.get("name") == "ACTION6":
        return f"ACTION6({a.get('x')},{a.get('y')})"
    return a.get("name", "?")


def simulate_safe(mod: Any, grid: list[list[int]], action: dict) -> dict:
    """Run world_model.simulate defensively; normalize the result shape."""
    res = mod.simulate([row[:] for row in grid], dict(action))
    if not isinstance(res, dict) or "grid" not in res:
        raise ValueError("simulate() must return a dict with a 'grid' key")
    return {
        "grid": res["grid"],
        "level_up": bool(res.get("level_up", False)),
        "game_over": bool(res.get("game_over", False)),
        "win": bool(res.get("win", False)),
    }
