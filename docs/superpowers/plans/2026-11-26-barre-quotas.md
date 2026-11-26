# Quotas Claude Code dans le tableau de bord Xfce — plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** afficher les quotas 5 h / 7 j de Claude Code sous forme de deux mini-barres dans xfce4-panel, avec infobulle, via xfce4-genmon-plugin.

**Architecture :** un script Python lancé chaque minute par genmon lit `current.json` à l'aide de `ConkyQuery` (`~/.local/share/claude-monitor/query.py`), calcule un état d'affichage pur (testable), le dessine dans un PNG avec pycairo et imprime `<img>…</img><tool>…</tool>` pour genmon. Logique (`etat.py`, `infobulle.py`), dessin (`dessin.py`) et point d'entrée (`barre_quotas.py`) sont séparés.

**Tech Stack :** Python 3 (bibliothèque standard), pycairo 1.27, xfce4-genmon-plugin 4.1.1, `unittest`.

**Spec :** `docs/superpowers/specs/2026-11-26-barre-quotas-design.md`

## Global Constraints

- Aucune nouvelle dépendance ; aucun accès réseau ; on ne modifie ni `query.py`, ni Conky, ni `claude-monitor.service`.
- Seuils, rythme et formats d'heure : uniquement via les méthodes de `ConkyQuery` (`bar_color`, `pace_color`, `elapsed_7d_percent`, `format_reset_time`, `format_time_remaining`). Le script ne contient que la table `${colorN}` → RVB.
- Couleurs : color2 `ebcb8b`, color3 `a3be8c`, color5 `bf616a`, color7 `d35400`, color8 `5e81ac` ; trait `2e3440` (2 px) ; fond de barre `555555`, bordure `1a1a1a` (1 px) ; texte `111111` ; gris (barre et texte grisés) `8c8c8c`.
- Données périmées : `timestamp` plus vieux que 15 min.
- Priorité des états : indisponible > périmé > réinitialisation dépassée (par fenêtre) > normal.
- Pourcentages entiers suivis d'une espace insécable (U+00A0) et de « % » ; « – » (U+2013) quand masqué.
- Le script ne sort jamais avec un code ≠ 0 et imprime toujours une sortie genmon valide.
- Tests : `python3 -I -m unittest discover -s tests -t .` depuis la racine du dépôt.
- Textes de l'interface en français, avec accents.

## Review Focus

1. `current.json` valide mais champ `usage_5h`/`usage_7d` absent ou non numérique → « indisponible », pas d'exception (test dans la tâche 1).
2. `timestamp` absent ou illisible → traité comme périmé ; `timestamp` dans le futur (horloge recalée) → frais (tâche 1).
3. Usage hors [0, 100] (ex. 104) → remplissage borné à la barre, texte affichant la vraie valeur « 104 % » (tâches 1 et 3).
4. `XDG_RUNTIME_DIR` non défini → repli sur `/tmp` (tâche 4).
5. Caractères `&`, `<`, `>` dans l'infobulle (ex. `plan_type` inattendu) → échappés pour Pango (tâche 4).

---

### Task 1: état des barres (`etat.py`)

**Files :**
- Create : `etat.py`
- Test : `tests/test_etat.py`

**Interfaces :**
- Consumes : `ConkyQuery` importé depuis `~/.local/share/claude-monitor` (ajouter ce dossier à `sys.path` en tête de `etat.py`, constante `DOSSIER_MONITOR = Path.home() / ".local/share/claude-monitor"`).
- Produces :
  - `RGB = tuple[float, float, float]` ; `hex_vers_rgb(h: str) -> RGB` (composantes 0–1).
  - `GRIS: RGB`, `COULEURS_CONKY: dict[str, RGB]` (clés `"${color2}"` … `"${color8}"`).
  - `@dataclass(frozen=True) class Barre: remplissage: float` (0–100, borné) `; texte: str` (ex. `"38 %"` ou `"–"`) `; couleur: RGB ; texte_grise: bool ; trait: float | None`.
  - `@dataclass(frozen=True) class Affichage: barre_5h: Barre ; barre_7j: Barre ; statut: str` — `statut` ∈ `"normal"`, `"perime"`, `"indisponible"`.
  - `calculer_affichage(etat: dict | None, maintenant: datetime, q: ConkyQuery) -> Affichage` — `maintenant` est un datetime avec fuseau (heure locale).
  - `reinit_depassee(reset_iso: str | None, maintenant: datetime) -> bool`.

