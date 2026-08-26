"""Journal des actions.

Chaque geste posé par l'application est inscrit : quel site, quel geste,
à quel moment, avec quel résultat. Deux fichiers par jour :
  journal-AAAA-MM-JJ.jsonl  format machine (une action par ligne)
  journal-AAAA-MM-JJ.txt    format lisible à l'œil nu
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

from .config import dossier_donnees


class Journal:
    def __init__(self, retention_jours: int = 90):
        self.dossier = dossier_donnees() / "journal"
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.retention_jours = retention_jours
        self._verrou = threading.Lock()
        self.purger()

    def _fichiers_du_jour(self) -> tuple[Path, Path]:
        jour = datetime.now().strftime("%Y-%m-%d")
        return (
            self.dossier / f"journal-{jour}.jsonl",
            self.dossier / f"journal-{jour}.txt",
        )

    def inscrire(self, categorie: str, message: str, **details) -> dict:
        """Inscrit une ligne au journal et la renvoie."""
        entree = {
            "horodatage": datetime.now().isoformat(timespec="seconds"),
            "categorie": categorie,
            "message": message,
            **details,
        }
        machine, lisible = self._fichiers_du_jour()
        ligne_lisible = (
            f"[{entree['horodatage']}] {categorie.upper():<12} {message}"
            + (f"  |  {json.dumps(details, ensure_ascii=False)}" if details else "")
        )
        with self._verrou:
            with machine.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entree, ensure_ascii=False) + "\n")
            with lisible.open("a", encoding="utf-8") as f:
                f.write(ligne_lisible + "\n")
        return entree

    def purger(self) -> int:
        """Supprime les journaux plus vieux que la durée de conservation."""
        if not self.retention_jours:
            return 0
        limite = datetime.now() - timedelta(days=self.retention_jours)
        supprimes = 0
        for fichier in self.dossier.glob("journal-*"):
            try:
                jour = datetime.strptime(fichier.stem.replace("journal-", ""), "%Y-%m-%d")
            except ValueError:
                continue
            if jour < limite:
                fichier.unlink(missing_ok=True)
                supprimes += 1
        return supprimes

    def dernieres_lignes(self, nombre: int = 50) -> list[str]:
        _, lisible = self._fichiers_du_jour()
        if not lisible.exists():
            return []
        return lisible.read_text(encoding="utf-8").splitlines()[-nombre:]
