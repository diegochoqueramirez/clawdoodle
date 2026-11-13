#!/usr/bin/env python3
"""Bake a scene into a self-contained animated SVG (no JavaScript, no GSAP at runtime).

Usage: python3 bake_svg.py <scene.json|name> [--out file.svg] [--fps 60] [--scale 4] [--verify]
How: headless Chrome loads the scene with GSAP, samples every element's transform / opacity / fill at --fps over one loop,
and this script writes the result as CSS @keyframes (linear, infinite) on the original <rect>/<g> markup. CSS animations run
inside <img src="x.svg">, in browsers and in HTML presentations. Keyframes are simplified (Ramer-Douglas-Peucker) so files stay small.
--verify renders the SVG at several moments and compares it with the GSAP render (same pixels expected, up to antialiasing).
"""
import argparse, html, json, os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export_gif as X  # noqa: E402

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
# error tolerance per component before a keyframe is kept (matrix a-d, e-f in scene units, opacity, color channel)
EPS = {"m": [0.002, 0.002, 0.002, 0.002, 0.03, 0.03], "o": 0.02, "f": 1.5}


def run_bake(chrome, scene_path, fps):
    url = f"file://{HERE}/bake.html?src={scene_path.as_uri()}&fps={fps}"
    r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                        "--virtual-time-budget=30000", "--dump-dom", url], capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="out">(.*?)</pre>', r.stdout, re.S)
    if not m:
        sys.exit("bake failed: no data from the browser (is the scene valid?)")
    return json.loads(html.unescape(m.group(1)))


def parse_color(c):
    return [float(v) for v in re.findall(r"[\d.]+", c)[:3]]


def vec(d, k):
    """joint vector of the animated channels of one element at sample k, plus the tolerance of each component"""
    v, eps = [], []
    if d["m"] is not None: v += d["m"][k]; eps += EPS["m"]
    if d["o"] is not None: v += [d["o"][k]]; eps += [EPS["o"]]
    if d["f"] is not None: v += parse_color(d["f"][k]); eps += [EPS["f"]] * 3
    return v, eps


def simplify(vs, eps):
    """Ramer-Douglas-Peucker over the joint series (index = time). Returns the kept sample indices (closed loop: last = first)."""
    n = len(vs)
    keep = {0, n - 1}
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        worst, wi = 0.0, None
        for i in range(a + 1, b):
            t = (i - a) / (b - a)
            err = max(abs(vs[i][c] - (vs[a][c] * (1 - t) + vs[b][c] * t)) / eps[c] for c in range(len(eps)))
            if err > worst:
                worst, wi = err, i
        if wi is not None and worst > 1.0:
            keep.add(wi); stack += [(a, wi), (wi, b)]
    return sorted(keep)


