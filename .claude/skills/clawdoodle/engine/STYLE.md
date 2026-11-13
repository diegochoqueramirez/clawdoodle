# Style guide (distilled from the ten reference scenes)

Read this together with `VOCAB.md`. The scenes in `scenes/` are the ground truth: when in doubt, copy how they do it.

## Look
- **Flat, two tones.** Each object = fill colors + (optionally) one darker tone for edges/details. No gradients, highlights, glow or shadows.
- **Pale objects need an edge.** `white`/`paper` fills disappear on light slides, so give them a `gray` or `dark` border
  (see the documents in `searching`, the checklist in `tests`, the envelope in `network`).
- **Ladybug rule: iconic silhouette first.** The object must be recognizable at 1x without a caption (lens + red ladybug, key, padlock,
  hourglass, rocket). If a viewer would call it "a blob", redraw it with a clearer outline and 2-3 contrasting colors.
- **Palette:** named colors only. Clawd is always `body`; accents (`red yellow green blue orange`) go on the thing that matters most in the scene.
- **Cell size:** `px` 6 by default; 4-5 for small, detailed things (documents, checklist). At most two different `px` per scene.
  Clawd's body is ~12 cells, so a cabinet is ~14 cells tall, a card ~5, a key ~9.

## Layout
- Canvas 224-252 x 122. Clawd at `x 14, y 26` (feet on the ground line y = 112; the extra 26 on top leaves room for `cheer`).
- The main object sits on the right (x 130-230), standing on the ground unless it floats (bubble, bulb, lens, bug).
- Leave >= 2 units to every edge, **including while objects pulse or move** (the validator checks moves; pulse adds ~15% around the center).
- <= 3 objects. One idea per scene.

## Timing: four beats in 3.5-4.4 s
1. **Setup (0-0.6 s):** Clawd orients (`look_r`, `look_up`, `think`, `crouch`).
2. **Action (0.6-2.0 s):** the object does the thing (move, cycle frames, ticks, rocket).
3. **Payoff (~2.0 s):** one clear beat: `swap` to the result + `pulse` + Clawd `cheer`.
4. **Reset (~3.0 s):** Clawd back to `rest`, objects return, then 0.3-0.5 s of calm. One `blink` around the middle (not during the payoff).
Everything must end where it started (the validator checks the loop). Ease out going up / in coming down; 0.3-0.5 s for pose changes.

## Pitfalls we hit (so you do not)
- A `fromTo` fade applies its "from" state at creation: fixed in the engine (`immediateRender:false`), but never write fades by hand.
- `pulse`/`spin` use the object's *current* center (fixed); a hand-rolled scale would push moved objects off the canvas.
- `cheer` + `hop` together reach 46 units above Clawd: not enough headroom with `y:26`.
- Do not use `point_r` with a long reach next to a tall object: the arm is a flat bar and reads as a stray rectangle.
- Pale objects with no edge (white on cream) look like empty frames.

## Making an abstract topic readable WITHOUT text (lessons from six cold-start tests)
The six test GIFs were understood as sequences but scored only ~3/5 for a beginner. What was missing every time was the same:
1. **Clawd must DO the action, not watch it.** In 5 of 6 tests he only looked and cheered. Give him a verb: `hold_r` to hand something over, `point_r` at the thing that matters,
   `look_r` -> act -> react (`sad` when it fails, `relief` when it is fixed, `cheer` when it works). The reaction is the payoff beat.
2. **One color code through the whole scene.** blue = data/normal, green = ok, red = problem, yellow = attention/active. Never reuse a color for a different meaning, and never let two
   sprites of the same hue touch (they fuse into one blob).
3. **Show state with something countable.** A full/empty container, a gauge (`add-gauge`), N copies of the same thing (`clone`) beat an abstract change. If a beginner cannot count it, it is not explaining.
4. **Make the consequence visible in the payoff.** A red meter alone is not a consequence: add a reaction (shake, sad pose, something falling, a door closing). "Nothing happens" reads as "nothing matters".
5. **Show cause and effect with ONE clear change** per beat (color OR size OR position), and keep the other two still.
6. **Anchor with a familiar object** (mailbox, cabinet, trash can, hourglass, padlock) and make its state obvious (open/closed, full/empty). Unfamiliar shapes (a custom robot) need a beat to be introduced.
7. **Show before/after side by side** when the topic is a change (a clone of the object in its old state, faded to `light`).

Recipes by kind of topic (compose from the ten reference scenes):
| Topic kind | Composition |
|---|---|
| process (A becomes B) | one moving object that changes frame/color on the way (`drop` water cycle: same drop = vapor -> rain), Clawd points at each stage |
| accumulation / leak | a container with a gauge filling in steps, items clones entering it, a "should be emptied" object (bin) that stays empty and gets pointed at, red + shake at the end |
| gradual failure | the same object recolored step by step (`recolor`): green -> yellow -> red, with a sad pose at the end |
| counting and blocking (rate limit, quota) | N identical clones pass one by one; a gauge counts them; the (N+1)th is stopped by a barrier that closes (swap) and bounces back |
| copy and restore (backup) | original + clone in a lighter color; the original disappears/breaks (shake + disappear + sad), the clone returns to its place (`moveTo`) and relief |
| branch and merge | a line diagram built with `Grid.line` (sprite_tools), a dot (clone) walking each path, Clawd on the branch (a second Clawd is not possible: use a small Clawd-colored square) |
| learning / improving | the object's state variable (lamp, face) moves red -> green over repeated examples (clones arrive one by one); the end state stays visible for a beat |
