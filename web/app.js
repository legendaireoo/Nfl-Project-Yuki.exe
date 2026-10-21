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
    else if (view === "ppi") loadPPI();
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

  // ---- PPI (original metric) -------------------------------------------
  function loadPPI() {
    const sel = document.getElementById("ppiGames");
    sel.addEventListener("change", () => fetchPPI(sel.value));
    fetchPPI(sel.value);
  }
  function fetchPPI(games) {
    const status = document.getElementById("ppiStatus");
    status.textContent = `Computing PPI across ${games} game(s) from raw tracking…`;
    api(`/api/ppi?games=${games}`).then((d) => {
      cache.ppi = d;
      status.textContent = `✓ ${d.playsScored.toLocaleString()} dropbacks scored across ${d.gamesAnalyzed} games · league avg PPI ${d.avgPPI}`;
      drawPPI(d);
    });
  }
  function drawPPI(d) {
    const cards = [
      { label: "Games Analyzed", value: d.gamesAnalyzed },
      { label: "Dropbacks Scored", value: d.playsScored.toLocaleString() },
      { label: "League Avg PPI", value: d.avgPPI, cls: "accent" },
      { label: "Top PPI Rusher", value: (d.rushers[0] || {}).name || "—", cls: "warn" },
    ];
    document.getElementById("ppiCards").innerHTML = cards
      .map((c) => `<div class="card ${c.cls || ""}"><div class="value" style="font-size:${String(c.value).length > 10 ? 18 : 26}px">${c.value}</div><div class="label">${c.label}</div></div>`)
      .join("");

    const maxPPI = Math.max(...d.rushers.map((r) => r.totalPPI), 1);
    document.getElementById("ppiRushTable").innerHTML =
      `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Plays</th><th class="num">Total PPI</th><th class="num">PPI/Play</th></tr></thead><tbody>` +
      d.rushers.slice(0, 25).map((r, i) => `<tr>
        <td class="rank">${i + 1}</td><td>${r.name}</td><td>${r.position}</td>
        <td class="num">${r.plays}</td>
        <td class="num bar-cell"><div class="bar" style="width:${(r.totalPPI / maxPPI) * 100}%"></div><span>${r.totalPPI}</span></td>
        <td class="num">${r.ppiPerPlay}</td></tr>`).join("") +
      `</tbody>`;

    document.getElementById("ppiGhostTable").innerHTML =
      `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Ghost PPI</th><th class="num">Unrewarded Plays</th></tr></thead><tbody>` +
      d.ghostLeaders.slice(0, 15).map((r, i) => `<tr>
        <td class="rank">${i + 1}</td><td>${r.name}</td><td>${r.position}</td>
        <td class="num">${r.ghostPPI}</td><td class="num">${r.ghostPlays}</td></tr>`).join("") +
      `</tbody>`;

    C.bar(document.getElementById("ppiDefChart"),
      d.teamsDefense.slice(0, 12).map((t) => ({ label: t.team, value: t.avgPPI })),
      { horizontal: true, color: C.PALETTE[3] });
    C.bar(document.getElementById("ppiOffChart"),
      d.teamsOffense.slice(0, 12).map((t) => ({ label: t.team, value: t.avgPPI })),
      { horizontal: true, color: C.PALETTE[1] });

    document.getElementById("ppiPlaysTable").innerHTML =
      `<thead><tr><th>#</th><th class="num">PPI</th><th class="num">Time to Throw</th><th>Defense</th><th>Offense</th><th></th></tr></thead><tbody>` +
      d.topPlays.slice(0, 15).map((p, i) => `<tr>
        <td class="rank">${i + 1}</td><td class="num"><strong>${p.ppi}</strong></td>
        <td class="num">${p.timeToThrow}s</td><td>${p.def}</td><td>${p.off}</td>
        <td><a href="#" class="goplay" data-game="${p.gameId}" data-play="${p.playId}">▶ watch</a></td></tr>`).join("") +
      `</tbody>`;

    document.querySelectorAll(".goplay").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        jumpToPlay(a.dataset.game, a.dataset.play);
      });
    });
  }

  function jumpToPlay(gameId, playId) {
    document.querySelector('.tab[data-view="viewer"]').click();
    const gSel = document.getElementById("gameSelect");
    const apply = () => {
      gSel.value = gameId;
      loadPlays(gameId, playId);
    };
    if (gSel.options.length) apply();
    else setTimeout(apply, 600);
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

  function loadPlays(gameId, targetPlayId) {
    const pSel = document.getElementById("playSelect");
    pSel.innerHTML = `<option>Loading…</option>`;
    api(`/api/plays?gameId=${gameId}`).then((plays) => {
      pSel.innerHTML = plays
        .map((p) => {
          const desc = p.description.length > 70 ? p.description.slice(0, 68) + "…" : p.description;
          return `<option value="${p.playId}">Q${p.quarter} ${p.down}&amp;${p.yardsToGo} [${p.coverage}] ${desc}</option>`;
        })
        .join("");
      if (!plays.length) return;
      const target = targetPlayId && plays.some((p) => p.playId == targetPlayId)
        ? String(targetPlayId) : plays[0].playId;
      pSel.value = target;
      loadPlay(gameId, target);
    });
  }

  function loadPlay(gameId, playId) {
    document.getElementById("playDesc").textContent = "Loading play…";
    // fetch PPI for this play in parallel and show it as a badge
    api(`/api/ppi-play?gameId=${gameId}&playId=${playId}`).then((ppi) => {
      const el = document.getElementById("ppiBadge");
      if (el) {
        if (ppi && ppi.ppi != null) {
          const color = ppi.ppi >= 60 ? "#ff6b6b" : ppi.ppi >= 40 ? "#ffbf47" : "#37d6a0";
          el.innerHTML = `⚡ PPI <strong style="color:${color}">${ppi.ppi}</strong> · throw in ${ppi.timeToThrow}s`;
        } else {
          el.textContent = "";
        }
      }
    });
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
