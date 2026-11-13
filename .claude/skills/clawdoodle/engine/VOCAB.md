# Scene vocabulary (what a scene may use)

Source of truth for names: `vocab.json` (checked against the JS by `validate_scene.py --selftest`). Always run
`python3 engine/validate_scene.py <scene>` before exporting; errors block the export, warnings are real risks.
Tools that save you from counting characters by hand: `clawd.py templates`, `add-sprite`, `add-gauge`, `clone`, `sprite-preview`, `palette` (see "Helpers" below).

## Scene file (`*.scene.json`)
```jsonc
{
  "name": "Thinking",                       // output: Clawd-<name>.gif
  "meta": { "topic": "...", "metaphor": "..." },   // optional, for humans
  "canvas": { "w": 232, "h": 122 },         // scene units. `clawd.py new` starts at 232 x 122 / loop 3.6; widen w freely (240-252) when objects sit far right
  "loop": 3.6,                              // seconds (1-8). The timeline is padded to exactly this.
  "clawd": { "x": 14, "y": 26 },            // top-left of Clawd
  "props": [ ... ],                         // objects (draw order = list order; "layer":"front" draws over Clawd, default "back" behind him)
  "overlap_ok": [["pad", "rocket"]],        // optional: sprite pairs that are meant to overlap (silences that warning)
  "timeline": [ { "at": 0.2, "action": "pose", ... }, ... ]   // processed in chronological order
}
```

