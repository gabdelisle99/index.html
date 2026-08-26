"""Lecture du code d'authentification à deux facteurs (2FA) dans le courriel.

Le connecteur utilisé est IMAP, le protocole standard de lecture de courriel :
il fonctionne avec Gmail, Outlook/Microsoft 365, iCloud, et la plupart des
fournisseurs professionnels, sans dépendre d'une API propriétaire.

Le mot de passe du courriel n'est jamais écrit dans un fichier : il est rangé
dans le coffre de Windows, sous le nom « courriel_2fa ». Pour Gmail et
Microsoft 365, utilisez un « mot de passe d'application » et non votre mot de
passe principal.

Limite connue : certaines organisations désactivent IMAP. Dans ce cas
l'application demande le code à voix haute et vous le dictez — la tâche
continue quand même.
"""

from __future__ import annotations

import email
import imaplib
import re
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header

from .secrets_win import obtenir_secret

NOM_SECRET = "courriel_2fa"


class ErreurCourriel(RuntimeError):
    pass


def _texte_du_message(message) -> str:
    morceaux = []
    if message.is_multipart():
        for partie in message.walk():
            if partie.get_content_type() in ("text/plain", "text/html"):
                charge = partie.get_payload(decode=True) or b""
                morceaux.append(charge.decode(partie.get_content_charset() or "utf-8", "ignore"))
    else:
        charge = message.get_payload(decode=True) or b""
        morceaux.append(charge.decode(message.get_content_charset() or "utf-8", "ignore"))
    texte = "\n".join(morceaux)
    return re.sub(r"<[^>]+>", " ", texte)


def _sujet(message) -> str:
    try:
        return str(make_header(decode_header(message.get("Subject", ""))))
    except Exception:
        return message.get("Subject", "")


class LecteurCodes2FA:
    def __init__(self, config, journal):
        self.reglages = config["courriel_2fa"]
        self.journal = journal

    def _connexion(self):
        mot_de_passe = obtenir_secret(NOM_SECRET)
        if not self.reglages.get("adresse") or not mot_de_passe:
            raise ErreurCourriel(
                "Le connecteur courriel n'est pas configuré. Renseignez l'adresse dans "
                "les réglages et le mot de passe d'application dans l'onglet Identifiants."
            )
        try:
            connexion = imaplib.IMAP4_SSL(self.reglages["serveur_imap"], int(self.reglages["port"]))
            connexion.login(self.reglages["adresse"], mot_de_passe)
        except Exception as erreur:
            raise ErreurCourriel(
                f"Connexion au courriel impossible : {erreur}. "
                "Vérifiez que l'accès IMAP est autorisé et que le mot de passe "
                "d'application est le bon."
            ) from erreur
        return connexion

    def chercher_code(self, indice: str = "", expediteur: str = "") -> str | None:
        """Cherche un code récent dans les courriels reçus. None si rien trouvé."""
        fenetre = int(self.reglages.get("fenetre_minutes", 10))
        depuis = datetime.now(timezone.utc) - timedelta(minutes=fenetre)
        motif = re.compile(self.reglages.get("motif_code", r"\b(\d{6})\b"))
        expediteurs = [e.lower() for e in self.reglages.get("expediteurs_attendus", [])]
        if expediteur:
            expediteurs = [expediteur.lower()]

        connexion = self._connexion()
        try:
            connexion.select(self.reglages.get("dossier", "INBOX"))
            critere = depuis.strftime("(SINCE %d-%b-%Y)")
            statut, donnees = connexion.search(None, critere)
            if statut != "OK":
                return None
            identifiants = donnees[0].split()[-25:]  # les 25 plus récents
            for identifiant in reversed(identifiants):
                statut, brut = connexion.fetch(identifiant, "(RFC822)")
                if statut != "OK" or not brut or not brut[0]:
                    continue
                message = email.message_from_bytes(brut[0][1])
                date_message = email.utils.parsedate_to_datetime(message.get("Date"))
                if date_message and date_message.tzinfo is None:
                    date_message = date_message.replace(tzinfo=timezone.utc)
                if date_message and date_message < depuis:
                    continue
                expediteur = (message.get("From") or "").lower()
                if expediteurs and not any(e in expediteur for e in expediteurs):
                    continue
                contenu = f"{_sujet(message)}\n{_texte_du_message(message)}"
                if indice and indice.lower() not in contenu.lower():
                    continue
                trouve = motif.search(contenu)
                if trouve:
                    code = trouve.group(1) if trouve.groups() else trouve.group(0)
                    self.journal.inscrire(
                        "2fa", "Code d'authentification récupéré dans le courriel",
                        expediteur=expediteur[:120],
                    )
                    return code
            return None
        finally:
            try:
                connexion.logout()
            except Exception:
                pass

    def attendre_code(self, indice: str = "", expediteur: str = "") -> str:
        """Attend l'arrivée du code (le courriel met souvent quelques secondes)."""
        limite = time.time() + int(self.reglages.get("attente_max_secondes", 120))
        while time.time() < limite:
            code = self.chercher_code(indice, expediteur)
            if code:
                return code
            time.sleep(5)
        raise ErreurCourriel(
            "Aucun code d'authentification n'est arrivé dans le délai prévu. "
            "Vérifiez votre boîte de réception, ou dictez-moi le code."
        )
