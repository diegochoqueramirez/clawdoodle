#!/usr/bin/env python3
"""Review helper for a generated GIF: contact sheets, zoomed crops and automatic checks.

Usage: python3 review_sheet.py out/Clawd-<Name>.gif [--outdir out/review-<Name>]
Writes: sheet.png (12 evenly spaced moments), zoom-*.png (Clawd at 2x, 6 moments), report.txt
Needs Pillow.
"""
import argparse, os
from PIL import Image, ImageChops

BG = (245, 240, 230, 255)


def load(path):
    im = Image.open(path); t = 0; frames = []
    for i in range(im.n_frames):
        im.seek(i); d = im.info["duration"]
        frames.append((t, d, im.convert("RGBA").copy())); t += d
    return frames, t


def at(frames, ms):
    return [f for s, d, f in frames if s <= ms][-1]


def flat(f):
    c = Image.new("RGBA", f.size, BG); c.alpha_composite(f); return c.convert("RGB")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("gif"); ap.add_argument("--outdir")
    a = ap.parse_args()
    name = os.path.splitext(os.path.basename(a.gif))[0]
    out = a.outdir or os.path.join(os.path.dirname(os.path.abspath(a.gif)), f"review-{name}")
    os.makedirs(out, exist_ok=True)
    frames, total = load(a.gif); W, H = frames[0][2].size
    lines = [f"{a.gif}: {len(frames)} frames, {total} ms, {W}x{H}"]

    # 12-moment contact sheet (time-based, so holds and fast moves are both visible)
    n, cols = 12, 4; tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (cols * tw, (n // cols) * th), "white")
    for k in range(n):
        ms = int(total * k / n)
        sheet.paste(flat(at(frames, ms)).resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
    sheet.save(os.path.join(out, "sheet.png"))

    # Zoomed crops of the left 55% (character area), 6 moments, 2 images of 3 moments each
    cw = int(W * 0.55)
    for part in range(2):
        z = Image.new("RGB", (cw * 3 // 1, H), "white")
        for j in range(3):
            ms = int(total * (part * 3 + j) / 6)
            z.paste(flat(at(frames, ms)).crop((0, 0, cw, H)), (j * cw, 0))
        z.save(os.path.join(out, f"zoom-{part + 1}.png"))

    # Automatic checks
    alpha_edge = 0
    for _, _, f in frames:
        al = f.getchannel("A")
        for box in [(0, 0, 2, H), (W - 2, 0, W, H), (0, 0, W, 2)]:  # left/right/top edges (bottom may have the floor)
            if al.crop(box).getbbox(): alpha_edge += 1
    lines.append(f"content touching left/right/top canvas edge: {'YES (%d hits) -> possible cropping' % alpha_edge if alpha_edge else 'no'}")
    # Minimum margin to every canvas edge over all frames (incl. bottom), as % of width. < 1.0% (~2.4 units, the validator margin is 2) deserves a look.
    mm = [10**9] * 4
    for _, _, f in frames:
        b = f.getchannel("A").point(lambda v: 255 if v > 0 else 0).getbbox()
        if b: mm = [min(mm[0], b[0]), min(mm[1], b[1]), min(mm[2], W - b[2]), min(mm[3], H - b[3])]
    pct = [100.0 * v / W for v in mm]
    tight = [n for n, p in zip(("left", "top", "right", "bottom"), pct) if p < 1.0]
    lines.append("min margin L/T/R/B (px): %s  (%% of width: %s)%s" % (mm, [round(p, 1) for p in pct],
                 "  -> TIGHT: " + ", ".join(tight) if tight else ""))
    # Compare on a flat background so invisible (transparent) pixels never count as change.
    def changed(f1, f2):
        d = ImageChops.difference(flat(f1), flat(f2)).convert("L").point(lambda v: 255 if v > 12 else 0)
        return d.histogram()[255]
    diffs = [changed(frames[i - 1][2], frames[i][2]) for i in range(1, len(frames))]
    mx = max(diffs) if diffs else 0
    med = sorted(diffs)[len(diffs) // 2] if diffs else 0
    lines.append(f"frame-to-frame change: median {med} px, max {mx} px at step {diffs.index(mx) + 1 if diffs else 0} (a max far above the median = jump/pop)")
    lines.append(f"loop seam (last vs first frame) differing pixels: {changed(frames[-1][2], frames[0][2])} (compare with the median above)")
    # Seam and jumps split by region: left 50% = character, right 50% = props/screen (scroll steps are expected jumps there).
    def region(f, a, b):
        return flat(f).crop((int(W * a), 0, int(W * b), H))
    def rchanged(f1, f2, a, b):
        d = ImageChops.difference(region(f1, a, b), region(f2, a, b)).convert("L").point(lambda v: 255 if v > 12 else 0)
        return d.histogram()[255]
    lines.append(f"loop seam, character half only: {rchanged(frames[-1][2], frames[0][2], 0, .5)} px (should be 0: a 1px shift = float residue in the rest pose)")
    cd = [rchanged(frames[i - 1][2], frames[i][2], 0, .5) for i in range(1, len(frames))]
    lines.append(f"character-only frame change: median {sorted(cd)[len(cd) // 2]} px, max {max(cd)} px (screen scroll steps are excluded here)")
    delays = sorted({d for _, d, _ in frames})
    lines.append(f"frame delays (ms): {delays}; total {total} ms")
    open(os.path.join(out, "report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines)); print("written to", out)


if __name__ == "__main__":
    main()
