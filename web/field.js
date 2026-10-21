/* Yuki.exe — football field renderer + play animation.
   Draws tracking frames onto a canvas. No external libraries. */
(function (global) {
  "use strict";

  const FIELD_LEN = 120; // yards (incl. end zones)
  const FIELD_WID = 53.3;

  function teamColors(play) {
    // Offense = possession team (blue), defense (red), ball (brown).
    return {
      offense: "#4f9dff",
      defense: "#ff6b6b",
      ball: "#8a5a28",
    };
  }

  function makeViewer(canvas, opts) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const margin = 10;
    const plotW = W - margin * 2;
    const plotH = H - margin * 2;

    const scaleX = plotW / FIELD_LEN;
    const scaleY = plotH / FIELD_WID;

    let play = null;
    let frameIdx = 0;
    let timer = null;

    function x2px(x) { return margin + x * scaleX; }
    function y2px(y) { return margin + (FIELD_WID - y) * scaleY; }

    function drawField() {
      // turf
      ctx.fillStyle = "#1f6b35";
      ctx.fillRect(0, 0, W, H);

      // alternating 10-yard bands for depth
      for (let yd = 10; yd < 110; yd += 20) {
        ctx.fillStyle = "rgba(255,255,255,0.03)";
        ctx.fillRect(x2px(yd), margin, 10 * scaleX, plotH);
      }

      // end zones
      ctx.fillStyle = "rgba(0,0,0,0.28)";
      ctx.fillRect(x2px(0), margin, 10 * scaleX, plotH);
      ctx.fillRect(x2px(110), margin, 10 * scaleX, plotH);

      // yard lines every 5 yards
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.lineWidth = 1;
      for (let yd = 10; yd <= 110; yd += 5) {
        ctx.beginPath();
        ctx.moveTo(x2px(yd), margin);
        ctx.lineTo(x2px(yd), margin + plotH);
        ctx.stroke();
      }
      // yardage numbers (10..50..10)
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      ctx.font = "bold 14px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      for (let yd = 20; yd <= 100; yd += 10) {
        const num = yd <= 60 ? yd - 10 : 110 - yd;
        ctx.fillText(String(num), x2px(yd), margin + 20);
        ctx.fillText(String(num), x2px(yd), margin + plotH - 8);
      }
      // sidelines
      ctx.strokeStyle = "rgba(255,255,255,0.8)";
      ctx.lineWidth = 2;
      ctx.strokeRect(x2px(0), margin, 110 * scaleX - x2px(0) + margin, plotH);
      ctx.strokeRect(margin, margin, plotW, plotH);
    }

    function drawLineOfScrimmage() {
      if (!play || !play.meta) return;
      const los = play.meta.absoluteYardlineNumber;
      if (los == null) return;
      ctx.strokeStyle = "#ffd166";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(x2px(los), margin);
      ctx.lineTo(x2px(los), margin + plotH);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    function drawFrame() {
      if (!play) { drawField(); return; }
      drawField();
      drawLineOfScrimmage();

      const colors = teamColors(play);
      const frame = play.frames[frameIdx] || [];
      const possession = play.meta ? play.meta.possessionTeam : null;

      // PPI timeline for this frame (live pressure meter + rusher spotlight)
      const ppi = play.ppi && play.ppi.series ? play.ppi.series[frameIdx] : null;
      const topRusher = ppi ? ppi.topRusher : null;

      // Locate the QB + top rusher positions first (for the heat line).
      let qbPos = null, rusherPos = null;
      const roleByTeam = {};
      frame.forEach((p) => {
        if (p.position === "QB" && possession && p.team === possession && p.x != null) {
          qbPos = { x: x2px(p.x), y: y2px(p.y) };
        }
        if (topRusher && p.nflId === topRusher && p.x != null) {
          rusherPos = { x: x2px(p.x), y: y2px(p.y) };
        }
      });

      // Heat line from the most dangerous rusher to the QB — intensity follows gauge.
      if (qbPos && rusherPos && ppi && ppi.gauge > 8) {
        const g = ppi.gauge / 100;
        ctx.save();
        ctx.strokeStyle = `rgba(255,${Math.round(180 - g * 150)},60,${0.25 + g * 0.5})`;
        ctx.lineWidth = 1 + g * 4;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(rusherPos.x, rusherPos.y);
        ctx.lineTo(qbPos.x, qbPos.y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
      }

      let eventText = "";
      frame.forEach((p) => {
        if (p.x == null || p.y == null) return;
        const px = x2px(p.x), py = y2px(p.y);
        if (p.event) eventText = p.event;

        if (p.team === "football" || p.nflId == null) {
          // ball
          ctx.beginPath();
          ctx.ellipse(px, py, 5, 3.2, 0, 0, Math.PI * 2);
          ctx.fillStyle = colors.ball;
          ctx.fill();
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 1;
          ctx.stroke();
          return;
        }

        const isOffense = possession && p.team === possession;
        const color = isOffense ? colors.offense : colors.defense;
        const isTopRusher = topRusher && p.nflId === topRusher;

        // Pulsing threat ring around the most dangerous rusher.
        if (isTopRusher && ppi && ppi.gauge > 8) {
          const g = ppi.gauge / 100;
          const pulse = 12 + 6 * Math.abs(Math.sin(frameIdx / 2));
          ctx.save();
          ctx.strokeStyle = `rgba(255,190,70,${0.35 + g * 0.5})`;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(px, py, pulse, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        }

        // direction indicator
        if (p.dir != null) {
          const rad = (p.dir - 90) * Math.PI / 180;
          ctx.strokeStyle = "rgba(255,255,255,0.6)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(px, py);
          ctx.lineTo(px + Math.cos(rad) * 12, py + Math.sin(rad) * 12);
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(px, py, 8, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = isTopRusher ? "#ffbe46" : "rgba(0,0,0,0.5)";
        ctx.lineWidth = isTopRusher ? 2 : 1;
        ctx.stroke();

        ctx.fillStyle = "#fff";
        ctx.font = "bold 9px Segoe UI, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(p.jersey || "", px, py);
        ctx.textBaseline = "alphabetic";
      });

      if (opts.onFrame) {
        opts.onFrame(frameIdx, play.frameCount, eventText, ppi ? ppi.gauge : null);
      }
    }

    function load(p) {
      stop();
      play = p;
      frameIdx = 0;
      drawFrame();
    }

    function setFrame(i) {
      if (!play) return;
      frameIdx = Math.max(0, Math.min(i, play.frameCount - 1));
      drawFrame();
    }

    function playAnim() {
      if (!play) return;
      stop();
      timer = setInterval(() => {
        if (frameIdx >= play.frameCount - 1) { stop(); if (opts.onEnd) opts.onEnd(); return; }
        frameIdx++;
        drawFrame();
      }, 100); // 10 fps ≈ tracking cadence
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    function reset() { stop(); setFrame(0); }

    drawField();

    return { load, setFrame, play: playAnim, stop, reset, get frameIdx() { return frameIdx; }, get frameCount() { return play ? play.frameCount : 0; } };
  }

  global.YukiField = { makeViewer };
})(window);
