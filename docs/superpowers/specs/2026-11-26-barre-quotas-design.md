# Quotas Claude Code dans le tableau de bord Xfce — conception

Date : 2026-11-26 · État : en attente d'approbation

## Intention

Le widget Conky (`~/.conky/MX-Claude/claude-conkyrc`) affiche les quotas Claude Code 5 h et 7 j sur le
bureau, mais il faut masquer toutes les fenêtres pour le voir. On veut la même information **toujours
visible** dans le tableau de bord Xfce (xfce4-panel, en haut de l'écran, 37 px de haut, police Luciole 12,
DPI 96), lisible d'un coup d'œil, avec le détail au survol.

## Objectifs

- Deux mini-barres empilées dans le tableau de bord : 5 h en haut, 7 j en bas (option C de
  `docs/maquettes/apparence-barre.html`).
- Mêmes couleurs et même sens que Conky.
- Infobulle détaillée au survol.
- Mise à jour toutes les minutes.

## Non-objectifs

- Ne pas modifier le widget Conky ni `claude-monitor.service` : ils restent tels quels.
- Ne pas interroger l'API Anthropic : on lit seulement `current.json`, déjà écrit par le service.
- Pas d'action au clic (hors périmètre de cette version).
- Pas de compatibilité avec d'autres tableaux de bord que xfce4-panel.

## Anti-objectifs (échec même si « ça marche »)

- Présenter un chiffre périmé comme actuel.
- Diverger de Conky : deux logiques de couleur qui finissent par ne plus être d'accord.
- Faire planter ou figer le tableau de bord si le fichier de données manque ou est corrompu.

## Contraintes

- Hauteur disponible : 37 px. Police Luciole (installée dans `~/.local/share/fonts`), DPI 96.
- Disponibles : xfce4-genmon-plugin 4.1.1, python3, pycairo 1.27. Aucune nouvelle dépendance.
- Données : `~/.local/share/claude-monitor/current.json`, réécrit toutes les 300 s :
  `usage_5h`, `usage_7d` (en %), `reset_5h`, `reset_7d` (ISO 8601 avec fuseau),
  `plan_type`, `timestamp` (ISO, heure locale sans fuseau), `last_update` (HH:MM:SS).
- Logique existante dans `~/.local/share/claude-monitor/query.py`, classe `ConkyQuery` :
  `bar_color`, `elapsed_7d_percent`, `pace_color`, `format_time_remaining`, `format_reset_time`,
  `load_current_state`. Elle renvoie des couleurs au format Conky (`${color3}`…). Source versionnée :
  `~/.local/src/ConkyClaudeCode` (branche `personnalisation`).

## Approches envisagées

1. **genmon + PNG dessiné avec pycairo** — *retenue par l'utilisateur.* Un script Python lancé par genmon
   importe `ConkyQuery`, dessine les barres dans un PNG et fournit l'infobulle. Rendu net, aucune nouvelle
   dépendance, une seule source de vérité avec Conky.
2. genmon + SVG écrit en texte : aucune dépendance, mais les traits fins de 1–2 px sont moins nets une fois
   rendus par librsvg à cette taille.
3. Greffon Xfce natif en C : démesuré pour deux barres et une infobulle.

## Ce qui a été décidé

### Aspect (validé par l'utilisateur)

```
 5 h ▕██████░░░░░░▏ 38 %
 7 j ▕██████████▌░▏ 80 %      ▌ = trait du temps écoulé sur 7 j
```

