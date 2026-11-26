import unittest
from datetime import datetime, timedelta, timezone

from etat import GRIS, ConkyQuery, calculer_affichage, hex_vers_rgb

MAINTENANT = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc).astimezone()


def horodatage(delta: timedelta) -> str:
    """Horodatage au format de current.json : ISO, heure locale, sans fuseau."""
    return (MAINTENANT + delta).replace(tzinfo=None).isoformat()


def etat_base(**surcharges) -> dict:
    etat = {
        "timestamp": horodatage(-timedelta(minutes=1)),
        "usage_5h": 38.0,
        "usage_7d": 50.0,
        "reset_5h": (MAINTENANT + timedelta(hours=2)).isoformat(),
        "reset_7d": (MAINTENANT + timedelta(hours=84)).isoformat(),
        "plan_type": "pro",
        "last_update": "11:59:00",
    }
    etat.update(surcharges)
    return etat


class TestEtat(unittest.TestCase):
    def setUp(self):
        self.q = ConkyQuery()

    def calc(self, etat):
        return calculer_affichage(etat, MAINTENANT, self.q)

    def test_5h_vert_jaune_rouge(self):
        self.assertEqual(self.calc(etat_base(usage_5h=59)).barre_5h.couleur, hex_vers_rgb("a3be8c"))
        self.assertEqual(self.calc(etat_base(usage_5h=60)).barre_5h.couleur, hex_vers_rgb("ebcb8b"))
        self.assertEqual(self.calc(etat_base(usage_5h=85)).barre_5h.couleur, hex_vers_rgb("bf616a"))

    def test_7j_rythme_tenu(self):
        b = self.calc(etat_base(usage_7d=50)).barre_7j
        self.assertEqual(b.couleur, hex_vers_rgb("5e81ac"))
        self.assertAlmostEqual(b.trait, 50.0, places=1)

    def test_7j_trop_rapide(self):
        self.assertEqual(self.calc(etat_base(usage_7d=56)).barre_7j.couleur, hex_vers_rgb("d35400"))

    def test_7j_dans_la_tolerance(self):
        self.assertEqual(self.calc(etat_base(usage_7d=55)).barre_7j.couleur, hex_vers_rgb("5e81ac"))

    def test_texte_pourcentage(self):
        b = self.calc(etat_base(usage_5h=38.4)).barre_5h
        self.assertEqual(b.texte, "38 %")
        self.assertFalse(b.texte_grise)

    def test_borne_remplissage(self):
        b = self.calc(etat_base(usage_5h=104)).barre_5h
        self.assertEqual(b.remplissage, 100)
        self.assertEqual(b.texte, "104 %")

    def verifier_indisponible(self, a):
        self.assertEqual(a.statut, "indisponible")
        for b in (a.barre_5h, a.barre_7j):
            self.assertEqual(b.texte, "–")
            self.assertEqual(b.couleur, GRIS)
            self.assertEqual(b.remplissage, 0)
            self.assertTrue(b.texte_grise)
            self.assertIsNone(b.trait)

    def test_indisponible_none(self):
        self.verifier_indisponible(self.calc(None))

    def test_indisponible_champ_manquant(self):
        etat = etat_base()
        del etat["usage_7d"]
        self.verifier_indisponible(self.calc(etat))

    def test_indisponible_non_numerique(self):
        self.verifier_indisponible(self.calc(etat_base(usage_5h="abc")))

    def test_perime_16_min(self):
        a = self.calc(etat_base(timestamp=horodatage(-timedelta(minutes=16))))
        self.assertEqual(a.statut, "perime")
        for b in (a.barre_5h, a.barre_7j):
            self.assertEqual(b.couleur, GRIS)
            self.assertTrue(b.texte_grise)
            self.assertIsNone(b.trait)
        self.assertEqual(a.barre_5h.texte, "38 %")

    def test_frais_14_min(self):
        self.assertEqual(self.calc(etat_base(timestamp=horodatage(-timedelta(minutes=14)))).statut, "normal")

    def test_timestamp_illisible_perime(self):
        self.assertEqual(self.calc(etat_base(timestamp="n'importe quoi")).statut, "perime")

    def test_timestamp_absent_perime(self):
        etat = etat_base()
        del etat["timestamp"]
        self.assertEqual(self.calc(etat).statut, "perime")

    def test_timestamp_aberrant_perime(self):
        self.assertEqual(self.calc(etat_base(timestamp="0001-01-01T00:00:00")).statut, "perime")

    def test_indisponible_nan(self):
        self.verifier_indisponible(self.calc(etat_base(usage_5h=float("nan"))))

    def test_indisponible_infini(self):
        self.verifier_indisponible(self.calc(etat_base(usage_7d=float("inf"))))

    def test_reset_7j_sans_fuseau(self):
        reset = (MAINTENANT + timedelta(hours=84)).replace(tzinfo=None).isoformat()
        self.assertAlmostEqual(self.calc(etat_base(reset_7d=reset)).barre_7j.trait, 50.0, places=1)

    def test_dossier_monitor_apres_le_depot(self):
        """Le dossier de claude-monitor ne doit pas passer devant le dépôt dans le chemin d'import
        (un fichier etat.py ou dessin.py posé là-bas masquerait le nôtre). Processus séparé :
        les autres modules de test modifient sys.path."""
        import subprocess
        import sys
        from pathlib import Path
        racine = str(Path(__file__).resolve().parent.parent)
        code = ("import sys; sys.path.insert(0, %r); import etat; "
                "print(sys.path.index(str(etat.DOSSIER_MONITOR)) > sys.path.index(%r))") % (racine, racine)
        sortie = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True)
        self.assertEqual(sortie.stdout.strip(), "True")

    def test_timestamp_futur_frais(self):
        self.assertEqual(self.calc(etat_base(timestamp=horodatage(timedelta(minutes=10)))).statut, "normal")

    def test_reinit_5h_depassee(self):
        a = self.calc(etat_base(reset_5h=(MAINTENANT - timedelta(minutes=1)).isoformat()))
        self.assertEqual(a.statut, "normal")
        self.assertEqual(a.barre_5h.texte, "–")
        self.assertEqual(a.barre_5h.couleur, GRIS)
        self.assertEqual(a.barre_5h.remplissage, 0)
        self.assertEqual(a.barre_7j.couleur, hex_vers_rgb("5e81ac"))

    def test_reinit_7j_depassee(self):
        a = self.calc(etat_base(reset_7d=(MAINTENANT - timedelta(minutes=1)).isoformat()))
        self.assertEqual(a.barre_7j.texte, "–")
        self.assertIsNone(a.barre_7j.trait)
        self.assertEqual(a.barre_5h.texte, "38 %")

    def test_perime_prime_sur_reinit(self):
        a = self.calc(etat_base(timestamp=horodatage(-timedelta(minutes=20)),
                                reset_5h=(MAINTENANT - timedelta(minutes=1)).isoformat()))
        self.assertEqual(a.statut, "perime")
        self.assertEqual(a.barre_5h.texte, "38 %")


if __name__ == "__main__":
    unittest.main()
