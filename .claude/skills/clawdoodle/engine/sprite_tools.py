#!/usr/bin/env python3
"""Helpers to build sprite grids by code (lines, diagonals, rectangles, circles, gauges) instead of counting characters by hand.

Use from a small Python script that writes the sprite into a scene:

    import sys; sys.path.insert(0, "<skill>/engine")
    from sprite_tools import Grid, gauge_frames
    g = Grid(20, 12)
    g.line(0, 10, 19, 10, "s")          # horizontal line
    g.line(4, 10, 10, 2, "s")           # diagonal (stair-stepped, as pixel art is)
    g.rect(8, 0, 3, 3, "g", filled=True)
    rows = g.rows()                      # list of equal-length strings -> "rows" of a sprite
    write_sprite("clawdoodles/<slug>/scene.json", "rails", {"s": "steel"}, rows=rows, x=140, y=30)   # insert/replace it in the scene

Characters are palette keys of the sprite ('.' = transparent). Every sprite has its own palette: {"s": "steel", "g": "green"}.
"""


class Grid:
    def __init__(self, w, h, fill="."):
        self.w, self.h = w, h
        self.c = [[fill] * w for _ in range(h)]

    def set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.c[y][x] = ch
        return self

    def line(self, x0, y0, x1, y1, ch, thick=1):
        """Bresenham line; thick > 1 draws a thick line (each point becomes a thick x thick block)."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            for ox in range(thick):
                for oy in range(thick):
                    self.set(x0 + ox, y0 + oy, ch)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy
        return self

    def rect(self, x, y, w, h, ch, filled=False):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if filled or yy in (y, y + h - 1) or xx in (x, x + w - 1):
                    self.set(xx, yy, ch)
        return self

    def circle(self, cx, cy, r, ch, filled=False):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (d <= r * r + r * 0.6) and (filled or d >= (r - 1) ** 2 + (r - 1) * 0.6):
                    self.set(xx, yy, ch)
        return self

    def paste(self, other, x, y):
        for yy, row in enumerate(other.c if isinstance(other, Grid) else other):
            for xx, ch in enumerate(row):
                if ch != ".":
                    self.set(x + xx, y + yy, ch)
        return self

    def flip_h(self):
        self.c = [row[::-1] for row in self.c]
        return self

    def rows(self):
        return ["".join(r) for r in self.c]


def gauge_frames(cells=6, vertical=False, border="d", fill="f", empty="e"):
    """Frames 0..cells of a segmented bar (frame k = k cells filled). Horizontal: (3*cells+1) x 5 cells; vertical: 5 x (3*cells+1), filling from the bottom.
    Palette to use: {border: 'dark', fill: <color>, empty: 'light'}."""
    frames = []
    for k in range(cells + 1):
        g = Grid(3 * cells + 1, 5)
        g.rect(0, 0, 3 * cells + 1, 5, border)
        for i in range(cells):
            ch = fill if i < k else empty
            for yy in (1, 2, 3):
                g.set(1 + 3 * i, yy, ch); g.set(2 + 3 * i, yy, ch)
            if i < cells - 1:
                for yy in range(1, 4):
                    g.set(3 + 3 * i, yy, border)
        rows = g.rows()
        if vertical:
            cols = ["".join(rows[r][c] for r in range(5)) for c in range(3 * cells + 1)]
            rows = cols[::-1]          # fill from the bottom: reverse so index 0 (first cells) ends at the bottom
        frames.append(rows)
    return frames


def write_sprite(scene_path, sprite_id, palette, rows=None, frames=None, x=0, y=0, px=6, **extra):
    """Insert or replace a sprite prop in a scene.json (keeps everything else). `extra` may hold hidden=True, layer="front", clone_of="id"...
    Returns the sprite's size in scene units (w, h)."""
    import json
    with open(scene_path) as f:
        spec = json.load(f)
    prop = {"type": "sprite", "id": sprite_id, "x": x, "y": y, "px": px, "palette": palette}
    if frames is not None:
        prop["frames"] = frames
    else:
        prop["rows"] = rows
    prop.update(extra)
    props = spec.setdefault("props", [])
    for i, p in enumerate(props):
        if p.get("id") == sprite_id:
            props[i] = prop
            break
    else:
        props.append(prop)
    with open(scene_path, "w") as f:
        json.dump(spec, f, indent=1)
    fr = frames[0] if frames is not None else rows
    return len(fr[0]) * px, len(fr) * px


def cell_to_xy(sprite_x, sprite_y, col, row, px=6, center=True):
    """Scene position of cell (col, row) of a sprite placed at (sprite_x, sprite_y): handy to move another object onto a given cell."""
    off = 0.5 if center else 0
    return sprite_x + (col + off) * px, sprite_y + (row + off) * px
