# Installation, pas à pas

Ce guide ne suppose **aucune connaissance technique**. Suivez les étapes dans
l'ordre. Chaque étape indique ce que vous devez voir à l'écran quand elle est
réussie.

Comptez 20 à 30 minutes la première fois, dont beaucoup d'attente.

---

## Étape 1 — Installer Python (une seule fois)

Python est le moteur qui fait tourner l'application. Il est gratuit.

1. Ouvrez le **Microsoft Store** (icône du sac bleu, ou menu Démarrer → tapez « Store »).
2. Dans la barre de recherche, tapez **Python 3.12**.
3. Cliquez sur **Obtenir** puis attendez la fin de l'installation.

✅ *Réussi si* : le Store affiche « Ouvrir » à la place de « Obtenir ».

> Si votre organisation bloque le Microsoft Store : allez sur
> <https://www.python.org/downloads/windows/>, téléchargez « Windows installer
> (64-bit) », et **cochez impérativement la case « Add python.exe to PATH »**
> sur le premier écran de l'installateur.

---

## Étape 2 — Récupérer l'application

Si vous avez reçu un fichier `.zip` : clic droit → **Extraire tout** → choisissez
un dossier facile à retrouver, par exemple `Documents\PiloteWeb`.

✅ *Réussi si* : le dossier contient `installer.bat`, `lancer.bat` et un
sous-dossier `pilote`.

---

## Étape 3 — Lancer l'installation

1. Ouvrez le dossier.
2. Double-cliquez sur **`installer.bat`**.
3. Une fenêtre noire s'ouvre et affiche des lignes qui défilent. **Laissez-la
   travailler** (3 à 8 minutes selon votre connexion).

✅ *Réussi si* : la fenêtre affiche « INSTALLATION TERMINEE » et attend que vous
appuyiez sur une touche.

❌ *Si elle affiche « Python n'est pas installe »* : reprenez l'étape 1, puis
redémarrez l'ordinateur, puis relancez `installer.bat`.

❌ *Si elle affiche « L'installation a echoue »* : vérifiez votre connexion
Internet et relancez. En entreprise, un pare-feu peut bloquer les
téléchargements : demandez l'autorisation pour `pypi.org` et
`playwright.azureedge.net`.

---

## Étape 4 — Obtenir une clé d'API Anthropic

C'est ce qui permet à l'application de « penser ». C'est la **seule dépense**.

1. Allez sur <https://console.anthropic.com>.
2. Créez un compte (ou connectez-vous).
3. Menu **Billing** → ajoutez un moyen de paiement et un premier crédit
   (20 $ US suffisent pour commencer et durent longtemps si vous suivez
   [COUTS.md](COUTS.md)).
4. Menu **API keys** → **Create key** → copiez la clé (elle commence par `sk-ant-`).

> ⚠ Cette clé est un moyen de paiement. Ne la partagez pas, ne la collez pas
> dans un courriel ou un site web.

**Conseil vivement recommandé** : dans la console Anthropic, menu **Limits**,
fixez une limite de dépense mensuelle. C'est le seul plafond qu'aucune erreur
de l'application ne peut dépasser.

---

## Étape 5 — Premier lancement

1. Double-cliquez sur **`lancer.bat`**. La fenêtre « Pilote Web » s'ouvre.
2. Onglet **Réglages** → collez votre clé dans « Clé d'API Anthropic » →
   **Enregistrer la clé**.
3. Onglet **Identifiants** → pour chaque site :
   - *Nom court du site* : un mot simple, sans espace, par exemple `crm` ;
   - *Identifiant* : ce que vous tapez d'habitude pour vous connecter ;
   - *Mot de passe* : votre mot de passe du site ;
   - **Enregistrer ce site**.
4. Onglet **Conversation** → écrivez : `Ouvre google.ca et dis-moi ce que tu vois`.

✅ *Réussi si* : une fenêtre de navigateur s'ouvre, la page se charge, et
l'application vous répond à l'écran et à voix haute.

> Le mot de passe part directement dans le champ de la page. Il n'est **jamais**
> envoyé à Claude, ni écrit dans le journal.

---

## Étape 6 — Activer la dictée (facultatif)

Sans cette étape, vous écrivez vos consignes au clavier ; tout le reste
fonctionne, y compris la réponse à voix haute.

1. Allez sur <https://alphacephei.com/vosk/models>.
2. Téléchargez **`vosk-model-small-fr-0.22`** (environ 40 Mo, gratuit).
3. Clic droit sur le fichier `.zip` → **Extraire tout** → extrayez-le dans
   `Documents\PiloteWeb`.
4. Ouvrez le dossier extrait et copiez son chemin complet depuis la barre
   d'adresse de l'Explorateur (ex. `C:\Users\Vous\Documents\PiloteWeb\vosk-model-small-fr-0.22`).
5. Dans Pilote Web : onglet **Réglages** → collez ce chemin dans « Modèle de
   dictée Vosk » → **Enregistrer les réglages** → fermez et relancez l'application.

