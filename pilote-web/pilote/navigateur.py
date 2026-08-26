"""Pilotage du navigateur (les « mains » de l'application).

L'application ne parle à aucune API : elle ouvre un vrai Chrome et agit dedans
comme le ferait une personne — elle regarde la page, clique, tape, lit.

Pour rester peu coûteux, l'état de la page est envoyé à Claude sous forme de
texte compact (la liste des éléments cliquables ou saisissables, plus le texte
visible), et non sous forme d'images. Une capture d'écran reste possible à la
demande, quand le texte ne suffit pas.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Callable

from .secrets_win import obtenir_identifiants

# Repérage des éléments : chaque élément utile reçoit une étiquette (« ref »)
# posée dans la page, du genre « c0e17 ». Claude ne manipule que ces étiquettes.
JS_SNAPSHOT = r"""
(limite) => {
  const SELECTEUR = 'a[href], button, input, select, textarea, summary, ' +
    '[role="button"], [role="link"], [role="tab"], [role="checkbox"], ' +
    '[role="menuitem"], [role="option"], [contenteditable="true"], [onclick]';
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = window.getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.opacity === '0') return false;
    return true;
  };
  const nom = (el) => {
    const etiquette = el.id
      ? (document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.innerText || '')
      : (el.closest('label')?.innerText || '');
    const candidats = [
      el.getAttribute('aria-label'),
      etiquette,
      el.getAttribute('placeholder'),
      el.getAttribute('title'),
      el.tagName === 'SELECT' ? '' : el.innerText,
      el.getAttribute('name'),
      el.type === 'checkbox' || el.type === 'radio' ? '' : el.value,
    ];
    for (const c of candidats) {
      if (c && String(c).trim()) return String(c).trim().replace(/\s+/g, ' ').slice(0, 90);
    }
    return '';
  };
  const elements = [];
  let compteur = 0;
  for (const el of document.querySelectorAll(SELECTEUR)) {
    if (elements.length >= limite) break;
    if (!visible(el)) continue;
    const ref = 'e' + (++compteur);
    el.setAttribute('data-pilote-ref', ref);
    const item = {
      ref: ref,
      balise: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || el.getAttribute('role') || '',
      nom: nom(el),
    };
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      if (el.type === 'checkbox' || el.type === 'radio') {
        item.coche = el.checked;
      } else {
        item.rempli = Boolean(el.value);
      }
    }
    if (el.tagName === 'SELECT') {
      item.options = Array.from(el.options).slice(0, 25).map(o => o.text.trim());
      item.valeur = el.value;
    }
    if (el.disabled) item.desactive = true;
    elements.push(item);
  }
  const texte = (document.body ? document.body.innerText : '') || '';
  return {
    url: location.href,
    titre: document.title,
    elements: elements,
    texte: texte.replace(/\n{3,}/g, '\n\n').trim(),
  };
}
"""


class ErreurNavigateur(RuntimeError):
    """Échec d'un geste dans le navigateur, après tous les réessais."""


