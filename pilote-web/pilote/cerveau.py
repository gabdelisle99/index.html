"""Le cerveau : la boucle de raisonnement avec Claude.

Déroulement d'une tâche :
  1. votre consigne (dictée ou tapée) part vers Claude, avec la liste des outils ;
  2. Claude répond par un geste à poser (« clique sur le bouton Connexion ») ;
  3. l'application pose le geste dans le navigateur et renvoie le résultat ;
  4. on recommence jusqu'à ce que Claude annonce que la tâche est terminée.

Trois garde-fous : un plafond de coût par tâche, un plafond d'étapes, et le
mode « Demande-moi avant d'agir » appliqué dans outils.py.
"""

from __future__ import annotations

import json
from typing import Callable

from .config import charger_profil_site, lister_profils_sites
from .outils import OUTILS, Executeur

# Tarifs de l'API en dollars US par million de jetons (entrée, sortie).
# Source : tarification publique Anthropic. À ajuster si les prix changent.
PRIX = {
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

CONSIGNE_SYSTEME = """Tu es « Pilote Web », l'assistant d'un professionnel québécois qui te
parle en français. Tu utilises des sites web à sa place, dans un vrai navigateur, comme le
ferait une personne : tu regardes la page, tu cliques, tu tapes, tu lis.

Règles de travail :
- Travaille par petits gestes vérifiés. Après chaque navigation, chaque clic qui change
  d'écran et chaque envoi de formulaire, observe la page avant de continuer.
- Ne clique jamais sur une étiquette que tu n'as pas vue dans la dernière observation :
  les étiquettes changent à chaque changement de page.
- Pour te connecter à un site, utilise saisir_identifiant : les mots de passe sont dans le
  coffre de Windows et ne doivent jamais apparaître dans ta réponse ni dans un champ texte
  ordinaire. Ne demande jamais un mot de passe à l'utilisateur.
- Si un code d'authentification à deux facteurs est demandé, utilise obtenir_code_2fa, puis
  saisis le code dans le champ prévu.
- Déclare honnêtement « ecriture: true » pour tout clic qui enregistre, soumet, crée,
  modifie ou supprime quelque chose. L'utilisateur peut avoir activé la confirmation ; s'il
  refuse, ne contourne pas — demande-lui ce qu'il souhaite.
- Si un geste échoue deux fois de suite de la même manière, change de stratégie plutôt que
  de répéter. Après trois échecs, explique le blocage à l'utilisateur avec
  demander_a_utilisateur.
- Ne devine jamais une donnée d'affaires (montant, date, nom de client). Si elle manque,
  demande-la.
- Économise : préfère observer_page et lire_texte à capture_ecran, qui coûte beaucoup plus cher.
- Quand la tâche est terminée, réponds en français, en trois phrases au maximum : ce que tu as
  fait, où, et le résultat. Ce texte est lu à voix haute — pas de listes à puces, pas de code.
"""


def fiche_des_sites_connus() -> str:
    """Résumé des profils de sites, ajouté à la consigne système.

    C'est le « deuxième étage » de l'application : un socle générique capable
    d'aller sur n'importe quel site, et des profils qui rendent les sites
    prioritaires nettement plus fiables (adresses, repères, parcours de
    connexion, interdits). Sans profil, l'application fonctionne quand même,
    mais elle tâtonne davantage.
    """
    fiches = []
    for nom in lister_profils_sites():
        profil = charger_profil_site(nom)
        if not profil or nom == "exemple_crm":
            continue
        lignes = [f"Site « {nom} » : {profil.get('description', '')}".strip()]
        if profil.get("url_connexion"):
            lignes.append(f"  Page de connexion : {profil['url_connexion']}")
        if profil.get("url_accueil"):
            lignes.append(f"  Accueil : {profil['url_accueil']}")
        if profil.get("site_identifiants"):
            lignes.append(
                f"  Identifiants enregistrés sous le nom « {profil['site_identifiants']} » "
                "(utilise saisir_identifiant)."
            )
        deux_facteurs = profil.get("authentification_2fa") or {}
        if deux_facteurs:
            lignes.append(
                "  Double authentification par courriel — appelle obtenir_code_2fa avec "
                f"indice « {deux_facteurs.get('indice', '')} »"
                + (f" et expéditeur « {deux_facteurs.get('expediteurs_attendus', [''])[0]} »"
                   if deux_facteurs.get("expediteurs_attendus") else "")
                + "."
            )
        for cle, valeur in (profil.get("reperes") or {}).items():
            lignes.append(f"  Repère {cle} : « {valeur} »")
        for consigne in profil.get("consignes", []):
            lignes.append(f"  Consigne : {consigne}")
        fiches.append("\n".join(lignes))
    if not fiches:
        return (
            "Aucun profil de site n'est configuré : procède par observation, prudemment, "
            "et demande confirmation quand un écran est ambigu."
        )
    return "Sites connus et leurs particularités :\n\n" + "\n\n".join(fiches)


class Cerveau:
    def __init__(
        self,
        config,
        journal,
        navigateur,
        demander_confirmation: Callable[[str], bool],
        demander_information: Callable[[str], str],
        signaler: Callable[[str, str], None],
    ):
        """`signaler(categorie, texte)` alimente l'affichage : « etape », « info », « cout »."""
        import anthropic

        self.anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.config = config
        self.journal = journal
        self.navigateur = navigateur
        self.signaler = signaler
        self.executeur = Executeur(
            navigateur, config, journal, demander_confirmation, demander_information
        )
        self.fiche_sites = fiche_des_sites_connus()
        self.messages: list[dict] = []
        self.cout_total_usd = 0.0
        self.interrompre = False
        self._fallbacks_disponibles = True

    # ------------------------------------------------------------- coûts
    def _compter_cout(self, usage) -> float:
        entree_prix, sortie_prix = PRIX.get(self.config["modele"], (5.0, 25.0))
        entree = getattr(usage, "input_tokens", 0) or 0
        sortie = getattr(usage, "output_tokens", 0) or 0
        ecriture_cache = getattr(usage, "cache_creation_input_tokens", 0) or 0
        lecture_cache = getattr(usage, "cache_read_input_tokens", 0) or 0
        cout = (
            entree * entree_prix
            + ecriture_cache * entree_prix * 1.25   # écrire dans le cache coûte 25 % de plus
            + lecture_cache * entree_prix * 0.10    # relire le cache coûte 90 % de moins
            + sortie * sortie_prix
        ) / 1_000_000
        self.cout_total_usd += cout
        self.signaler("cout", f"{self.cout_total_usd:.3f}")
        return cout

    # -------------------------------------------------------- historique
    def _elaguer(self) -> None:
        """Retire le détail des vieilles observations : l'historique reste léger."""
        poids = sum(len(json.dumps(m, default=str)) for m in self.messages)
        if poids < 60000:
            return
        restants_a_garder = 4
        for message in reversed(self.messages):
            if message["role"] != "user" or not isinstance(message["content"], list):
                continue
            for bloc in message["content"]:
                if isinstance(bloc, dict) and bloc.get("type") == "tool_result":
                    if restants_a_garder > 0:
                        restants_a_garder -= 1
                    elif isinstance(bloc.get("content"), str) and len(bloc["content"]) > 300:
                        bloc["content"] = (
                            bloc["content"][:300]
                            + "\n… (observation ancienne abrégée pour réduire le coût)"
                        )

    # ---------------------------------------------------------- appel API
    def _appel_claude(self):
        parametres = dict(
            model=self.config["modele"],
            max_tokens=int(self.config["max_tokens"]),
            system=[
                {"type": "text", "text": CONSIGNE_SYSTEME},
                {
                    "type": "text",
                    "text": self.fiche_sites,
                    # Le préfixe (consigne + fiches + outils) est mis en cache :
                    # à partir du deuxième appel, il coûte 10 % du prix d'entrée.
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            tools=OUTILS,
            messages=self.messages,
            thinking={"type": "adaptive"},
            output_config={"effort": self.config["effort"]},
        )
        if self._fallbacks_disponibles:
            try:
                return self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                    **parametres,
                )
            except self.anthropic.BadRequestError:
                # Option de repli indisponible sur ce compte : on continue sans elle.
                self._fallbacks_disponibles = False
                self.journal.inscrire("api", "Repli automatique indisponible ; appel standard")
        return self.client.messages.create(**parametres)

    def _appel_protege(self):
        try:
            return self._appel_claude()
        except self.anthropic.AuthenticationError as erreur:
            raise RuntimeError(
                "Votre clé d'API Anthropic est absente ou invalide. Ouvrez l'onglet "
                "Réglages pour la saisir de nouveau."
            ) from erreur
        except self.anthropic.RateLimitError as erreur:
            raise RuntimeError(
                "L'API Anthropic est momentanément saturée ou votre quota est atteint. "
                "Réessayez dans une minute."
            ) from erreur
        except self.anthropic.APIConnectionError as erreur:
            raise RuntimeError(
                "Impossible de joindre l'API Anthropic. Vérifiez votre connexion Internet."
            ) from erreur
        except self.anthropic.APIStatusError as erreur:
            raise RuntimeError(f"L'API Anthropic a renvoyé une erreur : {erreur}") from erreur

    # -------------------------------------------------------------- tâche
    def executer_tache(self, consigne: str) -> str:
        """Mène une tâche de bout en bout et renvoie le compte rendu à lire à voix haute."""
        self.interrompre = False
        self.journal.inscrire("tache", "Nouvelle consigne", consigne=consigne, mode=self.config.mode)
        self.messages.append({"role": "user", "content": consigne})

        limites = self.config["limites"]
        etapes_max = int(limites["etapes_max"])
        cout_max = float(limites["cout_max_par_tache_usd"])
        cout_depart = self.cout_total_usd

        for etape in range(1, etapes_max + 1):
            if self.interrompre:
                self.journal.inscrire("tache", "Tâche interrompue par l'utilisateur")
                return "J'ai arrêté la tâche à votre demande."

            if self.cout_total_usd - cout_depart > cout_max:
                message = (
                    f"J'arrête : cette tâche a déjà coûté {self.cout_total_usd - cout_depart:.2f} $ US, "
                    f"soit le plafond que vous avez fixé. Augmentez-le dans les réglages si nécessaire."
                )
                self.journal.inscrire("tache", "Plafond de coût atteint", cout=round(self.cout_total_usd, 4))
                return message

            self._elaguer()
            reponse = self._appel_protege()
            self._compter_cout(reponse.usage)

            if reponse.stop_reason == "refusal":
                self.journal.inscrire("tache", "Demande refusée par le modèle")
                return (
                    "Je ne peux pas poursuivre cette demande. Reformulez-la ou "
                    "précisez le contexte professionnel."
                )

            self.messages.append({"role": "assistant", "content": reponse.content})

            textes = [bloc.text for bloc in reponse.content if bloc.type == "text"]
            for texte in textes:
                if texte.strip():
                    self.signaler("etape", texte.strip())

            appels = [bloc for bloc in reponse.content if bloc.type == "tool_use"]
            if not appels:
                compte_rendu = "\n".join(textes).strip() or "Tâche terminée."
                self.journal.inscrire(
                    "tache", "Tâche terminée", etapes=etape,
                    cout_usd=round(self.cout_total_usd - cout_depart, 4),
                )
                return compte_rendu

            resultats = []
            for appel in appels:
                self.signaler("etape", f"→ {appel.name} {json.dumps(appel.input, ensure_ascii=False)[:120]}")
                contenu, est_erreur = self.executeur.executer(appel.name, appel.input)
                resultat = {
                    "type": "tool_result",
                    "tool_use_id": appel.id,
                    "content": contenu,
                }
                if est_erreur:
                    resultat["is_error"] = True
                resultats.append(resultat)
            self.messages.append({"role": "user", "content": resultats})

        self.journal.inscrire("tache", "Plafond d'étapes atteint", etapes=etapes_max)
        return (
            f"J'ai atteint la limite de {etapes_max} étapes sans terminer. "
            "Dites-moi comment poursuivre, ou augmentez la limite dans les réglages."
        )

    def nouvelle_conversation(self) -> None:
        self.messages = []
