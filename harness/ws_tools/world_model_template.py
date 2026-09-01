"""world_model.py — your executable theory of this game. EDIT THIS FILE.

This program IS your world model. It has TWO jobs, and skipping the first is the
most common way to fail a game:

  LEVEL 1 — STATE GROUNDING: turn pixels into named objects.
      What IS this world? Which cells are the avatar, a wall, a box, a counter,
      a goal? Nothing tells you; you invent the vocabulary. Write one small
      finder per entity kind and give it a real name.

  LEVEL 2 — MECHANISM: how that state changes under an action.
      Written over your OWN objects, not over raw pixels.

Reasoning at the pixel level is what makes hard games impossible. Reasoning over
`find_boxes(grid)` and `find_walls(grid)` is what makes them tractable — and it
lets you interrogate your own model cheaply:

    python tools/query.py 'import world_model as wm; print(wm.find_boxes(grid))'

When a prediction fails, the counterexample can indict EITHER layer: maybe the
rule is wrong, or maybe "box" was never the right object. Be willing to redraw
the vocabulary — that representational revision is usually the thing that cracks
a stuck game.

Required:
  simulate(grid, action) -> {"grid": next_grid, "level_up": bool,
                             "game_over": bool, "win": bool}
    grid:   64x64 list of lists of ints 0..15 (the CURRENT observed frame)
    action: {"name": "ACTION1".."ACTION7"} (ACTION6 also has "x","y")

Strongly recommended (this is the Level-1 half):
  find_<thing>(grid) -> positions/objects, one per entity kind you name
  describe(grid)     -> a compact dict of the whole parsed state, for queries
  LEVEL              -> module-level int if mechanics differ per level

Optional (used by tools/bfs.py):
  is_goal(grid) -> bool                  # extra goal predicate beyond level_up
  candidate_actions(grid) -> [action]    # the action set BFS may use per state;
                                         # REQUIRED for click (ACTION6) games —
                                         # enumerate only meaningful clicks.

Keep it deterministic and fast: search calls simulate thousands of times. Version
it as you go (`world_model_v2.py`, ...) if you want to keep a fallback.

Note that `tools/bfs.py` is a plain breadth-first search — fine for movement
puzzles, hopeless for combinatorial ones. For placement/packing/ordering games,
write your own search in Python over your parsed objects (A*, constraint
propagation, or just enumerating legal configurations). Planning is yours to
design; BFS is only the default.
"""

from __future__ import annotations


# --- LEVEL 1: state grounding -------------------------------------------------
# Replace these with real finders as soon as you can name anything.

def describe(grid: list[list[int]]) -> dict:
    """A compact, queryable summary of the parsed state. Grow this as you learn."""
    counts: dict[int, int] = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1
    return {"colour_counts": counts}


# --- LEVEL 2: mechanism -------------------------------------------------------

def simulate(grid: list[list[int]], action: dict) -> dict:
    # Placeholder theory: "nothing ever changes". Every real effect an action
    # has will therefore surface as a SURPRISE counterexample to fix.
    return {"grid": grid, "level_up": False, "game_over": False, "win": False}
