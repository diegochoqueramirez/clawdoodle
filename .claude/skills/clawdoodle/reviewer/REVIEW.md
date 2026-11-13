# Review checklist for generated Clawd GIFs

Run `python3 review_sheet.py out/Clawd-<Name>.gif` and LOOK at `sheet.png`, `zoom-1.png`, `zoom-2.png` and read `report.txt`.
Also freeze the scene at specific times with `index.html?scene=<name>&t=<seconds>` (serve the folder over http) when a frame needs a closer look.

## Must pass
1. Flat 2D: no shading, highlights, gradients or darker panels on Clawd or props. One body color, eyes black.
2. Clean joints: during every pose, no leg/arm/hand rectangle sticks out of the body in a way that reads as a glitch
   (check the leg-body junction on both sides in the leaned pose, and hands vs body edge).
3. Eyes stay put: blink swaps to "^ ^" arcs in the same position; eyes never drift with the body lean.
4. Nothing clipped: no part of Clawd or props touches the canvas edge (report.txt says so too).
5. Props read at a glance and nothing floats: hands reach what they touch, objects rest on the desk/ground.
6. Loop is seamless: loop seam near 0, no pop at the end -> start.
7. Motion: no jumps (largest frame-to-frame change is a smooth peak, not a spike); poses ease in and out; holds feel intentional.
8. Transparent background has no dark halos on light backgrounds (view sheet on the light bg and check edges).
9. Only rects, one palette, no tweened shapes (see README rules).

10. Attached limbs: a hand/arm that is moved relative to the body (reach) must stay connected (bridge rect), never float with a gap.
    Check every frame of the pose-in/pose-out, not only the peak. Hands that "type" must touch the target on the tap and hover <= 2 units otherwise.
11. Rest pose after any pose round-trip must equal frame 0 exactly (report: "character half only" seam = 0).
12. Margin: keep >= 2 grid units between any part (including hands at rest) and the canvas edge.

Known cosmetic limit: with crispEdges, a rotated rect over another rotated rect can show a 1px notch at the joint (e.g. left hand/body). Style/renderer limit, not fixed.

## Report format
List each problem with: where (time/frame), what you see, and the fix (file + value). Then apply the fixes in `svg/`,
re-export, re-run the review and say what changed. If something is a style choice rather than a bug, flag it and do not change it.

## Added for generic sprites (Phase 1)
13. Drawn objects read at a glance at 1x (not only zoomed): a viewer should name the object without a caption. If not, redraw the grid.
14. Objects use the named palette only and the same flat style as Clawd (no gradients, highlights, outlines with different thickness).
15. Scale is believable next to Clawd (a cell is ~6 units; Clawd's body is ~12 cells) and objects that should stand on the ground do.
16. Every object that appears, moves or changes frame returns to its start state before the loop restarts (`validate_scene.py` warns, but check the frames).
17. Hands/arms: in `point_r` the right arm stretches into a long flat bar; judge whether it reads as an arm or as a stray rectangle in this scene.
18. `validate_scene.py` warnings about overlaps may be intentional (a card inside a drawer, a lens over a bug); decide, do not just silence them.

## Added in Phase 2
19. Style fidelity to `engine/STYLE.md`: flat two-tone objects, pale objects with an edge, <= 2 `px` sizes, <= 3 objects, four beats (setup / action / payoff / reset).
20. Each object is recognizable at 1x without a caption; if it reads as a blob or an empty frame, redraw it.
21. Nothing touches the canvas edge in any frame, including while pulsing or moving (run `review_sheet.py` and also check the bottom edge by eye).
22. A hidden object really appears (it must be visible in the middle of the loop): check frames, not only the validator.

## Added in Phase 3 (visual pass over the ten reference scenes)
23. Sample the loop by TIME, never by frame index: exported GIFs drop duplicate frames and use variable frame durations
    (a 4 s loop can be 46 frames), so `frames[::k]` silently misses the end of the loop. `review_sheet.py` is time-based; custom grids must be too.
24. Rotating/spinning/pulsing props (hourglass flip, lens pulse) grow their bounding box: check the bottom and top margin at the worst moment
    (`review_sheet.py` now prints min margin L/T/R/B incl. bottom; < ~4 units is flagged). Fix with a small `hop`, a lower `pulse` scale or a higher start `y`.
25. Pale props need an edge also when they overlap something dark only part of the time (a card half out of a cabinet sits on the light background).
26. A small iconic detail must not read as a face: dots + a "v" inside a rectangle look like eyes and mouth. Draw the envelope flap as a long V from the top corners.

## Added in Phase 5 (cold-start tests)
27. Run `clawd.py sprite-preview` and look at the cream / white / dark rows: a part that vanishes on one of them needs an edge or another color; magenta cells are missing palette entries.
28. Clawd performs the action (hold / point / react), not just looks and cheers; the payoff shows a consequence (sad / relief / shake / something falling), not only a color change.
29. One color code, no two same-hue sprites touching, state shown with something countable (gauge, clones, full/empty).
30. `export-svg --verify` says OK. A MISMATCH usually means two moves of the same object overlap in time (the validator warns): fix the scene.
