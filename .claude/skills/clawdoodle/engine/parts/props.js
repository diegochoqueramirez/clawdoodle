/* Reusable props. Each builder is (svg, params, ctx) -> handles used by the actions.
 * ctx = { defs, ground, uid }. Everything is <rect> on the scene's pixel grid. */
(function () {
  const { el } = window.Clawd;
  const props = {};

  // Desk: top slab + two legs down to the ground.
  props.desk = (svg, p, ctx) => {
    const { x, y, w = 148 } = p;
    const g = el("g", { "shape-rendering": "crispEdges" }, svg);
    const legH = ctx.ground - y - 6;
    el("rect", { x: x + 4, y: y + 6, width: 6, height: legH, fill: "#8A6340" }, g);
    el("rect", { x: x + w - 10, y: y + 6, width: 6, height: legH, fill: "#8A6340" }, g);
    el("rect", { x, y, width: w, height: 6, fill: "#8A6340" }, g);
    return {};
  };

  // Keyboard: (x, y) is the top-left of the case; five keys that can flash.
  props.keyboard = (svg, p) => {
    const { x, y } = p;
    const g = el("g", { "shape-rendering": "crispEdges" }, svg);
    el("rect", { x, y, width: 40, height: 6, fill: "#3A3A3A" }, g);
    const keys = [0, 1, 2, 3, 4].map((i) =>
      el("rect", { x: x + 3 + i * 7, y: y + 1, width: 5, height: 3, fill: "#8C8C8C" }, g));
    return { kind: "keyboard", keys, keyOn: "#F2F2F2", keyOff: "#8C8C8C" };
  };

  // CRT: monitor + stand + a screen of scrolling binary (3x5 glyphs of 2px pixels) + blinking cursor.
  props.crt = (svg, p, ctx) => {
    const { x, y, seed: seed0 = 7 } = p;
    const g = el("g", { "shape-rendering": "crispEdges" }, svg);
    el("rect", { x: x + 22, y: y + 60, width: 40, height: 6, fill: "#3A3A3A" }, g);
    el("rect", { x: x + 36, y: y + 54, width: 12, height: 6, fill: "#4A4A4A" }, g);
    el("rect", { x, y, width: 88, height: 54, fill: "#5E5E5E" }, g);
    el("rect", { x: x + 8, y: y + 8, width: 72, height: 40, fill: "#0D1A12" }, g);

    const clipId = `screen-clip-${ctx.uid}`;
    el("rect", { x: x + 8, y: y + 8, width: 72, height: 40 }, el("clipPath", { id: clipId }, ctx.defs));
    const screen = el("g", { "clip-path": `url(#${clipId})`, "shape-rendering": "crispEdges" }, svg);
    const scroll = el("g", {}, screen);

    const GLYPH = { 0: ["111", "101", "101", "101", "111"], 1: ["010", "110", "010", "010", "111"] };
    let seed = seed0;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const ROWS = 6, ROW_H = 12, COL_W = 8, PX = 2, GX0 = x + 9, GY0 = y + 11;
    const rows = Array.from({ length: ROWS }, () => Array.from({ length: 9 }, () => (rnd() > 0.5 ? 1 : 0)));
    for (let rep = 0; rep < 2; rep++) { // twice -> seamless loop when scrolled by ROWS rows
      rows.forEach((row, r) => row.forEach((bit, col) => GLYPH[bit].forEach((line, gy) =>
        [...line].forEach((on, gx) => {
          if (on === "1") {
            el("rect", {
              x: GX0 + col * COL_W + gx * PX, y: GY0 + (rep * ROWS + r) * ROW_H + gy * PX,
              width: PX, height: PX, fill: r % 3 === 0 ? "#7CFF9B" : "#3DDC6E",
            }, scroll);
          }
        }))));
    }
    const cursor = el("rect", { x: GX0, y: GY0 + 2 * ROW_H, width: 6, height: 10, fill: "#7CFF9B" }, svg);
    cursor.setAttribute("clip-path", `url(#${clipId})`);
    return { kind: "crt", scroll, cursor, rows: ROWS, rowH: ROW_H };
  };

  // Generic sprite: a grid of characters -> rects. Lets a scene draw ANY object (the model writes the grid).
  //   { type:"sprite", id, x, y, px?:6, palette:{ "r":"red", "#":"#112233" }, rows:[...] | frames:[[...],[...]], hidden?, layer? }
  // '.' and ' ' are transparent. `px` = scene units per cell (Clawd's body is 78 units wide = 12 cells -> 6.5).
  // Multiple frames are stacked groups; the `swap` / `cycle` actions switch which one is shown.
  props.sprite = (svg, p) => {
    const px = p.px ?? 6;
    const frames = p.frames ?? [p.rows];
    const g = el("g", { "shape-rendering": "crispEdges" }, svg);
    const inner = el("g", {}, g);        // pulse / spin act on `inner`, move / hop / shake / opacity on `g`: separate transforms never fight
    const fills = {};
    for (const ch in (p.palette || {})) fills[ch] = window.Clawd.color(p.palette[ch]);
    const fgs = frames.map((rows, i) => {
      const fg = el("g", {}, inner);
      if (i > 0) fg.setAttribute("display", "none");
      rows.forEach((row, r) => {
        let c = 0;
        while (c < row.length) {            // merge horizontal runs of the same char into one rect
          const ch = row[c];
          let e = c;
          while (e < row.length && row[e] === ch) e++;
          if (ch !== "." && ch !== " ") {
            if (!fills[ch]) throw new Error(`Sprite ${p.id || ""}: no palette entry for '${ch}'`);
            el("rect", { x: p.x + c * px, y: p.y + r * px, width: (e - c) * px, height: px, fill: fills[ch], "data-c": ch }, fg);
          }
          c = e;
        }
      });
      return fg;
    });
    const w = frames[0][0].length * px, h = frames[0].length * px;
    if (p.hidden) g.setAttribute("opacity", 0);
    return { g, inner, frames: fgs, w, h, cx: p.x + w / 2, cy: p.y + h / 2, kind: "sprite", base: { x: p.x, y: p.y } };
  };

  window.Clawd.props = props;
})();