- Étiquettes « 5 h » / « 7 j » à gauche, pourcentages entiers à droite (« 38 % », espace insécable).
- Barres d'environ 70 × 9 px, fond gris foncé (#555), bordure 1 px (#1a1a1a), 5 px d'écart vertical.
- Texte en gras, ~11 px, couleur adaptée au fond clair du tableau de bord (#111 dans la maquette).

### Couleurs (reprises de Conky)

| Élément | Règle | Couleur |
|---|---|---|
| Barre 5 h | < 60 % | vert `a3be8c` (color3) |
| | < 85 % | jaune `ebcb8b` (color2) |
| | sinon | rouge `bf616a` (color5) |
| Barre 7 j | conso ≤ temps écoulé + 5 points, ou temps écoulé inconnu | bleu `5e81ac` (color8) |
| | conso > temps écoulé + 5 points (tolérance ajoutée le 2026-11-26 dans query.py, Conky compris) | orange `d35400` (color7) |
| Trait 7 j | position = % de temps écoulé sur 7 j ; absent si inconnu | anthracite `2e3440`, 2 px |

Les seuils et la règle de rythme viennent **de `ConkyQuery`** (on appelle ses méthodes) ; le script ne
contient qu'une table de correspondance `${colorN}` → RVB, reprise des valeurs de `claude-conkyrc`.

### Infobulle

```
Claude Code — forfait Pro
5 h : 38 % · réinitialisation à 13:40 (dans 33m)
7 j : 80 % · 99 % du temps écoulé · rythme tenu
réinitialisation Jeu 14:00 (dans 53m)
mis à jour à 12:41
```

- « rythme tenu » si conso ≤ temps écoulé, « rythme trop rapide » sinon ; segment omis si le temps écoulé
  est inconnu.
- Heures et durées produites par `format_reset_time` / `format_time_remaining` (formats de Conky).

### Données périmées ou absentes

- Données de plus de 15 min (d'après `timestamp`) : barres et pourcentages en **gris**, et l'infobulle
  commence par « Données périmées (dernière mise à jour à HH:MM) ».
- Heure de réinitialisation d'une fenêtre dépassée (`reset_5h` ou `reset_7d` ≤ maintenant) alors que les
  données ne sont pas encore rafraîchies — *choix de l'utilisateur (option A)* : **cette barre seule** passe
  en gris, son pourcentage devient « – » (et le trait 7 j disparaît), et sa ligne d'infobulle devient
  « 5 h : réinitialisation en cours… » (resp. « 7 j : … »). Retour automatique à l'affichage normal dès que
  le service écrit des données dont la réinitialisation est dans le futur. Règle propre à la barre :
  `query.py` et Conky ne changent pas (Conky continue d'afficher l'ancien chiffre pendant ce délai).
- Fichier absent ou illisible : barres vides grises, pourcentages remplacés par « – », infobulle
  « Données indisponibles ». Le script ne sort jamais en erreur vers genmon.

### Mécanique

- Script `barre_quotas.py` dans ce dépôt, appelé par genmon (période : 60 s).
- Il ajoute `~/.local/share/claude-monitor` au chemin d'import et importe `ConkyQuery`.
- Il dessine le PNG dans `$XDG_RUNTIME_DIR/claude-barre-quotas.png` (écriture dans un fichier temporaire
  puis `os.replace`, pour que genmon ne lise jamais une image à moitié écrite), puis écrit sur la sortie
  standard : `<img>chemin</img><tool>infobulle</tool>` (texte de l'infobulle échappé pour Pango).
- La logique (calcul de l'état d'affichage, texte de l'infobulle) est séparée du dessin, pour être testée
  avec `unittest` sans Cairo ni tableau de bord.

### Installation

- Un `install.sh` qui crée le lien `~/.local/bin/claude-barre-quotas` vers le script.
- Ajout du greffon genmon : à gauche de la zone de notification (`systray`, plugin-6), via la fenêtre
  « Ajouter des éléments » du tableau de bord, commande `~/.local/bin/claude-barre-quotas`, période 60 s,
  étiquette désactivée. La procédure manuelle est documentée dans un README ; pas de modification
  automatique de xfconf.

## Laissé au constructeur

- Dimensions exactes en pixels (largeur des colonnes de texte, marges) pour tenir dans 37 px et rester net.
- Facteur d'échelle si le DPI change (non requis aujourd'hui).
- Organisation interne du code et des tests (couvrir au minimum : seuils de couleur 5 h, rythme 7 j,
  données périmées, réinitialisation dépassée par fenêtre, fichier absent/corrompu, échappement Pango).
- Priorité des états si plusieurs s'appliquent : indisponible > périmé > réinitialisation dépassée > normal
  (*mon choix*).
