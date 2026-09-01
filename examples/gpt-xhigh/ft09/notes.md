# Lab notebook

## Status

- **WIN: 6/6 levels complete, 75 total real actions.**
- Per-level actions vs human baseline:
  - L0: 4 vs 43
  - L1: 7 vs 12
  - L2: 14 vs 23
  - L3: 16 vs 28
  - L4: 21 vs 65
  - L5: 13 vs 37
- Every level beat its baseline enough to hit the per-level 1.15 score cap.
- Only `ACTION6` (click) is legal.

## Object/rule hypothesis

- All meaningful graphics use 2x2 physical-pixel units.
- Three small static examples each contain a 3x3 macro-grid. Their central
  6x6 glyph has a color-8 center and four color-2 clue pixels; the eight outer
  macrocells are color 8/9.
- Confirmed across all three examples: each clue position maps independently
  to the outer cell at the same compass position: clue color 2 -> outer color
  9, clue color 0 -> outer color 8.
- Purple (color 4) lower-right panel is the editable query. Its clue is
  `.22/.8./.22`, so desired outer ring is `899/8?8/899`.
- Current query ring is all 9. Required changes: NW, W, E, SW -> color 8.

## Experiment/model

- Action 1: clicked NW at `(38,38)`. The full 6x6 macrocell toggled 9 -> 8,
  confirming whole-tile semantics. No other board cells changed.
- Every click also changes the two rightmost remaining color-12 footer cells
  to color 11. This caused the only prediction mismatch; now modeled as an
  action meter.
- Remaining solution clicks: W `(38,46)`, E `(54,46)`, SW `(38,54)`.

## Level 1

- Background/palette changed. Two vertically overlapping clue puzzles:
  - clue 1 `.22/.c./.2.`
  - clue 2 `.2./2c2/..2`
- Generalized mapping: color 2 -> alternate/ring color 9; color 0 -> the
  clue's center/base color (now 12). Thus level 0's apparent 8/9 binary rule
  was color-relative.
- Shared outer row agrees for both clues. Seven unique all-9 macrocells should
  change to color 12: top NW; upper W/E; shared NW/NE; bottom SW/S.
- Top-right 4x4 color-9 and color-12 swatches may be a palette or legend.
  Next discriminating/useful experiment: click top NW target at `(22,16)`.
  Direct-tile semantics predicts the whole 6x6 tile changes 9 -> 12. A
  selection-required UI would instead leave it unchanged.
- Action 5 confirmed direct toggling: `(22,16)` changed the whole tile 9 -> 12
  plus the two-cell footer tick, exactly as predicted. Swatches are a legend;
  no palette selection is required.

## Level 2

- Level 1 solved in 7 actions (baseline 12).
- Palette is now colors 8/12. Four overlapping clues: top/bottom centers use
  12; left/right centers use 8. Initial outer graph is all color 8.
- Therefore alternate color must be inferred level-wide, not merely from each
  clue's current ring: each clue maps color-2 positions to the *other* palette
  color and blank positions to its own center color.
- BFS found 14 unique corrections. First required click `(22,6)` confirmed the
  8 -> 12 board toggle exactly. Counterexample was footer-only: this denser
  level uses fractional cadence rather than the 2 pixels/click used in levels
  0-1. First four corrections produced cumulative footer fills `1,1,2,3`,
  i.e. increments `1,0,1,1`. This fits exact cumulative schedule
  `floor((2*n+1)/3)` for correction count `n`; model derives `n` from the
  initial 14 mismatches and current board. Fingerprint: upper-right color-8
  swatch.

## Level 3

- Level 2 solved in 14 actions (baseline 23).
- Upper-right swatches now expose an ordered 3-color palette: `9, 8, 12`.
- Three overlapping clues have centers 12, 9, 12. Color 8 occurs only in the
  palette.
- Killed hypothesis: clue-2 takes the center color's cyclic successor. Shared
  tiles between center-12 and center-9 clues demanded conflicting successors.
- Consistent rule: clue-2 means the outer tile must *differ* from center;
  blank means it must equal center. In 2-color levels, "different" happened
  to select the unique other color. Shared `!=12` and `!=9` constraints now
  force third color 8.
- Click transition still cycles the ordered palette. Thus current 9 tiles
  forced to 8 take one click; equality-to-12 tiles take two
  (`9 -> 8 -> 12`).
- First level-3 click at `(22,16)` confirmed `9 -> 8` exactly. Only miss was
  footer cadence: real advanced 1 pixel, not the level-1 2 pixels implied by
  the same top color. Second click `8 -> 12` changed no footer pixel.
