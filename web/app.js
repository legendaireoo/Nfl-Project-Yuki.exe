/* Yuki.exe — frontend controller. Vanilla JS, no frameworks. */
(function () {
  "use strict";

  const C = window.YukiCharts;
  const api = (path) => fetch(path).then((r) => r.json());

  // ---- tab navigation ---------------------------------------------------
  const loaded = {};
  document.getElementById("tabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    const view = btn.dataset.view;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === btn));
    document.querySelectorAll(".view").forEach((v) =>
      v.classList.toggle("active", v.id === "view-" + view)
    );
    render(view);
  });

  function render(view) {
    if (loaded[view]) {
      if (view === "overview" || view === "coverage" || view === "teams") redraw(view);
      return;
    }
    loaded[view] = true;
    if (view === "overview") loadOverview();
    else if (view === "coverage") loadCoverage();
    else if (view === "rush") loadRush();
    else if (view === "block") loadBlock();
    else if (view === "teams") loadTeams();
    else if (view === "viewer") loadViewer();
  }

  // cache data for redraw-on-resize/tab-return
  const cache = {};
  function redraw(view) {
    if (view === "overview" && cache.overview) drawOverview(cache.overview);
    if (view === "coverage" && cache.coverage) drawCoverage(cache.coverage);
    if (view === "teams" && cache.teams) drawTeams(cache.teams);
  }
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const active = document.querySelector(".tab.active").dataset.view;
      redraw(active);
    }, 180);
  });

  // ---- OVERVIEW ---------------------------------------------------------
  function loadOverview() {
    api("/api/overview").then((d) => {
      cache.overview = d;
      drawOverview(d);
    });
  }
  function drawOverview(d) {
    const cards = [
      { label: "Games", value: d.games },
      { label: "Players", value: d.players },
      { label: "Plays", value: d.plays.toLocaleString() },
      { label: "Completion %", value: d.completionPct + "%", cls: "accent" },
      { label: "Avg Yards / Play", value: d.avgYards, cls: "accent" },
      { label: "Play-Action %", value: d.playActionPct + "%", cls: "warn" },
      { label: "Total Pressures", value: d.totalPressures.toLocaleString(), cls: "danger" },
      { label: "Sacks", value: d.sacks, cls: "danger" },
    ];
    document.getElementById("statCards").innerHTML = cards
      .map((c) => `<div class="card ${c.cls || ""}"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
      .join("");

    const covData = Object.entries(d.coverages)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
    C.donut(document.getElementById("covChart"), covData);

    const resMap = { C: "Complete", I: "Incomplete", S: "Sack", R: "Scramble", IN: "Interception", NA: "Other" };
    const resData = Object.entries(d.passResults)
      .map(([k, v]) => ({ label: resMap[k] || k, value: v }))
      .sort((a, b) => b.value - a.value);
    C.bar(document.getElementById("resChart"), resData, { horizontal: true });

    const formData = Object.entries(d.formations)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
    C.bar(document.getElementById("formChart"), formData, { color: C.PALETTE[1] });
  }

  // ---- COVERAGE ---------------------------------------------------------
  function loadCoverage() {
    api("/api/coverage").then((d) => {
      cache.coverage = d;
      drawCoverage(d);
    });
  }
  function drawCoverage(d) {
    const filtered = d.filter((r) => r.plays >= 20);
    C.groupedBar(
      document.getElementById("coverageBar"),
      filtered.map((r) => ({ label: r.coverage, a: r.completionPct, b: r.avgYards })),
      { aLabel: "Completion %", bLabel: "Avg Yards" }
    );
    const rows = d
      .map(
        (r) => `<tr>
          <td>${r.coverage}</td>
          <td class="num">${r.plays.toLocaleString()}</td>
          <td class="num">${r.completionPct}%</td>
          <td class="num">${r.avgYards}</td>
        </tr>`
      )
      .join("");
    document.getElementById("coverageTable").innerHTML =
      `<thead><tr><th>Coverage</th><th class="num">Plays</th><th class="num">Comp %</th><th class="num">Avg Yds</th></tr></thead><tbody>${rows}</tbody>`;
  }

  // ---- PASS RUSH --------------------------------------------------------
  function loadRush() {
    api("/api/pass-rush").then((d) => {
      const max = Math.max(...d.map((r) => r.pressures), 1);
      const rows = d
        .map(
          (r, i) => `<tr>
            <td class="rank">${i + 1}</td>
            <td>${r.name}</td>
            <td>${r.position}</td>
            <td class="num">${r.snaps}</td>
            <td class="num">${r.sacks}</td>
            <td class="num">${r.hits}</td>
            <td class="num">${r.hurries}</td>
            <td class="num bar-cell"><div class="bar" style="width:${(r.pressures / max) * 100}%"></div><span>${r.pressures}</span></td>
            <td class="num">${r.pressureRate}%</td>
          </tr>`
        )
        .join("");
      document.getElementById("rushTable").innerHTML =
        `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Snaps</th><th class="num">Sacks</th><th class="num">Hits</th><th class="num">Hurries</th><th class="num">Pressures</th><th class="num">Rate</th></tr></thead><tbody>${rows}</tbody>`;
    });
  }

  // ---- PASS BLOCK -------------------------------------------------------
  function loadBlock() {
    api("/api/pass-block").then((d) => {
      const rows = d
        .map(
          (r, i) => `<tr>
            <td class="rank">${i + 1}</td>
            <td>${r.name}</td>
            <td>${r.position}</td>
            <td class="num">${r.snaps}</td>
            <td class="num">${r.sacksAllowed}</td>
            <td class="num">${r.hitsAllowed}</td>
            <td class="num">${r.hurriesAllowed}</td>
            <td class="num">${r.pressuresAllowed}</td>
            <td class="num">${r.pressureAllowedRate}%</td>
          </tr>`
        )
        .join("");
      document.getElementById("blockTable").innerHTML =
        `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Snaps</th><th class="num">Sacks All.</th><th class="num">Hits All.</th><th class="num">Hurries All.</th><th class="num">Pressures All.</th><th class="num">Rate</th></tr></thead><tbody>${rows}</tbody>`;
    });
  }

  // ---- TEAMS ------------------------------------------------------------
  function loadTeams() {
    api("/api/teams").then((d) => {
      cache.teams = d;
      drawTeams(d);
    });
  }
  function drawTeams(d) {
    C.scatter(
      document.getElementById("teamScatter"),
      d.map((r) => ({ x: r.pressureAllowedRate, y: r.pressureRate, label: r.team })),
      { xLabel: "Pressure rate allowed (offense) %", yLabel: "Pressure rate generated (defense) %" }
    );
    const rows = d
      .map(
        (r) => `<tr>
          <td>${r.team}</td>
          <td class="num">${r.rushSnaps}</td>
          <td class="num">${r.pressuresGenerated}</td>
          <td class="num">${r.pressureRate}%</td>
          <td class="num">${r.blockSnaps}</td>
          <td class="num">${r.pressuresAllowed}</td>
          <td class="num">${r.pressureAllowedRate}%</td>
        </tr>`
      )
      .join("");
    document.getElementById("teamTable").innerHTML =
      `<thead><tr><th>Team</th><th class="num">Rush Snaps</th><th class="num">Pressures</th><th class="num">Pass-Rush Rate</th><th class="num">Block Snaps</th><th class="num">Pressures All.</th><th class="num">Pressure-All. Rate</th></tr></thead><tbody>${rows}</tbody>`;
  }

  // ---- PLAY VIEWER ------------------------------------------------------
  let viewer;
  function loadViewer() {
    const fieldCanvas = document.getElementById("field");
    const slider = document.getElementById("frameSlider");
    const frameLabel = document.getElementById("frameLabel");
    const eventLabel = document.getElementById("eventLabel");
    const playBtn = document.getElementById("playBtn");

    viewer = YukiField.makeViewer(fieldCanvas, {
      onFrame: (i, total, event) => {
        slider.value = i;
        frameLabel.textContent = `frame ${i + 1} / ${total}`;
        eventLabel.textContent = event ? "● " + event : "";
      },
      onEnd: () => { playBtn.textContent = "▶ Play"; },
    });

    api("/api/games").then((games) => {
      const gSel = document.getElementById("gameSelect");
      gSel.innerHTML = games
        .map((g) => `<option value="${g.gameId}">${g.label}</option>`)
        .join("");
      gSel.addEventListener("change", () => loadPlays(gSel.value));
      if (games.length) loadPlays(games[0].gameId);
    });

    const pSel = document.getElementById("playSelect");
    pSel.addEventListener("change", () => loadPlay(document.getElementById("gameSelect").value, pSel.value));

    playBtn.addEventListener("click", () => {
      if (!viewer.frameCount) return;
      if (playBtn.textContent.startsWith("▶")) {
        if (viewer.frameIdx >= viewer.frameCount - 1) viewer.reset();
        viewer.play();
        playBtn.textContent = "⏸ Pause";
      } else {
        viewer.stop();
        playBtn.textContent = "▶ Play";
      }
    });
    document.getElementById("resetBtn").addEventListener("click", () => {
      viewer.reset();
      playBtn.textContent = "▶ Play";
    });
    slider.addEventListener("input", () => {
      viewer.stop();
      playBtn.textContent = "▶ Play";
      viewer.setFrame(parseInt(slider.value, 10));
    });
  }

  function loadPlays(gameId) {
    const pSel = document.getElementById("playSelect");
    pSel.innerHTML = `<option>Loading…</option>`;
    api(`/api/plays?gameId=${gameId}`).then((plays) => {
      pSel.innerHTML = plays
        .map((p) => {
          const desc = p.description.length > 70 ? p.description.slice(0, 68) + "…" : p.description;
          return `<option value="${p.playId}">Q${p.quarter} ${p.down}&amp;${p.yardsToGo} [${p.coverage}] ${desc}</option>`;
        })
        .join("");
      if (plays.length) loadPlay(gameId, plays[0].playId);
    });
  }

  function loadPlay(gameId, playId) {
    document.getElementById("playDesc").textContent = "Loading play…";
    api(`/api/play?gameId=${gameId}&playId=${playId}`).then((play) => {
      const m = play.meta || {};
      document.getElementById("playDesc").innerHTML =
        `<strong>${m.possessionTeam} vs ${m.defensiveTeam}</strong> · Q${m.quarter} · ${m.down} &amp; ${m.yardsToGo} · ` +
        `Coverage: <strong>${m.coverage || "?"}</strong> · Result: <strong>${m.passResult || "?"}</strong><br>${m.description || ""}`;
      const slider = document.getElementById("frameSlider");
      slider.max = Math.max(0, play.frameCount - 1);
      slider.value = 0;
      viewer.load(play);
      document.getElementById("playBtn").textContent = "▶ Play";
    });
  }

  // initial view
  render("overview");
})();
