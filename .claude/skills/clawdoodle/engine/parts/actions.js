/* Actions: (tl, c, step, ctx) adds tweens to the timeline.
 * c = Clawd handles, step = one entry of scene.timeline, ctx = { refs, loop }.
 * Clawd actions: pose, wave, type, blink.  Screen actions: scroll, cursor.
 * Generic actions (any sprite id, or "clawd" for the whole character): move, hop, shake, bob, pulse, appear, disappear, swap, cycle, spin.
 * Poses carry the weight (lean / squash) like in the Codrops breakdown. Everything stays flat and made of rects. */
(function () {
  // A pose is a full description; unspecified fields fall back to REST. Units are scene units (Clawd's body is 78 wide).
  const REST = {
    rot: 0, x: 0, y: 0, squash: 1,
    eyes: { x: 0, y: 0 }, hR: { x: 0, y: 0, ext: 0 }, hL: { x: 0, y: 0, ext: 0 },
    legRot: [0, 0, 0, 0], legScale: [1, 1, 1, 1], legX: [0, 0, 0, 0],
  };
  const P = (o) => Object.assign({}, REST, o);
  const POSES = {
    rest: REST,
    lean: P({ rot: 3, x: 4, y: -3, eyes: { x: 3, y: 0 }, hR: { x: 8, y: 2, ext: 0 },
      legRot: [7, 8, 8, 9], legScale: [1.15, 1.15, 1.1, 1.1], legX: [-2, 0, 0, -2.5] }),
    look_l: P({ rot: -2, x: -2, eyes: { x: -5, y: 0 } }),
    look_r: P({ rot: 2, x: 2, eyes: { x: 5, y: 0 } }),
    look_up: P({ y: -1, eyes: { x: 0, y: -7 } }),
    wave: P({ rot: -2, x: -1, eyes: { x: 2, y: 0 }, hR: { x: 6, y: -28, ext: 0 } }),
    point_r: P({ rot: 2, x: 3, eyes: { x: 3, y: 0 }, hR: { x: 10, y: -6, ext: 10 } }),
    think: P({ rot: -3, x: -2, eyes: { x: -3, y: -6 }, hR: { x: 2, y: -22, ext: 0 } }),
    shrug: P({ y: 1, eyes: { x: 0, y: 2 }, hL: { x: -4, y: -14, ext: 0 }, hR: { x: 4, y: -14, ext: 0 } }),
    cheer: P({ y: -2, eyes: { x: 0, y: -3 }, hL: { x: -2, y: -34, ext: 0 }, hR: { x: 2, y: -34, ext: 0 } }),
    sad: P({ y: 4, squash: 0.92, eyes: { x: 0, y: 5 }, hL: { x: 0, y: 10, ext: 0 }, hR: { x: 0, y: 10, ext: 0 } }),
    relief: P({ y: 2, squash: 0.96, eyes: { x: 0, y: 2 }, hL: { x: 0, y: 4, ext: 0 }, hR: { x: 2, y: -20, ext: 0 } }),
    hold_r: P({ rot: 1, x: 2, eyes: { x: 3, y: 0 }, hR: { x: 6, y: -2, ext: 6 } }),
    crouch: P({ squash: 0.86, eyes: { x: 0, y: 2 }, hL: { x: 0, y: 6, ext: 0 }, hR: { x: 0, y: 6, ext: 0 },
      legScale: [0.8, 0.8, 0.8, 0.8] }),
  };
  const actions = {};
  const target = (ctx, id) => {
    const h = ctx.refs[id];
    if (!h || !h.g) throw new Error(`Action target '${id}' is not a sprite or "clawd"`);
    return h;
  };

  // ---- Clawd ----

  // Move the whole character to a named pose; everything lands on the same beat.
  actions.pose = (tl, c, s) => {
    const Q = POSES[s.pose];
    if (!Q) throw new Error(`Unknown pose: ${s.pose}`);
    const d = s.dur ?? 0.4, ease = s.ease ?? "power2.out", bodyEase = s.bodyEase ?? ease, at = s.at;
    tl.to(c.upper, { rotation: Q.rot, x: Q.x, y: Q.y, scaleY: Q.squash, svgOrigin: c.hipPivot, duration: d, ease: bodyEase }, at)
      .to(c.eyes, { x: Q.eyes.x, y: Q.eyes.y, duration: d, ease }, at)
      .to(c.handR, { x: Q.hR.x, duration: d, ease }, at)
      .to([c.handR, c.armR], { y: Q.hR.y, duration: d, ease }, at)
      .to(c.armR, { attr: { width: c.armR.base.w + Q.hR.ext }, duration: d, ease }, at)
      .to(c.handL, { x: Q.hL.x, duration: d, ease }, at)
      .to([c.handL, c.armL], { y: Q.hL.y, duration: d, ease }, at)
      .to(c.armL, { attr: { x: c.armL.base.x - Q.hL.ext, width: c.armL.base.w + Q.hL.ext }, duration: d, ease }, at)
      .to(c.legs, {
        rotation: (i) => Q.legRot[i], x: (i) => Q.legX[i], scaleY: (i) => Q.legScale[i],
        svgOrigin: (i, t) => t.footPivot, duration: d, ease,
      }, at);
    // Back to the neutral pose: drop the transforms so float residue (e.g. 23.9999) can't shift the body 1px vs frame 0.
    if (!Q.rot && !Q.x && !Q.y && Q.squash === 1) tl.set([c.upper, c.legs], { clearProps: "transform" }, at + d);
  };

  // Wave the right hand side to side (use after the `wave` pose); `count` full swings in `dur` seconds.
  actions.wave = (tl, c, s) => {
    const n = s.count ?? 3, d = s.dur ?? 1, amp = s.amp ?? 5;
    tl.to(c.handR, { x: `+=${amp}`, duration: d / (2 * n), ease: "sine.inOut", yoyo: true, repeat: 2 * n - 1 }, s.at);
  };

  // Right hand taps a keyboard; body gives a tiny bounce around the given pose's y.
  actions.type = (tl, c, s, ctx) => {
    const kb = ctx.refs[s.target], base = POSES[s.pose ?? "rest"], baseY = base.y, baseHandY = base.hR.y;
    s.taps.forEach((dt, i) => {
      const t = s.at + dt, key = kb.keys[i % kb.keys.length];
      tl.to(c.upper, { y: baseY + 1, duration: 0.05, ease: "power2.in" }, t)
        .to(c.upper, { y: baseY, duration: 0.09, ease: "power2.out" }, t + 0.05)
        .to([c.handR, c.armR], { y: baseHandY + 2, duration: 0.06, ease: "power2.in" }, t)
        .set(key, { fill: kb.keyOn }, t + 0.04)
        .to([c.handR, c.armR], { y: baseHandY, duration: 0.08, ease: "power2.out" }, t + 0.06)
        .set(key, { fill: kb.keyOff }, t + 0.16);
    });
  };

  // Blink: swap open eyes for "^ ^" arcs for `hold` seconds.
  actions.blink = (tl, c, s) => {
    const hold = s.hold ?? 0.22;
    tl.set([c.eyeL, c.eyeR], { opacity: 0 }, s.at).set([c.arcL, c.arcR], { opacity: 1 }, s.at)
      .set([c.eyeL, c.eyeR], { opacity: 1 }, s.at + hold).set([c.arcL, c.arcR], { opacity: 0 }, s.at + hold);
  };

  // ---- CRT screen ----

  // Scroll a screen's content one row per step; `dur` should equal the scene loop for a seamless loop.
  actions.scroll = (tl, c, s, ctx) => {
    const h = ctx.refs[s.target];
    tl.fromTo(h.scroll, { y: 0 }, { y: -h.rows * h.rowH, duration: s.dur ?? ctx.loop, ease: `steps(${h.rows})`, immediateRender: false }, s.at);
  };

  // Blink a screen's cursor every `every` seconds.
  actions.cursor = (tl, c, s, ctx) => {
    const h = ctx.refs[s.target], every = s.every ?? 0.4, n = Math.floor((s.dur ?? ctx.loop) / every);
    for (let i = 0; i < n; i++) tl.set(h.cursor, { opacity: i % 2 ? 0 : 1 }, s.at + i * every);
  };

  // ---- Generic (any sprite id, or "clawd") ----
  // Every generic action starts from the object's NOMINAL position (ctx.pos, tracked by render.js in chronological order) and uses
  // absolute fromTo values with immediateRender:false. The result therefore does not depend on how the timeline is played
  // (continuous playback vs seeking to a time, as the GIF and SVG exporters do), even when a return overlaps the next departure.
  // Position history per object: segments {t0, from, to}. posAt(t) = where the object has settled by time t (the `to` of the latest segment
  // that started at or before t), so an action during a hold (e.g. a shake while the object waits displaced) starts from the right place.
  const segs = (ctx, id) => (ctx.segs[id] = ctx.segs[id] || []);
  const addSeg = (ctx, id, t0, from, to) => segs(ctx, id).push({ t0, from, to });
  const posAt = (ctx, id, t) => {
    let best = null;
    for (const sg of segs(ctx, id)) if (sg.t0 <= t + 1e-9 && (!best || sg.t0 >= best.t0)) best = sg;
    return best ? { x: best.to.x, y: best.to.y } : { x: 0, y: 0 };
  };
  const slide = (tl, g, from, to, d, ease, at) => {
    const f = {}, t = { duration: d, ease, immediateRender: false };
    if (from.x !== to.x) { f.x = from.x; t.x = to.x; }
    if (from.y !== to.y) { f.y = from.y; t.y = to.y; }
    if (Object.keys(f).length) tl.fromTo(g, f, t, at);
  };

  // Slide by (dx, dy) from the current nominal position. With `back: true` it returns after `hold` seconds; without it, it stays there.
  actions.move = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), d = s.dur ?? 0.4, ease = s.ease ?? "power2.inOut";
    const from = posAt(ctx, s.target, s.at), to = { x: from.x + (s.dx ?? 0), y: from.y + (s.dy ?? 0) };
    slide(tl, h.g, from, to, d, ease, s.at);
    addSeg(ctx, s.target, s.at, from, to);
    if (s.back) {
      const tb = s.at + d + (s.hold ?? 0);
      slide(tl, h.g, to, from, d, ease, tb);
      addSeg(ctx, s.target, tb, to, from);
    }
  };

  // Go to an ABSOLUTE scene position (the object's top-left; Clawd's top-left for "clawd"). `dur: 0` teleports (useful to reset a hidden object).
  actions.moveTo = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), d = s.dur ?? 0.4, ease = s.ease ?? "power2.inOut";
    const from = posAt(ctx, s.target, s.at);
    const to = { x: s.x !== undefined ? s.x - h.base.x : from.x, y: s.y !== undefined ? s.y - h.base.y : from.y };
    const go = (a, b, at) => (d === 0 ? tl.set(h.g, { x: b.x, y: b.y }, at) : slide(tl, h.g, a, b, d, ease, at));
    go(from, to, s.at);
    addSeg(ctx, s.target, s.at, from, to);
    if (s.back) {
      const tb = s.at + d + (s.hold ?? 0);
      go(to, from, tb);
      addSeg(ctx, s.target, tb, to, from);
    }
  };

  // Jump up `h` units and land; up slower (sine.out), down faster (power3.in) so it reads as gravity. `count` hops in a row.
  actions.hop = (tl, c, s, ctx) => {
    const g = target(ctx, s.target).g, p = posAt(ctx, s.target, s.at), h = s.h ?? 14, d = s.dur ?? 0.5, n = s.count ?? 1;
    for (let k = 0; k < n; k++) {
      const t = s.at + k * d;
      tl.fromTo(g, { y: p.y }, { y: p.y - h, duration: d * 0.55, ease: "sine.out", immediateRender: false }, t)
        .fromTo(g, { y: p.y - h }, { y: p.y, duration: d * 0.45, ease: "power3.in", immediateRender: false }, t + d * 0.55);
    }
  };

  // Shake side to side `count` times in `dur` seconds, ending where it started.
  actions.shake = (tl, c, s, ctx) => {
    const g = target(ctx, s.target).g, p = posAt(ctx, s.target, s.at), n = s.count ?? 4, d = s.dur ?? 0.4, amp = s.amp ?? 3;
    tl.fromTo(g, { x: p.x }, { x: p.x + amp, duration: d / (2 * n), ease: "sine.inOut", yoyo: true, repeat: 2 * n - 1, immediateRender: false }, s.at);
  };

  // Float up and down continuously: one cycle every `every` seconds for `dur` seconds (whole cycles only).
  actions.bob = (tl, c, s, ctx) => {
    const g = target(ctx, s.target).g, p = posAt(ctx, s.target, s.at), amp = s.amp ?? 3, every = s.every ?? 0.8;
    const n = Math.max(1, Math.floor((s.dur ?? (ctx.loop - s.at)) / every));
    tl.fromTo(g, { y: p.y }, { y: p.y - amp, duration: every / 2, ease: "sine.inOut", yoyo: true, repeat: 2 * n - 1, immediateRender: false }, s.at);
  };

  // Grow by `scale` around the object's center and settle back in `dur` seconds (on the inner layer, so it composes with any move).
  actions.pulse = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), k = s.scale ?? 1.15, d = s.dur ?? 0.3, origin = `${h.cx} ${h.cy}`, tg = h.inner || h.g;
    tl.to(tg, { scale: k, svgOrigin: origin, duration: d / 2, ease: "power2.out" }, s.at)
      .to(tg, { scale: 1, svgOrigin: origin, duration: d / 2, ease: "power2.in" }, s.at + d / 2);
  };

  // Show / hide (instant, or a fade of `fade` seconds). A sprite can start hidden with "hidden": true.
  actions.appear = (tl, c, s, ctx) => {
    const g = target(ctx, s.target).g;
    // immediateRender:false -> the "from" state is applied when the tween starts, not when it is created (else the object would be hidden from t=0)
    s.fade ? tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: s.fade, ease: "none", immediateRender: false }, s.at) : tl.set(g, { opacity: 1 }, s.at);
  };
  actions.disappear = (tl, c, s, ctx) => {
    const g = target(ctx, s.target).g;
    s.fade ? tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: s.fade, ease: "none", immediateRender: false }, s.at) : tl.set(g, { opacity: 0 }, s.at);
  };

  // Recolor a sprite without redrawing frames: map = { "<palette char>": "<color name>" }; `dur` 0 = instant. Put it back (second recolor) before the loop ends.
  actions.recolor = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), d = s.dur ?? 0.3;
    for (const ch in s.map) {
      const rects = h.g.querySelectorAll(`rect[data-c="${CSS.escape(ch)}"]`), col = window.Clawd.color(s.map[ch]);
      if (!rects.length) continue;
      d ? tl.to(rects, { fill: col, duration: d, ease: "none" }, s.at) : tl.set(rects, { fill: col }, s.at);
    }
  };

  // Multi-frame sprites: show frame `frame` at time `at`, or cycle through `frames` every `every` seconds for `dur`
  // (then go back to frame 0 unless `end` says otherwise).
  const showFrame = (tl, h, k, at) => h.frames.forEach((f, j) => tl.set(f, { display: j === k ? "inline" : "none" }, at));
  actions.swap = (tl, c, s, ctx) => showFrame(tl, target(ctx, s.target), s.frame, s.at);
  actions.cycle = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), dur = s.dur ?? (ctx.loop - s.at), n = Math.floor(dur / s.every);
    for (let i = 0; i < n; i++) showFrame(tl, h, s.frames[i % s.frames.length], s.at + i * s.every);
    showFrame(tl, h, s.end ?? 0, s.at + dur);
  };

  // Rotate `turns` full turns in `steps` discrete jumps (a gear, a loading wheel), landing on the starting look.
  actions.spin = (tl, c, s, ctx) => {
    const h = target(ctx, s.target), d = s.dur ?? 1, steps = s.steps ?? 8;
    tl.fromTo(h.inner || h.g, { rotation: 0 }, { rotation: 360 * (s.turns ?? 1), svgOrigin: `${h.cx} ${h.cy}`, duration: d, ease: `steps(${steps})`, immediateRender: false }, s.at);
  };

  window.Clawd.actions = actions;
  window.Clawd.poses = POSES;
})();
