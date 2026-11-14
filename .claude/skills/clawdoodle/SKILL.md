---
name: clawdoodle
disable-model-invocation: true
description: Creates a flat 2D pixel-style GIF of Clawd (the Claude Code mascot) acting out a topic or description the user gives (any topic, via a visual metaphor), reviews it with a separate reviewer agent, and refines it from conversational feedback (change topic, add/remove an object, slower, undo). Use when the user asks for a Clawd GIF or animation, or wants to explain a concept visually with the mascot.
---

# clawdoodle

The user describes a topic ("Clawd explaining what a cache is"). You turn it into a short looping GIF of Clawd doing something that stands for the topic,
check it yourself (and, for new drawings, with an optional reviewer agent), deliver it, and then edit it from the user's feedback ("slower", "add a book", "another topic", "undo").
Plan and status: `docs/clawdoodle-skill-design.md` at the repo root. Engine: `engine/` (SVG + GSAP rendered with headless Chrome, Pillow for the GIF).

**Deliverables:** a GIF and an animated SVG (a single self-contained `.svg`, no JavaScript, works in `<img src>`, browsers and HTML presentations). The SVG is baked from the GSAP timeline sampled at 60 fps and written as CSS keyframes.

## Paths (set once per run)
`SKILL_DIR` = the folder holding this file. Run every command through the cross-platform launcher: `python "$SKILL_DIR/scripts/run.py" <command> [args]` (on Windows `py "%SKILL_DIR%\scripts\run.py" ...`; use `python3` where `python` is missing). It picks the venv Python (`engine/.venv/bin/python` or `engine\Scripts\python.exe`) by itself. Below, `clawd <command>` means exactly that launcher call. Do not store the command in a shell variable (zsh does not word-split it): in bash/zsh define a function `clawd() { python3 "$SKILL_DIR/scripts/run.py" "$@"; }`; in PowerShell `function clawd { py "$SKILL_DIR\scripts\run.py" @args }`. To start a project over use another slug or `revert`; do not delete project folders.
**Timing (one render at a time, measured):** `render` (preview + review pack) ~30 s, `render --final` (GIF + animated SVG) ~50 s, `export-svg --verify` ~10 s. Several renders in parallel slow each other down a lot (6 at once took minutes): run them one after another, and run any command expected to pass your shell tool's timeout (often 120 s) in the background. `render` prints `rendered ...` only when it is done; the old `review/grid.png` is deleted at the start of each preview render, so if it is missing the render has not finished.

Run everything from the user's working directory; projects live in `./clawdoodles/<slug>/` (see below). First time on a machine: `python3 $SKILL_DIR/scripts/setup.py` (Windows: `py $SKILL_DIR\scripts\setup.py` or `setup.ps1`; macOS/Linux also `setup.sh`), then `clawd doctor` must say OK.

## Project layout (managed by `clawd.py`, do not hand-build paths)
`clawdoodles/<slug>/scene.json` (the only file you edit), `versions/vN.scene.json (+ vN.gif, vN.svg)`, `out/preview.gif`, `out/final.gif`, `out/final.svg`, `review/` (grid.png, sheet.png, zoom-*.png, report.txt).

## Workflow
1. **Understand.** Pick ONE visual metaphor for the topic (<= 3 objects, one idea, 3.5-4.4 s loop). Ask a single short question only if the topic is ambiguous
   and the answer would change the picture; if no metaphor is obvious, offer two and let the user choose. Read `engine/VOCAB.md` and `engine/STYLE.md`.
2. **Start from the closest example, or from scratch.** `engine/scenes/README.md` lists 11 worked scenes. `clawd new <slug> --from <example>` copies one (use it when the new topic has the same shape: a container filling, an object travelling, a state changing; then replace the sprites and the timeline); `clawd new <slug>` gives an EMPTY scene (232x122, loop 3.6 s, no props) for a topic with no close example. Then edit `scene.json`:
   new objects are `sprite` grids with named colors; start from a template when one fits (`clawd templates`, `add-sprite`, `add-gauge`, `clone`) and build lines/diagrams with `engine/sprite_tools.py`.
   **Before rendering, look at every sprite you drew:** `clawd sprite-preview <slug>` writes a zoomed PNG per sprite (cream / white / dark rows, magenta = missing palette entry) in seconds; open it with Read. Keep the four beats (setup / action / payoff / reset), make Clawd perform the action (see `engine/STYLE.md`, "Making an abstract topic readable WITHOUT text"), and make everything return to its start.
