import unittest
from datetime import timedelta

from etat import ConkyQuery, calculer_affichage
from infobulle import texte_infobulle
from tests.test_etat import MAINTENANT, etat_base, horodatage


class TestInfobulle(unittest.TestCase):
    def setUp(self):
        self.q = ConkyQuery()

    def texte(self, etat):
        return texte_infobulle(etat, calculer_affichage(etat, MAINTENANT, self.q), MAINTENANT, self.q)

    def lignes(self, etat):
        return self.texte(etat).split("\n")

    def test_premiere_ligne_pro(self):
        self.assertEqual(self.lignes(etat_base())[0], "Claude Code — forfait Pro")

    def test_forfait_inconnu(self):
        self.assertEqual(self.lignes(etat_base(plan_type="team"))[0], "Claude Code — forfait Team")

    def test_ligne_5h(self):
        etat = etat_base()
        fr5 = self.q.format_reset_time(etat["reset_5h"])
        tr5 = self.q.format_time_remaining(etat["reset_5h"])
        self.assertEqual(self.lignes(etat)[1], f"5 h : 38 % · réinitialisation {fr5} (dans {tr5})")

    def test_rythme_tenu(self):
        ligne = self.lignes(etat_base(usage_7d=50))[2]
        self.assertIn("50 % du temps écoulé", ligne)
        self.assertTrue(ligne.endswith("rythme tenu"))

    def test_rythme_trop_rapide(self):
        ligne = self.lignes(etat_base(usage_7d=56))[2]
        self.assertTrue(ligne.startswith("7 j : 56 % · 50 % du temps écoulé"))
        self.assertTrue(ligne.endswith("rythme trop rapide"))

    def test_ligne_reinit_7j(self):
        etat = etat_base()
        fr7 = self.q.format_reset_time(etat["reset_7d"])
        tr7 = self.q.format_time_remaining(etat["reset_7d"])
        self.assertEqual(self.lignes(etat)[3], f"réinitialisation {fr7} (dans {tr7})")

    def test_derniere_ligne(self):
        self.assertEqual(self.lignes(etat_base(last_update="12:41:36"))[-1], "mis à jour à 12:41")

    def test_sans_last_update_heure_du_timestamp(self):
        etat = etat_base()
        del etat["last_update"]
        attendu = (MAINTENANT - timedelta(minutes=1)).strftime("%H:%M")
        self.assertEqual(self.lignes(etat)[-1], f"mis à jour à {attendu}")

    def test_sans_aucune_heure(self):
        etat = etat_base()
        del etat["last_update"], etat["timestamp"]
        self.assertEqual(self.lignes(etat)[0], "Données périmées (dernière mise à jour à inconnue)")

    def test_reset_7j_sans_fuseau_garde_le_rythme(self):
        reset = (MAINTENANT + timedelta(hours=84)).replace(tzinfo=None).isoformat()
        self.assertIn("du temps écoulé", self.lignes(etat_base(reset_7d=reset))[2])

    def test_reinit_5h_en_cours(self):
        etat = etat_base(reset_5h=(MAINTENANT - timedelta(minutes=1)).isoformat())
        self.assertEqual(self.lignes(etat)[1], "5 h : réinitialisation en cours…")

    def test_reinit_7j_en_cours(self):
        lignes = self.lignes(etat_base(reset_7d=(MAINTENANT - timedelta(minutes=1)).isoformat()))
        self.assertEqual(lignes[2], "7 j : réinitialisation en cours…")
        self.assertFalse(any(l.startswith("réinitialisation") for l in lignes))

    def test_perime_en_tete(self):
        lignes = self.lignes(etat_base(timestamp=horodatage(-timedelta(minutes=20)), last_update="11:40:00"))
        self.assertEqual(lignes[0], "Données périmées (dernière mise à jour à 11:40)")
        self.assertEqual(lignes[1], "Claude Code — forfait Pro")

    def test_indisponible(self):
        self.assertEqual(self.texte(None), "Données indisponibles")


if __name__ == "__main__":
    unittest.main()
