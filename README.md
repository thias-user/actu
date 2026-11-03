# ACTU

Application d'actualité installable sur iPhone (application web, « PWA ») : chaque matin à 10h,
un robot choisit l'essentiel de l'actualité et l'application le présente en défilement plein écran.

**Installer :** scannez le QR code avec l'appareil photo de l'iPhone, ouvrez le lien dans Safari,
puis Partager → « Sur l'écran d'accueil ». Adresse : https://thias-user.github.io/actu/

<img src="qr-code-actu.png" alt="QR code d'installation d'ACTU" width="260">

## Les 5 onglets

| Onglet | Contenu |
| --- | --- |
| **À la une** | Défilement plein écran avec, pour chaque article, une petite scène pixel art animée qui résume le sujet (décor, personnages en costume, drapeaux). 3 articles France (journaux français), 3 Europe (journaux européens en anglais), 3 États-Unis (journaux américains), 3 Amérique latine (en espagnol, presse d'Espagne ou d'Amérique latine). Puis les éditions de la veille, de l'avant-veille, etc. Chaque article : titre, source, date, résumé, lien, et à la fin les publications YouTube/Bluesky des médias et créateurs (HugoDécrypte, Ulyces, franceinfo, Le Monde, AFP…) qui en parlent. |
| **Explorer** | Tous les articles collectés, à trier par thème, date, source ou importance, et à filtrer par région, période ou mot-clé. |
| **Le 20h** | Les journaux de 20h de TF1 (TF1+) et de France 2 (france.tv) des 14 derniers jours, avec les sujets du JT de TF1. |
| **ARTE** | Les documentaires et reportages en accès libre sur les chaînes YouTube d'ARTE (sans concerts ni films), classés par sujet (géopolitique, histoire, psychologie et quête de sens, philosophie, art…) et par région du monde. La recherche porte sur les titres, les descriptions complètes et les mots-clés des vidéos, tolère pluriels et petites fautes, et classe par pertinence. Miniatures en haute définition. |
| **Recherche** | Recherche par mots-clés dans les publications scientifiques (OpenAlex, HAL), et une sélection par thème renouvelée tous les 3 mois. |

Dans **Réglages** (roue dentée) : régions affichées, leur ordre et le **nombre d'articles par région (jusqu'à tous)**, la **traduction en
français**, centres d'intérêt, **thèmes personnalisés**, et le **code de lecture** qui permet de lire les articles en accès libre en entier dans l'application.

## Lecture intégrale

Le site étant public, les textes des journaux n'y sont jamais publiés en clair : le robot récupère chaque matin le texte des articles
en accès libre (jamais les articles payants, jamais un site qui refuse les robots) et le chiffre (AES-256) avec un code personnel,
enregistré dans le secret GitHub `ACTU_READ_KEY`. Seule l'application où ce code a été saisi peut les lire.

## Traduction

Option **Traduire en français** dans Réglages (désactivée au départ) : les articles en anglais (Europe, États-Unis) et en espagnol
(Amérique latine) s'affichent en français : titres, résumés, textes complets et schémas. Dans chaque article, un bouton
« Voir l'original » / « Traduire en français » change d'avis pour cet article seulement.

Gratuit et sans clé : le robot traduit chaque matin avec les modèles libres **OPUS-MT** de l'université d'Helsinki
(anglais → français, espagnol → français), qui tournent sur la machine de GitHub. Les modèles sont préparés une fois puis
gardés dans le cache de GitHub ; rien n'est stocké sur le téléphone. Les textes complets traduits sont chiffrés avec le code
de lecture, comme les originaux. Chaque passage traduit au plus 14 minutes de textes complets, les plus récents d'abord. C'est une
traduction automatique : fiable pour comprendre l'essentiel, moins élégante qu'un traducteur humain.

## En un coup d'œil

