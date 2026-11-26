"""Dessin des deux mini-barres dans un PNG transparent, pour genmon."""

import os
from pathlib import Path

import cairo

from etat import Affichage, Barre, hex_vers_rgb

HAUTEUR = 32
POLICE = "Luciole"
TAILLE_POLICE = 11

MARGE = 4
LARGEUR_ETIQUETTES = 22
ECART = 6
LARGEUR_BARRE = 70  # bordure comprise
HAUTEUR_BARRE = 9   # bordure comprise
ECART_BARRES = 5
LARGEUR_POURCENTAGES = 44

X_BARRE = MARGE + LARGEUR_ETIQUETTES + ECART
LARGEUR = X_BARRE + LARGEUR_BARRE + ECART + LARGEUR_POURCENTAGES + MARGE
Y_PREMIERE = (HAUTEUR - (2 * HAUTEUR_BARRE + ECART_BARRES)) // 2

FOND = hex_vers_rgb("555555")
BORDURE = hex_vers_rgb("1a1a1a")
TRAIT = hex_vers_rgb("2e3440")
TEXTE = hex_vers_rgb("111111")
TEXTE_GRIS = hex_vers_rgb("5c5c5c")  # lisible sur le fond clair du tableau de bord
ETIQUETTES = ("5 h", "7 j")


def texte_affichable(texte: str) -> str:
    """L'API texte simple de Cairo n'a pas de police de repli : l'espace insécable devient une espace."""
    return texte.replace("\u00a0", " ")


def preparer_police(ctx: cairo.Context) -> None:
    ctx.select_font_face(POLICE, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(TAILLE_POLICE)
    options = cairo.FontOptions()
    options.set_antialias(cairo.ANTIALIAS_GRAY)  # pas de franges colorées sur fond transparent
    ctx.set_font_options(options)


def y_barre(indice: int) -> int:
    """Ordonnée du bord haut (bordure comprise) de la barre."""
    return Y_PREMIERE + indice * (HAUTEUR_BARRE + ECART_BARRES)


def rect_barre(indice: int) -> tuple[int, int, int, int]:
    """Intérieur de la barre (sans bordure) : x, y, largeur, hauteur."""
    return X_BARRE + 1, y_barre(indice) + 1, LARGEUR_BARRE - 2, HAUTEUR_BARRE - 2


def texte_centre_vertical(ctx: cairo.Context, texte: str, x: float, y_centre: float, aligner_droite=False):
    texte = texte_affichable(texte)
    ext = ctx.text_extents(texte)
    if aligner_droite:
        x -= ext.x_advance
    ctx.move_to(x, round(y_centre - ext.y_bearing - ext.height / 2))
    ctx.show_text(texte)


def dessiner_barre(ctx: cairo.Context, indice: int, barre: Barre):
    x, y, l, h = rect_barre(indice)
    ctx.set_source_rgb(*BORDURE)
    ctx.rectangle(x - 1, y - 1, l + 2, h + 2)
    ctx.fill()
    ctx.set_source_rgb(*FOND)
    ctx.rectangle(x, y, l, h)
    ctx.fill()
    rempli = round(l * max(0.0, min(100.0, barre.remplissage)) / 100)
    if rempli:
        ctx.set_source_rgb(*barre.couleur)
        ctx.rectangle(x, y, rempli, h)
        ctx.fill()
    if barre.trait is not None:
        xt = x + round(l * barre.trait / 100) - 1
        xt = max(x - 1, min(x + l - 1, xt))
        ctx.set_source_rgb(*TRAIT)
        ctx.rectangle(xt, y - 2, 2, h + 4)
        ctx.fill()

    y_centre = y + h / 2
    ctx.set_source_rgb(*TEXTE)
    texte_centre_vertical(ctx, ETIQUETTES[indice], MARGE, y_centre)
    ctx.set_source_rgb(*(TEXTE_GRIS if barre.texte_grise else TEXTE))
    texte_centre_vertical(ctx, barre.texte, LARGEUR - MARGE, y_centre, aligner_droite=True)


def dessiner(affichage: Affichage, chemin: Path) -> None:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, LARGEUR, HAUTEUR)
    ctx = cairo.Context(surface)
    preparer_police(ctx)
    for indice, barre in enumerate((affichage.barre_5h, affichage.barre_7j)):
        dessiner_barre(ctx, indice, barre)
    surface.flush()

    temporaire = chemin.with_suffix(".tmp.png")
    surface.write_to_png(str(temporaire))
    os.replace(temporaire, chemin)
