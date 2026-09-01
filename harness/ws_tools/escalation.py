"""Stuck-level signals and the binding escalation directive.

Par-free triggers, adopted from Retrodict's runner (their measured effect: a level
that absorbed ~800 live probes was cleared in 59 actions once the directive was
injected into every invocation): ESCALATE_ACTIONS actions on one level, or
ESCALATE_RESETS self-issued RESETs on it. GAME_OVER-forced resets do not count.
The directive is delivered by run_game.py at the top of every session prompt
while the level is stuck; commit.py prints the same text. Zero cost otherwise.
"""
from __future__ import annotations

# Baseline-relative triggers. Retrodict's par-free 300-action / 2-reset rule
# mis-fires on this harness: our agents RESET as a cheap experiment (2 resets
# inside the first 20 actions is routine on games that finish at 100), and
# several public levels have human baselines in the hundreds, where 300 actions
# is not stuck. Replaying the development ledgers: the par-free rule fired on 15
# of 43 perfect games, several with <10 actions left on the level. The rule below
# only fires on levels whose learning attempt ran long (>=100 more actions
# followed on every perfect-game fire) and still fires within ~100 actions on
# the levels that absorbed thousands. Verified by tests/test_recovery_paths.py.
ESCALATE_T1 = 3.0        # x this level's human baseline -> tier 1
ESCALATE_T2 = 6.0        # x baseline -> tier 2
ESCALATE_RESETS = 4      # self-issued RESETs on one level (with >= 1.5x baseline spent)
MIN_ACTIONS = 40         # floor: tiny-baseline levels are noisy at any multiple
PARFREE_ACTIONS = 300    # fallback when no baseline is known for the level

ESCALATION_TEXT = """ESCALATION (level {level}: {spent} actions and {resets} self-resets without completing it):
this level is not yielding to live play. Binding directive until it completes:
 1. Inventory in notes.md BOTH what the log leaves unexplained AND the reachable
    places or states you have never visited. Unexplored territory outranks new
    mechanic hypotheses.
 2. Promote your checked rules into world_model.py and verify it retrodicts every
    recorded frame of THIS level (python tools/backtest.py --level {level}).
 3. Search the certified model (bounded) for a route to the goal. A timed-out
    search was too big -- never evidence that no route exists. If BFS exhausts the
    space, read its DIAGNOSIS line: a degenerate model is a bug; a genuinely
    explored graph means something real is missing -- an object, a state variable,
    an affordance of something you assumed was decoration. Frame-diff the
    animation residuals your model does not reproduce before enumerating more
    placements.
 4. If the rule you are missing is observable on an EARLIER level, go back for
    ground truth: commit [{{"name": "RESET", "full_reset": true}}] after a RESET,
    replay the levels you have modelled (nearly free with a certified model), and
    run the decisive experiment where the answer is visible.
Take live actions only as searched plans with computed predictions, or as single
probes that discriminate between model candidates. Do not repeat actions whose
outcome you can already compute."""

TIER2_TEXT = """ESCALATION 2: still stuck after simulating. Assume one of your rules is WRONG or a
region is unvisited: enumerate the frontier of states reachable under your model,
prefer plans that reach never-before-seen board configurations, and re-derive any
rule the search claims makes the goal unreachable."""


def stuck_signals(events: list[dict]) -> tuple[int, int, int]:
    """(current level, actions on it this attempt, self-issued RESETs on it).

    Mirrors commit.py's attempt segmentation: only events since the last
    full_reset count; a RESET that follows a GAME_OVER frame is forced, not chosen.
    """
    if not events:
        return 0, 0, 0
    start = 0
    for i, event in enumerate(events):
        if event.get("full_reset"):
            start = i
    segment = events[start:]
    level = segment[-1].get("level", 0)
    spent = resets = 0
    previous_game_over = False
    for event in segment:
        action = event.get("action")
        if event.get("prev_level", event.get("level")) == level and isinstance(action, dict):
            spent += 1
            if action.get("name") == "RESET" and not previous_game_over:
                resets += 1
        previous_game_over = bool(event.get("game_over"))
    return level, spent, resets


def tier(spent: int, resets: int, base: int = 0) -> int:
    """0 = not stuck, 1 = model-first directive, 2 = also assume a rule is wrong."""
    if base > 0:
        if spent >= max(ESCALATE_T2 * base, 2 * MIN_ACTIONS):
            return 2
        if spent >= max(ESCALATE_T1 * base, MIN_ACTIONS) or (
                resets >= ESCALATE_RESETS and spent >= max(1.5 * base, MIN_ACTIONS)):
            return 1
        return 0
    if spent >= 2 * PARFREE_ACTIONS:
        return 2
    if spent >= PARFREE_ACTIONS:
        return 1
    return 0


def directive(events: list[dict], baselines: list[int] | None = None) -> str:
    level, spent, resets = stuck_signals(events)
    base = baselines[level] if baselines and level < len(baselines) else 0
    current_tier = tier(spent, resets, base)
    if current_tier == 0:
        return ""
    text = ESCALATION_TEXT.format(level=level, spent=spent, resets=resets)
    if current_tier == 2:
        text += "\n" + TIER2_TEXT
    return text