3. **Check and preview.** `clawd check <slug>` (fix every error; take warnings seriously), then `clawd render <slug>` (preview, ~30 s; it also builds the review pack).
   LOOK at `review/grid.png` yourself (open it with Read) before involving the reviewer: do not outsource obvious problems.
4. **Self-review (default) / reviewer agent (optional).** The default review is yours: automatic checks (`check`, the margins and seam in `review/report.txt`) plus LOOKING at
   `review/grid.png` (and `zoom-*.png` when a pose or joint is in doubt) with the checklist in `reviewer/REVIEW.md`. Fix what you see and re-render. This is what runs every time.
   Launch the **reviewer agent** (second pair of eyes, ~1-15 min) ONLY when (a) you drew new objects or poses from scratch (new sprites are where the real bugs were: pale objects with no edge,
   things that read as something else, parts that almost clip), or (b) the user asks ("review it thoroughly", "revísalo a fondo"). To launch it: read `reviewer/AGENT_BRIEF.md`, fill the placeholders
   (`PROJECT_DIR SLUG TOPIC METAPHOR ROUND LANG SKILL_DIR PY WORKDIR USER_NOTES`; `PY` = the Python of `engine/.venv`, `bin/python` or `Scripts/python.exe`) and use the Agent tool (`subagent_type: general-purpose`). When it returns, re-run `clawd render <slug>`, open
   `review/grid.png` and confirm; do not trust the report blindly. Up to 3 rounds. Do NOT launch it for small edits (retime, remove, recolor) or for scenes copied almost unchanged from an example.
5. **Save and deliver.** `clawd render <slug> --final` (~50 s: GIF at scale 4 / 33 fps, plus the animated SVG), `clawd save <slug> -m "<what this version is>"`.
   Then run `clawd export-svg <slug> --verify` (~10 s): it compares the animated SVG with the GIF render at 8 moments and must say OK; a MISMATCH means the animation is order-dependent (usually two overlapping moves of the same object): fix the scene, do not ship. Tell the user (in their language): the GIF and SVG paths (`clawdoodles/<slug>/out/final.gif` and `final.svg`; the SVG is ~20-100 KB and is the better choice for HTML presentations: `<img src="final.svg">`), the metaphor chosen and why (one line), what the reviewer changed, known caveats, and that they can ask for changes.
6. **Corrections.** Always edit `scene.json` (never the GIF), then repeat from step 3 (steps 4-5 apply to every change that alters the picture):

| The user says | Do |
|---|---|
| "another topic / change the theme" | new project: `clawd new <new-slug> --from <closest example>`; keep the old one |
| "slower / faster" | `clawd retime <slug> --factor 1.25` (slower) or `0.8` (faster); it auto-saves the previous state |
| "remove the X" | `clawd remove <slug> <id>` (also removes every step that targeted it) |
| "add a X" | draw a new `sprite` (+ its timeline steps); if that makes more than 3 objects, say so and propose what to drop |
| "bigger / smaller" | ask which: image resolution (`render --scale N`) or object size (`px` of the sprite / `clawd` position) |
| "change the color of X" | edit that sprite's `palette` (named colors only) |
| "undo / go back" | `clawd versions <slug>` then `clawd revert <slug> <N>` (current state is saved first) |
| "what changed?" | `clawd diff <slug>` |

## Guardrails
- Never skip `check`, and never read `review/` files that predate the last `render` (`check` prints a NOTE when the pack is older than `scene.json`); never deliver without LOOKING at the time-sampled grid (index-sampled frames miss most of the loop because GIFs drop duplicate frames).
- Style is fixed: flat 2D, no shading/highlights, one body color, named palette, only rectangles, blink as "^ ^" arcs, no text inside the GIF, transparent background,
  nothing touching the canvas edge (also while pulsing/moving), seamless loop. Do not invent poses or actions outside `engine/vocab.json`.
- The reviewer agent (when used) edits only the project's `scene.json`; you own `save`, final renders and the message to the user.
- Reply to the user in their language; keep delivery messages short.

## Commands (full list: `clawd --help`)
`new [--from ex]` `list` `check` `render [--final] [--scale N] [--fps N] [--no-svg]` `export-svg [--verify]` `review-pack` `sprite-preview [id]` `templates` `add-sprite` `add-gauge` `clone` `palette` `save -m` `versions` `diff [A [B]]` `revert N` `retime --factor F` `remove <id>` `doctor`.
Lower-level tools (rarely needed): `engine/validate_scene.py`, `engine/export_gif.py`, `engine/bake_svg.py`, `engine/review_sheet.py`, `engine/frames_grid.py`; interactive preview: serve `engine/` over http and open `index.html?src=<scene url>`.
