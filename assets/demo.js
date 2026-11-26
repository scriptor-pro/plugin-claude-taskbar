// Réplique du rendu de dessin.py et des règles de etat.py / infobulle.py / query.py,
// pour la démonstration de la page. Mêmes dimensions, mêmes couleurs, mêmes seuils.
(() => {
  "use strict";

  const LANG = document.documentElement.lang.startsWith("en") ? "en" : "fr";

  const T = {
    fr: {
      etiquettes: ["5 h", "7 j"],
      pct: (v) => `${v} %`,
      forfait: "Claude Code — forfait Pro",
      perime: "Données périmées (dernière mise à jour à 13:58)",
      indispo: "Données indisponibles",
      enCours: () => "5 h : réinitialisation en cours…",
      ligne5: (u, h, r) => `5 h : ${u} % · réinitialisation ${h} (dans ${r})`,
      ligne7: (u, e, rythme) => `7 j : ${u} % · ${e} % du temps écoulé · ${rythme}`,
      tenu: "rythme tenu",
      rapide: "rythme trop rapide",
      reset7: (h, r) => `réinitialisation ${h} (dans ${r})`,
      maj: (h) => `mis à jour à ${h}`,
      jours: ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
      demain: "Demain",
      duree: (j, h, m) => (j > 0 ? `${j}j ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`),
      description: (a, b) => `Barre de quotas : 5 h ${a}, 7 jours ${b}`,
      masque: "masqué",
    },
    en: {
      etiquettes: ["5 h", "7 j"], // la barre est en français dans les deux langues
      pct: (v) => `${v} %`,
      forfait: "Claude Code — Pro plan",
      perime: "Stale data (last update at 13:58)",
      indispo: "Data unavailable",
      enCours: () => "5 h: reset in progress…",
      ligne5: (u, h, r) => `5 h: ${u} % · resets ${h} (in ${r})`,
      ligne7: (u, e, rythme) => `7 d: ${u} % · ${e} % of the week elapsed · ${rythme}`,
      tenu: "on pace",
      rapide: "ahead of pace",
      reset7: (h, r) => `resets ${h} (in ${r})`,
      maj: (h) => `updated at ${h}`,
      jours: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      demain: "Tomorrow",
      duree: (j, h, m) => (j > 0 ? `${j}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`),
      description: (a, b) => `Quota bar: 5 h ${a}, 7 days ${b}`,
      masque: "hidden",
    },
  }[LANG];

  // --- Géométrie et couleurs de dessin.py ---
  const HAUTEUR = 32, MARGE = 4, L_ETIQ = 22, ECART = 6, L_BARRE = 70, H_BARRE = 9, ECART_BARRES = 5, L_PCT = 44;
  const X_BARRE = MARGE + L_ETIQ + ECART;
  const LARGEUR = X_BARRE + L_BARRE + ECART + L_PCT + MARGE;
  const Y_PREMIERE = Math.floor((HAUTEUR - (2 * H_BARRE + ECART_BARRES)) / 2);
  const C = {
    fond: "#555555", bordure: "#1a1a1a", trait: "#2e3440", texte: "#111111", texteGris: "#5c5c5c",
    gris: "#8c8c8c", vert: "#a3be8c", jaune: "#ebcb8b", rouge: "#bf616a", bleu: "#5e81ac", orange: "#d35400",
  };
  const TOLERANCE_RYTHME = 5;

  const couleur5h = (u) => (u < 60 ? C.vert : u < 85 ? C.jaune : C.rouge);
  const tropRapide = (u7, el) => u7 > el + TOLERANCE_RYTHME;

  function barres(s) {
    const vide = { remplissage: 0, texte: "–", couleur: C.gris, grise: true, trait: null };
    if (s.etat === "indispo") return [vide, vide];
    if (s.etat === "perime") {
      const g = (u) => ({ remplissage: Math.min(u, 100), texte: T.pct(u), couleur: C.gris, grise: true, trait: null });
      return [g(s.u5), g(s.u7)];
    }
    const b5 = s.etat === "reinit"
      ? vide
      : { remplissage: Math.min(s.u5, 100), texte: T.pct(s.u5), couleur: couleur5h(s.u5), grise: false, trait: null };
    const b7 = {
      remplissage: Math.min(s.u7, 100), texte: T.pct(s.u7),
      couleur: tropRapide(s.u7, s.el) ? C.orange : C.bleu, grise: false, trait: s.el,
    };
    return [b5, b7];
  }

  function dessiner(canvas, s, echelle) {
    const dpr = window.devicePixelRatio || 1;
    const k = echelle * dpr;
    canvas.width = LARGEUR * k;
    canvas.height = HAUTEUR * k;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.clearRect(0, 0, LARGEUR, HAUTEUR);
    ctx.font = "700 11px Luciole, sans-serif";
    ctx.textBaseline = "middle";

    barres(s).forEach((b, i) => {
      const yo = Y_PREMIERE + i * (H_BARRE + ECART_BARRES);
      const x = X_BARRE + 1, y = yo + 1, l = L_BARRE - 2, h = H_BARRE - 2;
      ctx.fillStyle = C.bordure; ctx.fillRect(x - 1, y - 1, l + 2, h + 2);
      ctx.fillStyle = C.fond; ctx.fillRect(x, y, l, h);
      const rempli = Math.round((l * Math.max(0, Math.min(100, b.remplissage))) / 100);
      if (rempli) { ctx.fillStyle = b.couleur; ctx.fillRect(x, y, rempli, h); }
      if (b.trait !== null) {
        let xt = x + Math.round((l * b.trait) / 100) - 1;
        xt = Math.max(x - 1, Math.min(x + l - 1, xt));
        ctx.fillStyle = C.trait; ctx.fillRect(xt, y - 2, 2, h + 4);
      }
      const yc = y + h / 2 + 0.5;
      ctx.fillStyle = C.texte;
      ctx.textAlign = "left";
      ctx.fillText(T.etiquettes[i], MARGE, yc);
      ctx.fillStyle = b.grise ? C.texteGris : C.texte;
      ctx.textAlign = "right";
      ctx.fillText(b.texte.replace(" ", " "), LARGEUR - MARGE, yc);
    });

    const [b5, b7] = barres(s);
    canvas.setAttribute("aria-label", T.description(b5.texte === "–" ? T.masque : b5.texte, b7.texte === "–" ? T.masque : b7.texte));
  }

  // --- Infobulle (infobulle.py), avec une heure fictive de 14:41 ---
  const MAINTENANT = new Date(2026, 10, 26, 14, 41);

  function decrire(heures) {
    const cible = new Date(MAINTENANT.getTime() + heures * 3600e3);
    const hhmm = `${String(cible.getHours()).padStart(2, "0")}:${String(cible.getMinutes()).padStart(2, "0")}`;
    const jour = Math.round((new Date(cible).setHours(0, 0, 0, 0) - new Date(MAINTENANT).setHours(0, 0, 0, 0)) / 864e5);
    const quand = jour === 0 ? hhmm : jour === 1 ? `${T.demain} ${hhmm}` : `${T.jours[cible.getDay()]} ${hhmm}`;
    const minutes = Math.round(heures * 60);
    return [quand, T.duree(Math.floor(minutes / 1440), Math.floor((minutes % 1440) / 60), minutes % 60)];
  }

  function infobulle(s) {
    if (s.etat === "indispo") return T.indispo;
    const lignes = [];
    if (s.etat === "perime") lignes.push(T.perime);
    lignes.push(T.forfait);
    if (s.etat === "reinit") lignes.push(T.enCours());
    else lignes.push(T.ligne5(s.u5, ...decrire(2 + 10 / 60)));
    lignes.push(T.ligne7(s.u7, s.el, tropRapide(s.u7, s.el) ? T.rapide : T.tenu));
    lignes.push(T.reset7(...decrire(168 * (1 - s.el / 100))));
    lignes.push(T.maj(s.etat === "perime" ? "13:58" : "14:41"));
    return lignes.join("\n");
  }

  // --- Branchement ---
  const form = document.getElementById("reglages");
  const loupe = document.getElementById("loupe");
  const reelle = document.getElementById("barre-reelle");
  const bulle = document.getElementById("infobulle");

  function lire() {
    const d = new FormData(form);
    return { u5: +d.get("u5"), u7: +d.get("u7"), el: +d.get("el"), etat: d.get("etat") };
  }

  function rafraichir() {
    const s = lire();
    for (const nom of ["u5", "u7", "el"]) form.querySelector(`output[for="${nom}"]`).value = T.pct(s[nom]);
    dessiner(loupe, s, 4);
    dessiner(reelle, s, 1);
    bulle.textContent = infobulle(s);
  }

  form.addEventListener("input", rafraichir);
  window.matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`).addEventListener?.("change", rafraichir);
  document.fonts.load("700 11px Luciole").then(rafraichir, rafraichir);
  rafraichir();
})();
