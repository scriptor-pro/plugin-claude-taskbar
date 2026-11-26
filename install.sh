#!/bin/sh
# Installe la commande claude-barre-quotas (lien vers barre_quotas.py) dans ~/.local/bin.
set -eu

DOSSIER=$(cd "$(dirname "$0")" && pwd)
QUERY="$HOME/.local/share/claude-monitor/query.py"
CIBLE="$HOME/.local/bin/claude-barre-quotas"

if [ ! -f "$QUERY" ]; then
    echo "Erreur : $QUERY introuvable. Installez d'abord le widget Conky Claude Code (claude-monitor)." >&2
    exit 1
fi
if ! python3 -c "import cairo" 2>/dev/null; then
    echo "Erreur : le module Python cairo est absent (paquet python3-cairo)." >&2
    exit 1
fi

mkdir -p "$HOME/.local/bin"
ln -sfn "$DOSSIER/barre_quotas.py" "$CIBLE"
echo "Installé : $CIBLE → $DOSSIER/barre_quotas.py"
echo "Ajoutez maintenant le « Moniteur générique » au tableau de bord (voir README.md)."
