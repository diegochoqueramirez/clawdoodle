#!/usr/bin/env python3
"""Export a scene to an animated GIF by capturing frames from headless Chrome.

Usage: python3 export_gif.py <scene> [--out clawd-out/Clawd-<Name>.gif] [--scale 4] [--fps 33] [--bg #F5F0E6]
  scene = path to a *.scene.json file, or the name of engine/scenes/<name>.scene.json
Needs Chrome/Chromium (set CHROME_PATH to override the detection) and Pillow. Works offline (GSAP is vendored).
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def find_chrome():
    """Locate a Chrome/Chromium binary on macOS, Linux or Windows (CHROME_PATH wins)."""
    cands = [os.environ.get("CHROME_PATH", "")]
    cands += [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    cands += [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome/Chromium not found. Install it or set CHROME_PATH to the browser binary.")


def resolve_scene(arg):
    """-> absolute Path of the scene file (a path, or a name inside engine/scenes)."""
    p = Path(arg)
    if p.suffix == ".json" and p.exists():
        return p.resolve()
    q = Path(HERE) / "scenes" / f"{arg}.scene.json"
    if q.exists():
        return q
    sys.exit(f"Scene not found: {arg}")


def capture(chrome, scene_path, t, size, path):
    url = f"file://{HERE}/export.html?src={scene_path.as_uri()}&t={t:.4f}"
    subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--default-background-color=00000000", "--allow-file-access-from-files", f"--window-size={size[0]},{size[1]}",
        "--virtual-time-budget=4000", f"--screenshot={path}", url,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", default=None)
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--fps", type=float, default=33)
    ap.add_argument("--no-validate", action="store_true", help="skip validate_scene.py")
    ap.add_argument("--bg", default=None, help="hex color for an opaque background (default: transparent)")
    a = ap.parse_args()

    scene_path = resolve_scene(a.scene)
    if not a.no_validate:
        import validate_scene
        errs, warns = validate_scene.validate_file(scene_path)
        for w in warns:
            print("WARN: ", w, file=sys.stderr)
        for e in errs:
            print("ERROR:", e, file=sys.stderr)
        if errs:
            sys.exit(f"Scene has {len(errs)} error(s); fix them or pass --no-validate.")
    chrome = find_chrome()
    with open(scene_path) as f:
        spec = json.load(f)
    LOOP = spec["loop"]
    size = (spec["canvas"]["w"] * a.scale, spec["canvas"]["h"] * a.scale)
    a.out = a.out or os.path.join(os.getcwd(), "clawd-out", f"Clawd-{spec['name']}.gif")
    n = round(LOOP * a.fps)
    cs = max(2, round(LOOP * 100 / n))  # GIF delays are whole centiseconds
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            p = os.path.join(tmp, f"f{i:03d}.png")
            capture(chrome, scene_path, i * LOOP / n, size, p)
            im = Image.open(p).convert("RGBA")
            if im.size != size:  # headless Chrome can add chrome-height padding
                im = im.crop((0, 0, size[0], size[1]))
            frames.append(im)
            print(f"frame {i + 1}/{n}", end="\r", flush=True)
    print()

    if a.bg:
        bg = Image.new("RGBA", size, a.bg)
        frames = [Image.alpha_composite(bg, f) for f in frames]

    # One shared 255-color palette (+ index 255 for transparency) keeps colors stable between frames.
    sheet = Image.new("RGB", (size[0], size[1] * n))
    for i, f in enumerate(frames):
        sheet.paste(f.convert("RGB"), (0, i * size[1]))
    pal = sheet.quantize(255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for f in frames:
        p = f.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE)
        if not a.bg:
            p.paste(255, mask=f.getchannel("A").point(lambda v: 255 if v < 128 else 0))
        out.append(p)
    kw = dict(save_all=True, append_images=out[1:], duration=cs * 10, loop=0, disposal=2, optimize=False)
    if not a.bg:
        kw["transparency"] = 255
    out[0].save(a.out, **kw)
    print(f"{a.out}: {n} frames, {size[0]}x{size[1]}, {os.path.getsize(a.out) / 1024:.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
