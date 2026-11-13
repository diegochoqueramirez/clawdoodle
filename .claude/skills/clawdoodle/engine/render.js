/* Scene renderer: spec (see scenes/*.scene.json) -> SVG + one looping GSAP timeline.
 * spec = { name, canvas:{w,h}, loop, clawd:{x,y}, props:[{type,id,layer?,...}] (desk|keyboard|crt|sprite), timeline:[{at,action,...}] } */
(function () {
  window.Clawd.render = function (svg, spec) {
    svg.setAttribute("viewBox", `0 0 ${spec.canvas.w} ${spec.canvas.h}`);
    const defs = svg.querySelector("defs") || window.Clawd.el("defs", {}, svg);
    const ctx = { defs, ground: spec.clawd.y + 86, uid: 0, refs: {}, loop: spec.loop };

    const build = (layer) => (spec.props || [])
      .filter((p) => (p.layer || "back") === layer)
      .forEach((p) => {
        ctx.uid++;
        const make = window.Clawd.props[p.type];
        if (!make) throw new Error(`Unknown prop type: ${p.type}`);
        const h = make(svg, p, ctx);
        if (p.id) ctx.refs[p.id] = h;
      });

    build("back");                                        // behind Clawd
    const c = window.Clawd.create(svg, spec.clawd);
    ctx.refs.clawd = { g: c.root, inner: c.inner, cx: spec.clawd.x + 53, cy: spec.clawd.y + 43, kind: "clawd", base: { x: spec.clawd.x, y: spec.clawd.y } };
    build("front");                                       // in front of Clawd

    // Chronological order (stable), so each action sees the nominal position left by the ones before it.
    ctx.segs = {};
    const steps = spec.timeline.map((st, i) => [st, i]).sort((a, b) => (a[0].at - b[0].at) || (a[1] - b[1])).map((x) => x[0]);
    const tl = gsap.timeline({ repeat: -1 });
    steps.forEach((step) => {
      const act = window.Clawd.actions[step.action];
      if (!act) throw new Error(`Unknown action: ${step.action}`);
      act(tl, c, step, ctx);
    });
    tl.to({}, { duration: 0.01 }, spec.loop - 0.01);      // fixed loop length
    return tl;
  };
})();
