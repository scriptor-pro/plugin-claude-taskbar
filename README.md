# Quotas Claude Code dans le tableau de bord Xfce

Affiche en permanence, dans xfce4-panel, les quotas Claude Code sous forme de deux mini-barres :
**5 h** en haut, **7 j** en bas, avec le pourcentage à droite. Le détail apparaît au survol.

Les données viennent de `~/.local/share/claude-monitor/current.json`, écrit toutes les 5 minutes par le
service `claude-monitor` du widget Conky. Les couleurs et les calculs sont repris de son `query.py` :
la barre et Conky affichent toujours la même chose.

## Prérequis

- Le widget Conky Claude Code installé (`~/.local/share/claude-monitor/query.py` et le service `claude-monitor`).
- `xfce4-genmon-plugin` et `python3-cairo`.

## Installation

```sh
./install.sh
```

Cela crée la commande `~/.local/bin/claude-barre-quotas`. Ensuite, dans le tableau de bord :

1. Clic droit sur le tableau de bord → **Tableau de bord** → **Ajouter de nouveaux éléments**.
2. Ajouter **Moniteur générique** (Generic Monitor), puis le déplacer juste à gauche de la zone de notification.
3. Clic droit sur le nouvel élément → **Propriétés** :
   - Commande : `/home/<vous>/.local/bin/claude-barre-quotas` (chemin complet) ;
   - **Étiquette** décochée ;
   - Période : **60** secondes.

## Lecture

| Élément | Signification |
|---|---|
| Barre 5 h verte / jaune / rouge | moins de 60 % / moins de 85 % / au-delà |
| Barre 7 j bleue | consommation au plus 5 points au-dessus du temps écoulé |
| Barre 7 j orange | consommation de plus de 5 points au-dessus du temps écoulé |
| Trait sombre sur la barre 7 j | part de la semaine déjà écoulée |
| Barres et chiffres gris | données de plus de 15 minutes : chiffres non actuels |
| Barre grise et « – » | réinitialisation passée, en attente des nouvelles données |
| Deux barres vides et « – » | données indisponibles |
| « Claude ? » | erreur inattendue (détail au survol) |

## Tests

```sh
python3 -I -m unittest discover -s tests -t .
```