## Geometry cheat sheet (scene units)
- Clawd: body 78 x 52 at (x+14, y+12); hands reach x-8 .. x+114; feet at y+86 (the ground line). Leave >= 2 units to every canvas edge.
- **Safe x for the first object on the right: `clawd.x + 120`** (the hands reach `x+114`; with `lean`/`point_r`/`hold_r` they reach ~`x+128`). With `clawd.x = 14` start objects at x >= 134.
- Pose reach beyond that: cheer +34 up, wave +28 up, think +22 up, point_r +14 right, hold_r +12 right, lean +12 right.
- A sprite cell is `px` units (**default 6**, so 12 cells = 72 units = Clawd's body width). Use `px` 4-5 for small detailed things.
- Put an object on the ground with `y = clawd.y + 86 - rows*px` (or `--ground` in `clawd.py add-sprite`).

## Props
| type | fields |
|---|---|
| `sprite` | `id, x, y, px?=6, palette{char:colorName}, rows[] or frames[[...],[...]], hidden?, layer?` (each sprite has its OWN palette: the same character may mean different colors in two sprites) |
| `desk` | `x, y, w?=148` (top slab + legs down to the ground) |
| `keyboard` | `x, y` (40x6, 5 keys) |
| `crt` | `x, y, seed?` (88x66 monitor with scrolling code lines and a cursor) |

### Drawing a sprite
`rows` is a list of equal-length strings, one character per cell; `.` or space = transparent. `palette` maps each character to a **named color** (24):

| name | hex |
|---|---|
| `body` | `#DD775B` |
| `ink` | `#1A1A1A` |
| `white` | `#F7F4EE` |
| `paper` | `#F2EBDD` |
| `light` | `#C9C5BD` |
| `gray` | `#8C8C8C` |
| `steel` | `#5E5E5E` |
| `dark` | `#3A3A3A` |
| `brown` | `#8A6340` |
| `red` | `#E5484D` |
| `orange` | `#F2994A` |
| `yellow` | `#F5C542` |
| `green` | `#3DDC6E` |
| `mint` | `#7CFF9B` |
| `teal` | `#3CB8B0` |
| `sky` | `#9CCBF2` |
| `blue` | `#4C8DF6` |
| `purple` | `#9B6DF0` |
| `pink` | `#F28BB8` |
| `screen` | `#0D1A12` |
| `rose` | `#F29B9B` |
| `forest` | `#2F8F5B` |
| `navy` | `#2D4A8A` |
| `silver` | `#B0B0B0` |

(`clawd.py palette` writes `engine/palette.png` with swatches.) Hex colors work but trigger a warning; stay in the palette so every scene looks like the same family.
Rules: flat colors only (no gradients, highlights or shadows); at most 40x40 cells; **<= 3 objects per scene** (the validator warns above 3; clones of one sprite count once);
every frame of a multi-frame sprite has the same size. No text or numbers inside the GIF (a style rule): show quantities with gauges/counts of objects and states with color.
Example (a 5x4 card): `"rows": [".rrr.", "ppppp", "pgggp", "ppppp"], "palette": {"p":"paper","r":"red","g":"gray"}`.
Use `hidden: true` for objects that appear later (and make them disappear again before the loop ends). Merging two actors into one sprite (a sun inside the cloud sprite) is fine to save an object slot.

## Actions (`"at"` = start second; steps may be listed in any order, the engine sorts them by `at`)
Clawd: `pose{pose,dur?=0.4,ease?,bodyEase?}`, `wave{count?,dur?,amp?}`, `blink{hold?}`, `type{target:keyboard,taps[],pose?}`.
Screens: `scroll{target:crt,dur?}`, `cursor{target:crt,every?}`.
Any sprite id or `"clawd"` (all work from the object's nominal position, so they compose; the result does not depend on how the animation is played):
- `move{dx,dy,dur?=0.4,ease?,back?,hold?}`: slides by (dx, dy) from where the object is at `at`. **Without `back` it stays there** (the next move continues from there); with `back: true` it returns after waiting `hold` seconds (return takes `dur` too). It is fine to do out and back as two separate moves.
- `moveTo{x?,y?,dur?=0.4,ease?,back?,hold?}`: go to an ABSOLUTE scene position (the sprite's top-left; Clawd's top-left for "clawd"). `dur: 0` teleports (reset a hidden object).
- `hop{h?,dur?,count?}`, `shake{amp?,count?,dur?}`, `bob{amp?,every?,dur?}`, `pulse{scale?,dur?}`, `spin{turns?,steps?,dur?}`, `appear{fade?}`, `disappear{fade?}`.
- `recolor{map:{"<char>":"<color>"},dur?}`: change the color of every cell drawn with a palette character, without redrawing frames (a lamp red -> green). Put it back before the loop ends.
Multi-frame sprites: `swap{frame}`, `cycle{frames[],every,dur?,end?}`.
Poses: `rest lean look_l look_r look_up wave point_r think shrug cheer crouch sad relief hold_r`. `sad` = slumped, eyes down, arms hanging; `relief` = slumped with a hand to the forehead (wiping it); `shrug` and `cheer` have both hands up.
- `hold_r` extends the right hand a little (hand center about `(clawd.x + 109, clawd.y + 49)`): place a sprite there to make Clawd hold or hand over an object.

Two moves of the same object must not overlap in time (the validator warns): the later one wins while they overlap and the result is hard to predict.

## Loop rules (the validator checks these)
Everything must end where it started: last pose = `rest`; every displacement is undone (a `move` with `back`, or a move that returns it); things that `appear` must `disappear`;
multi-frame sprites end on frame 0; recolors are put back; nothing may run past `loop`. Use ~0.4 s for pose changes, ease out going up and in coming down, keep a
blink (`^ ^`) around the middle of the loop, and leave 0.3-0.5 s of calm at the end so the loop reads as a loop. Start the next pose after the previous one ends.

## Helpers (run with `clawd.py`; they only edit `scene.json`)
- `templates`: faces (happy/neutral/sad frames), check, cross, cloud, drop, sun, document, folder, arrow_right, arrow_down. `add-sprite <slug> <template> --at X Y [--id ID] [--px N] [--colors w=light] [--ground] [--hidden] [--layer front]`.
- `add-gauge <slug> <id> --cells 6 --at X Y [--color green] [--vertical]`: a segmented bar with frames 0..N; set the value with `swap`.
- `clone <slug> <id> --as NEW --at X Y [--hidden]`: an independent copy (a second envelope, more raindrops). Give each clone its own steps.
- `sprite-preview <slug> [id]` or `--template NAME`: zoomed PNG of the frames on cream, white and dark backgrounds, in seconds. Look at it before rendering: a pale part with no edge disappears on one of the rows; magenta cells = a character with no palette entry.
- For lines, diagonals, arrows and diagrams build the grid by code with `engine/sprite_tools.py`: `Grid.line/rect/circle/paste`, `gauge_frames`, `write_sprite(scene_path, id, palette, rows=..., x=, y=)` (insert/replace the sprite in a scene), `cell_to_xy(...)` (scene position of a cell, to move another object onto it). See its docstring.

## Metaphor starters (pick ONE per scene, <= 3 objects)
Eleven worked examples are listed in `scenes/README.md` (computing, thinking, database, debugging, searching, tests, deploy, waiting, security, network, cache).
Not covered yet (design them in the same style): memory = notebook / sticky notes, planning = map or route, monitoring = gauge,
data pipeline = conveyor belt, errors = warning triangle, permissions = badge or door. Recipes for abstract topics (process, accumulation, gradual failure,
counting and blocking, copy and restore, branch and merge) are in `STYLE.md`. Art conventions and timing structure: `STYLE.md`.