✅ *Réussi si* : le bouton **🎤 Parler** ne renvoie plus de message d'erreur et
affiche « J'écoute… » quand vous cliquez dessus.

La reconnaissance vocale fonctionne **hors ligne** : votre voix ne sort pas de
l'ordinateur.

---

## Étape 7 — Lecture automatique des codes 2FA (facultatif mais recommandé)

Pour que l'application aille chercher elle-même le code reçu par courriel.

### Si votre courriel est Gmail

1. Activez la validation en deux étapes sur votre compte Google (obligatoire).
2. Allez sur <https://myaccount.google.com/apppasswords>.
3. Créez un **mot de passe d'application**, nommez-le « Pilote Web », copiez les
   16 caractères affichés.
4. Dans Pilote Web : onglet **Identifiants** → collez-le dans « Mot de passe
   courriel » → **Enregistrer**.
5. Onglet **Réglages** :
   - *Serveur IMAP* : `imap.gmail.com`
   - *Adresse courriel* : votre adresse
   - *Courriel 2FA actif* : `oui`
   - **Enregistrer les réglages**.

### Si votre courriel est Microsoft 365 / Outlook

Même marche à suivre, avec `outlook.office365.com` comme serveur IMAP.
⚠ Beaucoup d'organisations désactivent IMAP : si la connexion échoue, votre
service informatique doit l'autoriser pour votre compte. **Ce n'est pas
bloquant** — sans connecteur, l'application vous demandera le code à voix haute
et vous le direz ou le taperez.

### Autre fournisseur

Cherchez « adresse serveur IMAP » suivi du nom de votre fournisseur. Le port
reste 993.

Réglages fins (expéditeurs attendus, forme du code, délai d'attente) : voir
`%APPDATA%\PiloteWeb\config.json`, section `courriel_2fa`.

---

## Étape 8 — Travailler dans une session déjà ouverte (facultatif)

Par défaut, l'application ouvre **son propre** navigateur et y garde vos
sessions ouvertes d'une fois à l'autre. C'est le mode le plus simple.

Si vous préférez qu'elle travaille dans un navigateur que **vous** avez ouvert
et où vous êtes déjà connecté :

1. Double-cliquez sur **`demarrer_chrome_partage.bat`** — un Chrome s'ouvre.
2. Connectez-vous à vos sites dans cette fenêtre-là.
3. Dans Pilote Web : onglet **Réglages** → *Navigateur* → **`session_ouverte`** →
   **Enregistrer les réglages**.
4. Lancez votre tâche : l'application travaillera dans **cette** fenêtre.

Pour revenir au mode simple, remettez *Navigateur* sur `profil_dedie`.

---

## Étape 9 — L'essai qui valide tout (scénario CRM)

C'est le test d'acceptation de la version 1.

1. Vérifiez que l'interrupteur **« Demande-moi avant d'agir »** est **coché**
   (pour ce premier essai, c'est plus prudent).
2. Écrivez ou dites :

   > « Ouvre le CRM, connecte-toi avec les identifiants enregistrés sous *crm*,
   > récupère le code d'authentification dans mon courriel, puis ouvre le dossier
   > de *[nom du client]* et lis-moi son statut. »

3. Suivez le déroulement dans la fenêtre : chaque geste s'affiche.
4. À la première action qui **écrit** dans le site, une fenêtre vous demande
   votre accord. Répondez **Oui** ou **Non**.

✅ *Réussi si* : l'application se connecte, entre le code 2FA, ouvre le dossier
et vous lit le statut à voix haute.

Si un blocage survient, l'application réessaie trois fois, puis vous prévient à
voix haute et vous explique où elle est coincée. L'onglet **Journal** contient
la trace de tout ce qu'elle a fait.

---

## Utilisation quotidienne

- Ouvrez `lancer.bat` quand vous en avez besoin, fermez la fenêtre quand vous
  avez fini. L'application **ne démarre pas** avec Windows et ne tourne **pas**
  en arrière-plan.
- Laissez « Demande-moi avant d'agir » coché tant que vous n'avez pas confiance
  dans une tâche précise. Décochez-la pour les tâches répétitives que vous
  connaissez.
- Surveillez le compteur de coût en haut à droite.

## En cas de problème

| Ce que vous voyez | Quoi faire |
|---|---|
| « installation incomplète » | relancez `installer.bat` |
| « Votre clé d'API est absente ou invalide » | onglet Réglages → recollez la clé |
| « L'API est momentanément saturée » | attendez une minute et redemandez |
| « Je n'arrive pas à… après 3 tentatives » | le site a changé ou est lent ; dites à l'application où cliquer, ou créez un profil de site ([PROFILS.md](PROFILS.md)) |
| L'application ne trouve pas le bon bouton | dites-lui le libellé exact affiché à l'écran |
| Fenêtre de navigateur restée ouverte | fermez-la à la main ; elle se rouvrira au besoin |

Le journal complet est dans `%APPDATA%\PiloteWeb\journal` (bouton *Ouvrir le
dossier du journal* dans l'onglet Journal).
