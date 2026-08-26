"""Les outils que Claude peut utiliser, et leur exécution.

Chaque outil est décrit à Claude en français. L'ordre de la liste ne doit pas
changer d'un appel à l'autre : il fait partie du préfixe mis en cache par
l'API, ce qui réduit fortement le coût.

Nature d'un outil :
  lecture  — regarder, lire, naviguer : jamais confirmé
  saisie   — remplir un champ : rien n'est encore enregistré dans le site
  ecriture — geste qui enregistre, soumet, modifie ou supprime : confirmé en
             mode « Demande-moi avant d'agir »
"""

from __future__ import annotations

import re
from typing import Callable

from .courriel import ErreurCourriel, LecteurCodes2FA
from .navigateur import ErreurNavigateur

# Libellés qui trahissent une écriture, même si Claude a coché « ecriture: false ».
MOTS_ECRITURE = re.compile(
    r"enregistr|sauvegard|soumett|soumiss|envoyer|envoi|cr[ée]er|ajouter|supprim|"
    r"effacer|modifier|valider|confirmer|payer|facturer|archiver|publier|"
    r"save|submit|send|create|delete|remove|update|confirm|pay",
    re.IGNORECASE,
)

OUTILS = [
    {
        "name": "observer_page",
        "description": (
            "Regarde la page actuellement ouverte et renvoie la liste des éléments "
            "utilisables (chacun avec son étiquette entre crochets) ainsi que le texte "
            "visible. À faire après chaque navigation ou changement d'écran, et avant "
            "tout clic : les étiquettes changent quand la page change."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "naviguer",
        "description": "Ouvre une adresse web dans le navigateur.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Adresse complète, avec https://"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cliquer",
        "description": (
            "Clique sur un élément repéré par son étiquette (ex. c0e12). "
            "Indique dans « ecriture » si ce clic enregistre, soumet, modifie ou "
            "supprime quelque chose dans le site."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Étiquette de l'élément, ex. c0e12"},
                "description": {"type": "string", "description": "Ce sur quoi vous cliquez, en français"},
                "ecriture": {"type": "boolean", "description": "true si le clic modifie des données"},
            },
            "required": ["ref", "description", "ecriture"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ecrire",
        "description": "Saisit du texte dans un champ. Le champ est vidé au préalable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string"},
                "texte": {"type": "string"},
                "description": {"type": "string", "description": "Nom du champ, en français"},
            },
            "required": ["ref", "texte", "description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "saisir_identifiant",
        "description": (
            "Saisit un identifiant ou un mot de passe enregistré dans le coffre de "
            "Windows, sans jamais vous le révéler. Utilisez-le pour toute connexion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string"},
                "site": {"type": "string", "description": "Nom du site tel qu'enregistré, ex. crm"},
                "champ": {"type": "string", "enum": ["utilisateur", "motdepasse"]},
            },
            "required": ["ref", "site", "champ"],
            "additionalProperties": False,
        },
    },
    {
        "name": "choisir",
        "description": "Choisit une option dans une liste déroulante.",
        "input_schema": {
            "type": "object",
            "properties": {"ref": {"type": "string"}, "valeur": {"type": "string"}},
            "required": ["ref", "valeur"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cocher",
        "description": "Coche ou décoche une case.",
        "input_schema": {
            "type": "object",
            "properties": {"ref": {"type": "string"}, "coche": {"type": "boolean"}},
            "required": ["ref", "coche"],
            "additionalProperties": False,
        },
    },
    {
        "name": "appuyer_touche",
        "description": "Envoie une touche du clavier (Enter, Tab, Escape, ArrowDown…).",
        "input_schema": {
            "type": "object",
            "properties": {
                "touche": {"type": "string"},
                "ecriture": {"type": "boolean", "description": "true si cette touche valide un formulaire"},
            },
            "required": ["touche", "ecriture"],
            "additionalProperties": False,
        },
    },
    {
        "name": "defiler",
        "description": "Fait défiler la page pour voir la suite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["bas", "haut"]},
                "pixels": {"type": "integer"},
            },
            "required": ["direction"],
            "additionalProperties": False,
        },
    },
    {
        "name": "attendre",
        "description": "Attend un délai, ou l'apparition d'un texte à l'écran.",
        "input_schema": {
            "type": "object",
            "properties": {
                "secondes": {"type": "number"},
                "texte": {"type": "string", "description": "Texte dont on attend l'apparition"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "lire_texte",
        "description": (
            "Lit le texte de la page, en entier ou d'une zone précise (sélecteur CSS). "
            "Sert à extraire un rapport, une fiche, un tableau."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"selecteur": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "capture_ecran",
        "description": (
            "Prend une image de la page. À n'utiliser qu'en dernier recours, quand le "
            "texte ne suffit pas (graphique, dessin, page illisible) : une image coûte "
            "beaucoup plus cher qu'une observation textuelle."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"raison": {"type": "string"}},
            "required": ["raison"],
            "additionalProperties": False,
        },
    },
    {
        "name": "obtenir_code_2fa",
        "description": (
            "Récupère dans la boîte courriel de l'utilisateur le code "
            "d'authentification à deux facteurs qui vient d'être envoyé."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "indice": {"type": "string", "description": "Mot attendu dans le courriel, ex. le nom du CRM"},
                "expediteur": {
                    "type": "string",
                    "description": "Adresse d'expédition attendue, si le profil du site la précise",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "demander_a_utilisateur",
        "description": (
            "Pose une question à l'utilisateur et attend sa réponse. À utiliser quand "
            "une information manque, qu'un choix vous revient, ou qu'un blocage "
            "persiste après plusieurs tentatives."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
            "additionalProperties": False,
        },
    },
]

NATURES = {
    "observer_page": "lecture",
    "naviguer": "lecture",
    "lire_texte": "lecture",
    "capture_ecran": "lecture",
    "defiler": "lecture",
    "attendre": "lecture",
    "obtenir_code_2fa": "lecture",
    "demander_a_utilisateur": "lecture",
    "ecrire": "saisie",
    "saisir_identifiant": "saisie",
    "choisir": "saisie",
    "cocher": "saisie",
    "cliquer": "variable",
    "appuyer_touche": "variable",
}


class ActionRefusee(RuntimeError):
    """L'utilisateur a refusé l'action proposée."""


class Executeur:
    """Exécute les outils, en appliquant le mode de confirmation et le journal."""

    def __init__(
        self,
        navigateur,
        config,
        journal,
        demander_confirmation: Callable[[str], bool],
        demander_information: Callable[[str], str],
    ):
        self.navigateur = navigateur
        self.config = config
        self.journal = journal
        self.demander_confirmation = demander_confirmation
        self.demander_information = demander_information
        self.lecteur_2fa = LecteurCodes2FA(config, journal)

    # ------------------------------------------------------------- nature
    def nature(self, nom: str, entree: dict) -> str:
        nature = NATURES.get(nom, "lecture")
        if nature != "variable":
            return nature
        if entree.get("ecriture"):
            return "ecriture"
        libelle = f"{entree.get('description', '')} {entree.get('touche', '')}"
        if MOTS_ECRITURE.search(libelle):
            return "ecriture"
        if nom == "appuyer_touche" and entree.get("touche") == "Enter":
            return "ecriture"
        return "lecture"

    def _resume_action(self, nom: str, entree: dict) -> str:
        if nom == "cliquer":
            return f"cliquer sur « {entree.get('description', entree.get('ref'))} »"
        if nom == "ecrire":
            return f"écrire « {entree.get('texte', '')[:60]} » dans « {entree.get('description', '')} »"
        if nom == "appuyer_touche":
            return f"appuyer sur la touche {entree.get('touche')}"
        if nom == "naviguer":
            return f"ouvrir {entree.get('url')}"
        if nom == "choisir":
            return f"choisir l'option « {entree.get('valeur')} »"
        if nom == "cocher":
            return f"{'cocher' if entree.get('coche', True) else 'décocher'} une case"
        return nom.replace("_", " ")

    # ---------------------------------------------------------- exécution
    def executer(self, nom: str, entree: dict) -> tuple:
        """Renvoie (contenu du résultat, est_une_erreur)."""
        nature = self.nature(nom, entree)
        resume = self._resume_action(nom, entree)
        confirmer_saisies = bool(self.config.get("confirmer_saisies", False))

        doit_confirmer = self.config.mode == "confirmation" and (
            nature == "ecriture" or (confirmer_saisies and nature == "saisie")
        )
        if doit_confirmer:
            page = self.navigateur.page.url if self.navigateur.page else ""
            if not self.demander_confirmation(f"Je m'apprête à {resume}.\nSite : {page}"):
                self.journal.inscrire("refus", f"Action refusée par l'utilisateur : {resume}", site=page)
                return ("L'utilisateur a refusé cette action. Proposez autre chose ou demandez-lui pourquoi.", False)

        try:
            contenu = self._appeler(nom, entree)
        except (ErreurNavigateur, ErreurCourriel) as erreur:
            self.journal.inscrire("echec", f"Échec : {resume}", outil=nom, erreur=str(erreur)[:400])
            return (str(erreur), True)
        except Exception as erreur:  # filet de sécurité : l'application ne doit jamais tomber
            self.journal.inscrire("echec", f"Erreur inattendue : {resume}", outil=nom, erreur=repr(erreur)[:400])
            return (f"Erreur inattendue : {erreur}", True)

        self.journal.inscrire(
            "action" if nature != "lecture" else "consultation",
            resume,
            outil=nom,
            nature=nature,
            site=self.navigateur.page.url if self.navigateur.page else "",
        )
        return (contenu, False)

    def _appeler(self, nom: str, entree: dict):
        navigateur = self.navigateur
        if nom == "observer_page":
            return navigateur.observer_en_texte()
        if nom == "naviguer":
            navigateur.naviguer(entree["url"])
            return navigateur.observer_en_texte()
        if nom == "cliquer":
            resultat = navigateur.cliquer(entree["ref"], entree.get("description", ""))
            return resultat + "\n\n" + navigateur.observer_en_texte()
        if nom == "ecrire":
            return navigateur.ecrire(entree["ref"], entree["texte"])
        if nom == "saisir_identifiant":
            return navigateur.ecrire_identifiant(entree["ref"], entree["site"], entree["champ"])
        if nom == "choisir":
            return navigateur.choisir(entree["ref"], entree["valeur"])
        if nom == "cocher":
            return navigateur.cocher(entree["ref"], entree.get("coche", True))
        if nom == "appuyer_touche":
            resultat = navigateur.appuyer(entree["touche"])
            return resultat + "\n\n" + navigateur.observer_en_texte()
        if nom == "defiler":
            navigateur.defiler(entree.get("direction", "bas"), int(entree.get("pixels", 600)))
            return navigateur.observer_en_texte()
        if nom == "attendre":
            resultat = navigateur.attendre(float(entree.get("secondes", 2)), entree.get("texte", ""))
            return resultat + "\n\n" + navigateur.observer_en_texte()
        if nom == "lire_texte":
            return navigateur.lire_texte(entree.get("selecteur", ""))
        if nom == "capture_ecran":
            image = navigateur.capture_ecran()
            return [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image}},
                {"type": "text", "text": "Capture de la page actuelle."},
            ]
        if nom == "obtenir_code_2fa":
            if not self.config["courriel_2fa"].get("actif"):
                reponse = self.demander_information(
                    "Le connecteur courriel n'est pas activé. Dictez-moi le code reçu."
                )
                return f"Code fourni par l'utilisateur : {reponse}"
            try:
                code = self.lecteur_2fa.attendre_code(
                    entree.get("indice", ""), entree.get("expediteur", "")
                )
                return f"Code d'authentification : {code}"
            except ErreurCourriel as erreur:
                reponse = self.demander_information(f"{erreur} Dictez-moi le code.")
                if not reponse:
                    raise
                return f"Code fourni par l'utilisateur : {reponse}"
        if nom == "demander_a_utilisateur":
            return f"Réponse de l'utilisateur : {self.demander_information(entree['question'])}"
        raise ErreurNavigateur(f"Outil inconnu : {nom}")
