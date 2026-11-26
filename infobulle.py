"""Texte brut (non échappé) de l'infobulle affichée au survol de la barre."""

from datetime import datetime

from etat import Affichage, ConkyQuery, lire_iso, reinit_depassee, reset_avec_fuseau, texte_pourcentage

FORFAITS = {"pro": "Pro", "max_5x": "Max 5x", "max_20x": "Max 20x"}
EN_COURS = "réinitialisation en cours…"


def heure_maj(etat: dict) -> str:
    """HH:MM de la dernière mise à jour : last_update, sinon timestamp, sinon « inconnue »."""
    if etat.get("last_update"):
        return str(etat["last_update"])[:5]
    ts = lire_iso(etat.get("timestamp")) if etat.get("timestamp") else None
    return ts.strftime("%H:%M") if ts else "inconnue"


def texte_infobulle(etat: dict | None, affichage: Affichage, maintenant: datetime, q: ConkyQuery) -> str:
    if affichage.statut == "indisponible":
        return "Données indisponibles"

    u5, u7 = float(etat["usage_5h"]), float(etat["usage_7d"])
    r5, r7 = etat.get("reset_5h"), etat.get("reset_7d")
    plan = str(etat.get("plan_type") or "inconnu")

    lignes = []
    if affichage.statut == "perime":
        lignes.append(f"Données périmées (dernière mise à jour à {heure_maj(etat)})")
    lignes.append(f"Claude Code — forfait {FORFAITS.get(plan, plan.title())}")

    if reinit_depassee(r5, maintenant):
        lignes.append(f"5 h : {EN_COURS}")
    else:
        lignes.append(f"5 h : {texte_pourcentage(u5)} · réinitialisation "
                      f"{q.format_reset_time(r5)} (dans {q.format_time_remaining(r5)})")

    if reinit_depassee(r7, maintenant):
        lignes.append(f"7 j : {EN_COURS}")
    else:
        ligne = f"7 j : {texte_pourcentage(u7)}"
        ecoule = q.elapsed_7d_percent(reset_avec_fuseau(r7), maintenant)
        if ecoule is not None:
            rythme = "rythme trop rapide" if q.pace_color(u7, ecoule) == "${color7}" else "rythme tenu"
            ligne += f" · {texte_pourcentage(ecoule)} du temps écoulé · {rythme}"
        lignes.append(ligne)
        lignes.append(f"réinitialisation {q.format_reset_time(r7)} (dans {q.format_time_remaining(r7)})")

    lignes.append(f"mis à jour à {heure_maj(etat)}")
    return "\n".join(lignes)
