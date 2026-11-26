import tempfile
import unittest
from pathlib import Path

import cairo

from dessin import HAUTEUR, LARGEUR, dessiner, rect_barre
from etat import GRIS, Affichage, Barre, hex_vers_rgb

VERT = hex_vers_rgb("a3be8c")
BLEU = hex_vers_rgb("5e81ac")


def pixel(surface: cairo.ImageSurface, x: int, y: int) -> tuple[int, int, int]:
    """(r, g, b) 0–255 d'un pixel opaque (ARGB32 = octets B, G, R, A en mémoire)."""
    donnees = surface.get_data()
    i = y * surface.get_stride() + x * 4
    b, g, r = donnees[i], donnees[i + 1], donnees[i + 2]
    return r, g, b


def en_octets(rgb) -> tuple[int, int, int]:
    return tuple(round(c * 255) for c in rgb)


def affichage(b5: Barre, b7: Barre) -> Affichage:
    return Affichage(b5, b7, "normal")


B5_VERT_50 = Barre(50, "50 %", VERT, False, None)
B7_BLEU_30 = Barre(30, "30 %", BLEU, False, 50)


class TestDessin(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.chemin = Path(self.dossier.name) / "barre.png"

    def tearDown(self):
        self.dossier.cleanup()

    def rendu(self, aff: Affichage) -> cairo.ImageSurface:
        dessiner(aff, self.chemin)
        return cairo.ImageSurface.create_from_png(str(self.chemin))

    def assertCouleur(self, obtenu, attendu_rgb):
        for o, a in zip(obtenu, en_octets(attendu_rgb)):
            self.assertLessEqual(abs(o - a), 2, f"{obtenu} ≠ {en_octets(attendu_rgb)}")

    def test_dimensions(self):
        s = self.rendu(affichage(B5_VERT_50, B7_BLEU_30))
        self.assertEqual((s.get_width(), s.get_height()), (LARGEUR, HAUTEUR))
        self.assertLessEqual(HAUTEUR, 37)

    def test_remplissage_couleur(self):
        s = self.rendu(affichage(B5_VERT_50, B7_BLEU_30))
        x, y, l, h = rect_barre(0)
        self.assertCouleur(pixel(s, x + l // 4, y + h // 2), VERT)
        self.assertCouleur(pixel(s, x + 3 * l // 4, y + h // 2), hex_vers_rgb("555555"))

    def test_remplissage_borne(self):
        s = self.rendu(affichage(Barre(100, "104 %", VERT, False, None), B7_BLEU_30))
        x, y, l, h = rect_barre(0)
        self.assertCouleur(pixel(s, x + l - 1, y + h // 2), VERT)

    def test_trait(self):
        s = self.rendu(affichage(B5_VERT_50, B7_BLEU_30))
        x, y, l, h = rect_barre(1)
        self.assertCouleur(pixel(s, x + l // 2, y + h // 2), hex_vers_rgb("2e3440"))

    def test_barre_grise(self):
        s = self.rendu(affichage(Barre(40, "40 %", GRIS, True, None), B7_BLEU_30))
        x, y, l, h = rect_barre(0)
        self.assertCouleur(pixel(s, x + 2, y + h // 2), GRIS)

    def test_pourcentage_ne_deborde_pas(self):
        """« 104 % » (le plus long texte possible en pratique) tient à droite de la barre."""
        import dessin
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        ctx = cairo.Context(surface)
        dessin.preparer_police(ctx)
        largeur = ctx.text_extents(dessin.texte_affichable("104\u00a0%")).x_advance
        x, _, l, _ = rect_barre(0)
        self.assertLessEqual(x + l + 1 + 3 + largeur, LARGEUR - 2)

    def test_espace_insecable_remplacee(self):
        import dessin
        self.assertEqual(dessin.texte_affichable("38\u00a0%"), "38 %")

    def test_ecriture_atomique(self):
        self.rendu(affichage(B5_VERT_50, B7_BLEU_30))
        self.assertTrue(self.chemin.exists())
        self.assertFalse(self.chemin.with_suffix(".tmp.png").exists())


if __name__ == "__main__":
    unittest.main()
