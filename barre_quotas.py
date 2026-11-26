#!/usr/bin/env python3
"""Point d'entrée pour xfce4-genmon-plugin : dessine les barres de quotas Claude Code
et imprime <img>…</img><tool>…</tool>. Ne sort jamais en erreur."""

import html
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NOM_PNG = "claude-barre-quotas.png"


def chemin_png() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / NOM_PNG


def sortie_genmon(chemin: Path, infobulle: str) -> str:
    return f"<img>{chemin}</img><tool>{html.escape(infobulle, quote=False)}</tool>"


def main() -> int:
    try:
        import etat
        from dessin import dessiner
        from infobulle import texte_infobulle

        q = etat.ConkyQuery()
        donnees = q.load_current_state()
        maintenant = datetime.now().astimezone()
        affichage = etat.calculer_affichage(donnees, maintenant, q)
        chemin = chemin_png()
        dessiner(affichage, chemin)
        print(sortie_genmon(chemin, texte_infobulle(donnees, affichage, maintenant, q)))
    except Exception as erreur:  # genmon doit toujours recevoir une sortie valide
        print(f"<txt>Claude ?</txt><tool>Erreur : {html.escape(str(erreur), quote=False)}</tool>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
