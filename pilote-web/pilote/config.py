"""Configuration de l'application.

Tout est rangé dans %APPDATA%\\PiloteWeb :
  config.json       les réglages (modifiables dans un simple bloc-notes)
  profil_navigateur/ le profil Chrome dédié (garde les sessions ouvertes)
  journal/          le journal des actions
  profils/          les profils de sites (sélecteurs, parcours de connexion)
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

APPLICATION = "PiloteWeb"


def dossier_donnees() -> Path:
    """Dossier de travail de l'application (créé au besoin)."""
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    racine = Path(base) if base else Path.home() / ".config"
    dossier = racine / APPLICATION
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


CONFIG_DEFAUT: dict = {
    "modele": "claude-opus-5",
    # Effort de raisonnement : low | medium | high | xhigh | max.
    # "medium" suffit pour la navigation courante et coûte nettement moins cher.
    "effort": "medium",
    "max_tokens": 8000,
    # "confirmation" = demande avant chaque écriture ; "autonome" = agit seul.
    "mode": "confirmation",
    "navigateur": {
        # "profil_dedie"   : Pilote Web ouvre son propre Chrome et garde les sessions.
        # "session_ouverte": Pilote Web se branche sur le Chrome déjà ouvert par vous
        #                    (lancez-le avec demarrer_chrome_partage.bat).
        "mode": "profil_dedie",
        "url_debogage": "http://127.0.0.1:9222",
        # Vide = le Chromium installé par installer.bat. Vous pouvez pointer ici
        # votre Chrome ou Edge déjà installé pour éviter un téléchargement.
        "chemin_executable": "",
        "fenetre_visible": True,
        "largeur": 1400,
        "hauteur": 900,
        "delai_chargement_ms": 20000,
        # Longueur maximale du texte de page envoyé à Claude : plafonne le coût.
        "texte_page_max": 3000,
        "elements_max": 120,
    },
    "reessais": {
        "nombre": 3,
        "delais_secondes": [2, 4, 8],
    },
    "journal": {
        "retention_jours": 90,
    },
    "voix": {
        "activee": True,
        "modele_vosk": "",          # chemin du modèle français ; vide = dictée désactivée
        "peripherique_micro": None,  # None = micro par défaut de Windows
        "vitesse": 175,
        "voix_tts": "",             # vide = voix française par défaut de Windows
    },
    "courriel_2fa": {
        "actif": False,
        "serveur_imap": "imap.gmail.com",
        "port": 993,
        "adresse": "",
        "dossier": "INBOX",
        "expediteurs_attendus": [],
        "motif_code": r"\b(\d{6})\b",
        "fenetre_minutes": 10,
        "attente_max_secondes": 120,
    },
    "limites": {
        "cout_max_par_tache_usd": 0.75,
        "etapes_max": 40,
    },
    "profil_par_defaut": "",
}


def _fusion(defaut: dict, charge: dict) -> dict:
    """Complète la config chargée avec les valeurs par défaut manquantes."""
    resultat = deepcopy(defaut)
    for cle, valeur in (charge or {}).items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = _fusion(resultat[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


class Config:
    """Réglages de l'application, lus et écrits dans config.json."""

    def __init__(self, chemin: Path | None = None):
        self.chemin = chemin or (dossier_donnees() / "config.json")
        premiere_fois = not self.chemin.exists()
        self.valeurs = self._charger()
        if premiere_fois:
            # On écrit le fichier dès le premier démarrage : l'utilisateur peut
            # ainsi le retrouver et l'ouvrir dans le Bloc-notes.
            self.enregistrer()

    def _charger(self) -> dict:
        if self.chemin.exists():
            try:
                charge = json.loads(self.chemin.read_text(encoding="utf-8"))
            except json.JSONDecodeError as erreur:
                raise SystemExit(
                    f"Le fichier de configuration {self.chemin} est illisible : {erreur}.\n"
                    "Corrigez-le ou supprimez-le pour repartir des réglages par défaut."
                )
            valeurs = _fusion(CONFIG_DEFAUT, charge)
        else:
            valeurs = deepcopy(CONFIG_DEFAUT)
        return valeurs

    def enregistrer(self) -> None:
        self.chemin.write_text(
            json.dumps(self.valeurs, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- accès pratiques ---------------------------------------------------
    def __getitem__(self, cle: str):
        return self.valeurs[cle]

    def get(self, cle: str, defaut=None):
        return self.valeurs.get(cle, defaut)

    @property
    def mode(self) -> str:
        return self.valeurs.get("mode", "confirmation")

    @mode.setter
    def mode(self, valeur: str) -> None:
        if valeur not in ("autonome", "confirmation"):
            raise ValueError("Le mode doit être 'autonome' ou 'confirmation'.")
        self.valeurs["mode"] = valeur
        self.enregistrer()

    @property
    def dossier_profil_navigateur(self) -> Path:
        dossier = dossier_donnees() / "profil_navigateur"
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier

    @property
    def dossier_profils_sites(self) -> Path:
        dossier = dossier_donnees() / "profils"
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier


def charger_profil_site(nom: str) -> dict:
    """Charge un profil de site (%APPDATA%\\PiloteWeb\\profils\\<nom>.json).

    Les profils livrés avec l'application servent de secours.
    """
    if not nom:
        return {}
    candidats = [
        dossier_donnees() / "profils" / f"{nom}.json",
        Path(__file__).parent / "profils" / f"{nom}.json",
    ]
    for chemin in candidats:
        if chemin.exists():
            return json.loads(chemin.read_text(encoding="utf-8"))
    return {}


def lister_profils_sites() -> list[str]:
    noms = set()
    for dossier in (dossier_donnees() / "profils", Path(__file__).parent / "profils"):
        if dossier.exists():
            noms.update(p.stem for p in dossier.glob("*.json"))
    return sorted(noms)
