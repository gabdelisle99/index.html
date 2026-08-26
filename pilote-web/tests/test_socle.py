"""Vérifications rapides du socle (sans navigateur ni API).

Lancer : .venv\\Scripts\\python.exe -m pytest tests  (ou python tests/test_socle.py)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Isole les fichiers de l'application dans un dossier temporaire.
_temporaire = tempfile.mkdtemp(prefix="pilote-test-")
os.environ["APPDATA"] = _temporaire
os.environ["XDG_CONFIG_HOME"] = _temporaire

from pilote.cerveau import PRIX, fiche_des_sites_connus  # noqa: E402
from pilote.config import Config, charger_profil_site  # noqa: E402
from pilote.journal import Journal  # noqa: E402
from pilote.outils import NATURES, OUTILS, Executeur  # noqa: E402


def test_config_valeurs_par_defaut():
    config = Config()
    assert config.mode == "confirmation"
    assert config["modele"] in PRIX
    config.mode = "autonome"
    assert Config(config.chemin).mode == "autonome"
    config.mode = "confirmation"


def test_journal_ecrit_et_relit():
    journal = Journal(retention_jours=1)
    journal.inscrire("action", "clic sur Enregistrer", site="https://exemple.test")
    lignes = journal.dernieres_lignes(5)
    assert any("clic sur Enregistrer" in ligne for ligne in lignes)


def test_outils_bien_formes():
    noms = [outil["name"] for outil in OUTILS]
    assert len(noms) == len(set(noms)), "deux outils portent le même nom"
    for outil in OUTILS:
        assert outil["name"] in NATURES, f"nature manquante pour {outil['name']}"
        schema = outil["input_schema"]
        assert schema["type"] == "object"
        for requis in schema.get("required", []):
            assert requis in schema["properties"], f"{outil['name']} : {requis} non décrit"


def _executeur():
    config = Config()
    journal = Journal(retention_jours=1)

    class FauxNavigateur:
        page = None

    return Executeur(
        FauxNavigateur(), config, journal,
        demander_confirmation=lambda texte: False,
        demander_information=lambda question: "",
    )


def test_nature_des_actions():
    executeur = _executeur()
    assert executeur.nature("observer_page", {}) == "lecture"
    assert executeur.nature("ecrire", {"ref": "c0e1", "texte": "x"}) == "saisie"
    # Claude déclare une écriture
    assert executeur.nature("cliquer", {"ref": "c0e1", "description": "Suivant", "ecriture": True}) == "ecriture"
    # Claude l'oublie, mais le libellé la trahit : on confirme quand même
    assert executeur.nature("cliquer", {"ref": "c0e1", "description": "Enregistrer la fiche", "ecriture": False}) == "ecriture"
    assert executeur.nature("cliquer", {"ref": "c0e1", "description": "Voir le dossier", "ecriture": False}) == "lecture"
    assert executeur.nature("appuyer_touche", {"touche": "Enter", "ecriture": False}) == "ecriture"
    assert executeur.nature("appuyer_touche", {"touche": "Tab", "ecriture": False}) == "lecture"


def test_refus_utilisateur_ne_bloque_pas_la_tache():
    executeur = _executeur()
    executeur.config.mode = "confirmation"
    contenu, erreur = executeur.executer(
        "cliquer", {"ref": "c0e1", "description": "Supprimer le dossier", "ecriture": True}
    )
    assert not erreur
    assert "refus" in contenu.lower()


def test_profil_exemple_lisible():
    profil = charger_profil_site("exemple_crm")
    assert profil["reperes"]["bouton_connexion"]
    # L'exemple ne doit pas polluer la consigne système.
    assert "exemple_crm" not in fiche_des_sites_connus()


if __name__ == "__main__":
    echecs = 0
    for nom, fonction in sorted(globals().items()):
        if nom.startswith("test_") and callable(fonction):
            try:
                fonction()
                print(f"  OK   {nom}")
            except AssertionError as erreur:
                echecs += 1
                print(f"  ECHEC {nom} : {erreur}")
    print("\nTous les tests passent." if not echecs else f"\n{echecs} test(s) en échec.")
    raise SystemExit(1 if echecs else 0)
