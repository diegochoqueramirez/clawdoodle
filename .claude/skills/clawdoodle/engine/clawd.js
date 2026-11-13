/* Clawd base character built only from <rect>s (same approach as the Codrops article).
 * Coordinates are absolute in the scene viewBox so GSAP svgOrigin values stay simple.
 * Local character space: width ~122 (hands included), height 86, ground at y = 86. */
(function () {
  const NS = "http://www.w3.org/2000/svg";

  const PALETTE = {
    body: "#DD775B",
    eye: "#1A1A1A",
  };

  // Closed named palette for scenes (keep in sync with vocab.json; validate_scene.py --selftest checks it).
  const NAMED = {
    body: "#DD775B", ink: "#1A1A1A", white: "#F7F4EE", paper: "#F2EBDD", light: "#C9C5BD",
    gray: "#8C8C8C", steel: "#5E5E5E", dark: "#3A3A3A", brown: "#8A6340", red: "#E5484D",
    orange: "#F2994A", yellow: "#F5C542", green: "#3DDC6E", mint: "#7CFF9B", teal: "#3CB8B0",
    sky: "#9CCBF2", blue: "#4C8DF6", purple: "#9B6DF0", pink: "#F28BB8", screen: "#0D1A12",
    rose: "#F29B9B", forest: "#2F8F5B", navy: "#2D4A8A", silver: "#B0B0B0",
  };
  function color(name) {
    if (NAMED[name]) return NAMED[name];
    if (/^#[0-9a-fA-F]{3,8}$/.test(name)) return name;
    throw new Error(`Unknown color: ${name}`);
  }

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function createClawd(svg, { x: ox, y: oy, groundClipId = "ground-clip" }) {
    const ground = oy + 86;

    const defs = svg.querySelector("defs") || el("defs", {}, svg);
    el("rect", { x: 0, y: 0, width: svg.viewBox.baseVal.width, height: ground },
      el("clipPath", { id: groundClipId }, defs));

    const root = el("g", { class: "clawd", "shape-rendering": "crispEdges" }, svg);
    const inner = el("g", {}, root);     // pulse / spin act on `inner`; move / hop / shake on `root`

    // Legs: thin, four of them, clipped by the ground so squash/stretch never sinks.
    const legsClip = el("g", { "clip-path": `url(#${groundClipId})` }, inner);
    const legXs = [17, 36, 62, 81];
    const legs = legXs.map((lx) => {
      const leg = el("rect", {
        x: ox + lx, y: oy + 58, width: 11, height: 28, fill: PALETTE.body,
      }, legsClip);
      leg.footPivot = `${ox + lx + 5.5} ${ground}`;
      return leg;
    });

    // Upper body: body + eyes + hands (flat, single color: no shading), rotated as one piece.
    const upper = el("g", {}, inner);
    el("rect", { x: ox + 14, y: oy + 12, width: 78, height: 52, fill: PALETTE.body }, upper);
    // Bridges: flat body-colored rects that fill the gap when a hand slides away from the body (they follow the hand in y).
    const armL = el("rect", { x: ox, y: oy + 38, width: 18, height: 22, fill: PALETTE.body }, upper);
    armL.base = { x: ox, w: 18 };
    const handL = el("rect", { x: ox - 8, y: oy + 38, width: 22, height: 22, fill: PALETTE.body }, upper);
    const armR = el("rect", { x: ox + 88, y: oy + 38, width: 14, height: 22, fill: PALETTE.body }, upper);
    armR.base = { x: ox + 88, w: 14 };
    const handR = el("rect", { x: ox + 92, y: oy + 38, width: 22, height: 22, fill: PALETTE.body }, upper);

    const eyes = el("g", {}, upper);
    const eyeL = el("rect", { x: ox + 33, y: oy + 28, width: 8, height: 11, fill: PALETTE.eye }, eyes);
    const eyeR = el("rect", { x: ox + 65, y: oy + 28, width: 8, height: 11, fill: PALETTE.eye }, eyes);

    // Closed-eye arcs ("^"): three rects, same color as the eyes, swapped in by the blink.
    const makeArc = (ex, ey) => {
      const g = el("g", { opacity: 0 }, eyes);
      el("rect", { x: ex + 2, y: ey + 3.5, width: 4, height: 2, fill: PALETTE.eye }, g);
      el("rect", { x: ex, y: ey + 5.5, width: 2, height: 2, fill: PALETTE.eye }, g);
      el("rect", { x: ex + 6, y: ey + 5.5, width: 2, height: 2, fill: PALETTE.eye }, g);
      return g;
    };
    const arcL = makeArc(ox + 33, oy + 28);
    const arcR = makeArc(ox + 65, oy + 28);

    return {
      root, inner, upper, legs, handL, handR, armL, armR, eyes, eyeL, eyeR, arcL, arcR,
      ground,
      hipPivot: `${ox + 53} ${oy + 65}`, // body pivot, same idea as svgOrigin "53 65" in the article
      PALETTE,
    };
  }

  window.Clawd = { create: createClawd, el, PALETTE, NAMED, color };
})();
