"""Fenêtre de l'application (français).

Tkinter est livré avec Python : aucune dépendance payante, aucun installateur
supplémentaire. Tout ce qui touche au navigateur et à Claude tourne dans un fil
d'exécution séparé, pour que la fenêtre ne fige jamais.
"""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from . import secrets_win
from .cerveau import Cerveau
from .config import Config, dossier_donnees
from .journal import Journal
from .navigateur import Navigateur
from .voix import Ecouteur, Parleur

CLE_API = "anthropic_api_key"


class Application:
    def __init__(self):
        self.config = Config()
        self.journal = Journal(self.config["journal"]["retention_jours"])
        self.parleur = Parleur(self.config, self.journal)
        self.ecouteur = Ecouteur(self.config, self.journal)

        self.taches: queue.Queue = queue.Queue()
        self.evenements: queue.Queue = queue.Queue()
        self.navigateur = None
        self.cerveau = None
        self.occupe = False

        self._preparer_cle_api()
        self._construire_fenetre()
        self._demarrer_fil_travail()

    # -------------------------------------------------------------- clé API
    def _preparer_cle_api(self) -> None:
        if os.environ.get("ANTHROPIC_API_KEY"):
            return
        try:
            cle = secrets_win.obtenir_secret(CLE_API)
        except Exception:
            cle = None
        if cle:
            os.environ["ANTHROPIC_API_KEY"] = cle

    # ------------------------------------------------------------- fenêtre
    def _construire_fenetre(self) -> None:
        self.racine = tk.Tk()
        self.racine.title("Pilote Web — assistant de navigation")
        self.racine.geometry("980x680")
        self.racine.protocol("WM_DELETE_WINDOW", self.quitter)

        barre = ttk.Frame(self.racine, padding=(10, 8))
        barre.pack(fill="x")

        self.var_mode = tk.BooleanVar(value=self.config.mode == "confirmation")
        ttk.Checkbutton(
            barre,
            text="Demande-moi avant d'agir",
            variable=self.var_mode,
            command=self._changer_mode,
        ).pack(side="left")

        self.etiquette_etat = ttk.Label(barre, text="Prêt.")
        self.etiquette_etat.pack(side="left", padx=20)

        self.etiquette_cout = ttk.Label(barre, text="Coût de la session : 0,000 $ US")
        self.etiquette_cout.pack(side="right")

        onglets = ttk.Notebook(self.racine)
        onglets.pack(fill="both", expand=True, padx=10, pady=6)
        self._onglet_conversation(onglets)
        self._onglet_journal(onglets)
        self._onglet_identifiants(onglets)
        self._onglet_reglages(onglets)

        self.racine.after(120, self._traiter_evenements)

    def _onglet_conversation(self, onglets) -> None:
        cadre = ttk.Frame(onglets, padding=8)
        onglets.add(cadre, text="Conversation")

        self.zone = scrolledtext.ScrolledText(cadre, wrap="word", height=22, font=("Segoe UI", 10))
        self.zone.pack(fill="both", expand=True)
        self.zone.configure(state="disabled")

        saisie = ttk.Frame(cadre)
        saisie.pack(fill="x", pady=(8, 0))

        self.champ = ttk.Entry(saisie, font=("Segoe UI", 11))
        self.champ.pack(side="left", fill="x", expand=True, ipady=4)
        self.champ.bind("<Return>", lambda _evenement: self._envoyer())

        ttk.Button(saisie, text="Envoyer", command=self._envoyer).pack(side="left", padx=4)
        self.bouton_micro = ttk.Button(saisie, text="🎤 Parler", command=self._parler)
        self.bouton_micro.pack(side="left", padx=4)
        ttk.Button(saisie, text="Arrêter", command=self._arreter).pack(side="left")

        self._ecrire_zone(
            "Pilote Web est prêt. Dites ou écrivez ce que vous voulez faire, "
            "par exemple : « Ouvre le CRM, connecte-toi et sors la liste des dossiers "
            "ouverts cette semaine ».\n"
        )
        if not self.ecouteur.disponible:
            self._ecrire_zone(f"(Dictée vocale hors service : {self.ecouteur.motif_indisponible})\n")
        if not self.parleur.disponible:
            self._ecrire_zone(f"(Lecture à voix haute hors service : {self.parleur.motif_indisponible})\n")

    def _onglet_journal(self, onglets) -> None:
        cadre = ttk.Frame(onglets, padding=8)
        onglets.add(cadre, text="Journal")
        self.zone_journal = scrolledtext.ScrolledText(cadre, wrap="word", height=22, font=("Consolas", 9))
        self.zone_journal.pack(fill="both", expand=True)
        boutons = ttk.Frame(cadre)
        boutons.pack(fill="x", pady=6)
        ttk.Button(boutons, text="Rafraîchir", command=self._rafraichir_journal).pack(side="left")
        ttk.Button(
            boutons, text="Ouvrir le dossier du journal",
            command=lambda: self._ouvrir_dossier(dossier_donnees() / "journal"),
        ).pack(side="left", padx=6)
        ttk.Label(
            boutons,
            text=f"Conservation : {self.config['journal']['retention_jours']} jours",
        ).pack(side="right")
        self._rafraichir_journal()

    def _onglet_identifiants(self, onglets) -> None:
        cadre = ttk.Frame(onglets, padding=12)
        onglets.add(cadre, text="Identifiants")

        ttk.Label(
            cadre,
            text=(
                "Les mots de passe sont rangés dans le coffre de Windows.\n"
                "Ils ne sont jamais envoyés à Claude : l'application les saisit "
                "directement dans la page."
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.champs_identifiants = {}
        lignes = [
            ("Nom court du site (ex. crm)", "site", False),
            ("Identifiant / courriel", "utilisateur", False),
            ("Mot de passe", "motdepasse", True),
        ]
        for index, (etiquette, cle, secret) in enumerate(lignes, start=1):
            ttk.Label(cadre, text=etiquette).grid(row=index, column=0, sticky="w", pady=3)
            champ = ttk.Entry(cadre, width=42, show="•" if secret else "")
            champ.grid(row=index, column=1, sticky="w", pady=3)
            self.champs_identifiants[cle] = champ

        ttk.Button(cadre, text="Enregistrer ce site", command=self._enregistrer_identifiants).grid(
            row=4, column=1, sticky="w", pady=(8, 18)
        )

        ttk.Separator(cadre, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            cadre,
            text=(
                "Mot de passe d'application du courriel (lecture des codes 2FA).\n"
                "Gmail et Microsoft 365 exigent un mot de passe d'application, "
                "pas votre mot de passe habituel."
            ),
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 6))
        self.champ_courriel = ttk.Entry(cadre, width=42, show="•")
        self.champ_courriel.grid(row=7, column=1, sticky="w", pady=3)
        ttk.Label(cadre, text="Mot de passe courriel").grid(row=7, column=0, sticky="w")
        ttk.Button(cadre, text="Enregistrer", command=self._enregistrer_courriel).grid(
            row=8, column=1, sticky="w", pady=8
        )

    def _onglet_reglages(self, onglets) -> None:
        cadre = ttk.Frame(onglets, padding=12)
        onglets.add(cadre, text="Réglages")
        self.champs_reglages = {}
        ligne = 0

        ttk.Label(cadre, text="Clé d'API Anthropic").grid(row=ligne, column=0, sticky="w", pady=3)
        self.champ_cle = ttk.Entry(cadre, width=52, show="•")
        self.champ_cle.grid(row=ligne, column=1, sticky="w")
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.champ_cle.insert(0, "•" * 20)
        ttk.Button(cadre, text="Enregistrer la clé", command=self._enregistrer_cle).grid(
            row=ligne, column=2, padx=6
        )
        ligne += 1

        def ajouter(etiquette, cle, valeurs=None, largeur=24):
            nonlocal ligne
            ttk.Label(cadre, text=etiquette).grid(row=ligne, column=0, sticky="w", pady=3)
            if valeurs:
                champ = ttk.Combobox(cadre, values=valeurs, width=largeur - 2, state="readonly")
            else:
                champ = ttk.Entry(cadre, width=largeur)
            champ.grid(row=ligne, column=1, sticky="w")
            self.champs_reglages[cle] = champ
            ligne += 1
            return champ

        ajouter("Modèle Claude", "modele", ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"])
        ajouter("Effort de raisonnement", "effort", ["low", "medium", "high", "xhigh", "max"])
        ajouter("Navigateur", "navigateur.mode", ["profil_dedie", "session_ouverte"])
        ajouter("Plafond de coût par tâche ($ US)", "limites.cout_max_par_tache_usd")
        ajouter("Nombre d'étapes maximum", "limites.etapes_max")
        ajouter("Réessais avant alerte", "reessais.nombre")
        ajouter("Conservation du journal (jours)", "journal.retention_jours")
        ajouter("Modèle de dictée Vosk (dossier)", "voix.modele_vosk", largeur=52)
        ajouter("Courriel 2FA actif (oui/non)", "courriel_2fa.actif")
        ajouter("Serveur IMAP", "courriel_2fa.serveur_imap", largeur=32)
        ajouter("Adresse courriel", "courriel_2fa.adresse", largeur=32)

        ttk.Button(cadre, text="Enregistrer les réglages", command=self._enregistrer_reglages).grid(
            row=ligne, column=1, sticky="w", pady=12
        )
        ttk.Label(
            cadre,
            text="Certains réglages (navigateur, modèle) prennent effet à la prochaine tâche.",
        ).grid(row=ligne + 1, column=0, columnspan=3, sticky="w")

        self._remplir_reglages()

    # ------------------------------------------------------- utilitaires UI
    def _valeur_config(self, chemin: str):
        valeur = self.config.valeurs
        for morceau in chemin.split("."):
            valeur = valeur[morceau]
        return valeur

    def _fixer_config(self, chemin: str, valeur) -> None:
        morceaux = chemin.split(".")
        cible = self.config.valeurs
        for morceau in morceaux[:-1]:
            cible = cible[morceau]
        ancienne = cible[morceaux[-1]]
        if isinstance(ancienne, bool):
            valeur = str(valeur).strip().lower() in ("oui", "true", "vrai", "1")
        elif isinstance(ancienne, int):
            valeur = int(float(valeur))
        elif isinstance(ancienne, float):
            valeur = float(str(valeur).replace(",", "."))
        cible[morceaux[-1]] = valeur

    def _remplir_reglages(self) -> None:
        for cle, champ in self.champs_reglages.items():
            valeur = self._valeur_config(cle)
            if isinstance(valeur, bool):
                valeur = "oui" if valeur else "non"
            if isinstance(champ, ttk.Combobox):
                champ.set(str(valeur))
            else:
                champ.delete(0, "end")
                champ.insert(0, str(valeur))

    def _ecrire_zone(self, texte: str) -> None:
        self.zone.configure(state="normal")
        self.zone.insert("end", texte)
        self.zone.see("end")
        self.zone.configure(state="disabled")

    def _rafraichir_journal(self) -> None:
        self.zone_journal.delete("1.0", "end")
        self.zone_journal.insert("end", "\n".join(self.journal.dernieres_lignes(400)))
        self.zone_journal.see("end")

    def _ouvrir_dossier(self, chemin) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(chemin))  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", str(chemin)])
        except Exception as erreur:
            messagebox.showerror("Pilote Web", f"Impossible d'ouvrir le dossier : {erreur}")

    # ------------------------------------------------------------- actions
    def _changer_mode(self) -> None:
        self.config.mode = "confirmation" if self.var_mode.get() else "autonome"
        libelle = (
            "Mode « Demande-moi avant d'agir » activé."
            if self.config.mode == "confirmation"
            else "Mode autonome activé : j'agirai sans demander."
        )
        self.journal.inscrire("mode", libelle)
        self._ecrire_zone(f"\n[{libelle}]\n")
        self.parleur.dire(libelle)

    def _enregistrer_identifiants(self) -> None:
        site = self.champs_identifiants["site"].get().strip()
        utilisateur = self.champs_identifiants["utilisateur"].get().strip()
        mot_de_passe = self.champs_identifiants["motdepasse"].get()
        if not (site and utilisateur and mot_de_passe):
            messagebox.showwarning("Pilote Web", "Remplissez les trois champs.")
            return
        try:
            secrets_win.enregistrer_identifiants(site, utilisateur, mot_de_passe)
        except Exception as erreur:
            messagebox.showerror("Pilote Web", str(erreur))
            return
        self.journal.inscrire("identifiants", f"Identifiants enregistrés pour « {site} »")
        self.champs_identifiants["motdepasse"].delete(0, "end")
        messagebox.showinfo("Pilote Web", f"Identifiants enregistrés pour « {site} ».")

    def _enregistrer_courriel(self) -> None:
        valeur = self.champ_courriel.get()
        if not valeur:
            return
        try:
            secrets_win.enregistrer_secret("courriel_2fa", valeur)
        except Exception as erreur:
            messagebox.showerror("Pilote Web", str(erreur))
            return
        self.champ_courriel.delete(0, "end")
        messagebox.showinfo("Pilote Web", "Mot de passe du courriel enregistré.")

    def _enregistrer_cle(self) -> None:
        cle = self.champ_cle.get().strip()
        if not cle or set(cle) == {"•"}:
            return
        try:
            secrets_win.enregistrer_secret(CLE_API, cle)
        except Exception as erreur:
            messagebox.showerror("Pilote Web", str(erreur))
            return
        os.environ["ANTHROPIC_API_KEY"] = cle
        self.champ_cle.delete(0, "end")
        self.champ_cle.insert(0, "•" * 20)
        messagebox.showinfo("Pilote Web", "Clé d'API enregistrée dans le coffre de Windows.")

    def _enregistrer_reglages(self) -> None:
        try:
            for cle, champ in self.champs_reglages.items():
                self._fixer_config(cle, champ.get())
            self.config.enregistrer()
        except Exception as erreur:
            messagebox.showerror("Pilote Web", f"Réglage invalide : {erreur}")
            return
        self.journal.inscrire("reglages", "Réglages modifiés")
        self._remplir_reglages()
        messagebox.showinfo("Pilote Web", "Réglages enregistrés.")

    def _envoyer(self) -> None:
        consigne = self.champ.get().strip()
        if not consigne:
            return
        self.champ.delete(0, "end")
        self._lancer_tache(consigne)

    def _parler(self) -> None:
        if not self.ecouteur.disponible:
            messagebox.showinfo(
                "Pilote Web",
                "La dictée n'est pas disponible : "
                f"{self.ecouteur.motif_indisponible}.\nVous pouvez écrire votre consigne.",
            )
            return
        self.bouton_micro.configure(text="🎤 J'écoute…", state="disabled")
        self.etiquette_etat.configure(text="J'écoute…")

        def ecouter():
            try:
                texte = self.ecouteur.ecouter()
            except Exception as erreur:
                self.evenements.put(("erreur", f"Micro : {erreur}"))
                texte = ""
            self.evenements.put(("dictee", texte))

        threading.Thread(target=ecouter, daemon=True).start()

    def _arreter(self) -> None:
        if self.cerveau:
            self.cerveau.interrompre = True
        self.parleur.taire()
        self.etiquette_etat.configure(text="Arrêt demandé…")

    def _lancer_tache(self, consigne: str) -> None:
        if self.occupe:
            messagebox.showinfo("Pilote Web", "Une tâche est déjà en cours. Attendez ou cliquez sur Arrêter.")
            return
        if not os.environ.get("ANTHROPIC_API_KEY"):
            messagebox.showwarning(
                "Pilote Web",
                "Aucune clé d'API Anthropic n'est enregistrée.\n"
                "Ouvrez l'onglet Réglages pour la saisir.",
            )
            return
        self.occupe = True
        heure = datetime.now().strftime("%H:%M")
        self._ecrire_zone(f"\n[{heure}] Vous : {consigne}\n")
        self.etiquette_etat.configure(text="Travail en cours…")
        self.taches.put(consigne)

    # ------------------------------------------------------ fil de travail
    def _demarrer_fil_travail(self) -> None:
        self._fil = threading.Thread(target=self._boucle_travail, daemon=True)
        self._fil.start()

    def _boucle_travail(self) -> None:
        """Tourne dans son propre fil : navigateur (Playwright) et appels à Claude."""
        while True:
            consigne = self.taches.get()
            if consigne is None:
                break
            if consigne == "__fermer__":
                # La fermeture doit se faire dans le fil qui a ouvert le navigateur.
                try:
                    if self.navigateur:
                        self.navigateur.arreter()
                finally:
                    self.navigateur = None
                    self.cerveau = None
                    self.evenements.put(("ferme", ""))
                break
            try:
                if self.navigateur is None:
                    self.evenements.put(("info", "Ouverture du navigateur…"))
                    self.navigateur = Navigateur(
                        self.config, self.journal,
                        avertir=lambda message: self.evenements.put(("alerte", message)),
                    )
                    self.navigateur.demarrer()
                if self.cerveau is None:
                    self.cerveau = Cerveau(
                        self.config, self.journal, self.navigateur,
                        demander_confirmation=self._demander_confirmation,
                        demander_information=self._demander_information,
                        signaler=lambda categorie, texte: self.evenements.put((categorie, texte)),
                    )
                reponse = self.cerveau.executer_tache(consigne)
                self.evenements.put(("reponse", reponse))
            except Exception as erreur:
                self.journal.inscrire("echec", "Tâche interrompue par une erreur", erreur=repr(erreur)[:400])
                self.evenements.put(("erreur", str(erreur)))
            finally:
                self.evenements.put(("fin", ""))

    # ------------------------------------ questions posées depuis le travail
    def _demander_confirmation(self, texte: str) -> bool:
        reponse: dict = {}
        fini = threading.Event()

        def poser():
            self.parleur.dire("Je demande votre accord avant d'agir.")
            reponse["ok"] = messagebox.askyesno("Confirmation requise", texte + "\n\nJe continue ?")
            fini.set()

        self.racine.after(0, poser)
        fini.wait()
        return bool(reponse.get("ok"))

    def _demander_information(self, question: str) -> str:
        reponse: dict = {}
        fini = threading.Event()

        def poser():
            self.parleur.dire(question)
            reponse["texte"] = simpledialog.askstring("Pilote Web", question, parent=self.racine) or ""
            fini.set()

        self.racine.after(0, poser)
        fini.wait()
        return reponse.get("texte", "")

    # ------------------------------------------------------- boucle d'écran
    def _traiter_evenements(self) -> None:
        try:
            while True:
                categorie, texte = self.evenements.get_nowait()
                if categorie == "etape":
                    self._ecrire_zone(f"   {texte}\n")
                elif categorie == "info":
                    self._ecrire_zone(f"   {texte}\n")
                elif categorie == "cout":
                    self.etiquette_cout.configure(
                        text=f"Coût de la session : {float(texte):.3f} $ US".replace(".", ",")
                    )
                elif categorie == "reponse":
                    self._ecrire_zone(f"\nPilote Web : {texte}\n")
                    self.parleur.dire(texte)
                elif categorie == "alerte":
                    self._ecrire_zone(f"\n⚠ {texte}\n")
                    self.parleur.dire(texte)
                elif categorie == "erreur":
                    self._ecrire_zone(f"\n⚠ {texte}\n")
                    self.parleur.dire("Un problème m'empêche de continuer. Regardez l'écran.")
                elif categorie == "dictee":
                    self.bouton_micro.configure(text="🎤 Parler", state="normal")
                    self.etiquette_etat.configure(text="Prêt.")
                    if texte:
                        self._lancer_tache(texte)
                    else:
                        self._ecrire_zone("   (Je n'ai rien entendu.)\n")
                elif categorie == "ferme":
                    pass
                elif categorie == "fin":
                    self.occupe = False
                    self.etiquette_etat.configure(text="Prêt.")
                    self._rafraichir_journal()
        except queue.Empty:
            pass
        self.racine.after(120, self._traiter_evenements)

    # --------------------------------------------------------------- sortie
    def quitter(self) -> None:
        if self.occupe and not messagebox.askyesno(
            "Pilote Web", "Une tâche est en cours. Quitter quand même ?"
        ):
            return
        self.journal.inscrire("application", "Fermeture")
        if self.cerveau:
            self.cerveau.interrompre = True
        self.taches.put("__fermer__")
        self._fil.join(timeout=6)
        self.racine.destroy()

    def demarrer(self) -> None:
        self.journal.inscrire("application", "Démarrage", version_config=str(self.config.chemin))
        self.racine.mainloop()


def lancer() -> None:
    Application().demarrer()
