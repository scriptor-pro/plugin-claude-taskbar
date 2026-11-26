"""État d'affichage des deux barres de quotas, calculé à partir de current.json.

Les seuils, le rythme et le temps écoulé viennent de ConkyQuery (query.py du widget Conky),
pour que la barre des tâches et Conky ne divergent jamais.
"""

import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DOSSIER_MONITOR = Path.home() / ".local/share/claude-monitor"
if str(DOSSIER_MONITOR) not in sys.path:
    sys.path.append(str(DOSSIER_MONITOR))

from query import ConkyQuery  # noqa: E402

RGB = tuple[float, float, float]

DELAI_PEREMPTION = timedelta(minutes=15)
TIRET = "–"


def hex_vers_rgb(h: str) -> RGB:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


GRIS: RGB = hex_vers_rgb("8c8c8c")

# Valeurs reprises de ~/.conky/MX-Claude/claude-conkyrc
COULEURS_CONKY: dict[str, RGB] = {
    "${color2}": hex_vers_rgb("ebcb8b"),
    "${color3}": hex_vers_rgb("a3be8c"),
    "${color5}": hex_vers_rgb("bf616a"),
    "${color7}": hex_vers_rgb("d35400"),
    "${color8}": hex_vers_rgb("5e81ac"),
}


@dataclass(frozen=True)
class Barre:
    remplissage: float
    texte: str
    couleur: RGB
    texte_grise: bool
    trait: float | None


@dataclass(frozen=True)
class Affichage:
    barre_5h: Barre
    barre_7j: Barre
    statut: str  # "normal", "perime" ou "indisponible"


BARRE_VIDE = Barre(remplissage=0, texte=TIRET, couleur=GRIS, texte_grise=True, trait=None)


def texte_pourcentage(valeur: float) -> str:
    return f"{valeur:.0f} %"


def borner(valeur: float) -> float:
    return max(0.0, min(100.0, valeur))


def lire_iso(texte) -> datetime | None:
    """Lit une date ISO ; une date sans fuseau est interprétée en heure locale."""
    try:
        dt = datetime.fromisoformat(str(texte).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.astimezone()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def reset_avec_fuseau(reset_iso: str | None) -> str | None:
    """Ajoute le fuseau local à une date de réinitialisation qui n'en a pas (query.py en a besoin)."""
    dt = lire_iso(reset_iso) if reset_iso else None
    return dt.isoformat() if dt else reset_iso


def reinit_depassee(reset_iso: str | None, maintenant: datetime) -> bool:
    reset = lire_iso(reset_iso) if reset_iso else None
    return reset is not None and reset <= maintenant


def est_perime(etat: dict, maintenant: datetime) -> bool:
    ts = lire_iso(etat.get("timestamp")) if etat.get("timestamp") else None
    return ts is None or maintenant - ts > DELAI_PEREMPTION


def est_nombre(valeur) -> bool:
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool) and math.isfinite(valeur)


def calculer_affichage(etat: dict | None, maintenant: datetime, q: ConkyQuery) -> Affichage:
    if not isinstance(etat, dict) or not (est_nombre(etat.get("usage_5h")) and est_nombre(etat.get("usage_7d"))):
        return Affichage(BARRE_VIDE, BARRE_VIDE, "indisponible")

    u5, u7 = float(etat["usage_5h"]), float(etat["usage_7d"])

    if est_perime(etat, maintenant):
        def grise(u: float) -> Barre:
            return Barre(borner(u), texte_pourcentage(u), GRIS, True, None)
        return Affichage(grise(u5), grise(u7), "perime")

    r5, r7 = etat.get("reset_5h"), etat.get("reset_7d")

    if reinit_depassee(r5, maintenant):
        b5 = BARRE_VIDE
    else:
        b5 = Barre(borner(u5), texte_pourcentage(u5), COULEURS_CONKY[q.bar_color(u5)], False, None)

    if reinit_depassee(r7, maintenant):
        b7 = BARRE_VIDE
    else:
        ecoule = q.elapsed_7d_percent(reset_avec_fuseau(r7), maintenant)
        b7 = Barre(borner(u7), texte_pourcentage(u7), COULEURS_CONKY[q.pace_color(u7, ecoule)], False, ecoule)

    return Affichage(b5, b7, "normal")
