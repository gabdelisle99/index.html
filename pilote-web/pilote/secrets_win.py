"""Identifiants enregistrés, rangés dans le coffre de Windows.

Aucun mot de passe n'est écrit dans un fichier de l'application : tout passe
par le Gestionnaire d'identification de Windows (Credential Manager), via la
bibliothèque `keyring`. Les mots de passe ne sont jamais envoyés à Claude —
l'outil de saisie les insère directement dans la page.
"""

from __future__ import annotations

SERVICE = "PiloteWeb"


class CoffreIndisponible(RuntimeError):
    pass


def _keyring():
    try:
        import keyring  # import tardif : l'application démarre même sans keyring
    except ImportError as erreur:  # pragma: no cover - dépend de l'installation
        raise CoffreIndisponible(
            "La bibliothèque keyring n'est pas installée. "
            "Relancez installer.bat pour compléter l'installation."
        ) from erreur
    return keyring


def enregistrer_identifiants(site: str, utilisateur: str, mot_de_passe: str) -> None:
    """Enregistre le couple identifiant / mot de passe pour un site."""
    keyring = _keyring()
    keyring.set_password(SERVICE, f"{site}:utilisateur", utilisateur)
    keyring.set_password(SERVICE, f"{site}:motdepasse", mot_de_passe)


def obtenir_identifiants(site: str) -> tuple[str, str] | None:
    """Renvoie (utilisateur, mot de passe) ou None si rien n'est enregistré."""
    keyring = _keyring()
    utilisateur = keyring.get_password(SERVICE, f"{site}:utilisateur")
    mot_de_passe = keyring.get_password(SERVICE, f"{site}:motdepasse")
    if utilisateur and mot_de_passe:
        return utilisateur, mot_de_passe
    return None


def supprimer_identifiants(site: str) -> None:
    keyring = _keyring()
    for suffixe in ("utilisateur", "motdepasse"):
        try:
            keyring.delete_password(SERVICE, f"{site}:{suffixe}")
        except Exception:
            pass


def enregistrer_secret(nom: str, valeur: str) -> None:
    """Secret libre (par exemple le mot de passe d'application du courriel)."""
    _keyring().set_password(SERVICE, nom, valeur)


def obtenir_secret(nom: str) -> str | None:
    return _keyring().get_password(SERVICE, nom)
