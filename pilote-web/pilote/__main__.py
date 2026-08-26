"""Point d'entrée : python -m pilote (c'est ce que fait lancer.bat)."""

from __future__ import annotations

import sys


def _erreur_visible(titre: str, message: str) -> None:
    """Affiche l'erreur dans une fenêtre : l'utilisateur ne lit pas la console."""
    print(f"{titre}\n\n{message}", file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror(titre, message)
        racine.destroy()
    except Exception:
        pass


def verifier_installation() -> str | None:
    """Renvoie un message d'aide si quelque chose manque, sinon None."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return (
            "La bibliothèque « anthropic » n'est pas installée.\n\n"
            "Fermez cette fenêtre et double-cliquez sur installer.bat."
        )
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return (
            "La bibliothèque « playwright » n'est pas installée.\n\n"
            "Fermez cette fenêtre et double-cliquez sur installer.bat."
        )
    return None


def main() -> int:
    probleme = verifier_installation()
    if probleme:
        _erreur_visible("Pilote Web — installation incomplète", probleme)
        return 1
    from .interface import lancer

    try:
        lancer()
    except Exception as erreur:  # pragma: no cover - filet ultime
        _erreur_visible("Pilote Web — erreur inattendue", str(erreur))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