Règles :
- `etat` None, ou `usage_5h`/`usage_7d` non numériques → `statut="indisponible"`, deux barres `remplissage=0, texte="–", couleur=GRIS, texte_grise=True, trait=None`.
- `timestamp` (ISO naïf, heure locale → `.astimezone()`) absent/illisible ou `maintenant - ts > 15 min` → `statut="perime"`, barres en `GRIS`, `texte_grise=True`, texte = vrai pourcentage, `trait=None`.
- Sinon `statut="normal"` ; pour chaque fenêtre dont `reinit_depassee` est vrai : barre en `GRIS`, `texte="–"`, `remplissage=0`, `texte_grise=True`, `trait=None`.
- Barre 5 h normale : `COULEURS_CONKY[q.bar_color(u5)]`. Barre 7 j normale : `el = q.elapsed_7d_percent(r7, maintenant)`, couleur `COULEURS_CONKY[q.pace_color(u7, el)]`, `trait=el`.

- [ ] **Step 1 : écrire les tests qui échouent** — `tests/test_etat.py`, avec `MAINTENANT = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc).astimezone()` et un `etat_base()` frais (timestamp = MAINTENANT − 1 min en heure locale naïve, reset_5h = +2 h, reset_7d = +84 h) :
  - `test_5h_vert_jaune_rouge` : u5 = 59 → `hex_vers_rgb("a3be8c")` ; 60 → `ebcb8b` ; 85 → `bf616a`.
  - `test_7j_rythme_tenu` : u7 = 50, reset_7d = +84 h → couleur `5e81ac`, `trait ≈ 50.0` (places=1).
  - `test_7j_trop_rapide` : u7 = 51, même reset → `d35400`.
  - `test_texte_pourcentage` : u5 = 38.4 → `barre_5h.texte == "38 %"`, `texte_grise is False`.
  - `test_borne_remplissage` : u5 = 104 → `remplissage == 100`, `texte == "104 %"`.
  - `test_indisponible_none` et `test_indisponible_champ_manquant` (sans `usage_7d`) et `test_indisponible_non_numerique` (`usage_5h="abc"`) → `statut == "indisponible"`, textes `"–"`, couleurs `GRIS`.
  - `test_perime_16_min` : timestamp −16 min → `statut == "perime"`, couleurs `GRIS`, `texte == "38 %"`, `texte_grise`, `trait is None`.
  - `test_frais_14_min` : −14 min → `statut == "normal"`.
  - `test_timestamp_illisible_perime` et `test_timestamp_futur_frais` (+10 min → normal).
  - `test_reinit_5h_depassee` : reset_5h = −1 min → `barre_5h.texte == "–"`, couleur `GRIS` ; `barre_7j` inchangée (bleue).
  - `test_reinit_7j_depassee` : reset_7d = −1 min → `barre_7j.texte == "–"`, `trait is None`.
  - `test_perime_prime_sur_reinit` : timestamp −20 min et reset_5h passé → `statut == "perime"`, `barre_5h.texte == "38 %"`.

- [ ] **Step 2 : lancer** `python3 -I -m unittest discover -s tests -t .` — attendu : ÉCHEC (`ModuleNotFoundError: etat`).
- [ ] **Step 3 : implémenter `etat.py`** selon les interfaces et règles ci-dessus.
- [ ] **Step 4 : relancer** — attendu : tous les tests OK.
- [ ] **Step 5 : commit** `git add etat.py tests/test_etat.py && git commit -m "État d'affichage des barres de quotas"`

### Task 2: texte de l'infobulle (`infobulle.py`)

**Files :**
- Create : `infobulle.py`
- Test : `tests/test_infobulle.py`

**Interfaces :**
- Consumes : `calculer_affichage`, `reinit_depassee`, `Affichage` (tâche 1).
- Produces : `texte_infobulle(etat: dict | None, affichage: Affichage, maintenant: datetime, q: ConkyQuery) -> str` — texte brut (non échappé), lignes séparées par `\n`.

Format exact (normal) :
```
Claude Code — forfait {plan}
5 h : {u5} % · réinitialisation {q.format_reset_time(r5)} (dans {q.format_time_remaining(r5)})
7 j : {u7} % · {el:.0f} % du temps écoulé · rythme tenu|rythme trop rapide
réinitialisation {q.format_reset_time(r7)} (dans {q.format_time_remaining(r7)})
mis à jour à {last_update[:5]}
```
- `plan` : `{"pro": "Pro", "max_5x": "Max 5x", "max_20x": "Max 20x"}`, sinon `plan_type.title()` (même table que la route `plan` de `query.py`).
- Espaces avant « % » : insécables. « rythme trop rapide » si `u7 > el`. Si `el` est None, la ligne 7 j s'arrête après « {u7} % ».
- Réinitialisation 5 h dépassée : la ligne 5 h devient `5 h : réinitialisation en cours…`. Réinitialisation 7 j dépassée : la ligne 7 j devient `7 j : réinitialisation en cours…` et la ligne « réinitialisation … » 7 j disparaît.
- `statut == "perime"` : ligne ajoutée en tête `Données périmées (dernière mise à jour à {HH:MM})`, le reste inchangé.
- `statut == "indisponible"` : texte entier `Données indisponibles`.
- Note : le spec écrivait « réinitialisation à 13:40 » ; « à » est retiré parce que `format_reset_time` peut renvoyer « Demain 13:40 » ou « Jeu 14:00 ».

