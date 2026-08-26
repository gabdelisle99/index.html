"""Voix : écouter la consigne, répondre à voix haute.

Tout est gratuit et hors ligne :
  - la parole vers le texte passe par Vosk (modèle français à télécharger une fois) ;
  - le texte vers la parole passe par la voix française déjà installée dans Windows.

Si le micro, Vosk ou la voix manquent, l'application continue de fonctionner :
on tape la consigne et on lit la réponse à l'écran. Rien ne bloque.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path


class Parleur:
    """Synthèse vocale (voix Windows). Un seul fil d'exécution, en file d'attente."""

    def __init__(self, config, journal=None):
        self.config = config
        self.journal = journal
        self.disponible = False
        self.motif_indisponible = ""
        self._file: queue.Queue = queue.Queue()
        self._moteur = None
        try:
            import pyttsx3  # noqa: F401

            self.disponible = True
        except Exception as erreur:  # pragma: no cover
            self.motif_indisponible = f"synthèse vocale indisponible ({erreur})"
            return
        self._fil = threading.Thread(target=self._boucle, daemon=True)
        self._fil.start()

    def _preparer_moteur(self):
        import pyttsx3

        moteur = pyttsx3.init()
        reglages = self.config["voix"]
        moteur.setProperty("rate", int(reglages.get("vitesse", 175)))
        voulue = (reglages.get("voix_tts") or "").lower()
        for voix in moteur.getProperty("voices"):
            identite = f"{voix.id} {getattr(voix, 'name', '')}".lower()
            if voulue and voulue in identite:
                moteur.setProperty("voice", voix.id)
                break
            if not voulue and ("french" in identite or "fr-" in identite or "français" in identite):
                moteur.setProperty("voice", voix.id)
                break
        return moteur

    def _boucle(self):
        while True:
            texte = self._file.get()
            if texte is None:
                return
            try:
                if self._moteur is None:
                    self._moteur = self._preparer_moteur()
                self._moteur.say(texte)
                self._moteur.runAndWait()
            except Exception:
                self._moteur = None  # on retentera avec un moteur neuf

    def dire(self, texte: str) -> None:
        if not texte:
            return
        if self.config["voix"].get("activee", True) and self.disponible:
            self._file.put(texte)

    def taire(self) -> None:
        try:
            if self._moteur:
                self._moteur.stop()
        except Exception:
            pass


class Ecouteur:
    """Reconnaissance vocale hors ligne (Vosk)."""

    def __init__(self, config, journal=None):
        self.config = config
        self.journal = journal
        self.disponible = False
        self.motif_indisponible = ""
        self._modele = None
        chemin = (config["voix"].get("modele_vosk") or "").strip()
        if not chemin:
            self.motif_indisponible = (
                "aucun modèle de dictée installé (voir docs/INSTALLATION.md, étape 6)"
            )
            return
        if not Path(chemin).exists():
            self.motif_indisponible = f"modèle de dictée introuvable : {chemin}"
            return
        try:
            import sounddevice  # noqa: F401
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)
            self._modele = Model(chemin)
            self.disponible = True
        except Exception as erreur:  # pragma: no cover
            self.motif_indisponible = f"dictée indisponible ({erreur})"

    def ecouter(self, duree_max: float = 20.0, silence_final: float = 1.2) -> str:
        """Écoute le micro et renvoie ce qui a été dit (chaîne vide si rien)."""
        if not self.disponible:
            raise RuntimeError(self.motif_indisponible)

        import sounddevice as sd
        from vosk import KaldiRecognizer

        frequence = 16000
        reconnaisseur = KaldiRecognizer(self._modele, frequence)
        blocs: queue.Queue = queue.Queue()

        def rappel(donnees, images, horodatage, statut):  # noqa: ARG001
            blocs.put(bytes(donnees))

        morceaux: list[str] = []
        peripherique = self.config["voix"].get("peripherique_micro")
        with sd.RawInputStream(
            samplerate=frequence, blocksize=4000, dtype="int16",
            channels=1, callback=rappel, device=peripherique,
        ):
            import time

            debut = time.time()
            dernier_son = debut
            while time.time() - debut < duree_max:
                try:
                    donnees = blocs.get(timeout=0.5)
                except queue.Empty:
                    continue
                if reconnaisseur.AcceptWaveform(donnees):
                    partiel = json.loads(reconnaisseur.Result()).get("text", "")
                    if partiel:
                        morceaux.append(partiel)
                        dernier_son = time.time()
                else:
                    if json.loads(reconnaisseur.PartialResult()).get("partial"):
                        dernier_son = time.time()
                if morceaux and time.time() - dernier_son > silence_final:
                    break
        reste = json.loads(reconnaisseur.FinalResult()).get("text", "")
        if reste:
            morceaux.append(reste)
        return " ".join(m for m in morceaux if m).strip()
