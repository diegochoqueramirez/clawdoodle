#!/usr/bin/env python3
"""Time-sampled contact sheet of a whole GIF loop (what the reviewer must look at).

Usage: python3 frames_grid.py <gif> [--out grid.png] [--n 16] [--cols 4]
Frames are sampled by TIME, not by index: exported GIFs drop duplicate frames and have variable delays,
so index sampling covers only part of the loop. Each tile is labeled with its time in seconds.
"""
import argparse
from PIL import Image, ImageDraw

BG = (245, 240, 230, 255)


def load(path):
    im = Image.open(path); t = 0; frames = []
    for i in range(im.n_frames):
        im.seek(i); d = im.info["duration"]
        frames.append((t, im.convert("RGBA").copy())); t += d
    return frames, t


def grid(gif, out, n=16, cols=4, tile_w=300):
    frames, total = load(gif)
    W, H = frames[0][1].size
    tw = tile_w; th = round(H * tw / W)
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), "white")
    d = ImageDraw.Draw(sheet)
    for k in range(n):
        ms = int(total * k / n)
        f = [f for t, f in frames if t <= ms][-1]
        c = Image.new("RGBA", f.size, BG); c.alpha_composite(f)
        x, y = (k % cols) * tw, (k // cols) * th
        sheet.paste(c.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 4, y + 3), f"{ms / 1000:.2f}s", fill=(90, 90, 90))
    sheet.save(out)
    return total, len(frames)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("gif"); ap.add_argument("--out", default="grid.png")
    ap.add_argument("--n", type=int, default=16); ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    total, nf = grid(a.gif, a.out, a.n, a.cols)
    print(f"{a.out}: {a.n} tiles over {total} ms ({nf} stored frames)")
