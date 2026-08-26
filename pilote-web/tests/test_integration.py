"""Essai de bout en bout : vraie page, vrai navigateur, cerveau simulé.

Ce test remplace Claude par un « modèle » scripté, mais tout le reste est réel :
le navigateur s'ouvre, la page se charge, les champs se remplissent, le clic
enregistre. C'est la vérification qui rassure le plus avant de brancher l'API.

Il est ignoré si Playwright ou son navigateur ne sont pas installés.

Lancer :  .venv\\Scripts\\python.exe tests\\test_integration.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_temporaire = tempfile.mkdtemp(prefix="pilote-integration-")
os.environ["APPDATA"] = _temporaire
os.environ["XDG_CONFIG_HOME"] = _temporaire
os.environ.setdefault("ANTHROPIC_API_KEY", "cle-de-test")

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>CRM fictif</title></head><body>
<h1>Nouveau dossier</h1>
<label for="client">Nom du client</label><input id="client" type="text">
<label for="ville">Ville</label>
<select id="ville"><option>Montréal</option><option>Québec</option></select>
<button id="ok" onclick="document.getElementById('etat').textContent =
  'Dossier enregistré pour ' + document.getElementById('client').value +
  ' (' + document.getElementById('ville').value + ')'">Enregistrer la fiche</button>
<div id="etat">Aucun dossier</div>
</body></html>"""


def _navigateur_disponible() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    return True


def executer() -> bool:
    from pilote.cerveau import Cerveau
    from pilote.config import Config
    from pilote.journal import Journal
    from pilote.navigateur import Navigateur

    fichier = Path(_temporaire) / "crm.html"
    fichier.write_text(PAGE, encoding="utf-8")

    config = Config()
    config.valeurs["navigateur"]["fenetre_visible"] = False
    if os.environ.get("PILOTE_CHROME"):
        config.valeurs["navigateur"]["chemin_executable"] = os.environ["PILOTE_CHROME"]
    config.valeurs["mode"] = "confirmation"  # on vérifie aussi la confirmation
    journal = Journal(retention_jours=1)
    navigateur = Navigateur(config, journal, avertir=lambda message: print("ALERTE:", message))
    navigateur.demarrer()

    confirmations: list[str] = []
    etapes: list[str] = []

    def reference(observation: str, libelle: str) -> str:
        for ligne in observation.splitlines():
            if libelle.lower() in ligne.lower() and ligne.strip().startswith("["):
                return ligne.strip()[1 : ligne.strip().index("]")]
        raise AssertionError(f"élément « {libelle} » absent de l'observation")

    # « Modèle » scripté : décide du geste suivant à partir de la dernière observation.
    class ModeleScripte:
        def __init__(self):
            self.etape = 0
            self.messages = SimpleNamespace(create=self.repondre)
            self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.repondre))

        def repondre(self, **parametres):
            self.etape += 1
            dernier = parametres["messages"][-1]
            observation = ""
            if isinstance(dernier["content"], list):
                for bloc in dernier["content"]:
                    if isinstance(bloc, dict) and bloc.get("type") == "tool_result":
                        if isinstance(bloc["content"], str):
                            observation = bloc["content"]

            def reponse(blocs, stop="tool_use"):
                return SimpleNamespace(
                    content=blocs, stop_reason=stop,
                    usage=SimpleNamespace(
                        input_tokens=1000, output_tokens=200,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0,
                    ),
                )

            def outil(nom, entree):
                return SimpleNamespace(type="tool_use", id=f"t{self.etape}", name=nom, input=entree)

            def texte(valeur):
                return SimpleNamespace(type="text", text=valeur)

            if self.etape == 1:
                return reponse([outil("naviguer", {"url": fichier.as_uri()})])
            if self.etape == 2:
                return reponse([outil("ecrire", {
                    "ref": reference(observation, "Nom du client"),
                    "texte": "Boulangerie Tremblay",
                    "description": "Nom du client",
                })])
            if self.etape == 3:
                observation = navigateur.observer_en_texte()
                return reponse([outil("choisir", {
                    "ref": reference(observation, "select"), "valeur": "Québec",
                })])
            if self.etape == 4:
                observation = navigateur.observer_en_texte()
                return reponse([outil("cliquer", {
                    "ref": reference(observation, "Enregistrer la fiche"),
                    "description": "Enregistrer la fiche",
                    "ecriture": True,
                })])
            if self.etape == 5:
                return reponse([outil("lire_texte", {"selecteur": "#etat"})])
            return reponse([texte(f"Fiche créée. {observation.strip()}")], stop="end_turn")

    cerveau = Cerveau(
        config, journal, navigateur,
        demander_confirmation=lambda message: (confirmations.append(message), True)[1],
        demander_information=lambda question: "",
        signaler=lambda categorie, valeur: etapes.append(f"{categorie}:{valeur[:60]}"),
    )
    cerveau.client = ModeleScripte()
    cerveau._fallbacks_disponibles = False

    try:
        reponse = cerveau.executer_tache(
            "Crée une fiche pour la Boulangerie Tremblay, à Québec."
        )
    finally:
        navigateur.arreter()

    print("Réponse finale :", reponse)
    print("Confirmations demandées :", len(confirmations))
    print("Coût simulé : %.4f $ US" % cerveau.cout_total_usd)

    controles = [
        ("la fiche est enregistrée dans la page", "Dossier enregistré pour Boulangerie Tremblay" in reponse),
        ("la ville choisie est reprise", "Québec" in reponse),
        ("une seule confirmation, pour l'écriture", len(confirmations) == 1),
        ("la confirmation portait sur le bon geste", "Enregistrer la fiche" in confirmations[0]),
        ("le journal contient l'action", any(
            "Enregistrer la fiche" in ligne for ligne in journal.dernieres_lignes(200))),
        ("le journal ne contient aucun mot de passe", not any(
            "motdepasse" in ligne.lower() for ligne in journal.dernieres_lignes(200))),
    ]
    echecs = 0
    for libelle, resultat in controles:
        print(("  OK   " if resultat else "  ECHEC ") + libelle)
        echecs += 0 if resultat else 1
    return echecs == 0


if __name__ == "__main__":
    if not _navigateur_disponible():
        print("Playwright n'est pas installé : essai ignoré.")
        raise SystemExit(0)
    reussi = executer()
    print("\nEssai de bout en bout réussi." if reussi else "\nEssai de bout en bout en échec.")
    raise SystemExit(0 if reussi else 1)
