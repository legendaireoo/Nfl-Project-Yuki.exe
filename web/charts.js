/* Yuki.exe — tiny vanilla-canvas chart helpers. No external libraries. */
(function (global) {
  "use strict";

  const PALETTE = [
    "#4f9dff", "#37d6a0", "#ffbf47", "#ff6b6b", "#b78bff",
    "#45c2d9", "#ff9f68", "#7ee787", "#f778ba", "#a5a9ff",
    "#ffd166", "#06d6a0",
  ];

  function setupHiDPI(canvas) {
    const ratio = global.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const cssW = rect.width || canvas.width;
    const cssH = canvas.height; // height is fixed via attribute
    canvas.width = cssW * ratio;
    canvas.height = cssH * ratio;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx, w: cssW, h: cssH };
  }

  function clear(ctx, w, h) {
    ctx.clearRect(0, 0, w, h);
  }

  /* Horizontal/vertical bar chart.
     data: [{label, value}], opts: {horizontal, color, valueFmt} */
  function bar(canvas, data, opts) {
    opts = opts || {};
    const { ctx, w, h } = setupHiDPI(canvas);
    clear(ctx, w, h);
    if (!data.length) return;

    const pad = { top: 16, right: 18, bottom: 28, left: opts.horizontal ? 120 : 40 };
    const maxV = Math.max(...data.map((d) => d.value), 1);
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    ctx.font = "12px Segoe UI, sans-serif";
    ctx.fillStyle = "#8c9bb3";

    if (opts.horizontal) {
      const bh = Math.min(26, (plotH / data.length) * 0.7);
      const gap = plotH / data.length;
      data.forEach((d, i) => {
        const y = pad.top + gap * i + (gap - bh) / 2;
        const bw = (d.value / maxV) * plotW;
        ctx.fillStyle = opts.color || PALETTE[i % PALETTE.length];
        roundRect(ctx, pad.left, y, Math.max(bw, 1), bh, 4);
        ctx.fill();
        ctx.fillStyle = "#e6edf6";
        ctx.textAlign = "right";
        ctx.fillText(d.label, pad.left - 8, y + bh / 2 + 4);
        ctx.textAlign = "left";
        const vtxt = opts.valueFmt ? opts.valueFmt(d.value) : String(d.value);
        ctx.fillText(vtxt, pad.left + bw + 6, y + bh / 2 + 4);
      });
    } else {
      const bw = Math.min(60, (plotW / data.length) * 0.65);
      const gap = plotW / data.length;
      data.forEach((d, i) => {
        const x = pad.left + gap * i + (gap - bw) / 2;
        const bh = (d.value / maxV) * plotH;
        const y = pad.top + plotH - bh;
        ctx.fillStyle = opts.color || PALETTE[i % PALETTE.length];
        roundRect(ctx, x, y, bw, Math.max(bh, 1), 4);
        ctx.fill();
        ctx.fillStyle = "#e6edf6";
        ctx.textAlign = "center";
        const vtxt = opts.valueFmt ? opts.valueFmt(d.value) : String(d.value);
        ctx.fillText(vtxt, x + bw / 2, y - 5);
        ctx.fillStyle = "#8c9bb3";
        ctx.save();
        ctx.translate(x + bw / 2, pad.top + plotH + 14);
        const lbl = d.label.length > 10 ? d.label.slice(0, 9) + "…" : d.label;
        ctx.fillText(lbl, 0, 0);
        ctx.restore();
        ctx.textAlign = "left";
      });
    }
  }

  /* Grouped bar: two series per category.
     data: [{label, a, b}], opts: {aLabel, bLabel, aFmt, bFmt} */
  function groupedBar(canvas, data, opts) {
    opts = opts || {};
    const { ctx, w, h } = setupHiDPI(canvas);
    clear(ctx, w, h);
    if (!data.length) return;

    const pad = { top: 20, right: 18, bottom: 44, left: 40 };
    const maxA = Math.max(...data.map((d) => d.a), 0.01);
    const maxB = Math.max(...data.map((d) => d.b), 0.01);
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;
    const gap = plotW / data.length;
    const bw = Math.min(26, (gap / 2) * 0.8);

    ctx.font = "11.5px Segoe UI, sans-serif";
    data.forEach((d, i) => {
      const cx = pad.left + gap * i + gap / 2;
      const ah = (d.a / maxA) * plotH;
      const bh = (d.b / maxB) * plotH;
      // series A
      ctx.fillStyle = PALETTE[0];
      roundRect(ctx, cx - bw - 2, pad.top + plotH - ah, bw, Math.max(ah, 1), 3);
      ctx.fill();
      // series B
      ctx.fillStyle = PALETTE[1];
      roundRect(ctx, cx + 2, pad.top + plotH - bh, bw, Math.max(bh, 1), 3);
      ctx.fill();
      // label
      ctx.fillStyle = "#8c9bb3";
      ctx.textAlign = "center";
      ctx.save();
      ctx.translate(cx, pad.top + plotH + 12);
      ctx.rotate(-Math.PI / 5);
      ctx.fillText(d.label, 0, 0);
      ctx.restore();
    });
    ctx.textAlign = "left";
    // legend
    ctx.fillStyle = PALETTE[0];
    roundRect(ctx, pad.left, 2, 10, 10, 2); ctx.fill();
    ctx.fillStyle = "#e6edf6";
    ctx.fillText(opts.aLabel || "A", pad.left + 15, 11);
    const bx = pad.left + 15 + ctx.measureText(opts.aLabel || "A").width + 16;
    ctx.fillStyle = PALETTE[1];
    roundRect(ctx, bx, 2, 10, 10, 2); ctx.fill();
    ctx.fillStyle = "#e6edf6";
    ctx.fillText(opts.bLabel || "B", bx + 15, 11);
  }

  /* Donut chart. data: [{label, value}] */
  function donut(canvas, data) {
    const { ctx, w, h } = setupHiDPI(canvas);
    clear(ctx, w, h);
    if (!data.length) return;

    const total = data.reduce((s, d) => s + d.value, 0) || 1;
    const cx = Math.min(w, h) / 2 + 10;
    const cy = h / 2;
    const rOuter = Math.min(cx, cy) - 14;
    const rInner = rOuter * 0.58;

    let angle = -Math.PI / 2;
    data.forEach((d, i) => {
      const slice = (d.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, rOuter, angle, angle + slice);
      ctx.closePath();
      ctx.fillStyle = PALETTE[i % PALETTE.length];
      ctx.fill();
      angle += slice;
    });
    // inner hole
    ctx.beginPath();
    ctx.arc(cx, cy, rInner, 0, Math.PI * 2);
    ctx.fillStyle = "#141b27";
    ctx.fill();
    ctx.fillStyle = "#e6edf6";
    ctx.font = "bold 18px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(total.toLocaleString(), cx, cy + 2);
    ctx.font = "11px Segoe UI, sans-serif";
    ctx.fillStyle = "#8c9bb3";
    ctx.fillText("plays", cx, cy + 18);
    ctx.textAlign = "left";

    // legend to the right
    let ly = 20;
    const lx = cx + rOuter + 24;
    ctx.font = "12.5px Segoe UI, sans-serif";
    data.forEach((d, i) => {
      ctx.fillStyle = PALETTE[i % PALETTE.length];
      roundRect(ctx, lx, ly - 9, 11, 11, 3); ctx.fill();
      ctx.fillStyle = "#e6edf6";
      const pct = ((d.value / total) * 100).toFixed(1);
      ctx.fillText(`${d.label} — ${pct}%`, lx + 18, ly);
      ly += 21;
    });
  }

  /* Scatter. data: [{x, y, label}], opts: {xLabel, yLabel} */
  function scatter(canvas, data, opts) {
    opts = opts || {};
    const { ctx, w, h } = setupHiDPI(canvas);
    clear(ctx, w, h);
    if (!data.length) return;

    const pad = { top: 20, right: 24, bottom: 46, left: 56 };
    const xs = data.map((d) => d.x), ys = data.map((d) => d.y);
    const minX = Math.min(...xs) * 0.95, maxX = Math.max(...xs) * 1.05;
    const minY = Math.min(...ys) * 0.95, maxY = Math.max(...ys) * 1.05;
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const sx = (x) => pad.left + ((x - minX) / (maxX - minX || 1)) * plotW;
    const sy = (y) => pad.top + plotH - ((y - minY) / (maxY - minY || 1)) * plotH;

    // axes + gridlines
    ctx.strokeStyle = "#243044";
    ctx.lineWidth = 1;
    ctx.font = "11px Segoe UI, sans-serif";
    ctx.fillStyle = "#8c9bb3";
    for (let i = 0; i <= 4; i++) {
      const gy = pad.top + (plotH / 4) * i;
      ctx.beginPath(); ctx.moveTo(pad.left, gy); ctx.lineTo(pad.left + plotW, gy); ctx.stroke();
      const val = (maxY - (i / 4) * (maxY - minY)).toFixed(1);
      ctx.textAlign = "right";
      ctx.fillText(val, pad.left - 8, gy + 4);
    }
    ctx.textAlign = "center";
    ctx.fillText(opts.xLabel || "x", pad.left + plotW / 2, h - 8);
    ctx.save();
    ctx.translate(14, pad.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(opts.yLabel || "y", 0, 0);
    ctx.restore();

    // points
    data.forEach((d, i) => {
      const px = sx(d.x), py = sy(d.y);
      ctx.beginPath();
      ctx.arc(px, py, 5, 0, Math.PI * 2);
      ctx.fillStyle = PALETTE[i % PALETTE.length];
      ctx.fill();
      ctx.fillStyle = "#e6edf6";
      ctx.font = "10.5px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(d.label, px, py - 9);
    });
    ctx.textAlign = "left";
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  global.YukiCharts = { bar, groupedBar, donut, scatter, PALETTE };
})(window);
