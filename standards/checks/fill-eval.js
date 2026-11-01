(() => {
  // The same rule as measure_fill.py, on the app's own Chromium. The body band (y 200 to 968) is
  // rastered into a 12x16 grid, every visible content box marks the cells it touches, and a page
  // fails when it covers too little of the band or leaves the lower half empty. A box counts when
  // it carries text of its own or draws something; an svg frame with nothing drawn in it does not.
  const BODY_TOP = 200, BODY_BOTTOM = 968, MID = (BODY_TOP + BODY_BOTTOM) / 2;
  const COLS = 12, ROWS = 16;
  const CELL_W = 1920 / COLS, CELL_H = (BODY_BOTTOM - BODY_TOP) / ROWS;
  const slides = document.querySelectorAll("section.slide").length
    ? document.querySelectorAll("section.slide")
    : document.querySelectorAll("section.page");
  const out = [];
  let lowerRows = 0;
  for (let cy = 0; cy < ROWS; cy++) if (BODY_TOP + (cy + 0.5) * CELL_H > MID) lowerRows++;
  slides.forEach((el, i) => {
    const host = el.getBoundingClientRect();
    const rows = [];
    const walk = (node) => {
      for (const c of node.children) {
        const s = getComputedStyle(c);
        if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity) === 0) continue;
        const r = c.getBoundingClientRect();
        const hasText = Array.from(c.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());
        const graphic = ["IMG", "SVG", "RECT", "TEXT", "CANVAS"].includes(c.tagName.toUpperCase());
        const drawn = c.tagName.toUpperCase() !== "SVG" ||
          !!c.querySelector("rect,circle,ellipse,line,path,polyline,polygon,text,image,use");
        if ((hasText || graphic) && drawn && r.width > 0 && r.height > 0) {
          rows.push({ t: r.top - host.top, b: r.bottom - host.top,
                      l: r.left - host.left, r: r.right - host.left });
        }
        walk(c);
      }
    };
    walk(el);
    const inside = rows.filter((b) => b.b > BODY_TOP && b.t < BODY_BOTTOM);
    const contains = (a, b, slack) => a.t <= b.t + slack && a.b >= b.b - slack &&
      a.l <= b.l + slack && a.r >= b.r - slack;
    const bounds = (list) => {
      let crosses = 0, overlaps = 0;
      for (const b of list) if (b.b > BODY_BOTTOM + 1) crosses++;
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const a = list[i], b = list[j];
          if (contains(a, b, 2) || contains(b, a, 2)) continue;
          const w = Math.min(a.r, b.r) - Math.max(a.l, b.l);
          const h = Math.min(a.b, b.b) - Math.max(a.t, b.t);
          if (w > 2 && h > 2) overlaps++;
        }
      }
      return { crosses, overlaps };
    };
    const { crosses, overlaps } = bounds(inside);
    const cells = new Set(), lowerCells = new Set();
    let bottom = 0;
    for (const b of inside) {
      const t = Math.max(b.t, BODY_TOP), bo = Math.min(b.b, BODY_BOTTOM);
      const l = Math.max(b.l, 0), rr = Math.min(b.r, 1920);
      if (bo <= t || rr <= l) continue;
      for (let cy = Math.floor((t - BODY_TOP) / CELL_H);
           cy <= Math.floor((bo - BODY_TOP - 1e-6) / CELL_H); cy++) {
        for (let cx = Math.floor(l / CELL_W); cx <= Math.floor((rr - 1e-6) / CELL_W); cx++) {
          cells.add(cx + ":" + cy);
          if (BODY_TOP + (cy + 0.5) * CELL_H > MID) lowerCells.add(cx + ":" + cy);
        }
      }
      bottom = Math.max(bottom, Math.min(BODY_BOTTOM, b.b));
    }
    out.push({
      page: i + 1,
      share: Math.round((cells.size / (COLS * ROWS)) * 1000) / 1000,
      lower: lowerRows ? Math.round((lowerCells.size / (COLS * lowerRows)) * 1000) / 1000 : 0,
      bottom: Math.round(bottom), crosses, overlaps,
    });
  });
  return JSON.stringify(out);
})()