- This repeats level 2's `1,0,...` prefix. Unified complex-board hypothesis:
  cumulative footer fill is `floor((2*n+1)/3)` where `n` is palette-cycle
  clicks. `n` is derivable along the no-wrap BFS path by summing each outer
  tile's palette index relative to the initial first-color board.

## Level 4

- Level 3 solved in 16 actions (baseline 28).
- Editable swatches moved left and are `14,15` (`e,f`); swatch detection must
  scan the top edge rather than assume x=60.
- New clue marker 3 means the corresponding ring position is absent/non-tile:
  it exactly marks board boundaries and neighboring clue cells. Ignore it.
- Killed hypothesis: checker `e6e/6e6/e6e` is a locked effective-color-6
  tile. After all 9 plain mismatches were corrected, game did not level up;
  the only remaining blue edges point to the three checker tiles.
- Revised: 6 is preserved texture overlay and e is the editable base color.
  First checker click revealed its full transition: it cycles the checker
  base plus the four orthogonally adjacent macrocells. Overlay 6 remains.
  Observed change was four full 36px tiles + checker’s 20 base pixels + one
  footer pixel = 165. This is a plus-switch, not an isolated tile.
- Parser now permits clue outer markers `{0,2,3}`, validates only non-3 ring
  positions, and reads checker tiles by effective fixed color 6.
- Eight clues produce 29 constrained tiles; 9 plain-e tiles are unsatisfied.
  First required `(32,6)` toggled e -> f exactly, validating parser/palette.
  Footer increments on first two corrections were `0,1`, killing provisional
  2/9 scaling. Third click also advanced 1, but clicks 4-5 advanced `0,0`,
  killing the provisional 2/3 schedule. Full observed prefix is
  `0,1,1,0,0`; click 6 advanced 1, killing a five-click repetition.
  Current post-initial phase hypothesis is `1,1,0,0` repeated, predicting
  clicks 7-9 increments `1,0,0`. Model uses explicit cumulative fill keyed by
  e/f tile progress.
- Clicks 7-9 matched `1,0,0`; footer cumulative is 4. Three textured tiles
  remained. First textured click advanced footer to 5; two textured switches
  remain. Candidate policy now prioritizes side-effecting switches, then
  repairs plain constraints.
- All three switches verified. Their changed-cell counts reflect valid
  orthogonal neighbors: 165, 129, 164 including footer where applicable.
  After switches, exactly 9 plain mismatches remain. Footer phase is again
  derivable: action count `12 + (9 - remaining)` on canonical cleanup;
  continue observed post-initial increment cycle `1,1,0,0`.
- Level 4 solved in 21 actions (baseline 65).

## Level 5

- Final level palette is `11,14` (`b,e`).
- Most editable tiles carry texture `b6b/bbb/bbb`: overlay 6 at north
  microposition only. General rule from level 4: overlay positions encode
  which neighboring macrocells a click also cycles. Level-4 checker therefore
  encoded N/W/E/S; level-5 tile encodes N.
- Generalized texture parser returns base color plus arbitrary overlay
  directions. Click cycles center and all encoded-direction neighbors,
  preserving each tile's own overlay.
- For N-directed binary switches, process mismatches bottom-to-top: a lower
  click can disturb north, while later northern clicks repair it. Candidate
  ordering uses switch-direction projection.
- This layout fingerprints the final level. Terminal reality sets both
  `win=True` and `level_up=True`; non-final solved boards set only level-up.
- BFS found a 13-click bottom-up win path. First click `(22,40)` confirmed the
  N-only board effect exactly; only footer differed. Real increment was 0,
  matching level 4's late-level phase.
- Final footer phase is made grid-derivable by matching the current binary
  constraint-tile signature against the 13 canonical switch origins. Use the
  established cumulative `0,1,2,2,2,3,4,...` fill sequence.
- The 13-action plan executed to terminal WIN. Final action `(6,8)` was
  predicted as win; final audit supplied the engine nuance that both win and
  level-up flags are true on the terminal transition.

## Final mechanics

- Outer micro-marker 0: neighboring macrocell must equal clue center color.
- Outer micro-marker 2: neighboring macrocell must differ from clue center.
- Outer micro-marker 3: absent/non-tile direction; no constraint.
- Upper swatches give ordered editable palette; clicking cycles one step.
- Texture overlay 6 positions encode additional macrocells toggled by a click;
  center tile always toggles too. Overlay pixels remain unchanged.
- Multiple clues merge into equality/inequality CSP constraints. With 3
  palette colors, intersecting inequalities may force the third color.
- Solve side-effecting switch boards in dependency order (e.g. bottom-up for
  north-directed switches), then repair plain cells. Full-history backtest is
  the certification boundary.
