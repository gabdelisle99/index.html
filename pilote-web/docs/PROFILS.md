# Profils de sites : rendre un site fiable

## Pourquoi

L'application sait aller sur **n'importe quel site** : elle regarde la page et
se débrouille. Mais se débrouiller, c'est tâtonner — et tâtonner, c'est plus
lent, plus cher, et parfois faux.

D'où une construction à deux étages :

1. **le socle générique** — fonctionne partout, sans configuration ;
2. **les profils** — une fiche par site important, qui dit à l'application où
   sont les choses et ce qu'elle ne doit pas faire.

Pour vos deux ou trois sites de tous les jours (le CRM en tête), écrivez un
profil. C'est un quart d'heure, une fois, et ça change tout.

## Comment en créer un

1. Ouvrez `%APPDATA%\PiloteWeb\profils\` (raccourci : onglet Journal →
   *Ouvrir le dossier du journal* → remontez d'un dossier).
2. Copiez-y le fichier `pilote\profils\exemple_crm.json` de l'application.
3. Renommez la copie avec le nom court de votre site, par exemple `crm.json`.
4. Ouvrez-la avec le Bloc-notes et remplissez les champs.
5. Fermez et relancez Pilote Web.

Le contenu des profils est ajouté aux consignes permanentes de l'application :
elle sait alors, avant même d'ouvrir la page, où elle met les pieds.

## Les champs

| Champ | À quoi il sert |
|---|---|
| `description` | une phrase : à quoi sert ce site |
| `url_accueil`, `url_connexion` | pour y aller directement, sans chercher |
| `site_identifiants` | le *nom court* sous lequel vous avez enregistré vos identifiants dans l'onglet Identifiants |
| `authentification_2fa.expediteurs_attendus` | l'adresse qui envoie les codes — évite de lire le mauvais courriel |
| `authentification_2fa.indice` | un mot présent dans le courriel de code |
| `authentification_2fa.motif_code` | la forme du code ; `\b(\d{6})\b` = six chiffres |
| `reperes` | les libellés exacts affichés à l'écran : champ identifiant, bouton de connexion, texte qui prouve que la connexion a réussi… |
| `consignes` | vos règles maison, en français, une par ligne |

## Les consignes, c'est là que ça se joue

Les `consignes` sont lues telles quelles par le cerveau de l'application.
Écrivez-y ce que vous diriez à une nouvelle employée :

```json
"consignes": [
  "Après la connexion, attendre l'apparition du texte « Tableau de bord ».",
  "La recherche de dossier se fait par le champ « Rechercher » en haut à droite.",
  "Ne jamais utiliser le bouton « Supprimer » sans confirmation explicite.",
  "Les montants s'entrent sans espace ni symbole de dollar.",
  "Si un bandeau « Session expirée » apparaît, se reconnecter avant de continuer."
]
```

## Vérifier qu'un profil est pris en compte

Lancez une tâche sur ce site et regardez la fenêtre : l'application doit aller
droit à la page de connexion, sans chercher. Si elle tâtonne encore, le nom du
fichier ne correspond probablement pas, ou le fichier contient une erreur de
ponctuation JSON (une virgule en trop, un guillemet manquant).

## Quand le site change

Un site remanié casse les repères. Les symptômes : « Je n'arrive pas à cliquer
sur… », ou des gestes qui partent dans une mauvaise direction. Corrigez les
libellés dans le profil — l'application redevient précise immédiatement.
