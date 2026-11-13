#!/usr/bin/env python3
"""Validate a Clawd scene before rendering. Pure Python (no Pillow).

Usage: python3 validate_scene.py <scene.json> [--strict]     exit 1 on errors (2 on warnings with --strict)
       python3 validate_scene.py --selftest                  checks vocab.json against the JS engine (no drift)

Errors block the export. Warnings are real risks (clipped at the edge, loop jump, overlaps, off-palette color).
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOCAB = json.loads((HERE / "vocab.json").read_text())
# Clawd geometry in scene units (see clawd.js): hands reach x-8 .. x+114, body top y+12, feet y+86.
CLAWD = {"l": -8, "r": 114, "top": 12, "bottom": 86, "body": (14, 12, 92, 64)}
HEX = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(spec):
    E, W = [], []
    lim = VOCAB["limits"]
    if not isinstance(spec, dict):
        return ["scene must be a JSON object"], W
    for k in ("name", "canvas", "loop", "clawd", "timeline"):
        if k not in spec:
            E.append(f"missing required key '{k}'")
    if E:
        return E, W
    cw, ch = spec["canvas"].get("w"), spec["canvas"].get("h")
    if not (_num(cw) and _num(ch)) or not (0 < cw <= lim["canvas_max"] and 0 < ch <= lim["canvas_max"]):
        E.append(f"canvas.w/h must be numbers in (0, {lim['canvas_max']}]")
        return E, W
    loop = spec["loop"]
    if not _num(loop) or not (lim["loop_min"] <= loop <= lim["loop_max"]):
        E.append(f"loop must be between {lim['loop_min']} and {lim['loop_max']} seconds")
        return E, W
    if loop > 5.5:
        W.append(f"loop is {loop} s: loops longer than ~5 s read as slow and heavy (typical 3-4.5 s); cut dead time or split the idea")
    cx, cy = spec["clawd"].get("x"), spec["clawd"].get("y")
    if not (_num(cx) and _num(cy)):
        E.append("clawd.x / clawd.y must be numbers")
        return E, W

    boxes = {}          # id -> (x0,y0,x1,y1) base box
    kinds = {"clawd": "clawd"}
    hidden = {}
    nframes = {}
    palettes = {}
    recolors = []   # (at, target, char, color)
    ids_seen = set()
    margin = lim["margin"]

    def in_bounds(name, b, extra=(0, 0, 0, 0)):
        x0, y0, x1, y1 = b[0] - extra[0], b[1] - extra[2], b[2] + extra[1], b[3] + extra[3]
        if x0 < margin or y0 < margin or x1 > cw - margin or y1 > ch - margin:
            W.append(f"{name} reaches outside the canvas safe area (box {x0:.0f},{y0:.0f}..{x1:.0f},{y1:.0f}, canvas {cw}x{ch}, margin {margin}): it may be clipped")

    for i, p in enumerate(spec.get("props", [])):
        t = p.get("type")
        where = f"props[{i}]" + (f" ({p.get('id')})" if p.get("id") else "")
        if t not in VOCAB["props"]:
            E.append(f"{where}: unknown prop type '{t}' (known: {', '.join(VOCAB['props'])})")
            continue
        for r in VOCAB["props"][t]["required"]:
            if r not in p:
                E.append(f"{where}: missing '{r}'")
        if "one_of" in VOCAB["props"][t] and not any(k in p for k in VOCAB["props"][t]["one_of"]):
            E.append(f"{where}: needs one of {VOCAB['props'][t]['one_of']}")
        if "x" not in p or "y" not in p:
            continue
        pid = p.get("id")
        if pid:
            if pid in ids_seen or pid == "clawd":
                E.append(f"{where}: duplicate or reserved id '{pid}'")
            ids_seen.add(pid)
            kinds[pid] = t
            hidden[pid] = bool(p.get("hidden"))
        x, y = p["x"], p["y"]
        if t == "desk":
            b = (x, y, x + p.get("w", 148), cy + CLAWD["bottom"])
        elif t == "keyboard":
            b = (x, y, x + 40, y + 6)
        elif t == "crt":
            b = (x, y, x + 88, y + 66)
        else:  # sprite
            frames = p.get("frames") or [p.get("rows")]
            if not all(isinstance(f, list) and f and all(isinstance(r, str) for r in f) for f in frames):
                E.append(f"{where}: rows/frames must be lists of strings")
                continue
            wid = {len(r) for f in frames for r in f}
            hei = {len(f) for f in frames}
            if len(wid) != 1 or len(hei) != 1:
                E.append(f"{where}: all rows and frames must have the same size (widths {sorted(wid)}, heights {sorted(hei)})")
                continue
            w_c, h_c = wid.pop(), hei.pop()
            if w_c > lim["sprite_dim_max"] or h_c > lim["sprite_dim_max"] or w_c * h_c > lim["sprite_cells_max"]:
                E.append(f"{where}: sprite too big ({w_c}x{h_c} cells; max {lim['sprite_dim_max']} per side / {lim['sprite_cells_max']} cells)")
            pal = p.get("palette", {})
            used = {ch_ for f in frames for r in f for ch_ in r if ch_ not in ". "}
            for ch_ in used:
                if ch_ not in pal:
                    E.append(f"{where}: character '{ch_}' has no palette entry")
            for ch_, cn in pal.items():
                if cn in VOCAB["palette"]:
                    continue
                if HEX.match(str(cn)):
                    W.append(f"{where}: color '{cn}' for '{ch_}' is outside the closed palette ({', '.join(VOCAB['palette'])}); prefer a named color")
                else:
                    E.append(f"{where}: unknown color '{cn}' for '{ch_}'")
            px = p.get("px", 6)
            b = (x, y, x + w_c * px, y + h_c * px)
            if pid:
                nframes[pid] = len(frames)
                palettes[pid] = pal
        if pid:
            boxes[pid] = b
        elif t == "sprite":
            boxes[f"props[{i}]"] = b
        in_bounds(where, b)

    # Clawd base box
    cb = (cx + CLAWD["l"], cy + CLAWD["top"], cx + CLAWD["r"], cy + CLAWD["bottom"])
    boxes["clawd"] = cb

    # Timeline
    names = set(kinds)
    reach = {"l": 0, "r": 0, "u": 0, "d": 0}
    pose_events, vis_events, frame_events = [], {}, {}
    grow = []     # (target, at, extra_x, extra_y): pulse/spin enlarge the bounding box around the object's center
    mv_steps = []  # (at, index, action, step): processed in chronological order below, with the same position model as the engine
    used_poses = set()
    for i, s in enumerate(spec["timeline"]):
        a = s.get("action")
        where = f"timeline[{i}] ({a})"
        if a not in VOCAB["actions"]:
            E.append(f"{where}: unknown action '{a}' (known: {', '.join(VOCAB['actions'])})")
            continue
        info = VOCAB["actions"][a]
        for r in info["required"]:
            if r not in s:
                E.append(f"{where}: missing '{r}'")
        at = s.get("at")
        if not _num(at) or at < 0 or at > loop:
            E.append(f"{where}: 'at' must be a number between 0 and loop ({loop})")
            continue
        d = s.get("dur", 0.4 if a in ("pose", "move", "moveTo") else 0)
        if a in ("pose", "move", "moveTo", "hop", "shake", "pulse", "spin") and _num(d) and at + d * (s.get("count", 1) if a == "hop" else 1) > loop + 0.01:
            W.append(f"{where}: ends at {at + d:.2f}s, after the loop ({loop}s): the loop will jump")
        if "target" in info.get("required", []) or "target" in s:
            tg = s.get("target")
            if tg not in names:
                E.append(f"{where}: target '{tg}' does not exist (ids: {', '.join(sorted(names))})")
                continue
            ok = info.get("target_kind", ["any"])
            k = kinds[tg]
            if ok == ["any"]:
                if k not in ("sprite", "clawd"):
                    E.append(f"{where}: target '{tg}' is a {k}; this action works on sprites and 'clawd'")
            elif k not in ok:
                E.append(f"{where}: target '{tg}' is a {k}; needs {' or '.join(ok)}")
        if a == "pose":
            if s.get("pose") not in VOCAB["poses"]:
                E.append(f"{where}: unknown pose '{s.get('pose')}' (known: {', '.join(VOCAB['poses'])})")
            else:
                used_poses.add(s["pose"])
                pose_events.append((at, at + (d or 0.4), s["pose"]))
        if a == "swap":
            if s.get("target") in nframes and not (isinstance(s["frame"], int) and 0 <= s["frame"] < nframes[s["target"]]):
                E.append(f"{where}: frame {s['frame']} out of range (sprite has {nframes[s['target']]} frames)")
            frame_events.setdefault(s["target"], []).append((at, s["frame"]))
        if a == "cycle":
            n = nframes.get(s.get("target"), 0)
            if not all(isinstance(f, int) and 0 <= f < n for f in s["frames"]):
                E.append(f"{where}: frames {s['frames']} out of range (sprite has {n} frames)")
            if not _num(s["every"]) or s["every"] <= 0:
                E.append(f"{where}: 'every' must be > 0")
            frame_events.setdefault(s["target"], []).append((at + (s.get("dur", loop - at)), s.get("end", 0)))
        if a in ("appear", "disappear") and s.get("target") in kinds:
            vis_events.setdefault(s["target"], []).append((at, a == "appear"))
        if a in ("move", "moveTo", "hop", "shake", "bob"):
            if a == "moveTo" and "x" not in s and "y" not in s:
                E.append(f"{where}: needs 'x' and/or 'y' (absolute position)")
            mv_steps.append((at, i, a, s))
        if a == "recolor":
            tg, mp = s.get("target"), s.get("map")
            if not isinstance(mp, dict) or not mp:
                E.append(f"{where}: 'map' must be an object like {{\"r\": \"green\"}} (palette character -> color name)")
            else:
                for ch_, cn in mp.items():
                    if tg in palettes and ch_ not in palettes[tg]:
                        E.append(f"{where}: sprite '{tg}' has no palette character '{ch_}'")
                    elif cn not in VOCAB["palette"] and not HEX.match(str(cn)):
                        E.append(f"{where}: unknown color '{cn}'")
                    else:
                        recolors.append((at, tg, ch_, cn))
        if a in ("pulse", "spin") and s.get("target") in boxes and kinds.get(s["target"]) == "sprite":
            bx = boxes[s["target"]]
            bw, bh = bx[2] - bx[0], bx[3] - bx[1]
            if a == "pulse":
                k = s.get("scale", 1.15)
                grow_x, grow_y = max(0, (k - 1) / 2 * bw), max(0, (k - 1) / 2 * bh)
            else:
                diag = (bw ** 2 + bh ** 2) ** 0.5
                grow_x, grow_y = max(0, (diag - bw) / 2), max(0, (diag - bh) / 2)
            grow.append((s["target"], at, grow_x, grow_y))
        if a == "spin" and _num(s.get("turns", 1)) and s.get("turns", 1) != int(s.get("turns", 1)):
            W.append(f"{where}: 'turns' should be a whole number so the loop lands on the starting look")
    def hidden_at(tg, t):
        h = hidden.get(tg, False)
        for et, shown in sorted(vis_events.get(tg, [])):
            if et <= t:
                h = not shown
        return h
    # Position model identical to the engine: each target has segments (t0, from, to); where it has "settled" at time t is the `to`
    # of the latest segment started by t. A move that returns (back) adds a second segment; actions during a hold start from the right place.
    segs, pts, intervals, final_pos = {}, [], {}, {}

    def settled(tg, t):
        best = None
        for sg in segs.get(tg, []):
            if sg[0] <= t + 1e-9 and (best is None or sg[0] >= best[0]):
                best = sg
        return (best[2][0], best[2][1]) if best else (0.0, 0.0)

    def base_of(tg):
        return (cx, cy) if tg == "clawd" else (boxes[tg][0], boxes[tg][1])

    for at_, _i, a_, st in sorted(mv_steps, key=lambda z: (z[0], z[1])):
        tg = st["target"]
        frm = settled(tg, at_)
        if a_ in ("move", "moveTo"):
            d_ = st.get("dur", 0.4)
            if a_ == "move":
                to = (frm[0] + st.get("dx", 0), frm[1] + st.get("dy", 0))
            else:
                bx_, by_ = base_of(tg)
                to = (st["x"] - bx_ if "x" in st else frm[0], st["y"] - by_ if "y" in st else frm[1])
            segs.setdefault(tg, []).append((at_, frm, to)); pts.append((tg, at_ + d_, to))
            intervals.setdefault(tg, []).append((at_, at_ + d_))
            if st.get("back"):
                tb = at_ + d_ + st.get("hold", 0)
                segs[tg].append((tb, to, frm)); pts.append((tg, tb + d_, frm))
                intervals[tg].append((tb, tb + d_))
        elif a_ == "hop":
            pts.append((tg, at_ + 0.25, (frm[0], frm[1] - st.get("h", 14))))
        elif a_ == "shake":
            pts.append((tg, at_, (frm[0] + st.get("amp", 3), frm[1])))
        elif a_ == "bob":
            pts.append((tg, at_, (frm[0], frm[1] - st.get("amp", 3))))
    for tg, t_, (x_, y_) in pts:
        if not hidden_at(tg, t_):
            reach_for(reach, tg, x_, y_)
    for tg in segs:
        final_pos[tg] = settled(tg, 1e9)
        iv = sorted(intervals.get(tg, []))
        for (s0, e0), (s1, e1) in zip(iv, iv[1:]):
            if s1 < e0 - 0.04:
                W.append(f"'{tg}': two moves overlap in time ({s0:.2f}-{e0:.2f}s and {s1:.2f}-{e1:.2f}s); the later one wins while they overlap (check the return of the first)")
    pe = sorted(pose_events)
    for (s0, e0, n0), (s1, e1, n1) in zip(pe, pe[1:]):
        if s1 < e0 - 0.04:
            W.append(f"poses '{n0}' ({s0:.2f}-{e0:.2f}s) and '{n1}' ({s1:.2f}-{e1:.2f}s) overlap; start the next pose after the previous one ends")
    for tg, at_, gx, gy in grow:
        if not hidden_at(tg, at_):
            r = reach.setdefault(tg, {"l": 0, "r": 0, "u": 0, "d": 0})
            # pulse/spin growth is a worst-case estimate (full rotation at the same moment as any hop): allow 4 units of slack
            gx, gy = max(0, gx - 4), max(0, gy - 4)
            r["l"], r["r"] = r["l"] + gx, r["r"] + gx
            r["u"], r["d"] = r["u"] + gy, r["d"] + gy
    # Clawd extents from used poses + hop/move
    ex = [0, 0, 0, 0]
    for pn in used_poses:
        r = VOCAB["poses"][pn]["reach"]
        ex = [max(ex[0], r[0]), max(ex[1], r[1]), max(ex[2], r[2]), max(ex[3], r[3])]
    cr = reach.get("clawd", {"l": 0, "r": 0, "u": 0, "d": 0})
    in_bounds("clawd", cb, (ex[0] + cr["l"], ex[1] + cr["r"], ex[2] + cr["u"], ex[3] + cr["d"]))
    for tg, bb in boxes.items():
        if tg == "clawd" or kinds.get(tg) != "sprite":
            continue
        r = reach.get(tg)
        if r:
            in_bounds(f"sprite '{tg}' (with its motion)", bb, (r["l"], r["r"], r["u"], r["d"]))

    # Style limit: at most 3 objects (clones of one sprite count once)
    n_obj = sum(1 for p_ in spec.get("props", []) if p_.get("type") in ("sprite", "desk", "keyboard", "crt") and not p_.get("clone_of"))
    if n_obj > 3:
        W.append(f"{n_obj} objects: the style limit is 3 (one idea per scene). Merge objects into one sprite, use frames, or drop one")
    # Loop seam checks
    if pose_events:
        pose_events.sort()
        last = pose_events[-1]
        if last[2] != "rest":
            W.append(f"the last pose is '{last[2]}', not 'rest': Clawd will jump back to rest when the loop restarts")
    for tg, (ox, oy) in final_pos.items():
        if abs(ox) > 0.01 or abs(oy) > 0.01:
            W.append(f"'{tg}' ends displaced by ({ox:g}, {oy:g}) after its moves: add \"back\": true or a move that returns it")
    state = {}
    for at_, tg, ch_, cn in sorted(recolors):
        state[(tg, ch_)] = cn
    for (tg, ch_), cn in state.items():
        orig = palettes.get(tg, {}).get(ch_)
        if orig is not None and cn != orig:
            W.append(f"sprite '{tg}' ends recolored ('{ch_}' is {cn}, not {orig}): recolor it back before the loop ends or the loop will pop")
    for tg, ev in vis_events.items():
        ev.sort()
        final = ev[-1][1]
        initial = not hidden.get(tg, False)
        if final != initial:
            W.append(f"'{tg}' ends {'visible' if final else 'hidden'} but starts {'visible' if initial else 'hidden'}: the loop will pop")
    for tg, ev in frame_events.items():
        ev.sort()
        if ev[-1][1] != 0:
            W.append(f"sprite '{tg}' ends on frame {ev[-1][1]}, not frame 0: the loop will pop")

    # Overlaps
    ok_pairs = spec.get("overlap_ok", [])   # intended overlaps: [["idA", "idB"], ...]
    sp = [k for k in boxes if k != "clawd" and kinds.get(k, "sprite") == "sprite"]
    for i, a_ in enumerate(sp):
        for b_ in sp[i + 1:]:
            if [a_, b_] in ok_pairs or [b_, a_] in ok_pairs:
                continue
            ov = overlap(boxes[a_], boxes[b_])
            smaller = min(area(boxes[a_]), area(boxes[b_]))
            if smaller and ov / smaller > 0.3:
                W.append(f"sprites '{a_}' and '{b_}' overlap by {100 * ov / smaller:.0f}% of the smaller one (intended?)")
        bd = CLAWD["body"]
        body_box = (cx + bd[0], cy + bd[1], cx + bd[2], cy + bd[3])
        if overlap(boxes[a_], body_box) > 0:
            W.append(f"sprite '{a_}' overlaps Clawd's body (flat colors may hide one of them)")
    return E, W


def reach_for(reach, tg, dx, dy):
    r = reach.setdefault(tg, {"l": 0, "r": 0, "u": 0, "d": 0})
    if dx > 0: r["r"] = max(r["r"], dx)
    if dx < 0: r["l"] = max(r["l"], -dx)
    if dy < 0: r["u"] = max(r["u"], -dy)
    if dy > 0: r["d"] = max(r["d"], dy)


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def overlap(a, b):
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def validate_file(path):
    try:
        spec = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read scene: {e}"], []
    return validate(spec)


def selftest():
    """vocab.json must list exactly what the JS engine implements."""
    bad = []
    js = lambda n: (HERE / n).read_text()
    pose_block = re.search(r"const POSES = \{(.*?)\n  \};", js("parts/actions.js"), re.S).group(1)
    poses = set(re.findall(r"^\s{4}(\w+):", pose_block, re.M))
    actions = set(re.findall(r"^\s{2}actions\.(\w+) =", js("parts/actions.js"), re.M))
    props = set(re.findall(r"^\s{2}props\.(\w+) =", js("parts/props.js"), re.M))
    named_block = re.search(r"const NAMED = \{(.*?)\};", js("clawd.js"), re.S).group(1)
    named = dict(re.findall(r"(\w+): \"(#[0-9A-Fa-f]{6})\"", named_block))
    for label, js_set, voc in (("poses", poses, set(VOCAB["poses"])), ("actions", actions, set(VOCAB["actions"])), ("props", props, set(VOCAB["props"]))):
        if js_set != voc:
            bad.append(f"{label}: JS-only {sorted(js_set - voc)}, vocab-only {sorted(voc - js_set)}")
    if {k: v.lower() for k, v in named.items()} != {k: v.lower() for k, v in VOCAB["palette"].items()}:
        bad.append("palette differs between clawd.js NAMED and vocab.json")
    return bad


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        bad = selftest()
        print("selftest: " + ("OK (vocab.json matches the JS engine)" if not bad else "FAILED"))
        for b in bad:
            print("  -", b)
        return 1 if bad else 0
    if not args:
        print(__doc__)
        return 1
    errs, warns = validate_file(args[0])
    for e in errs:
        print("ERROR:", e)
    for w in warns:
        print("WARN: ", w)
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    return 1 if errs else (2 if warns and "--strict" in args else 0)


if __name__ == "__main__":
    sys.exit(main())