class Navigateur:
    def __init__(self, config, journal, avertir: Callable[[str], None] | None = None):
        self.config = config
        self.journal = journal
        self.avertir = avertir or (lambda message: None)
        self._playwright = None
        self._navigateur = None
        self.contexte = None
        self.page = None

    # ------------------------------------------------------------------ vie
    def demarrer(self) -> None:
        from playwright.sync_api import sync_playwright

        reglages = self.config["navigateur"]
        self._playwright = sync_playwright().start()

        if reglages["mode"] == "session_ouverte":
            url = reglages["url_debogage"]
            try:
                self._navigateur = self._playwright.chromium.connect_over_cdp(url)
            except Exception as erreur:
                raise ErreurNavigateur(
                    "Impossible de me brancher sur votre navigateur déjà ouvert "
                    f"({url}). Lancez d'abord demarrer_chrome_partage.bat, ou "
                    "choisissez le mode « profil dédié » dans les réglages.\n"
                    f"Détail : {erreur}"
                ) from erreur
            self.contexte = (
                self._navigateur.contexts[0]
                if self._navigateur.contexts
                else self._navigateur.new_context()
            )
            self.page = self.contexte.pages[-1] if self.contexte.pages else self.contexte.new_page()
        else:
            options = dict(
                user_data_dir=str(self.config.dossier_profil_navigateur),
                headless=not reglages["fenetre_visible"],
                viewport={"width": reglages["largeur"], "height": reglages["hauteur"]},
                args=["--disable-blink-features=AutomationControlled"],
            )
            if reglages.get("chemin_executable"):
                options["executable_path"] = reglages["chemin_executable"]
            self.contexte = self._playwright.chromium.launch_persistent_context(**options)
            self.page = self.contexte.pages[0] if self.contexte.pages else self.contexte.new_page()

        self.page.set_default_timeout(reglages["delai_chargement_ms"])
        self.journal.inscrire("navigateur", "Navigateur démarré", mode=reglages["mode"])

    def arreter(self) -> None:
        for fermeture in (
            lambda: self.contexte and self.config["navigateur"]["mode"] != "session_ouverte"
            and self.contexte.close(),
            lambda: self._navigateur and self._navigateur.close(),
            lambda: self._playwright and self._playwright.stop(),
        ):
            try:
                fermeture()
            except Exception:
                pass
        self.page = self.contexte = self._navigateur = self._playwright = None

    # -------------------------------------------------------- réessais
    def _reessayer(self, description: str, action: Callable[[], Any]) -> Any:
        """Exécute un geste ; en cas d'échec, réessaie puis prévient l'utilisateur."""
        reglages = self.config["reessais"]
        delais = list(reglages["delais_secondes"])
        tentatives = max(1, int(reglages["nombre"]))
        derniere = None
        for tentative in range(1, tentatives + 1):
            try:
                return action()
            except Exception as erreur:
                derniere = erreur
                self.journal.inscrire(
                    "reessai",
                    f"Échec : {description}",
                    tentative=tentative,
                    sur=tentatives,
                    erreur=str(erreur)[:300],
                )
                if tentative < tentatives:
                    attente = delais[min(tentative - 1, len(delais) - 1)] if delais else 2
                    time.sleep(attente)
        message = (
            f"Je n'arrive pas à {description} après {tentatives} tentatives. "
            f"Détail technique : {str(derniere)[:200]}"
        )
        self.avertir(message)
        raise ErreurNavigateur(message)

    # -------------------------------------------------------- observation
    def _cadres(self):
        """Cadres de la page (page principale + iframes accessibles)."""
        return list(self.page.frames)

    def observer(self) -> dict:
        """Photographie textuelle de la page, prête à être envoyée à Claude."""
        reglages = self.config["navigateur"]
        limite = int(reglages["elements_max"])
        elements: list[dict] = []
        morceaux_texte: list[str] = []
        url = self.page.url
        titre = ""

        for index, cadre in enumerate(self._cadres()):
            if len(elements) >= limite:
                break
            try:
                brut = cadre.evaluate(JS_SNAPSHOT, limite - len(elements))
            except Exception:
                continue  # cadre inaccessible (autre domaine) ou détaché
            if index == 0:
                titre = brut.get("titre", "")
            for element in brut.get("elements", []):
                element["ref"] = f"c{index}{element['ref']}"
                elements.append(element)
            texte = brut.get("texte", "")
            if texte:
                morceaux_texte.append(texte)

        texte = "\n\n".join(morceaux_texte)
        maximum = int(reglages["texte_page_max"])
        tronque = len(texte) > maximum
        return {
            "url": url,
            "titre": titre,
            "elements": elements,
            "texte": texte[:maximum],
            "texte_tronque": tronque,
        }

    def observer_en_texte(self) -> str:
        """Version compacte de l'observation (économise des jetons)."""
        vue = self.observer()
        lignes = [f"URL : {vue['url']}", f"Titre : {vue['titre']}", "", "Éléments utilisables :"]
        for element in vue["elements"]:
            details = []
            if element.get("type"):
                details.append(element["type"])
            if element.get("rempli"):
                details.append("déjà rempli")
            if element.get("coche") is not None:
                details.append("coché" if element["coche"] else "non coché")
            if element.get("desactive"):
                details.append("désactivé")
            if element.get("options"):
                details.append("options : " + " | ".join(element["options"]))
            suffixe = f" ({', '.join(details)})" if details else ""
            lignes.append(f"  [{element['ref']}] {element['balise']} « {element.get('nom', '')} »{suffixe}")
        if not vue["elements"]:
            lignes.append("  (aucun élément interactif détecté)")
        lignes += ["", "Texte visible :", vue["texte"]]
        if vue["texte_tronque"]:
            lignes.append("… (texte coupé ; utilisez defiler ou lire_texte pour la suite)")
        return "\n".join(lignes)

    def _localiser(self, ref: str):
        """Retrouve l'élément portant l'étiquette donnée."""
        if not ref or not ref.startswith("c"):
            raise ErreurNavigateur(f"Étiquette d'élément invalide : {ref!r}")
        index_cadre = int(ref[1 : ref.index("e")])
        cadres = self._cadres()
        if index_cadre >= len(cadres):
            raise ErreurNavigateur(f"Le cadre de l'élément {ref} n'existe plus ; refaites une observation.")
        cible = cadres[index_cadre].locator(f'[data-pilote-ref="{ref[ref.index("e"):]}"]')
        if cible.count() == 0:
            raise ErreurNavigateur(
                f"L'élément {ref} n'est plus dans la page. Refaites une observation."
            )
        return cible.first

    # ------------------------------------------------------------- gestes
    def naviguer(self, url: str) -> str:
        def action():
            self.page.goto(url, wait_until="domcontentloaded")
            return f"Page ouverte : {self.page.url}"

        return self._reessayer(f"ouvrir {url}", action)

    def cliquer(self, ref: str, description: str = "") -> str:
        def action():
            element = self._localiser(ref)
            element.scroll_into_view_if_needed(timeout=5000)
            element.click()
            self.page.wait_for_timeout(600)
            return f"Clic effectué sur {description or ref}. URL : {self.page.url}"

        return self._reessayer(f"cliquer sur {description or ref}", action)

    def ecrire(self, ref: str, texte: str, effacer: bool = True) -> str:
        def action():
            element = self._localiser(ref)
            element.scroll_into_view_if_needed(timeout=5000)
            if effacer:
                element.fill(texte)
            else:
                element.click()
                element.type(texte, delay=20)
            return f"Texte saisi dans {ref}."

        return self._reessayer(f"écrire dans {ref}", action)

    def ecrire_identifiant(self, ref: str, site: str, champ: str) -> str:
        """Saisit un identifiant enregistré sans jamais l'exposer à Claude."""
        identifiants = obtenir_identifiants(site)
        if not identifiants:
            raise ErreurNavigateur(
                f"Aucun identifiant enregistré pour « {site} ». "
                "Ajoutez-le dans l'onglet Identifiants de l'application."
            )
        utilisateur, mot_de_passe = identifiants
        valeur = utilisateur if champ == "utilisateur" else mot_de_passe
        self.ecrire(ref, valeur, effacer=True)
        return f"{champ.capitalize()} de « {site} » saisi (valeur masquée)."

    def choisir(self, ref: str, valeur: str) -> str:
        def action():
            element = self._localiser(ref)
            try:
                element.select_option(label=valeur)
            except Exception:
                element.select_option(value=valeur)
            return f"Option « {valeur} » choisie dans {ref}."

        return self._reessayer(f"choisir « {valeur} » dans {ref}", action)

    def cocher(self, ref: str, coche: bool = True) -> str:
        def action():
            element = self._localiser(ref)
            element.check() if coche else element.uncheck()
            return f"Case {ref} {'cochée' if coche else 'décochée'}."

        return self._reessayer(f"{'cocher' if coche else 'décocher'} {ref}", action)

    def appuyer(self, touche: str) -> str:
        def action():
            self.page.keyboard.press(touche)
            self.page.wait_for_timeout(500)
            return f"Touche {touche} envoyée."

        return self._reessayer(f"appuyer sur {touche}", action)

    def defiler(self, direction: str = "bas", pixels: int = 600) -> str:
        def action():
            delta = pixels if direction == "bas" else -pixels
            self.page.mouse.wheel(0, delta)
            self.page.wait_for_timeout(400)
            return f"Page défilée vers le {direction}."

        return self._reessayer(f"défiler vers le {direction}", action)

    def attendre(self, secondes: float = 2, texte: str = "") -> str:
        def action():
            if texte:
                self.page.get_by_text(texte, exact=False).first.wait_for(
                    timeout=int(secondes * 1000) or 15000
                )
                return f"Le texte « {texte} » est apparu."
            self.page.wait_for_timeout(int(secondes * 1000))
            return f"Attente de {secondes} seconde(s)."

        return self._reessayer("attendre la page", action)

    def lire_texte(self, selecteur: str = "") -> str:
        def action():
            if selecteur:
                elements = self.page.locator(selecteur)
                nombre = min(elements.count(), 40)
                return "\n".join(elements.nth(i).inner_text() for i in range(nombre))
            return self.page.inner_text("body")[: int(self.config["navigateur"]["texte_page_max"]) * 3]

        return self._reessayer("lire le texte de la page", action)

    def capture_ecran(self) -> str:
        """Capture d'écran en base64 (à n'utiliser qu'en dernier recours : coûteux)."""
        def action():
            return base64.standard_b64encode(self.page.screenshot(type="png")).decode("ascii")

        return self._reessayer("prendre une capture d'écran", action)