- [ ] **Step 1 : tests** (même `etat_base()` que la tâche 1 ; les heures attendues sont calculées avec `q.format_reset_time`/`q.format_time_remaining`) :
  - `test_premiere_ligne_pro` : `lignes[0] == "Claude Code — forfait Pro"`.
  - `test_forfait_inconnu` : `plan_type="team"` → `"… forfait Team"`.
  - `test_ligne_5h` : `lignes[1] == f"5 h : 38 % · réinitialisation {fr5} (dans {tr5})"`.
  - `test_rythme_tenu` / `test_rythme_trop_rapide` : `lignes[2]` se termine par « rythme tenu » / « rythme trop rapide » et contient `"50 % du temps écoulé"`.
  - `test_derniere_ligne` : `last_update="12:41:36"` → `"mis à jour à 12:41"`.
  - `test_reinit_5h_en_cours` : `lignes[1] == "5 h : réinitialisation en cours…"`.
  - `test_reinit_7j_en_cours` : ligne 7 j = `"7 j : réinitialisation en cours…"`, aucune autre ligne ne commence par « réinitialisation ».
  - `test_perime_en_tete` : `lignes[0].startswith("Données périmées (dernière mise à jour à ")`.
  - `test_indisponible` : texte == `"Données indisponibles"`.
- [ ] **Step 2 : lancer** les tests — attendu : ÉCHEC (module absent).
- [ ] **Step 3 : implémenter `texte_infobulle`.**
- [ ] **Step 4 : relancer** — attendu : tous les tests OK.
- [ ] **Step 5 : commit** `git commit -m "Texte de l'infobulle"` (avec les deux fichiers).

### Task 3: dessin du PNG (`dessin.py`)

**Files :**
- Create : `dessin.py`
- Test : `tests/test_dessin.py`

