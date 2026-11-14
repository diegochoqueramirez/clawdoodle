#!/usr/bin/env python3
"""clawd: project manager for Clawd GIFs (the skill calls this instead of hand-building paths).

A project lives in ./clawdoodles/<slug>/ (override the base with CLAWD_HOME):
  scene.json          the current scene (the ONLY thing edited when the user asks for changes)
  versions/vN.scene.json (+ vN.gif, log.json)   history
  out/preview.gif, out/final.gif, out/final.svg   renders
  review/                                         review pack for the reviewer agent

Commands (run with scripts/run.py):
  new <slug> [--from <example>]   create a project (empty template, or a copy of an example scene)
  list                            projects and how many versions each has
  check <slug>                    validate the scene
  render <slug> [--final] [--scale N] [--fps N] [--no-pack] [--no-svg]
                                  validate + export (preview = scale 3 / 20 fps, final = scale 4 / 33 fps); preview also builds the review pack;
                                  --final also writes out/final.svg (animated SVG, no JavaScript)
  export-svg <slug> [--verify]    bake out/final.svg only (animated SVG that works in <img> and presentations); --verify compares it with the GSAP render
  review-pack <slug>              review/: grid.png (whole loop, sampled by time), sheet.png, zoom-*.png, report.txt
  save <slug> -m "message"        snapshot scene (+ latest GIF) as the next version
  versions <slug>                 list versions
  diff <slug> [A [B]]             what changed (default: last saved version vs current)
  revert <slug> <N>               restore vN (current state is saved first)
  retime <slug> --factor F        make the whole animation slower (F>1) or faster (F<1)
  remove <slug> <id>              delete an object and every step that targets it
  templates                       list the sprite templates (faces, check, cross, cloud, drop, sun, document, folder, arrows)
  add-sprite <slug> <template> --at X Y [--id ID] [--px N] [--colors a=name,b=name] [--ground] [--layer front] [--hidden]
                                  insert a template as a sprite (remap its palette with --colors)
  add-gauge <slug> <id> --cells N --at X Y [--color green] [--vertical] [--px 4] [--ground]
                                  insert a segmented bar with frames 0..N (use swap to set the value)
  clone <slug> <id> --as NEW --at X Y [--hidden]
                                  independent copy of a sprite (a second envelope, a second drop...); clones do not count for the 3-object limit
  sprite-preview <slug> [id] | --template NAME
                                  zoomed PNG of a sprite's frames on cream / white / dark (no browser, instant): judge readability before rendering
  palette [--out file.png]        PNG with every named color (defaults to engine/palette.png)
  doctor                          check the install (Pillow, Chrome, vocabulary selftest)
"""
import argparse, copy, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows consoles default to a legacy codepage
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_scene as V  # noqa: E402

BASE = Path(os.environ.get("CLAWD_HOME") or "clawdoodles")
# Defaults that retime must make explicit, otherwise a default duration would not scale.
DEFAULT_DUR = {"pose": 0.4, "move": 0.4, "hop": 0.5, "shake": 0.4, "pulse": 0.3, "spin": 1.0, "wave": 1.0}
TIME_KEYS = ("at", "dur", "hold", "fade", "every")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "scene"


def pdir(slug):
    d = BASE / slugify(slug)
    if not (d / "scene.json").exists():
        sys.exit(f"No project '{slug}' in {BASE}. Create it with: clawd.py new {slug}")
    return d


def load(d):
    return json.loads((d / "scene.json").read_text(encoding="utf-8"))