def fmt(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def build(data, scale):
    n, loop = data["n"], data["loop"]
    root = ET.fromstring(f'<svg xmlns="{NS}">{data["svg"]}</svg>')
    parent = {c: p for p in root.iter() for c in p}
    by_idx = {e.get("data-b"): e for e in root.iter() if e.get("data-b") is not None}
    css, removed, animated = [], 0, 0
    for key, d in zip(range(len(data["data"])), data["data"]):
        e = by_idx.get(str(key))
        if e is None:
            continue
        for a in ("style", "transform", "opacity", "display", "data-svg-origin", "data-c"):
            e.attrib.pop(a, None)
        e.attrib.pop("data-b", None)
        if d["m"] is None and d["o"] is None and d["f"] is None:           # static element
            if d["o0"] == 0:
                parent[e].remove(e); removed += 1; continue                 # never visible: drop it
            if d["o0"] != 1: e.set("opacity", fmt(d["o0"]))
            m = d["m0"]
            if any(abs(m[i] - v) > 1e-4 for i, v in enumerate([1, 0, 0, 1, 0, 0])):
                e.set("transform", "matrix(" + ",".join(fmt(v) for v in m) + ")")
            continue
        if d["o"] is not None and max(d["o"]) == 0 and d["m"] is None and d["f"] is None:
            parent[e].remove(e); removed += 1; continue
        animated += 1
        vs, eps = [], None
        for k in range(n):
            v, eps = vec(d, k); vs.append(v)
        vs.append(vs[0]); eps = eps                                          # close the loop on sample 0
        idx = set(simplify(vs, eps))
        # Hard steps (a frame swap, a key flash) must stay hard: GSAP flips them instantly, but sampled at 60 fps a plain linear
        # keyframe pair would cross-fade them over 16 ms (visible as a ghost). Keep both neighbours and add a 0.4 ms transition.
        o_at = (6 if d["m"] is not None else 0)
        f_at = o_at + (1 if d["o"] is not None else 0)
        jumps = set()
        for j in range(1, n + 1):
            hard = (d["o"] is not None and abs(vs[j][o_at] - vs[j - 1][o_at]) > 0.5) or \
                   (d["f"] is not None and max(abs(vs[j][f_at + c] - vs[j - 1][f_at + c]) for c in range(3)) > 100)
            if hard:
                jumps.add(j); idx |= {j - 1, j}
        idx = sorted(idx)
        e.set("id", f"b{key}")

        def kf(pct, v):
            props, c = [], 0
            if d["m"] is not None:
                props.append("transform:matrix(" + ",".join(fmt(x) for x in v[c:c + 6]) + ")"); c += 6
            if d["o"] is not None:
                props.append(f"opacity:{fmt(v[c])}"); c += 1
            if d["f"] is not None:
                r, g, b = (int(round(x)) for x in v[c:c + 3])
                props.append(f"fill:rgb({r},{g},{b})")
            return f"{pct:.4f}".rstrip("0").rstrip(".") + f"%{{{';'.join(props)}}}"

        jt = d.get("jt") or {}
        lines, prev = [], None
        for i in idx:
            if i in jumps and prev == i - 1:
                # exact flip time found by bisection in the browser (fallback: middle of the interval)
                mid = 100.0 * jt[str(i)] / loop if str(i) in jt else 100.0 * (i - 0.5) / n
                lo = 100.0 * (i - 1) / n + 0.0005
                lines.append(kf(max(lo, mid - 0.005), vs[i - 1])); lines.append(kf(max(lo + 0.0005, mid), vs[i]))
            lines.append(kf(100.0 * i / n, vs[i]))
            prev = i
        css.append(f"@keyframes k{key}{{{''.join(lines)}}}#b{key}{{animation-name:k{key}}}")
    w, h = data["canvas"]["w"], data["canvas"]["h"]
    body = "".join(ET.tostring(c, encoding="unicode") for c in root)
    body = body.replace(f' xmlns="{NS}"', "").replace(" ns0:", " ")
    style = (f"<style>[id^=b]{{animation-duration:{fmt(loop)}s;animation-timing-function:linear;animation-iteration-count:infinite;"
             f"animation-fill-mode:both;transform-origin:0 0}}" + "".join(css) + "</style>")
    svg = (f'<svg xmlns="{NS}" viewBox="0 0 {w} {h}" width="{w * scale}" height="{h * scale}" role="img" '
           f'aria-label="Clawd: {html.escape(data["name"])}">{style}{body}</svg>')
    return svg, animated, removed


def tolerant_diff(A, B, size=3, level=40):
    """Pixels that really differ between two renders. The SVG antialiases the edges of rotated parts (intermediate colors) while the
    GSAP render stair-steps them (pure colors), so a plain pixel diff counts every edge. Here a pixel passes if, per channel, its value
    lies inside the min..max range of the neighbourhood (size x size) of the other image, +/- `level`. A ghost frame, a missing or
    displaced part still fails because its colors do not occur nearby."""
    from PIL import ImageChops, ImageFilter

    def violations(x, ref):
        lo, hi = ref.filter(ImageFilter.MinFilter(size)), ref.filter(ImageFilter.MaxFilter(size))
        below, above = ImageChops.subtract(lo, x), ImageChops.subtract(x, hi)   # how far x falls outside [lo, hi]
        r, g, b = ImageChops.lighter(below, above).split()
        return ImageChops.lighter(ImageChops.lighter(r, g), b)

    both = ImageChops.lighter(violations(A, B), violations(B, A))
    return both.point(lambda v: 255 if v > level else 0).histogram()[255]


def verify(svg_path, scene_path, chrome, data, scale):
    """Compare the baked SVG with the live GSAP render at several moments."""
    from PIL import Image, ImageChops
    W, H = data["canvas"]["w"] * scale, data["canvas"]["h"] * scale
    loop = data["loop"]
    res = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(1, 9):
            t = loop * k / 9
            a, b = os.path.join(tmp, f"g{k}.png"), os.path.join(tmp, f"s{k}.png")
            X.capture(chrome, scene_path, t, (W, H), a)
            url = f"file://{HERE}/svg_check.html?svg={Path(svg_path).resolve().as_uri()}&t={t:.4f}"
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                            "--allow-file-access-from-files", f"--window-size={W},{H}", "--virtual-time-budget=4000",
                            f"--screenshot={b}", url], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            A, B = Image.open(a).convert("RGBA").crop((0, 0, W, H)), Image.open(b).convert("RGBA").crop((0, 0, W, H))
            bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            fa, fb = Image.alpha_composite(bg, A).convert("RGB"), Image.alpha_composite(bg, B).convert("RGB")
            res.append((round(t, 2), tolerant_diff(fa, fb)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene"); ap.add_argument("--out"); ap.add_argument("--fps", type=float, default=60)
    ap.add_argument("--scale", type=int, default=4); ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    scene_path = X.resolve_scene(a.scene)
    spec = json.loads(scene_path.read_text())
    chrome = X.find_chrome()
    data = run_bake(chrome, scene_path, a.fps)
    svg, animated, removed = build(data, a.scale)
    out = Path(a.out) if a.out else Path.cwd() / "clawd-out" / f"Clawd-{spec['name']}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg)
    print(f"{out}: {len(svg) / 1024:.0f} KB, {animated} animated elements, {removed} never-visible elements dropped, {data['n']} samples @ {a.fps:g} fps")
    if a.verify:
        res = verify(out, scene_path, chrome, data, a.scale)
        total = data["canvas"]["w"] * a.scale * data["canvas"]["h"] * a.scale
        worst = max(d for _, d in res)
        pct = 100 * worst / total
        print("verify (pixels that differ by >40 levels vs the GSAP render, tolerating 1 px edge shifts):", ", ".join(f"{t}s: {d}" for t, d in res),
              f"| worst {worst} of {total} ({pct:.3f}%) -> {'OK' if pct < 0.05 else 'MISMATCH: look at it'}")


if __name__ == "__main__":
    main()
