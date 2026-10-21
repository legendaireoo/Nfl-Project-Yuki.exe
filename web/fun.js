/* Yuki.exe — "fun layer": turns dry numbers into playful, human language.
   Pure helpers, no dependencies. Shared by app.js. */
(function (global) {
  "use strict";

  // Map a 0-100 PPI into a fun danger level with emoji + label + color.
  function pressureLevel(ppi) {
    if (ppi == null) return { emoji: "❓", label: "Unknown", color: "#8c9bb3", blurb: "No data on this play." };
    if (ppi >= 80) return { emoji: "💀", label: "INFERNO", color: "#ff3b3b", blurb: "The QB got wrecked. Pocket in pieces!" };
    if (ppi >= 60) return { emoji: "🔥", label: "Blazing", color: "#ff6b6b", blurb: "Serious heat — the QB had to let it go fast." };
    if (ppi >= 40) return { emoji: "😬", label: "Hot", color: "#ffbf47", blurb: "Big push, the QB feels the pressure." };
    if (ppi >= 20) return { emoji: "🙂", label: "Manageable", color: "#9bd67f", blurb: "A little pressure, nothing alarming." };
    return { emoji: "😎", label: "Chilling", color: "#37d6a0", blurb: "The QB had all day. Rock-solid pocket." };
  }

  // Fun nickname for a pass rusher based on their profile.
  function rusherNickname(r) {
    const perPlay = r.ppiPerPlay != null ? r.ppiPerPlay : 0;
    const ghostRatio = r.totalPPI ? (r.ghostPPI || 0) / r.totalPPI : 0;
    if (ghostRatio > 0.78) return { tag: "👻 The Ghost", why: "He terrorizes the QB without ever showing up on the stat sheet." };
    if (perPlay >= 15) return { tag: "👹 The Nightmare", why: "Monster pressure on every single play." };
    if (r.totalPPI >= 450) return { tag: "🌋 The Volcano", why: "An eruption of pressure, again and again." };
    if (perPlay >= 11) return { tag: "⚡ The Lightning", why: "Explosive: he arrives fast and hard." };
    return { tag: "🛠️ The Grinder", why: "Steady pressure, snap after snap." };
  }

  // Fun one-liner comparing a rusher to an "average" rusher.
  function rusherCompare(r, leagueAvgPerPlay) {
    if (!leagueAvgPerPlay || !r.ppiPerPlay) return "";
    const x = r.ppiPerPlay / leagueAvgPerPlay;
    if (x >= 1.05) return `🧨 He brings ${x.toFixed(1)}× more pressure than an average rusher.`;
    if (x >= 0.95) return "Right at the league average.";
    return "Below the league average.";
  }

  // Team defense personality.
  function defenseVibe(avgPPI) {
    if (avgPPI >= 52) return "🦈 Hungry pack";
    if (avgPPI >= 48) return "💪 Aggressive";
    if (avgPPI >= 44) return "⚖️ Balanced";
    return "😴 Laid-back";
  }

  // Offense protection personality (lower PPI faced = better).
  function offenseVibe(avgPPI) {
    if (avgPPI <= 38) return "🧱 Impenetrable wall";
    if (avgPPI <= 42) return "🛡️ Solid";
    if (avgPPI <= 46) return "🚪 Leaky";
    return "🚨 Sieve";
  }

  // A fun sentence describing a whole play's pressure story.
  function playStory(ppi, ttt) {
    const lvl = pressureLevel(ppi);
    let t = "";
    if (ttt != null) {
      if (ttt <= 1.8) t = ` The QB released the ball in ${ttt}s — lightning fast!`;
      else if (ttt >= 3.2) t = ` He held on for ${ttt}s in the pocket — gutsy!`;
      else t = ` Ball released in ${ttt}s.`;
    }
    return `${lvl.emoji} <strong>${lvl.label}</strong> — ${lvl.blurb}${t}`;
  }

  global.YukiFun = {
    pressureLevel,
    rusherNickname,
    rusherCompare,
    defenseVibe,
    offenseVibe,
    playStory,
  };
})(window);
