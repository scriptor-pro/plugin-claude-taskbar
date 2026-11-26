import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import barre_quotas
from barre_quotas import chemin_png, sortie_genmon


def lancer_main() -> tuple[int, str]:
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        code = barre_quotas.main()
    return code, tampon.getvalue()


class TestSortie(unittest.TestCase):
    def test_chemin_xdg(self):
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1000"}):
            self.assertEqual(chemin_png(), Path("/run/user/1000/claude-barre-quotas.png"))

    def test_chemin_repli_tmp(self):
        env = {k: v for k, v in os.environ.items() if k != "XDG_RUNTIME_DIR"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(chemin_png(), Path(f"/tmp/claude-barre-quotas-{os.getuid()}.png"))

    def test_chemin_xdg_vide(self):
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": ""}):
            self.assertEqual(chemin_png(), Path(f"/tmp/claude-barre-quotas-{os.getuid()}.png"))

    def test_echappement(self):
        self.assertEqual(sortie_genmon(Path("/x.png"), "a & <b>"),
                         "<img>/x.png</img><tool>a &amp; &lt;b&gt;</tool>")

    def test_main_ne_plante_jamais(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"XDG_RUNTIME_DIR": d}), \
                patch("etat.calculer_affichage", side_effect=RuntimeError("boum <x>")):
            code, sortie = lancer_main()
        self.assertEqual(code, 0)
        self.assertIn("<txt>Claude ?</txt>", sortie)
        self.assertIn("boum &lt;x&gt;", sortie)

    def test_main_bout_en_bout(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"XDG_RUNTIME_DIR": d}):
            code, sortie = lancer_main()
            self.assertEqual(code, 0)
            self.assertTrue(sortie.startswith("<img>"), sortie)
            self.assertTrue((Path(d) / "claude-barre-quotas.png").exists())


if __name__ == "__main__":
    unittest.main()
