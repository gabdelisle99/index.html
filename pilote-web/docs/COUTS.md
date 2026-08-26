# Ce que ça coûte, et comment payer moins

**Tout est gratuit dans cette application sauf une chose : le raisonnement de
Claude, facturé à l'usage par Anthropic.** Il n'existe pas de version à coût
zéro qui garde Claude comme cerveau. Voici donc les chiffres, honnêtement.

## Ce qui est gratuit

| Élément | Coût |
|---|---|
| Python, Playwright, le navigateur Chromium | 0 $ |
| L'interface, le journal, le coffre de mots de passe | 0 $ (fournis par Windows) |
| La dictée (Vosk, hors ligne) | 0 $ |
| La voix de synthèse (voix Windows) | 0 $ |
| La lecture des codes 2FA par IMAP | 0 $ |
| **L'API Anthropic** | **facturée au jeton** |

## Comment le coût se forme

À chaque étape d'une tâche, l'application envoie à Claude : ses consignes
permanentes, la liste de ses outils, et l'historique de la tâche en cours
(ce qu'elle a vu et fait). Claude répond par le geste suivant. Plus la tâche
compte d'étapes, plus l'historique est long, plus l'étape coûte cher.

Deux mécanismes intégrés freinent cette croissance :

- **la mise en cache du préfixe** : les consignes et les outils (~2 400 jetons)
  ne sont facturés plein tarif qu'une fois ; ensuite, ils coûtent 10 % ;
- **l'allègement de l'historique** : passé un certain poids, les vieilles
  observations de pages sont abrégées automatiquement.

## Estimation par tâche

Hypothèses : une observation de page ≈ 950 jetons, une réponse de Claude
≈ 250 jetons, effort de raisonnement `medium`, tarifs publics d'Anthropic
(Opus 5 : 5 $ / 25 $ par million de jetons ; Sonnet 5 : 2 $ / 10 $ ;
Haiku 4.5 : 1 $ / 5 $). **Ce sont des ordres de grandeur, à ± 50 %.**

| Tâche | Étapes | Claude Opus 5 | Claude Sonnet 5 | Claude Haiku 4.5 |
|---|---|---|---|---|
| Lire une fiche déjà ouverte | 5 | ~0,10 $ US | ~0,04 $ | ~0,02 $ |
| Connexion + 2FA + consultation | 12 | ~0,40 $ | ~0,16 $ | ~0,08 $ |
| Création d'une fiche complète | 20 | ~0,95 $ | ~0,38 $ | ~0,19 $ |

Sur un rythme de **15 tâches par jour, 21 jours par mois** :

| Modèle | Coût mensuel approximatif |
|---|---|
| Claude Opus 5 | ~130 $ US |
| Claude Sonnet 5 | ~50 $ US |
| Claude Haiku 4.5 | ~25 $ US |

## Les sept leviers d'économie

Tous sont dans l'onglet **Réglages** ou dans `%APPDATA%\PiloteWeb\config.json`.

1. **Le modèle** — c'est le levier principal, un facteur 2 à 5.
   L'application est livrée avec **Claude Opus 5**, le plus capable : c'est lui
   qui se débrouille le mieux sur un site inconnu ou une page inhabituelle.
   Une fois qu'une tâche est rodée, **Claude Sonnet 5** la fait très bien pour
   le tiers du prix. Réglage : *Modèle Claude*.
2. **L'effort de raisonnement** — livré à `medium`, qui suffit pour de la
   navigation. `high` coûte plus cher et sert surtout à démêler une page
   compliquée ; `low` convient à des tâches très répétitives.
3. **Les profils de sites** — un profil bien fait supprime les étapes de
   tâtonnement. C'est souvent 30 % d'étapes en moins, donc 30 % de moins sur la
   facture ([PROFILS.md](PROFILS.md)).
4. **Des consignes précises** — « ouvre le dossier 1042 et lis-moi le statut »
   coûte deux fois moins cher que « regarde dans le CRM ce qui se passe avec ce
   client ».
5. **Le plafond par tâche** — *Plafond de coût par tâche*, livré à 0,75 $ US.
   L'application s'arrête net et vous prévient. Rien ne peut déraper en silence.
6. **Éviter les captures d'écran** — une image coûte environ 15 fois une
   observation textuelle. Les consignes de l'application lui disent déjà de
   n'en prendre qu'en dernier recours.
7. **La limite de dépense dans la console Anthropic** — le seul plafond
   qu'aucun bogue de cette application ne peut franchir. Réglez-la : menu
   *Limits* sur <https://console.anthropic.com>.

## Suivre la dépense réelle

- **Dans l'application** : le coût cumulé de la session s'affiche en haut à
  droite, et se met à jour à chaque étape.
- **Dans le journal** : chaque tâche terminée inscrit son coût
  (`cout_usd`) dans `%APPDATA%\PiloteWeb\journal`.
- **Chez Anthropic** : la console affiche la facturation réelle, qui fait foi.
  Les chiffres de l'application sont un calcul local à partir des tarifs
  inscrits dans `pilote/cerveau.py` — si Anthropic change ses prix, mettez ce
  tableau à jour.

## Le budget mensuel n'a pas encore été fixé

Le montant acceptable par mois fait partie des informations qui restent à
décider (voir [PLAN_DE_CONSTRUCTION.md](PLAN_DE_CONSTRUCTION.md), section 8).
En attendant, l'application est livrée prudemment : Opus 5, plafond de 0,75 $
par tâche, 40 étapes maximum.