**Interfaces :**
- Consumes : `Affichage`, `Barre`, `hex_vers_rgb` (tâche 1).
- Produces :
  - constantes `LARGEUR: int`, `HAUTEUR: int` (hauteur ≤ 37 ; point de départ : 32) ;
  - `rect_barre(indice: int) -> tuple[int, int, int, int]` (x, y, l, h de l'intérieur de la barre, sans la bordure ; 0 = 5 h, 1 = 7 j) ;
  - `dessiner(affichage: Affichage, chemin: Path) -> None` — écrit d'abord `chemin.with_suffix(".tmp.png")`, puis `os.replace`.

Mise en page (spec + maquette) : colonne d'étiquettes « 5 h » / « 7 j » (Luciole gras, ~11 px, `111111`), deux barres d'environ 70 × 9 px empilées avec 5 px d'écart, colonne des pourcentages à droite (gris `8c8c8c` si `texte_grise`). Le remplissage couvre `remplissage %` de la largeur intérieure ; le trait (2 px, `2e3440`) est centré sur `trait %` et déborde de 1 px en haut et en bas. Fond PNG transparent (ARGB32). Dimensions exactes à régler par le constructeur.

- [ ] **Step 1 : tests** (lire le PNG avec `cairo.ImageSurface.create_from_png`, échantillonner un pixel ; attention à l'ordre BGRA prémultiplié de ARGB32 — prévoir un utilitaire `pixel(surface, x, y) -> (r, g, b)` dans le test) :
  - `test_dimensions` : surface `LARGEUR × HAUTEUR`.
  - `test_remplissage_couleur` : 5 h à 50 % vert → pixel au quart de `rect_barre(0)` ≈ `a3be8c` (tolérance ±2 par composante) ; pixel aux trois quarts ≈ `555555`.
  - `test_remplissage_borne` : `remplissage=100` → dernier pixel intérieur ≈ couleur de la barre.
  - `test_trait` : 7 j avec `trait=50` → pixel au milieu de `rect_barre(1)` ≈ `2e3440`.
  - `test_ecriture_atomique` : après `dessiner`, le `.tmp.png` n'existe plus et le fichier final existe.
- [ ] **Step 2 : lancer** — attendu : ÉCHEC.
- [ ] **Step 3 : implémenter `dessin.py`** (API « toy » de Cairo : `select_font_face("Luciole", NORMAL, BOLD)`).
- [ ] **Step 4 : relancer** — attendu : OK. Ouvrir un PNG généré (`dessiner` sur `etat_base()`) et le regarder pour vérifier la netteté et la lisibilité à taille réelle.
- [ ] **Step 5 : commit** `git commit -m "Dessin des barres en PNG"`.

### Task 4: point d'entrée genmon (`barre_quotas.py`)

**Files :**
- Create : `barre_quotas.py` (exécutable, `#!/usr/bin/env python3`)
- Test : `tests/test_sortie.py`

**Interfaces :**
- Consumes : tâches 1 à 3.
- Produces :
  - `chemin_png() -> Path` : `$XDG_RUNTIME_DIR/claude-barre-quotas.png`, ou `/tmp/claude-barre-quotas.png` si la variable est absente ou vide ;
  - `sortie_genmon(chemin: Path, infobulle: str) -> str` : `f"<img>{chemin}</img><tool>{html.escape(infobulle, quote=False)}</tool>"` ;
  - `main() -> int` : `q = ConkyQuery()`, `etat = q.load_current_state()`, `maintenant = datetime.now().astimezone()`, calcul, dessin, impression ; **toute** exception → imprime `<txt>Claude ?</txt><tool>Erreur : {message échappé}</tool>` ; renvoie toujours 0. `if __name__ == "__main__": sys.exit(main())`. Les imports de `etat`, `dessin` et `infobulle` se font dans `main()`, sous le `try`, pour qu'un `query.py` introuvable soit aussi rattrapé. Ajouter au début `sys.path.insert(0, str(Path(__file__).resolve().parent))`, pour que l'import fonctionne via le lien dans `~/.local/bin`.

- [ ] **Step 1 : tests** :
  - `test_chemin_xdg` (avec `XDG_RUNTIME_DIR=/run/user/1000` via `unittest.mock.patch.dict(os.environ, …)`) et `test_chemin_repli_tmp` (variable supprimée).
  - `test_echappement` : `sortie_genmon(Path("/x.png"), "a & <b>")` == `"<img>/x.png</img><tool>a &amp; &lt;b&gt;</tool>"`.
  - `test_main_ne_plante_jamais` : `patch("etat.calculer_affichage", side_effect=RuntimeError("boum"))`, capture de stdout → code 0, sortie contenant `<txt>Claude ?</txt>` et `boum`.
  - `test_main_bout_en_bout` : `XDG_RUNTIME_DIR` pointé vers un `tempfile.TemporaryDirectory()` → code 0, la sortie commence par `<img>` et le PNG existe.
- [ ] **Step 2 : lancer** — attendu : ÉCHEC.
- [ ] **Step 3 : implémenter `barre_quotas.py`**, puis `chmod +x barre_quotas.py`.
- [ ] **Step 4 : relancer** toute la suite — attendu : OK. Puis `./barre_quotas.py` à la main : une ligne `<img>…</img><tool>…</tool>` avec les chiffres actuels de `current.json`.
- [ ] **Step 5 : commit** `git commit -m "Point d'entrée genmon"`.

### Task 5: installation et mise en place dans le tableau de bord

**Files :**
- Create : `install.sh`, `README.md`

- [ ] **Step 1 : `install.sh`** (`set -eu`) : vérifie que `~/.local/share/claude-monitor/query.py` existe et que `python3 -c "import cairo"` passe (sinon message clair et code 1), puis `ln -sfn "$(pwd)/barre_quotas.py" ~/.local/bin/claude-barre-quotas` (le script est résolu depuis son propre dossier, pas depuis le répertoire courant).
- [ ] **Step 2 : `README.md`** en français : rôle, prérequis, `./install.sh`, procédure manuelle (clic droit sur le tableau de bord → Tableau de bord → Ajouter des éléments → « Moniteur générique », le placer juste à gauche de la zone de notification ; propriétés : commande `~/.local/bin/claude-barre-quotas`, étiquette décochée, période 60 s), lancement des tests, signification des couleurs et des états gris.
- [ ] **Step 3 : vérifier** : `./install.sh` puis `claude-barre-quotas` → sortie genmon valide ; `python3 -I -m unittest discover -s tests -t .` → OK.
- [ ] **Step 4 : contrôle visuel avec l'utilisateur** : il ajoute le greffon en suivant le README. On vérifie ensemble que les barres sont nettes, que l'infobulle s'affiche, que l'image se rafraîchit au bout d'une minute (sinon : genmon garde l'image en cache pour un chemin identique → alterner deux noms de fichier) et que le rendu tient dans les 37 px.
- [ ] **Step 5 : commit** `git commit -m "Installation et documentation"`.
