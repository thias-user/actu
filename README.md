# ACTU

Application d'actualité installable sur iPhone (application web, « PWA ») : chaque matin à 10h,
un robot choisit l'essentiel de l'actualité et l'application le présente en défilement plein écran.

**Installer :** scannez le QR code avec l'appareil photo de l'iPhone, ouvrez le lien dans Safari,
puis Partager → « Sur l'écran d'accueil ». Adresse : https://thias-user.github.io/actu/

<img src="qr-code-actu.png" alt="QR code d'installation d'ACTU" width="260">

## Les 6 onglets

| Onglet | Contenu |
| --- | --- |
| **À la une** | Défilement plein écran avec, pour chaque article, une petite scène pixel art animée qui résume le sujet (décor, personnages en costume, drapeaux). 3 articles France (journaux français), 3 Europe (journaux européens en anglais), 3 États-Unis (journaux américains), 3 Amérique latine (en espagnol, presse d'Espagne ou d'Amérique latine). Puis les éditions de la veille, de l'avant-veille, etc. Chaque article : titre, source, date, résumé, lien, et à la fin les publications YouTube/Bluesky des médias et créateurs (HugoDécrypte, Ulyces, franceinfo, Le Monde, AFP…) qui en parlent. |
| **Explorer** | Tous les articles collectés, à trier par thème, date, source ou importance, et à filtrer par région, période ou mot-clé. |
| **Le 20h** | Les journaux de 20h de TF1 (TF1+) et de France 2 (france.tv) des 14 derniers jours, avec les sujets du JT de TF1. |
| **ARTE** | Les reportages en accès libre sur les chaînes YouTube d'ARTE, classés par sujet (géopolitique, histoire, philosophie, art…) et par région du monde. |
| **TikTok** | Les dernières vidéos des comptes officiels des grands médias (Le Monde, franceinfo, AFP, BBC, Reuters, New York Times, El País…), via le module d'intégration de TikTok. |
| **Recherche** | Recherche par mots-clés dans les publications scientifiques (OpenAlex, HAL), et une sélection par thème renouvelée tous les 3 mois. |

Dans **Réglages** (roue dentée) : régions affichées, leur ordre et le **nombre d'articles par région (jusqu'à tous)**, centres d'intérêt,
**thèmes personnalisés**, et le **code de lecture** qui permet de lire les articles en accès libre en entier dans l'application.

## Lecture intégrale

Le site étant public, les textes des journaux n'y sont jamais publiés en clair : le robot récupère chaque matin le texte des articles
en accès libre (jamais les articles payants, jamais un site qui refuse les robots) et le chiffre (AES-256) avec un code personnel,
enregistré dans le secret GitHub `ACTU_READ_KEY`. Seule l'application où ce code a été saisi peut les lire.

## En un coup d'œil

À la fin de chaque article, une mini-vidéo en pixel art résume l'information en 5 étapes sous-titrées : **Où ?** (le monument
du pays ou de la ville), **Qui ?** (les acteurs, en costume selon leur rôle), **Quoi ?** (l'action), **Liens** (qui est lié à qui)
et **Et après ?** (les conséquences). Le scénario est calculé gratuitement par le robot à partir du texte de l'article (aucun
service payant) et chiffré avec le code de lecture ; sans code, l'application en fait une version simplifiée à partir du titre.

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
