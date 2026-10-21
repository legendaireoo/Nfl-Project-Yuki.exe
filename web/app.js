/* Yuki.exe — frontend controller. Vanilla JS, no frameworks. */
(function () {
  "use strict";

  const C = window.YukiCharts;
  const api = (path) => fetch(path).then((r) => r.json());

  // ---- universal click-to-sort for any <table> --------------------------
  // Click a header to sort rows by that column; click again to reverse.
  document.addEventListener("click", (e) => {
    const th = e.target.closest("th");
    if (!th) return;
    const table = th.closest("table");
    if (!table || !table.tBodies.length) return;
    const idx = Array.from(th.parentNode.children).indexOf(th);
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows).filter((r) => r.cells.length > idx);
    if (rows.length < 2) return;

    const asc = table.dataset.sortCol == idx ? table.dataset.sortAsc !== "true" : false;
    const num = (s) => {
      const m = String(s).replace(/[^0-9.\-]/g, "");
      return m === "" ? null : parseFloat(m);
    };
    rows.sort((a, b) => {
      const av = a.cells[idx].textContent.trim();
      const bv = b.cells[idx].textContent.trim();
      const an = num(av), bn = num(bv);
      let cmp;
      if (an !== null && bn !== null) cmp = an - bn;
      else cmp = av.localeCompare(bv, "fr");
      return asc ? cmp : -cmp;
    });
    rows.forEach((r) => tbody.appendChild(r));
    table.dataset.sortCol = idx;
    table.dataset.sortAsc = asc;
    // header arrow indicator
    Array.from(th.parentNode.children).forEach((h) =>
      (h.textContent = h.textContent.replace(/[ ▲▼]+$/, ""))
    );
    th.textContent = th.textContent.replace(/[ ▲▼]+$/, "") + (asc ? " ▲" : " ▼");
  });

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
    else if (view === "prow") loadPROW();
    else if (view === "game") loadGame();
    else if (view === "pocket") loadPocket();
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
      { label: "🏟️ Games", value: d.games },
      { label: "🧑 Players", value: d.players },
      { label: "🎯 Plays", value: d.plays.toLocaleString() },
      { label: "✅ Completions", value: d.completionPct + "%", cls: "accent" },
      { label: "📏 Yards / play", value: d.avgYards, cls: "accent" },
      { label: "🎭 Play-action", value: d.playActionPct + "%", cls: "warn" },
      { label: "💥 Pressures faced", value: d.totalPressures.toLocaleString(), cls: "danger" },
      { label: "🛑 Sacks (QB down)", value: d.sacks, cls: "danger" },
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
      `<thead><tr><th>Coverage</th><th class="num">Plays</th><th class="num">✅ Completion %</th><th class="num">📏 Avg Yds</th></tr></thead><tbody>${rows}</tbody>`;
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
        `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Plays</th><th class="num">🛑 Sacks</th><th class="num">💢 Hits</th><th class="num">😰 Hurries</th><th class="num">💥 Pressures</th><th class="num">Rate</th></tr></thead><tbody>${rows}</tbody>`;
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
        `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">Plays</th><th class="num">🛑 Sacks allowed</th><th class="num">💢 Hits allowed</th><th class="num">😰 Hurries allowed</th><th class="num">💥 Pressures allowed</th><th class="num">Rate</th></tr></thead><tbody>${rows}</tbody>`;
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
      { xLabel: "Pressure allowed by offense (%)", yLabel: "Pressure generated by defense (%)" }
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
      `<thead><tr><th>Team</th><th class="num">Rush plays</th><th class="num">💥 Pressures gen.</th><th class="num">Rush rate</th><th class="num">Block plays</th><th class="num">Pressures allowed</th><th class="num">Allowed rate</th></tr></thead><tbody>${rows}</tbody>`;
  }

  // ---- PPI (original metric) -------------------------------------------
  function loadPPI() {
    const sel = document.getElementById("ppiGames");
    sel.addEventListener("change", () => fetchPPI(sel.value));
    fetchPPI(sel.value);
  }
  function fetchPPI(games) {
    const status = document.getElementById("ppiStatus");
    status.textContent = `🔄 Computing pressure across ${games} game(s)…`;
    api(`/api/ppi?games=${games}`).then((d) => {
      cache.ppi = d;
      status.textContent = `✓ ${d.playsScored.toLocaleString()} plays analyzed across ${d.gamesAnalyzed} games · avg pressure ${d.avgPPI}/100`;
      drawPPI(d);
    });
  }
  function drawPPI(d) {
    const F = window.YukiFun;
    const avgLvl = F.pressureLevel(d.avgPPI);
    const king = d.rushers[0] || {};
    const cards = [
      { label: "🏟️ Games analyzed", value: d.gamesAnalyzed },
      { label: "🎯 Plays scored", value: d.playsScored.toLocaleString() },
      { label: `${avgLvl.emoji} Avg pressure`, value: d.avgPPI + "/100", cls: "accent" },
      { label: "👑 King of pressure", value: king.name || "—", cls: "warn" },
    ];
    document.getElementById("ppiCards").innerHTML = cards
      .map((c) => `<div class="card ${c.cls || ""}"><div class="value" style="font-size:${String(c.value).length > 10 ? 18 : 26}px">${c.value}</div><div class="label">${c.label}</div></div>`)
      .join("");

    // league average pressure-per-play for the fun comparison line
    const leagueAvgPerPlay =
      d.rushers.reduce((s, r) => s + (r.ppiPerPlay || 0), 0) / (d.rushers.length || 1);

    // Rusher cards with nicknames instead of a dry table.
    const maxPPI = Math.max(...d.rushers.map((r) => r.totalPPI), 1);
    document.getElementById("ppiRushCards").innerHTML = d.rushers
      .slice(0, 12)
      .map((r, i) => {
        const nick = F.rusherNickname(r);
        const cmp = F.rusherCompare(r, leagueAvgPerPlay);
        const w = (r.totalPPI / maxPPI) * 100;
        const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i + 1}`;
        return `<div class="rusher-card">
          <div class="rc-head">
            <span class="rc-rank">${medal}</span>
            <span class="rc-name">${r.name}</span>
            <span class="rc-pos">${r.position}</span>
          </div>
          <div class="rc-nick">${nick.tag}</div>
          <div class="rc-meter"><div class="rc-fill" style="width:${w}%"></div></div>
          <div class="rc-stat">🔥 Total pressure: <strong>${r.totalPPI}</strong> · ${r.plays} plays</div>
          <div class="rc-why">${nick.why} ${cmp}</div>
        </div>`;
      })
      .join("");

    document.getElementById("ppiGhostTable").innerHTML =
      `<thead><tr><th>#</th><th>Player</th><th>Pos</th><th class="num">👻 Ghost pressure</th><th class="num">Unrewarded plays</th></tr></thead><tbody>` +
      d.ghostLeaders.slice(0, 15).map((r, i) => `<tr>
        <td class="rank">${i + 1}</td><td>${r.name}</td><td>${r.position}</td>
        <td class="num"><strong>${r.ghostPPI}</strong></td><td class="num">${r.ghostPlays}</td></tr>`).join("") +
      `</tbody>`;

    C.bar(document.getElementById("ppiDefChart"),
      d.teamsDefense.slice(0, 12).map((t) => ({ label: t.team, value: t.avgPPI })),
      { horizontal: true, color: C.PALETTE[3] });
    C.bar(document.getElementById("ppiOffChart"),
      d.teamsOffense.slice(0, 12).map((t) => ({ label: t.team, value: t.avgPPI })),
      { horizontal: true, color: C.PALETTE[1] });

    document.getElementById("ppiPlaysTable").innerHTML =
      `<thead><tr><th>#</th><th>Level</th><th class="num">Score</th><th class="num">Throw in</th><th>Defense</th><th>Offense</th><th></th></tr></thead><tbody>` +
      d.topPlays.slice(0, 15).map((p, i) => {
        const lvl = F.pressureLevel(p.ppi);
        return `<tr>
        <td class="rank">${i + 1}</td>
        <td><span style="color:${lvl.color};font-weight:700">${lvl.emoji} ${lvl.label}</span></td>
        <td class="num"><strong>${p.ppi}</strong></td>
        <td class="num">${p.timeToThrow}s</td><td>${p.def}</td><td>${p.off}</td>
        <td><a href="#" class="goplay" data-game="${p.gameId}" data-play="${p.playId}">🍿 watch</a></td></tr>`;
      }).join("") +
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

    const pmFill = document.getElementById("pmFill");
    const pmVal = document.getElementById("pmVal");
    viewer = YukiField.makeViewer(fieldCanvas, {
      onFrame: (i, total, event, gauge) => {
        slider.value = i;
        frameLabel.textContent = `frame ${i + 1} / ${total}`;
        eventLabel.textContent = event ? "● " + event : "";
        if (gauge != null) {
          const g = Math.round(gauge);
          pmFill.style.width = g + "%";
          pmFill.style.background =
            g >= 66 ? "#ff6b6b" : g >= 33 ? "#ffbf47" : "#37d6a0";
          pmVal.textContent = g;
        }
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

  const RES_FR = { C: "✅ completion", I: "❌ incomplete", S: "🛑 sack (QB down)", R: "🏃 QB scrambles", IN: "🙈 interception" };

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
    document.getElementById("playDesc").textContent = "Loading play… 🍿";
    // fetch PPI for this play in parallel and show it as a fun story badge
    api(`/api/ppi-play?gameId=${gameId}&playId=${playId}`).then((ppi) => {
      const el = document.getElementById("ppiBadge");
      if (el) {
        if (ppi && ppi.ppi != null) {
          el.innerHTML = window.YukiFun.playStory(ppi.ppi, ppi.timeToThrow) +
            ` <span class="pm-note">(note ${ppi.ppi}/100)</span>`;
        } else {
          el.textContent = "";
        }
      }
    });
    api(`/api/play?gameId=${gameId}&playId=${playId}`).then((play) => {
      const m = play.meta || {};
      document.getElementById("playDesc").innerHTML =
        `<strong>${m.possessionTeam} ⚔️ ${m.defensiveTeam}</strong> · Q${m.quarter} · ${m.down} &amp; ${m.yardsToGo} · ` +
        `Coverage: <strong>${m.coverage || "?"}</strong> · Result: <strong>${RES_FR[m.passResult] || m.passResult || "?"}</strong><br>${m.description || ""}`;
      const slider = document.getElementById("frameSlider");
      slider.max = Math.max(0, play.frameCount - 1);
      slider.value = 0;
      viewer.load(play);
      document.getElementById("playBtn").textContent = "▶ Play";
    });
  }

  // ---- FENÊTRE DE TIR (PROW) -------------------------------------------
  function loadPROW() {
    const kSel = document.getElementById("prowK");
    kSel.addEventListener("change", () => drawProwChart(parseInt(kSel.value, 10)));
    const status = document.getElementById("prowStatus");
    status.textContent = "🔄 Loading…";
    api("/api/prow").then((d) => {
      cache.prow = d;
      if (!d.available) {
        status.textContent = "⚠️ PROW data unavailable.";
        return;
      }
      status.textContent = `✓ ${d.headline.n_throws.toLocaleString()} throws · ${d.headline.n_games} games`;
      drawPROW(d);
    });
  }

  function drawPROW(d) {
    const h = d.headline;
    const cards = [
      { label: "🎯 Throws analyzed", value: h.n_throws.toLocaleString() },
      { label: "✅ Open at release", value: Math.round(h.open_rate * 100) + "%", cls: "accent" },
      { label: "😶 Covered at release", value: Math.round(h.covered_rate * 100) + "%", cls: "danger" },
      { label: "🙈 Missed windows", value: Math.round(h.missed * 100) + "%", cls: "warn" },
    ];
    document.getElementById("prowCards").innerHTML = cards
      .map((c) => `<div class="card ${c.cls || ""}"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
      .join("");

    // QB table
    document.getElementById("prowQbTable").innerHTML =
      `<thead><tr><th>#</th><th>Quarterback</th><th class="num">Throws</th><th class="num">🙈 Missed windows</th></tr></thead><tbody>` +
      d.qbMissed.map((q, i) => `<tr>
        <td class="rank">${i + 1}</td><td>${q.name}</td>
        <td class="num">${q.throws}</td><td class="num"><strong>${q.missedPct}%</strong></td></tr>`).join("") +
      `</tbody>`;

    // Examples table (clickable -> viewer)
    document.getElementById("prowExTable").innerHTML =
      `<thead><tr><th>Target (covered)</th><th>Open teammate</th><th class="num">Open for</th><th></th></tr></thead><tbody>` +
      d.examples.slice(0, 12).map((e) => `<tr>
        <td>${e.target} <span class="mini">(${e.targetSep}yd)</span></td>
        <td>${e.altName || "?"}</td>
        <td class="num">${e.altProw}s</td>
        <td><a href="#" class="goplay" data-game="${e.gameId}" data-play="${e.playId}">🍿 watch</a></td></tr>`).join("") +
      `</tbody>`;
    document.querySelectorAll("#prowExTable .goplay").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        jumpToPlay(a.dataset.game, a.dataset.play);
      });
    });

    drawProwChart(3);
  }

  function drawProwChart(k) {
    api(`/api/prow-buckets?k=${k}`).then((br) => {
      C.bar(
        document.getElementById("prowChart"),
        br.buckets.map((b) => ({ label: b.label, value: b.completionPct })),
        { valueFmt: (v) => v + "%" }
      );
      const diff = (br.openPct - br.coveredPct).toFixed(1);
      document.getElementById("prowChartHint").innerHTML =
        `With a <strong>${k}-yard</strong> threshold: open at release = <strong>${br.openPct}%</strong> completion, ` +
        `covered = <strong>${br.coveredPct}%</strong> → a <strong>+${diff} point</strong> gap! ` +
        `But notice the "open" bars are almost all the same height: duration barely changes a thing. 🤷`;
    });
  }

  // ---- MINI-GAME: Guess the Pressure -----------------------------------
  function loadGame() {
    const startBtn = document.getElementById("gameStart");
    const nextBtn = document.getElementById("gameNext");
    const choicesEl = document.getElementById("gameChoices");
    const resultEl = document.getElementById("gameResult");
    const descEl = document.getElementById("gameDesc");
    const scoreEl = document.getElementById("gameScore");
    const F = window.YukiFun;

    const gameViewer = YukiField.makeViewer(document.getElementById("gameField"), {});
    let topPlays = [];
    let pool = [];
    let current = null;
    let score = 0, total = 0, streak = 0;

    const LEVELS = [
      { label: "😎 Chilling", min: 0, max: 20 },
      { label: "🙂 Manageable", min: 20, max: 40 },
      { label: "😬 Hot", min: 40, max: 60 },
      { label: "🔥 Blazing", min: 60, max: 80 },
      { label: "💀 Inferno", min: 80, max: 101 },
    ];
    function levelIndex(ppi) {
      for (let i = 0; i < LEVELS.length; i++) if (ppi >= LEVELS[i].min && ppi < LEVELS[i].max) return i;
      return LEVELS.length - 1;
    }

    function updateScore() {
      scoreEl.textContent = `Score: ${score} / ${total} · Streak: ${streak} 🔥`;
    }

    function pickPlay() {
      if (!pool.length) pool = topPlays.slice();
      const idx = Math.floor(Math.random() * pool.length);
      return pool.splice(idx, 1)[0];
    }

    function newRound() {
      resultEl.innerHTML = "";
      nextBtn.classList.add("hidden");
      choicesEl.innerHTML = "⏳ Loading play…";
      current = pickPlay();
      api(`/api/play?gameId=${current.gameId}&playId=${current.playId}`).then((play) => {
        descEl.innerHTML = `<strong>${(play.meta || {}).possessionTeam} ⚔️ ${(play.meta || {}).defensiveTeam}</strong> — watch closely… then guess!`;
        gameViewer.load(play);
        gameViewer.reset();
        gameViewer.play();
        // show the answer buttons
        choicesEl.innerHTML = LEVELS.map(
          (l, i) => `<button class="choice-btn" data-i="${i}">${l.label}</button>`
        ).join("");
        choicesEl.querySelectorAll(".choice-btn").forEach((b) =>
          b.addEventListener("click", () => answer(parseInt(b.dataset.i, 10)))
        );
      });
    }

    function answer(guessIdx) {
      const truth = levelIndex(current.ppi);
      total++;
      const diff = Math.abs(guessIdx - truth);
      let msg, cls;
      if (diff === 0) {
        score += 2; streak++;
        msg = `🎉 Perfect! It really was <strong>${LEVELS[truth].label}</strong> (${current.ppi}/100). +2 points!`;
        cls = "good";
      } else if (diff === 1) {
        score += 1; streak = 0;
        msg = `👍 Close! The real answer: <strong>${LEVELS[truth].label}</strong> (${current.ppi}/100). +1 point.`;
        cls = "ok";
      } else {
        streak = 0;
        msg = `😅 Missed! It was <strong>${LEVELS[truth].label}</strong> (${current.ppi}/100).`;
        cls = "bad";
      }
      updateScore();
      resultEl.className = "game-result " + cls;
      resultEl.innerHTML = msg + "<br>" + F.playStory(current.ppi, current.timeToThrow);
      choicesEl.querySelectorAll(".choice-btn").forEach((b) => {
        const i = parseInt(b.dataset.i, 10);
        b.disabled = true;
        if (i === truth) b.classList.add("correct");
        else if (i === guessIdx) b.classList.add("wrong");
      });
      nextBtn.classList.remove("hidden");
    }

    function begin() {
      startBtn.textContent = "🎲 New game";
      if (topPlays.length) { newRound(); return; }
      choicesEl.innerHTML = "⏳ Setting up the game…";
      api("/api/ppi?games=20").then((d) => {
        // use a spread of plays across all pressure levels for variety
        topPlays = (d.quizPlays && d.quizPlays.length ? d.quizPlays : d.topPlays || []).concat();
        if (topPlays.length < 8) { choicesEl.innerHTML = "Not enough data."; return; }
        newRound();
      });
    }

    startBtn.addEventListener("click", begin);
    nextBtn.addEventListener("click", newRound);
    updateScore();
  }

  // ---- POCKET WATCH: will the pocket break? ----------------------------
  function loadPocket() {
    const startBtn = document.getElementById("pwStart");
    const nextBtn = document.getElementById("pwNext");
    const choicesEl = document.getElementById("pwChoices");
    const resultEl = document.getElementById("pwResult");
    const descEl = document.getElementById("pwDesc");
    const scoreEl = document.getElementById("pwScore");
    const pbiCache = {};

    const pwViewer = YukiField.makeViewer(document.getElementById("pwField"), {});
    let pool = [];
    let bag = [];
    let current = null;
    let stage = 0; // 0 = hold/break, 1 = side, 2 = rusher
    let score = 0, total = 0, streak = 0;

    function updateScore() {
      scoreEl.textContent = `Score: ${score} / ${total} · Streak: ${streak} 🔥`;
    }

    function pick() {
      if (!bag.length) bag = pool.slice();
      return bag.splice(Math.floor(Math.random() * bag.length), 1)[0];
    }

    function showChoices(buttons) {
      choicesEl.innerHTML = buttons
        .map((b, i) => `<button class="choice-btn" data-v="${b.v}">${b.label}</button>`)
        .join("");
      choicesEl.querySelectorAll(".choice-btn").forEach((btn) =>
        btn.addEventListener("click", () => onPick(btn.dataset.v, btn))
      );
    }

    function newRound() {
      resultEl.innerHTML = "";
      resultEl.className = "game-result";
      nextBtn.classList.add("hidden");
      choicesEl.innerHTML = "⏳ Loading play…";
      stage = 0;
      current = pick();
      api(`/api/play?gameId=${current.gameId}&playId=${current.playId}`).then((play) => {
        descEl.innerHTML = `<strong>${(play.meta || {}).defensiveTeam} rush ⚔️ ${(play.meta || {}).possessionTeam} protection</strong> — watch the first moment… will the pocket hold?`;
        pwViewer.load(play);
        pwViewer.reset();
        // show only the first ~1s then pause for the guess
        pwViewer.play();
        setTimeout(() => pwViewer.stop(), 1100);
        askHoldBreak();
      });
    }

    function askHoldBreak() {
      showChoices([
        { v: "hold", label: "🛡️ The pocket HOLDS" },
        { v: "break", label: "💥 The pocket BREAKS" },
      ]);
    }

    function onPick(val, btn) {
      if (stage === 0) {
        total++;
        const truth = current.breaks ? "break" : "hold";
        const right = val === truth;
        if (right) { score += 1; streak++; } else { streak = 0; }
        markButtons(btn, (b) => b.dataset.v === truth);
        updateScore();
        if (!current.breaks) {
          resultEl.className = "game-result " + (right ? "good" : "bad");
          resultEl.innerHTML = right
            ? "🎉 Right! The pocket held — clean all the way."
            : "😅 Nope — the pocket actually held.";
          finishRound();
          return;
        }
        resultEl.className = "game-result " + (right ? "good" : "ok");
        resultEl.innerHTML = (right ? "🎉 Right, it breaks! " : "😬 It actually breaks! ") +
          `Now: which side gives way?`;
        stage = 1;
        setTimeout(() => askSide(), 600);
      } else if (stage === 1) {
        total++;
        const truth = current.breachSide;
        const right = val === truth;
        if (right) { score += 1; streak++; } else { streak = 0; }
        markButtons(btn, (b) => b.dataset.v === truth);
        updateScore();
        resultEl.className = "game-result " + (right ? "good" : "ok");
        resultEl.innerHTML = (right ? "✅ Correct side! " : `❌ It broke on the <strong>${truth}</strong>. `) +
          "Last one: which rusher breaks through?";
        stage = 2;
        setTimeout(() => askRusher(), 600);
      } else {
        total++;
        const right = val === current.breachRusher;
        if (right) { score += 2; streak++; } else { streak = 0; }
        markButtons(btn, (b) => b.dataset.v === current.breachRusher);
        updateScore();
        resultEl.className = "game-result " + (right ? "good" : "bad");
        resultEl.innerHTML = right
          ? `🏆 Nailed it! ${nameOf(current.breachRusher)} breached in ${current.breachTime}s. +2 points!`
          : `😅 It was <strong>${nameOf(current.breachRusher)}</strong> (breached in ${current.breachTime}s).`;
        finishRound();
      }
    }

    function askSide() {
      showChoices([
        { v: "LEFT", label: "⬅️ Left" },
        { v: "MIDDLE", label: "⬆️ Middle" },
        { v: "RIGHT", label: "➡️ Right" },
      ]);
    }

    function askRusher() {
      // offer the true breacher + a few decoys from this play's rushers
      api(`/api/play?gameId=${current.gameId}&playId=${current.playId}`).then((play) => {
        const rushers = {};
        (play.frames || []).forEach((fr) =>
          fr.forEach((p) => {
            if (p.nflId && p.name) pbiCache[p.nflId] = p.name; // cache every name we see
            if (p.position && /DE|DT|OLB|ILB|LB|NT|MLB/.test(p.position) && p.nflId) rushers[p.nflId] = p.name || ("#" + p.nflId);
          })
        );
        rushers[current.breachRusher] = nameOf(current.breachRusher);
        let ids = Object.keys(rushers);
        // keep the true one + up to 3 others
        ids = ids.filter((id) => id !== current.breachRusher);
        shuffle(ids);
        const picks = [current.breachRusher].concat(ids.slice(0, 3));
        shuffle(picks);
        showChoices(picks.map((id) => ({ v: id, label: "😤 " + (rushers[id] || ("#" + id)) })));
      });
    }

    function nameOf(id) { return pbiCache[id] || ("#" + id); }

    function markButtons(clicked, isCorrect) {
      choicesEl.querySelectorAll(".choice-btn").forEach((b) => {
        b.disabled = true;
        if (isCorrect(b)) b.classList.add("correct");
        else if (b === clicked) b.classList.add("wrong");
      });
    }

    function finishRound() { nextBtn.classList.remove("hidden"); }

    function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } }

    function begin() {
      startBtn.textContent = "🎲 New game";
      if (pool.length) { newRound(); return; }
      choicesEl.innerHTML = "⏳ Setting up the game…";
      api("/api/pocket?games=20").then((d) => {
        pool = (d.pool || []).concat();
        // cache rusher names from the leaderboard for nicer labels
        (d.leaders || []).forEach((r) => (pbiCache[r.nflId] = r.name));
        if (pool.length < 6) { choicesEl.innerHTML = "Not enough data."; return; }
        newRound();
      });
    }

    startBtn.addEventListener("click", begin);
    nextBtn.addEventListener("click", newRound);
    updateScore();
  }

  // initial view
  render("overview");
})();
