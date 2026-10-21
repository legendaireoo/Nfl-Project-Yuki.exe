/* Yuki.exe — "fun layer": turns dry numbers into playful, human language.
   Pure helpers, no dependencies. Shared by app.js. */
(function (global) {
  "use strict";

  // Map a 0-100 PPI into a fun danger level with emoji + label + color.
  function pressureLevel(ppi) {
    if (ppi == null) return { emoji: "❓", label: "Inconnu", color: "#8c9bb3", blurb: "Pas de données sur cette action." };
    if (ppi >= 80) return { emoji: "💀", label: "INFERNAL", color: "#ff3b3b", blurb: "Le QB s'est fait détruire. Pocket en miettes !" };
    if (ppi >= 60) return { emoji: "🔥", label: "Brûlant", color: "#ff6b6b", blurb: "Grosse chaleur — le QB a dû lâcher vite." };
    if (ppi >= 40) return { emoji: "😬", label: "Chaud", color: "#ffbf47", blurb: "Ça pousse fort, le QB sent la pression." };
    if (ppi >= 20) return { emoji: "🙂", label: "Gérable", color: "#9bd67f", blurb: "Un peu de pression, rien d'alarmant." };
    return { emoji: "😎", label: "Peinard", color: "#37d6a0", blurb: "Le QB a eu tout son temps. Pocket béton." };
  }

  // Fun nickname for a pass rusher based on their profile.
  function rusherNickname(r) {
    const perPlay = r.ppiPerPlay != null ? r.ppiPerPlay : 0;
    const ghostRatio = r.totalPPI ? (r.ghostPPI || 0) / r.totalPPI : 0;
    if (ghostRatio > 0.78) return { tag: "👻 Le Fantôme", why: "Il terrorise le QB sans jamais apparaître sur la feuille de stats." };
    if (perPlay >= 15) return { tag: "👹 Le Cauchemar", why: "Pression monstrueuse à chaque action." };
    if (r.totalPPI >= 450) return { tag: "🌋 Le Volcan", why: "Une éruption de pression, encore et encore." };
    if (perPlay >= 11) return { tag: "⚡ L'Éclair", why: "Explosif : il arrive vite et fort." };
    return { tag: "🛠️ Le Bosseur", why: "Pression régulière, snap après snap." };
  }

  // Fun one-liner comparing a rusher to an "average" rusher.
  function rusherCompare(r, leagueAvgPerPlay) {
    if (!leagueAvgPerPlay || !r.ppiPerPlay) return "";
    const x = r.ppiPerPlay / leagueAvgPerPlay;
    if (x >= 1.05) return `🧨 Il met ${x.toFixed(1)}× plus de pression qu'un rusher moyen.`;
    if (x >= 0.95) return "Dans la moyenne de la ligue.";
    return "Sous la moyenne de la ligue.";
  }

  // Team defense personality.
  function defenseVibe(avgPPI) {
    if (avgPPI >= 52) return "🦈 Meute affamée";
    if (avgPPI >= 48) return "💪 Agressive";
    if (avgPPI >= 44) return "⚖️ Équilibrée";
    return "😴 Tranquille";
  }

  // Offense protection personality (lower PPI faced = better).
  function offenseVibe(avgPPI) {
    if (avgPPI <= 38) return "🧱 Mur imprenable";
    if (avgPPI <= 42) return "🛡️ Solide";
    if (avgPPI <= 46) return "🚪 Perméable";
    return "🚨 Passoire";
  }

  // A fun sentence describing a whole play's pressure story.
  function playStory(ppi, ttt) {
    const lvl = pressureLevel(ppi);
    let t = "";
    if (ttt != null) {
      if (ttt <= 1.8) t = ` Le QB a lâché le ballon en ${ttt}s — éclair !`;
      else if (ttt >= 3.2) t = ` Il a tenu ${ttt}s dans la pocket — du courage !`;
      else t = ` Ballon lâché en ${ttt}s.`;
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
