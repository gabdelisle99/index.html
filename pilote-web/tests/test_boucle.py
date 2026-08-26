"""Vérifie la boucle de raisonnement sans appeler l'API (client simulé).

On simule les réponses de Claude pour contrôler que l'application :
  - exécute bien les outils demandés et renvoie les résultats ;
  - respecte le plafond de coût et le plafond d'étapes ;
  - s'arrête proprement si le modèle refuse la demande ;
  - allège l'historique quand il devient trop lourd.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_temporaire = tempfile.mkdtemp(prefix="pilote-boucle-")
os.environ["APPDATA"] = _temporaire
os.environ["XDG_CONFIG_HOME"] = _temporaire
os.environ.setdefault("ANTHROPIC_API_KEY", "cle-de-test")

from pilote.cerveau import Cerveau  # noqa: E402
from pilote.config import Config  # noqa: E402
from pilote.journal import Journal  # noqa: E402


class FauxNavigateur:
    """Navigateur factice : renvoie des observations plausibles."""

    page = SimpleNamespace(url="https://crm.test/dossiers")

    def observer_en_texte(self):
        return "URL : https://crm.test/dossiers\nÉléments utilisables :\n  [c0e1] button « Nouveau dossier »"

    def naviguer(self, url):
        self.page = SimpleNamespace(url=url)
        return f"Page ouverte : {url}"

    def cliquer(self, ref, description=""):
        return f"Clic effectué sur {description or ref}."

    def lire_texte(self, selecteur=""):
        return "Dossier 1042 — ouvert le 12 août"


def _bloc_texte(texte):
    return SimpleNamespace(type="text", text=texte)


def _bloc_outil(identifiant, nom, entree):
    return SimpleNamespace(type="tool_use", id=identifiant, name=nom, input=entree)


class FauxClient:
    """Rejoue une suite de réponses préparées d'avance."""

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = []
        self.messages = SimpleNamespace(create=self._create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **parametres):
        self.appels.append(parametres)
        return self.reponses.pop(0)


def _reponse(contenu, stop_reason="tool_use", entree=1200, sortie=300):
    return SimpleNamespace(
        content=contenu,
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=entree,
            output_tokens=sortie,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )


def _cerveau(reponses, mode="autonome"):
    config = Config()
    config.valeurs["mode"] = mode
    journal = Journal(retention_jours=1)
    cerveau = Cerveau(
        config, journal, FauxNavigateur(),
        demander_confirmation=lambda texte: True,
        demander_information=lambda question: "42",
        signaler=lambda categorie, texte: None,
    )
    cerveau.client = FauxClient(reponses)
    cerveau._fallbacks_disponibles = False
    return cerveau


def test_tache_complete_en_deux_etapes():
    cerveau = _cerveau([
        _reponse([
            _bloc_texte("J'ouvre le CRM."),
            _bloc_outil("t1", "naviguer", {"url": "https://crm.test"}),
        ]),
        _reponse([_bloc_texte("Le dossier 1042 est ouvert depuis le 12 août.")], stop_reason="end_turn"),
    ])
    reponse = cerveau.executer_tache("Ouvre le CRM et lis le dossier 1042.")
    assert "1042" in reponse
    # L'historique contient bien la consigne, la réponse, le résultat d'outil, la conclusion.
    assert cerveau.messages[0]["role"] == "user"
    assert any(
        isinstance(m["content"], list)
        and any(getattr(b, "type", b.get("type") if isinstance(b, dict) else "") == "tool_result"
                for b in m["content"])
        for m in cerveau.messages if m["role"] == "user"
    )
    assert cerveau.cout_total_usd > 0


def test_requete_avec_consigne_et_outils():
    cerveau = _cerveau([_reponse([_bloc_texte("Fait.")], stop_reason="end_turn")])
    cerveau.executer_tache("Bonjour")
    parametres = cerveau.client.appels[0]
    assert parametres["model"] == cerveau.config["modele"]
    assert parametres["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert parametres["output_config"]["effort"] == cerveau.config["effort"]
    assert parametres["thinking"] == {"type": "adaptive"}
    assert any(outil["name"] == "observer_page" for outil in parametres["tools"])


def test_refus_du_modele_arrete_proprement():
    cerveau = _cerveau([_reponse([_bloc_texte("")], stop_reason="refusal")])
    reponse = cerveau.executer_tache("Demande problématique")
    assert "ne peux pas poursuivre" in reponse


def test_plafond_de_cout():
    cerveau = _cerveau([
        _reponse([_bloc_outil("t1", "observer_page", {})], entree=2_000_000, sortie=100_000)
        for _ in range(3)
    ])
    cerveau.config.valeurs["limites"]["cout_max_par_tache_usd"] = 0.05
    reponse = cerveau.executer_tache("Tâche coûteuse")
    assert "plafond" in reponse.lower()


def test_plafond_d_etapes():
    cerveau = _cerveau([_reponse([_bloc_outil(f"t{i}", "observer_page", {})]) for i in range(6)])
    cerveau.config.valeurs["limites"]["etapes_max"] = 5
    reponse = cerveau.executer_tache("Tâche sans fin")
    assert "limite de 5 étapes" in reponse


def test_elagage_de_l_historique():
    cerveau = _cerveau([])
    cerveau.messages = [
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": "x" * 4000}
        ]}
        for i in range(30)
    ]
    cerveau._elaguer()
    abreges = sum(
        1 for m in cerveau.messages
        for b in m["content"] if "abrégée" in b["content"]
    )
    assert abreges == 26, f"{abreges} messages abrégés au lieu de 26"


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