À la fin de chaque article, un **schéma de pensée** animé, au format rectangle, résume l'information case par case, de façon
à se lire sans l'article : **Où ?** (le lieu, avec sa fiche), **Quand ?** (les dates citées, les articles du même sujet publiés
dans ACTU avant ou après, et le jour de l'article), **Qui ?** (chaque acteur : qui il est, d'après Wikipédia, et ce qu'il fait
dans cette histoire), **Quoi ?** (l'essentiel en quelques phrases), **Comment ?** (les moyens, le déroulé, un chiffre clé),
**Pourquoi ?** (les causes données par les sources ; si elles n'en donnent pas, trois hypothèses, présentées comme telles),
**Liens** (qui s'oppose à qui, qui soutient qui), **Pour comprendre** (une page Wikipédia sur le sujet quand elle apporte
quelque chose, et le pays en bref : régime et dirigeants, niveau de vie, croissance, inflation, chômage, inégalités, avec une
lecture d'ensemble), **Regard critique** (comment l'information est construite : genre et angle du titre, recoupement entre
médias et façon dont chacun la titre, sources anonymes, ce qui n'est pas établi, versions contestées, qui parle et qui manque,
mots chargés, chiffres qui ne concordent pas, angles morts, ancienneté des faits, mise en regard avec le pays) et **Et après ?**
(les suites annoncées). Tous les textes sont des phrases entières, jamais coupées. La caméra s'approche de chaque case, puis montre le schéma entier ;
touchez une case pour l'agrandir. Le bouton plein écran affiche le schéma sur tout le téléphone, droit ; le bouton « Paysage »
le fait pivoter.

Tout est gratuit, sans clé ni service payant : le robot repère les acteurs, les dates, les causes et les relations dans le texte,
puis vérifie chaque fiche Wikipédia contre l'article avant de la garder (mieux vaut pas de fiche qu'une fiche fausse ; les
définitions évidentes, comme « école maternelle », sont écartées). Le pays en bref vient de la Banque mondiale et de Wikidata,
relus chaque semaine. Les fiches sont gardées dans le cache du robot. Le schéma est chiffré avec le code de lecture ; sans code,
l'application en fait une version courte à partir du titre et du résumé, avec le pays en bref.

## Comment ça marche

- `app/` : l'application (HTML, CSS, JavaScript sans dépendance). Environ 110 Ko : seuls vos réglages restent sur le téléphone ;
  articles, images et vidéos sont lus en direct sur internet.
- `robot/` : le robot Python qui lit environ 90 flux RSS de journaux, les chaînes YouTube, Bluesky, TF1+, france.tv, OpenAlex et HAL,
  puis écrit les fichiers de `app/data/`. Il s'identifie honnêtement et respecte les sites qui refusent les robots.
- `.github/workflows/actu.yml` : GitHub lance le robot chaque matin vers 10h (heure de Paris), enregistre les nouvelles données
  et republie le site sur GitHub Pages. Gratuit, et sans que votre ordinateur soit allumé.

## Modifier

- Ajouter un journal : une ligne `F(...)` dans `robot/config.py` (section `FEEDS`).
- Ajouter un thème pour tout le monde : `app/themes.json`. Pour vous seul : Réglages → Mes thèmes personnalisés.
- Mise à jour immédiate : onglet **Actions** du dépôt GitHub → « ACTU – mise à jour et publication » → **Run workflow**.
- Facultatif : un quota OpenAlex personnel et gratuit (clé à créer sur openalex.org) dans le secret GitHub `OPENALEX_API_KEY`.

Tester en local : `pip install -r robot/requirements.txt`, puis `python robot/run_daily.py --force` et `python -m http.server --directory app`.

## Limites honnêtes

- X (Twitter), Instagram et TikTok n'autorisent pas la lecture automatique de leurs publications : ACTU utilise YouTube et Bluesky,
  où ces médias et créateurs publient aussi.
- Certains journaux (Le Monde, NYT, WSJ…) réservent une partie de leurs articles à leurs abonnés.
- Les replays du 20h restent sur TF1+ et france.tv (droits de diffusion) : ACTU ouvre directement la bonne édition.
- GitHub met en pause les tâches planifiées d'un dépôt sans aucune activité pendant 60 jours. Les publications quotidiennes du robot
  comptent normalement comme de l'activité. Si les mises à jour s'arrêtaient, relancez-les depuis l'onglet Actions.
