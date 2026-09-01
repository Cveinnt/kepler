"""Grid -> PNG rendering shared by the daemon (frame dump) and tools/render.py.

Uses the arc_agi toolkit's own COLOR_MAP so rendered frames match the official
viewer. Game-agnostic: colors and scale only, no game knowledge.
"""
from __future__ import annotations

from PIL import Image

try:
    from arc_agi.rendering import COLOR_MAP, hex_to_rgb
    PALETTE = {k: hex_to_rgb(v) for k, v in COLOR_MAP.items()}
except Exception:  # fallback: still 16 distinguishable colors
    PALETTE = {i: ((i * 37) % 256, (i * 91) % 256, (i * 151) % 256) for i in range(16)}

SCALE = 8  # 64x64 -> 512x512, the resolution VISTA reports models read reliably


def grid_to_png(grid: list[list[int]], path: str, scale: int = SCALE) -> None:
    h, w = len(grid), len(grid[0])
    img = Image.new("RGB", (w, h))
    img.putdata([PALETTE.get(int(v), (0, 0, 0)) for row in grid for v in row])
    img = img.resize((w * scale, h * scale), Image.NEAREST)
    img.save(path)