def dump(d, spec):
    (d / "scene.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], **kw)


def versions_log(d):
    f = d / "versions" / "log.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


# ---------------------------------------------------------------------------
def cmd_new(a):
    d = BASE / slugify(a.slug)
    if (d / "scene.json").exists():
        sys.exit(f"Project already exists: {d}")
    for sub in ("versions", "out", "review"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    if a.src:
        src = HERE / "scenes" / f"{a.src}.scene.json"
        if not src.exists():
            sys.exit(f"Unknown example '{a.src}'. Available: " + ", ".join(sorted(p.name.split('.')[0] for p in (HERE / 'scenes').glob('*.scene.json'))))
        spec = json.loads(src.read_text(encoding="utf-8"))
        spec["name"] = a.slug.title().replace("-", "")
    else:
        spec = {"name": a.slug.title().replace("-", ""), "meta": {"topic": "", "metaphor": ""},
                "canvas": {"w": 232, "h": 122}, "loop": 3.6, "clawd": {"x": 14, "y": 26}, "props": [], "timeline": []}
    dump(d, spec)
    print(f"created {d}/scene.json")


def cmd_list(a):
    if not BASE.exists():
        print("(no projects yet)"); return
    for d in sorted(BASE.iterdir()):
        if (d / "scene.json").exists():
            print(f"{d.name:30s} {len(versions_log(d))} version(s)")


def cmd_check(a):
    d = pdir(a.slug)
    sha_f = d / "review" / "scene.sha"
    if sha_f.exists() and sha_f.read_text(encoding="utf-8") != hashlib.sha1((d / "scene.json").read_bytes()).hexdigest()[:10]:
        print("NOTE: review/ (grid.png ...) was built from an OLDER scene.json: do not trust it, run render again.")
    errs, warns = V.validate_file(d / "scene.json")
    for e in errs: print("ERROR:", e)
    for w in warns: print("WARN: ", w)
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    return 1 if errs else 0


def cmd_render(a):
    d = pdir(a.slug)
    if cmd_check(a):
        sys.exit("Fix the errors first.")
    kind = "final" if a.final else "preview"
    if kind == "preview" and not a.no_pack:
        for old in (d / "review").glob("*"):
            if old.is_file() and old.suffix in (".png", ".txt", ".sha"):
                old.unlink()          # a stale grid.png must never be mistaken for the render in progress
    scale = a.scale or (4 if a.final else 3)
    fps = a.fps or (33 if a.final else 20)
    out = d / "out" / f"{kind}.gif"
    r = run([sys.executable, HERE / "export_gif.py", d / "scene.json", "--scale", scale, "--fps", fps, "--out", out, "--no-validate"])
    if r.returncode:
        sys.exit("export failed")
    if kind == "preview" and not a.no_pack:
        cmd_review_pack(argparse.Namespace(slug=a.slug))
    print(f"\nrendered {out}")
    if kind == "final" and not a.no_svg:
        cmd_export_svg(argparse.Namespace(slug=a.slug, verify=False))


def cmd_export_svg(a):
    d = pdir(a.slug)
    if cmd_check(a):
        sys.exit("Fix the errors first.")
    out = d / "out" / "final.svg"
    cmd = [sys.executable, HERE / "bake_svg.py", d / "scene.json", "--out", out]
    if a.verify:
        cmd.append("--verify")
    if run(cmd).returncode:
        sys.exit("svg export failed")
    print(f"rendered {out}")


def cmd_review_pack(a):
    d = pdir(a.slug)
    gif = d / "out" / "preview.gif"
    if not gif.exists():
        gif = d / "out" / "final.gif"
    if not gif.exists():
        sys.exit("Nothing rendered yet: run render first.")
    rv = d / "review"; rv.mkdir(exist_ok=True)
    r = run([sys.executable, HERE / "review_sheet.py", gif, "--outdir", rv], capture_output=True, text=True)
    report = [l for l in r.stdout.splitlines() if l and "Warning" not in l and "getdata" not in l]
    import frames_grid
    total, nf = frames_grid.grid(str(gif), str(rv / "grid.png"), n=16, cols=4)
    errs, warns = V.validate_file(d / "scene.json")
    report += [f"validator: {len(errs)} error(s), {len(warns)} warning(s)"] + [f"  WARN: {w}" for w in warns]
    (rv / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    (rv / "scene.sha").write_text(hashlib.sha1((d / "scene.json").read_bytes()).hexdigest()[:10], encoding="utf-8")
    print("review pack:", rv)
    print("\n".join(report))
    print(f"LOOK at: {rv / 'grid.png'} (whole loop, 16 moments sampled by time), {rv / 'sheet.png'}, {rv / 'zoom-1.png'}, {rv / 'zoom-2.png'}")


def cmd_save(a):
    d = pdir(a.slug)
    (d / "versions").mkdir(exist_ok=True)
    log = versions_log(d)
    sha = hashlib.sha1((d / "scene.json").read_bytes()).hexdigest()[:10]
    if log and log[-1]["sha"] == sha:
        print(f"scene unchanged since v{log[-1]['n']}; nothing saved")
        return
    n = len(log) + 1
    shutil.copy(d / "scene.json", d / "versions" / f"v{n}.scene.json")
    gifs = [p for p in (d / "out" / "final.gif", d / "out" / "preview.gif") if p.exists()]
    if gifs:
        latest = max(gifs, key=lambda p: p.stat().st_mtime)
        shutil.copy(latest, d / "versions" / f"v{n}.gif")
    svg = d / "out" / "final.svg"
    if svg.exists() and (not gifs or svg.stat().st_mtime >= max(p.stat().st_mtime for p in gifs) - 120):
        shutil.copy(svg, d / "versions" / f"v{n}.svg")   # only when the SVG is as fresh as the GIF (rendered together)
    log.append({"n": n, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "message": a.message or "",
                "sha": sha, "gif": bool(gifs)})
    (d / "versions" / "log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"saved v{n}: {a.message or ''}")


def cmd_versions(a):
    d = pdir(a.slug)
    for e in versions_log(d):
        print(f"v{e['n']}  {e['time']}  {e['sha']}  {'[gif] ' if e['gif'] else '      '}{e['message']}")
    if not versions_log(d):
        print("(no versions saved yet)")


def _scene(d, ref):
    if ref in (None, "current"):
        return load(d)
    n = int(str(ref).lstrip("v"))
    f = d / "versions" / f"v{n}.scene.json"
    if not f.exists():
        sys.exit(f"No version v{n}")
    return json.loads(f.read_text(encoding="utf-8"))


def summarize_diff(A, B):
    out = []
    for k in ("name", "loop"):
        if A.get(k) != B.get(k): out.append(f"{k}: {A.get(k)} -> {B.get(k)}")
    if A.get("canvas") != B.get("canvas"): out.append(f"canvas: {A.get('canvas')} -> {B.get('canvas')}")
    if A.get("clawd") != B.get("clawd"): out.append(f"clawd: {A.get('clawd')} -> {B.get('clawd')}")
    pa = {p.get("id") or f"#{i}": p for i, p in enumerate(A.get("props", []))}
    pb = {p.get("id") or f"#{i}": p for i, p in enumerate(B.get("props", []))}
    for k in pb.keys() - pa.keys(): out.append(f"+ prop {k} ({pb[k].get('type')})")
    for k in pa.keys() - pb.keys(): out.append(f"- prop {k} ({pa[k].get('type')})")
    for k in pa.keys() & pb.keys():
        if pa[k] != pb[k]:
            ch = [f for f in set(pa[k]) | set(pb[k]) if pa[k].get(f) != pb[k].get(f)]
            out.append(f"~ prop {k}: changed {', '.join(sorted(ch))}")
    ta, tb = A.get("timeline", []), B.get("timeline", [])
    la, lb = A.get("loop"), B.get("loop")
    if la and lb and abs(lb / la - 1) > 1e-6 and len(ta) == len(tb):
        r = lb / la
        same = all(x.get("action") == y.get("action") and x.get("target") == y.get("target") and x.get("pose") == y.get("pose")
                   and abs(x.get("at", 0) * r - y.get("at", 0)) < 0.011 for x, y in zip(ta, tb))
        if same:
            out.append(f"timeline: same {len(ta)} steps, uniformly retimed x{r:.2f}")
            return out
    key = lambda s: json.dumps(s, sort_keys=True)
    sa, sb = [key(s) for s in ta], [key(s) for s in tb]
    added = [s for s in tb if key(s) not in sa]
    removed = [s for s in ta if key(s) not in sb]
    out.append(f"timeline: {len(ta)} -> {len(tb)} steps ({len(added)} added/changed, {len(removed)} removed/changed)")
    for s in removed[:8]: out.append(f"  - {s.get('action')} at {s.get('at')} {s.get('target', s.get('pose', ''))}")
    for s in added[:8]: out.append(f"  + {s.get('action')} at {s.get('at')} {s.get('target', s.get('pose', ''))}")
    return out


def cmd_diff(a):
    d = pdir(a.slug)
    log = versions_log(d)
    if a.a is None and not log:
        sys.exit("No saved versions to compare with.")
    A = _scene(d, a.a if a.a is not None else f"v{len(log)}")
    B = _scene(d, a.b)
    print("\n".join(summarize_diff(A, B)) or "(no differences)")


def cmd_revert(a):
    d = pdir(a.slug)
    src = d / "versions" / f"v{a.n}.scene.json"
    if not src.exists():
        sys.exit(f"No version v{a.n}")
    cmd_save(argparse.Namespace(slug=a.slug, message=f"autosave before revert to v{a.n}"))
    shutil.copy(src, d / "scene.json")
    print(f"scene.json restored from v{a.n}. Render again to refresh the GIF.")


def retime(spec, f):
    s = copy.deepcopy(spec)
    s["loop"] = round(s["loop"] * f, 3)
    for st in s.get("timeline", []):
        act = st.get("action")
        if act in DEFAULT_DUR and "dur" not in st:
            st["dur"] = DEFAULT_DUR[act]
        if act == "blink" and "hold" not in st:
            st["hold"] = 0.22
        if act in ("cycle", "scroll", "cursor", "bob") and "dur" not in st:
            st["dur"] = round(s["loop"] / f - st["at"], 3)        # default was "until the end of the old loop"
        if act == "bob" and "every" not in st:
            st["every"] = 0.8
        if act == "cursor" and "every" not in st:
            st["every"] = 0.4
        for k in TIME_KEYS:
            if isinstance(st.get(k), (int, float)):
                st[k] = round(st[k] * f, 3)
        if isinstance(st.get("taps"), list):
            st["taps"] = [round(t * f, 3) for t in st["taps"]]
        if act == "wave" and "count" not in st:
            pass
    return s


def cmd_retime(a):
    d = pdir(a.slug)
    cmd_save(argparse.Namespace(slug=a.slug, message=f"before retime x{a.factor}"))
    spec = retime(load(d), a.factor)
    dump(d, spec)
    print(f"retimed x{a.factor}: loop is now {spec['loop']} s. Run check/render.")
    return 0


def cmd_remove(a):
    d = pdir(a.slug)
    spec = load(d)
    n0 = len(spec.get("props", []))
    spec["props"] = [p for p in spec.get("props", []) if p.get("id") != a.id]
    if len(spec["props"]) == n0:
        sys.exit(f"No prop with id '{a.id}'. ids: " + ", ".join(p.get("id", "?") for p in spec["props"]))
    t0 = len(spec["timeline"])
    spec["timeline"] = [s for s in spec["timeline"] if s.get("target") != a.id]
    if "overlap_ok" in spec:
        spec["overlap_ok"] = [p for p in spec["overlap_ok"] if a.id not in p]
    dump(d, spec)
    print(f"removed '{a.id}' and {t0 - len(spec['timeline'])} timeline step(s) that targeted it")


def _load_templates():
    return json.loads((HERE / "templates.json").read_text(encoding="utf-8"))["templates"]


def _parse_colors(txt):
    m = {}
    for part in (txt or "").split(","):
        if part.strip():
            k, _, v = part.partition("=")
            if len(k.strip()) != 1 or not v.strip():
                sys.exit(f"--colors expects 'c=name,c=name' with one character per key, got '{part}'")
            if v.strip() not in V.VOCAB["palette"] and not V.HEX.match(v.strip()):
                sys.exit(f"Unknown color '{v.strip()}'. Named colors: " + ", ".join(V.VOCAB["palette"]))
            m[k.strip()] = v.strip()
    return m


def _place(spec, prop, ground):
    frames = prop.get("frames") or [prop["rows"]]
    px = prop.get("px", 6)
    h = len(frames[0]) * px
    if ground:
        prop["y"] = spec["clawd"]["y"] + 86 - h
    w = len(frames[0][0]) * px
    return w, h


def _check_new_id(spec, pid):
    if any(p.get("id") == pid for p in spec["props"]) or pid == "clawd":
        sys.exit(f"id '{pid}' already exists; choose another with --id")


def cmd_templates(a):
    for n, t in _load_templates().items():
        fr = t.get("frames") or [t["rows"]]
        print(f"{n:12s} {len(fr[0][0])}x{len(fr[0])} cells, {len(fr)} frame(s), palette {t['palette']}  {t['desc']}")


def cmd_add_sprite(a):
    d = pdir(a.slug); spec = load(d)
    T = _load_templates()
    if a.template not in T:
        sys.exit(f"Unknown template '{a.template}'. Available: " + ", ".join(T))
    t = copy.deepcopy(T[a.template]); pid = a.id or a.template
    _check_new_id(spec, pid)
    pal = dict(t["palette"]); pal.update(_parse_colors(a.colors))
    prop = {"type": "sprite", "id": pid, "x": a.at[0], "y": a.at[1], "px": a.px or t["px"], "palette": pal}
    for k in ("rows", "frames"):
        if k in t: prop[k] = t[k]
    if a.layer: prop["layer"] = a.layer
    if a.hidden: prop["hidden"] = True
    w, h = _place(spec, prop, a.ground)
    spec["props"].append(prop); dump(d, spec)
    print(f"added sprite '{pid}' from '{a.template}' at ({prop['x']},{prop['y']}), {w}x{h} units (px {prop['px']}). Next: sprite-preview {a.slug} {pid}, then check.")


def cmd_add_gauge(a):
    d = pdir(a.slug); spec = load(d)
    _check_new_id(spec, a.id)
    from sprite_tools import gauge_frames
    prop = {"type": "sprite", "id": a.id, "x": a.at[0], "y": a.at[1], "px": a.px or 4,
            "palette": {"d": "dark", "f": a.color, "e": "light"}, "frames": gauge_frames(a.cells, a.vertical)}
    w, h = _place(spec, prop, a.ground)
    spec["props"].append(prop); dump(d, spec)
    print(f"added gauge '{a.id}' with frames 0..{a.cells} ({w}x{h} units). Set the value with: {{\"action\": \"swap\", \"target\": \"{a.id}\", \"frame\": K, \"at\": T}}")


def cmd_clone(a):
    d = pdir(a.slug); spec = load(d)
    src = next((p for p in spec["props"] if p.get("id") == a.id and p.get("type") == "sprite"), None)
    if not src:
        sys.exit(f"No sprite with id '{a.id}'")
    _check_new_id(spec, a.new)
    c = copy.deepcopy(src); c.update({"id": a.new, "x": a.at[0], "y": a.at[1], "clone_of": a.id})
    if a.hidden: c["hidden"] = True
    spec["props"].append(c); dump(d, spec)
    print(f"cloned '{a.id}' as '{a.new}' at ({c['x']},{c['y']}). Clones are independent: give them their own timeline steps.")


def _preview_png(frames, palette, px, title, out):
    from PIL import Image, ImageDraw
    pal = {ch: V.VOCAB["palette"].get(name, name) for ch, name in palette.items()}
    h, w = len(frames[0]), len(frames[0][0])
    z = max(4, min(22, 520 // max(w, h)))
    bgs = [("cream", (245, 240, 230)), ("white", (255, 255, 255)), ("dark", (34, 34, 34))]
    pad, lab = 10, 16
    W = len(frames) * (w * z + pad) + pad
    H = len(bgs) * (h * z + lab + pad) + 28 + pad
    img = Image.new("RGB", (max(W, 320), H), (250, 250, 250)); d = ImageDraw.Draw(img)
    d.text((pad, 6), f"{title}: {w}x{h} cells x px {px} = {w * px}x{h * px} scene units; {len(frames)} frame(s)", fill=(60, 60, 60))
    y0 = 28
    for bn, bc in bgs:
        d.text((pad, y0 - 1), bn, fill=(120, 120, 120))
        for fi, rows in enumerate(frames):
            x0 = pad + fi * (w * z + pad)
            d.rectangle([x0, y0 + lab, x0 + w * z, y0 + lab + h * z], fill=bc)
            for r, row in enumerate(rows):
                for c_, ch in enumerate(row):
                    if ch in ". ":
                        continue
                    col = pal.get(ch)
                    if col is None:
                        d.rectangle([x0 + c_ * z, y0 + lab + r * z, x0 + (c_ + 1) * z, y0 + lab + (r + 1) * z], fill=(255, 0, 255))   # missing palette entry
                        continue
                    d.rectangle([x0 + c_ * z, y0 + lab + r * z, x0 + (c_ + 1) * z - 1, y0 + lab + (r + 1) * z - 1], fill=col)
            if bn == "cream" and len(frames) > 1:
                d.text((x0 + 44, y0 + 1), f"frame {fi}", fill=(120, 120, 120))
        y0 += h * z + lab + pad
    img.save(out)


def cmd_sprite_preview(a):
    if a.template:
        t = _load_templates().get(a.template) or sys.exit(f"Unknown template '{a.template}'")
        out = Path(a.out or f"sprite-{a.template}.png")
        _preview_png(t.get("frames") or [t["rows"]], t["palette"], t["px"], a.template, out)
        print("written", out); return
    d = pdir(a.slug); spec = load(d)
    sprites = [p for p in spec["props"] if p.get("type") == "sprite" and (not a.id or p.get("id") == a.id)]
    if not sprites:
        sys.exit("No such sprite" + (f" '{a.id}'" if a.id else "s in this scene"))
    (d / "review").mkdir(exist_ok=True)
    for p in sprites:
        out = d / "review" / f"sprite-{p.get('id', 'x')}.png"
        _preview_png(p.get("frames") or [p["rows"]], p.get("palette", {}), p.get("px", 6), p.get("id", "sprite"), out)
        print("written", out, "(magenta cells = characters with no palette entry; check the dark/white rows for pale parts)")


def cmd_palette(a):
    from PIL import Image, ImageDraw
    pal = V.VOCAB["palette"]; names = list(pal)
    cols = 6; cw, ch_ = 120, 64
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * cw, rows * ch_), (245, 240, 230)); d = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        x, y = (i % cols) * cw, (i // cols) * ch_
        d.rectangle([x + 6, y + 6, x + cw - 6, y + 38], fill=pal[n], outline=(0, 0, 0))
        d.text((x + 8, y + 42), n, fill=(30, 30, 30)); d.text((x + 8, y + 52), pal[n], fill=(110, 110, 110))
    out = Path(a.out) if a.out else HERE / "palette.png"
    img.save(out); print("written", out)


def cmd_doctor(a):
    ok = True
    try:
        import PIL
        print("Pillow:", PIL.__version__)
    except ImportError:
        print("Pillow: MISSING (run scripts/setup.sh)"); ok = False
    try:
        import export_gif
        print("Chrome:", export_gif.find_chrome())
    except SystemExit as e:
        print("Chrome:", e); ok = False
    bad = V.selftest()
    print("vocabulary selftest:", "OK" if not bad else "FAILED " + "; ".join(bad))
    ok = ok and not bad
    print("gsap vendored:", (HERE / "vendor" / "gsap.min.js").exists())
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("new"); p.add_argument("slug"); p.add_argument("--from", dest="src"); p.set_defaults(f=cmd_new)
    p = sp.add_parser("list"); p.set_defaults(f=cmd_list)
    p = sp.add_parser("check"); p.add_argument("slug"); p.set_defaults(f=cmd_check)
    p = sp.add_parser("render"); p.add_argument("slug"); p.add_argument("--final", action="store_true")
    p.add_argument("--scale", type=int); p.add_argument("--fps", type=float); p.add_argument("--no-pack", action="store_true"); p.add_argument("--no-svg", action="store_true"); p.set_defaults(f=cmd_render)
    p = sp.add_parser("export-svg"); p.add_argument("slug"); p.add_argument("--verify", action="store_true"); p.set_defaults(f=cmd_export_svg)
    p = sp.add_parser("review-pack"); p.add_argument("slug"); p.set_defaults(f=cmd_review_pack)
    p = sp.add_parser("save"); p.add_argument("slug"); p.add_argument("-m", "--message", default=""); p.set_defaults(f=cmd_save)
    p = sp.add_parser("versions"); p.add_argument("slug"); p.set_defaults(f=cmd_versions)
    p = sp.add_parser("diff"); p.add_argument("slug"); p.add_argument("a", nargs="?"); p.add_argument("b", nargs="?"); p.set_defaults(f=cmd_diff)
    p = sp.add_parser("revert"); p.add_argument("slug"); p.add_argument("n", type=int); p.set_defaults(f=cmd_revert)
    p = sp.add_parser("retime"); p.add_argument("slug"); p.add_argument("--factor", type=float, required=True); p.set_defaults(f=cmd_retime)
    p = sp.add_parser("remove"); p.add_argument("slug"); p.add_argument("id"); p.set_defaults(f=cmd_remove)
    p = sp.add_parser("templates"); p.set_defaults(f=cmd_templates)
    p = sp.add_parser("add-sprite"); p.add_argument("slug"); p.add_argument("template"); p.add_argument("--at", type=float, nargs=2, required=True)
    p.add_argument("--id"); p.add_argument("--px", type=float); p.add_argument("--colors"); p.add_argument("--ground", action="store_true")
    p.add_argument("--layer", choices=["back", "front"]); p.add_argument("--hidden", action="store_true"); p.set_defaults(f=cmd_add_sprite)
    p = sp.add_parser("add-gauge"); p.add_argument("slug"); p.add_argument("id"); p.add_argument("--cells", type=int, required=True)
    p.add_argument("--at", type=float, nargs=2, required=True); p.add_argument("--color", default="green"); p.add_argument("--vertical", action="store_true")
    p.add_argument("--px", type=float); p.add_argument("--ground", action="store_true"); p.set_defaults(f=cmd_add_gauge)
    p = sp.add_parser("clone"); p.add_argument("slug"); p.add_argument("id"); p.add_argument("--as", dest="new", required=True)
    p.add_argument("--at", type=float, nargs=2, required=True); p.add_argument("--hidden", action="store_true"); p.set_defaults(f=cmd_clone)
    p = sp.add_parser("sprite-preview"); p.add_argument("slug", nargs="?"); p.add_argument("id", nargs="?"); p.add_argument("--template"); p.add_argument("--out")
    p.set_defaults(f=cmd_sprite_preview)
    p = sp.add_parser("palette"); p.add_argument("--out"); p.set_defaults(f=cmd_palette)
    p = sp.add_parser("doctor"); p.set_defaults(f=cmd_doctor)
    a = ap.parse_args()
    sys.exit(a.f(a) or 0)


if __name__ == "__main__":
    main()
