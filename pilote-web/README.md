# Pilote Web

Application **Windows** qui utilise des sites web à votre place, **sans API** :
elle ouvre un vrai navigateur et y agit comme le ferait une personne — elle
regarde l'écran, clique, tape, lit, extrait.

- **Cerveau** : Claude (API Anthropic).
- **Mains** : un vrai navigateur Chromium, piloté par Playwright.
- **Commande** : à la voix ou au clavier, en français.
- **Réponse** : à voix haute *et* à l'écran.

> **Cible de la version 1** : ouvrir un CRM sans API, s'y connecter, passer
> l'authentification à deux facteurs reçue par courriel, puis poser des actions
> dans le site. C'est le test d'acceptation retenu.

## Démarrage rapide

1. Double-cliquez sur **`installer.bat`** (une seule fois, ~5 minutes).
   *Si l'installation refuse de trouver Python, lancez `diagnostic.bat` : il dit
   ce que votre ordinateur a réellement comme Python.*
2. Double-cliquez sur **`tester.bat`** (gratuit, aucun appel à l'API), puis sur
   **`lancer.bat`**.
3. Onglet **Réglages** → collez votre clé d'API Anthropic → *Enregistrer la clé*.
4. Onglet **Identifiants** → enregistrez le nom court du site, votre identifiant
   et votre mot de passe (ils vont dans le coffre de Windows, pas dans un fichier).
5. Onglet **Conversation** → dites ou écrivez ce que vous voulez faire.

La marche à suivre détaillée, sans aucun prérequis technique, est dans
**[docs/INSTALLATION.md](docs/INSTALLATION.md)**.

## Ce que l'application sait faire

| Capacité | État |
|---|---|
| Lire des dossiers, extraire des rapports | ✅ |
| Entrer des données, créer des fiches, remplir des formulaires | ✅ |
| Se connecter seule avec des identifiants enregistrés | ✅ |
| Travailler dans une session déjà ouverte par vous | ✅ (`demarrer_chrome_partage.bat`) |
| Récupérer seule le code 2FA reçu par courriel | ✅ par IMAP (Gmail, Microsoft 365, etc.) |
| Aller sur n'importe quel site | ✅ socle générique — voir la limite ci-dessous |
| Mode autonome / « Demande-moi avant d'agir » | ✅ interrupteur en haut de la fenêtre |
| Journal de toutes les actions | ✅ onglet Journal, conservation réglable |
| Réessais puis alerte en cas de blocage | ✅ 3 tentatives (2 s, 4 s, 8 s) puis alerte vocale |
| Plafond de coût et d'étapes par tâche | ✅ réglable |

## Les trois limites à connaître

1. **Le coût n'est pas nul.** L'API Anthropic est facturée à l'usage. Comptez
   environ **0,40 $ US par tâche** de douze étapes avec Claude Opus 5, environ
   **0,15 $** avec Claude Sonnet 5. Le détail et les leviers d'économie sont
   dans **[docs/COUTS.md](docs/COUTS.md)**.
2. **Les conditions d'utilisation des sites visités n'ont pas été vérifiées.**
   Automatiser une connexion et un 2FA peut y contrevenir. À confirmer auprès de
   chaque fournisseur avant la mise en production. Le point est signalé, pas tranché.
3. **« N'importe quel site » coûte de la fiabilité.** Sans configuration, l'application
   tâtonne. Pour vos sites de tous les jours, créez un *profil de site* : c'est
   une page de configuration qui la rend nettement plus sûre. Voir
   **[docs/PROFILS.md](docs/PROFILS.md)**.

## Où se trouvent vos données

Tout est dans `%APPDATA%\PiloteWeb` :

| Dossier / fichier | Contenu |
|---|---|
| `config.json` | vos réglages |
| `journal\` | le journal des actions (texte lisible + format machine) |
| `profils\` | vos profils de sites |
| `profil_navigateur\` | les sessions du navigateur dédié (vous restez connecté) |

Les mots de passe et la clé d'API ne sont **pas** dans ces fichiers : ils sont
dans le **Gestionnaire d'identification de Windows**.

## Documentation

| Document | Pour quoi |
|---|---|
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | installer et configurer, étape par étape |
| [docs/PLAN_DE_CONSTRUCTION.md](docs/PLAN_DE_CONSTRUCTION.md) | choix techniques, architecture, ce qui reste à décider |
| [docs/COUTS.md](docs/COUTS.md) | estimation de coût et économies |
| [docs/PROFILS.md](docs/PROFILS.md) | rendre un site prioritaire fiable |

## Vérifier que le socle fonctionne

Double-cliquez sur **`tester.bat`** — il lance les trois séries et affiche le
résultat en clair. Ou, en ligne de commande :

```
.venv\Scripts\python.exe tests\test_socle.py
.venv\Scripts\python.exe tests\test_boucle.py
.venv\Scripts\python.exe tests\test_integration.py
```

Aucun de ces tests ne consomme d'API — ils ne coûtent rien.

- `test_socle.py` : configuration, journal, classification lecture / écriture.
- `test_boucle.py` : boucle de raisonnement, plafonds de coût et d'étapes,
  allègement de l'historique.
- `test_integration.py` : essai complet sur une fausse page de CRM, avec le vrai
  navigateur — remplissage, choix dans une liste, clic d'enregistrement, et
  vérification qu'une seule confirmation a été demandée, sur le bon geste.
  Le navigateur y travaille **sans fenêtre** : rien ne s'ouvre à l'écran, c'est
  voulu. Seul le résultat affiché compte.
