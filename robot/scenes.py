"""Description de la petite scène pixel art qui résume chaque article.

Le robot ne dessine rien : il choisit un décor, des personnages (costumes), un objet, des drapeaux et une étiquette ;
l'application dessine et anime la scène sur le téléphone (app/pixel.js). Ajouter un sujet = ajouter une ligne à TOPICS.
"""
import re

from common import compile_keywords, entities, norm

# sujet : (mots-clés, décor, costumes, objet, ambiance, étiquette)
TOPICS = [
    ("guerre", "guerre guerres war wars guerra militaire* military militar* armee army ejercito soldat* soldier* soldado* troupe* troops "
     "frappe* airstrike* bombard* missile* misil* drone* nato invasion front combat* offensive* cessez_le_feu ceasefire alto_el_fuego "
     "char tank* artillerie* artillery", "ruins", ["soldier", "soldier"], "tank", "dusk", "GUERRE"),
    ("diplomatie", "sommet summit cumbre diplomat* negociation* negotiation* talks pourparlers accord deal treaty traite tratado "
     "rencontre meeting reunion embassy ambassad* visite visit", "parliament", ["politician", "politician"], "handshake", "day", "DIPLOMATIE"),
    ("election", "election* eleccion* elector* electoral* vote votes voter* voto* scrutin* campagne campaign* campana primaire* primaries "
     "midterm* sondage* poll* encuesta* referendum* candidat* candidate* urnes ballot*", "parliament", ["politician", "citizen"], "ballot", "day", "ELECTIONS"),
    ("gouvernement", "gouvernement* government* gobierno* ministre* minister* ministro* parlement* parliament* assemblee senat* senate "
     "senado congres congress* congreso loi law ley budget demission* resign* dimision* premier_ministre prime_minister", "parliament",
     ["politician"], "podium", "day", "POLITIQUE"),
    ("manifestation", "manifest* protest* greve* huelga* mobilisation* syndicat* rassemblement* marcha* emeute* riot* "
     "cortege* blocage* bloquent", "city", ["protester", "protester", "protester"], "sign", "day", "MOBILISATION"),
    ("justice", "proces tribunal* juge* judge* court juicio jueza juez condamn* sentence* verdict* avocat* lawyer* abogado* plainte "
     "lawsuit* fiscal* parquet", "court", ["judge", "citizen"], "gavel", "day", "JUSTICE"),
    ("police", "police* policier* policia* gendarme* arrest* interpell* enquete* investigation* meurtre* murder* homicid* asesinato* "
     "fusillade* shooting* shoots tiroteo* attentat* atentado* attack* ataque* balle balles par_balle tirs arme armes gun guns vol_a_main_armee robbery robo* narcotrafic* cartel* explosif* explosivo*", "night", ["police", "police"],
     "siren", "night", "ENQUETE"),
    ("catastrophe", "seisme* earthquake* terremoto* sismo* tsunami* volcan* eruption* explosion* incendie* wildfire* blaze incendio* "
     "inondation* flood* inundacion* ouragan* hurricane* huracan* tempete* storm* tormenta* crash accident* collision* effondrement* "
     "collapse* derrumbe* glissement", "city", ["firefighter", "firefighter"], "fire", "dusk", "ALERTE"),
    ("climat", "climat* climate clima rechauffement warming secheresse drought sequia biodiversite biodiversity biodiversidad foret* "
     "forest* bosque* pollution contaminacion carbone carbon co2 glacier* glaciar* cop30 cop31 environnement environment*", "forest",
     ["farmer", "citizen"], "tree", "day", "CLIMAT"),
    ("espace", "espace_ spatial* space nasa esa cnes spacex astronaut* astronaute* fusee* rocket* cohete* satellite* satelite* lune moon "
     "luna mars_mission planete* planet* telescope* iss", "space", ["astronaut"], "rocket", "night", "ESPACE"),
    ("sante", "sante health* salud hopita* hospital* medecin* doctor* medico* vaccin* vaccine* vacuna* virus epidemi* pandemi* cancer* "
     "maladie* disease* enfermedad* medicament* medication* obesite obesity wegovy patient* paciente* soins healthcare stroke avc "
     "infarctus heart_attack", "hospital",
     ["doctor", "citizen"], "cross", "day", "SANTE"),
    ("science", "scien* cienci* chercheur* researcher* investigador* decouverte* discover* descubr* etude study estudio fossile* fossil* "
     "dinosaure* dinosaur* archeolog* archaeolog* arqueolog* genet* adn dna laboratoire lab", "field", ["scientist"], "flask", "day", "SCIENCE"),
    ("cyber", "cyber* hack* hacker* piratage pirate* ransomware rancongiciel fuite_de_donnees data_breach", "night", ["hacker"], "laptop",
     "night", "CYBERATTAQUE"),
    ("tech", "aitech robot* numerique digital tech technolog* tecnolog* logiciel* software smartphone* iphone apple google microsoft "
     "nvidia openai anthropic chatgpt semi_conducteur* semiconductor* puce* chip chips startup*", "city", ["scientist", "business"],
     "robot", "night", "TECH"),
    ("energie", "petrole* oil petroleo gaz gas carburant* fuel combustible* gazole diesel essence energie energy energia electricite "
     "electricity centrale_nucleaire nuclear_plant reacteur* opep opec", "desert", ["worker"], "barrel", "sunset", "ENERGIE"),
    ("bourse", "bourse* stock* wall_street nasdaq dow_jones cac_40 banque* bank* banco* bitcoin crypto* taux interest_rate* tasa* fed "
     "bce ecb investisseur* investor* inversor* marches markets mercados", "city", ["business", "business"], "coins", "day", "FINANCE"),
    ("economie", "econom* croissance growth crecimiento inflation inflacion pib gdp chomage unemployment desempleo emploi* jobs empleo* "
     "entreprise* company companies empresa* industri* usine* factory fabrica* commerce trade comercio tarif* tariff* arancel* "
     "douane* exportation* importation* hausse_des_prix baisse_des_prix prices precio* salaire* wage* dette debt deuda impot* tax taxes", "factory",
     ["business", "worker"], "chart", "day", "ECONOMIE"),
    ("agriculture", "agricult* agriculteur* paysan* farmer* campesino* ferme* recolte* harvest* cosecha* betail elevage cattle", "field",
     ["farmer", "farmer"], "tractor", "sunset", "AGRICULTURE"),
    ("migration", "migrant* migration* migratoire* refugie* refugee* refugiado* frontiere* border* frontera* exil* asile asylum", "desert",
     ["citizen", "citizen", "citizen"], "boat", "sunset", "MIGRATIONS"),
    ("education", "ecole* school* escuela* lycee* lyceen* eleve* student* estudiante* universite* university* universidad* enseignant* "
     "teacher* profesor* parcoursup bac", "city", ["student", "teacher"], "book", "day", "EDUCATION"),
    ("religion", "pape pope papa vatican eglise church iglesia religio* mosquee mosque synagogue cathedrale", "court", ["priest", "citizen"],
     "dove", "sunset", "RELIGION"),
    ("transport", "avion* plane* airplane* aerien* airline* aeroport* airport* aeropuerto* flight* vuelo* train* ferroviaire* rail* "
     "sncf tren* metro autoroute highway voiture* coche*", "city", ["citizen"], "plane", "day", "TRANSPORTS"),
    ("f1", "formule_1 formula_1 f1 grand_prix gran_premio motogp verstappen hamilton leclerc antonelli norris piastri ferrari mclaren "
     "mercedes red_bull", "stadium", ["racer"], "car", "day", "F1"),
    ("sport", "sport* deporte* football soccer futbol* ligue_1 champions_league liga premier_league psg om real_madrid barca tennis tenis "
     "rugby basket* nba nfl olymp* jo match partido mondial mundial coupe copa cyclisme ciclismo athletisme marathon boxe ufc golf "
     "mbappe messi alcaraz sinner djokovic wembanyama voile skipper* regate* vendee_globe route_du_rhum "
     "transat* course_au_large", "stadium", ["athlete", "athlete"], "ball", "day", "SPORT"),
    ("musique", "musique* music* musica* concert* concierto* album* chanteu* singer* cantante* rap rappeu* rapper* rock jazz festival_de_musique "
     "tournee* grammy* spotify chanson* song* cancion*", "stage", ["musician", "musician"], "guitar", "night", "MUSIQUE"),
    ("mode", "la_mode de_mode fashion* moda defile* runway desfile* couture couturier* pret_a_porter luxe luxury lujo chanel dior vuitton hermes "
     "gucci prada balenciaga lvmh kering vetement* clothing ropa mannequin*", "stage", ["model", "model"], "runway", "night", "MODE"),
    ("culture", "art arts artiste* artist* artista* musee* museum* museo* exposition* exhibition* exposicion* peinture* painting* pintur* "
     "cinema cine film films movie* pelicula* festival* livre livres book books libro* roman romans novel* novela* ecrivain* writer* "
     "escritor* goncourt medicis renaudot femina oscar* cesar theatre theater teatro patrimoine heritage serie", "city",
     ["artist"], "easel", "sunset", "CULTURE"),
]
_RX = [(t[0], compile_keywords(t[1].split()), t[2:]) for t in TOPICS]

# drapeaux dessinables par l'application (mots normalisés → code)
FLAGS = {
    "france": "fr", "germany": "de", "italy": "it", "spain": "es", "uk": "gb", "ukraine": "ua", "russia": "ru", "poland": "pl",
    "belgium": "be", "belgique": "be", "belgica": "be", "eu": "eu", "usa": "us", "mexico": "mx", "argentina": "ar", "brazil": "br",
    "colombia": "co", "venezuela": "ve", "chile": "cl", "peru": "pe", "china": "cn", "japan": "jp", "israel": "il", "iran": "ir",
    "india": "in", "turkey": "tr", "canada": "ca", "cuba": "cu", "ireland": "ie", "irlande": "ie", "netherlands": "nl", "bulgaria": "bg",
    "bulgarie": "bg", "sweden": "se", "suede": "se", "palestine": "ps", "gaza": "ps", "lebanon": "lb", "liban": "lb", "nato": "nato",
    "belgian": "be", "bulgarian": "bg", "swedish": "se", "dutch": "nl", "irish": "ie", "cubano": "cu", "cubana": "cu",
}
REGION_FLAG = {"fr": "fr", "us": "us", "eu": "eu"}  # drapeau par défaut de chaque région
FLAG_NAMES = {"fr": "FRANCE", "de": "ALLEMAGNE", "it": "ITALIE", "es": "ESPAGNE", "gb": "ROYAUME-UNI", "ua": "UKRAINE",
              "ru": "RUSSIE", "pl": "POLOGNE", "be": "BELGIQUE", "eu": "UE", "us": "USA", "mx": "MEXIQUE", "ar": "ARGENTINE",
              "br": "BRESIL", "co": "COLOMBIE", "ve": "VENEZUELA", "cl": "CHILI", "pe": "PEROU", "cn": "CHINE", "jp": "JAPON",
              "il": "ISRAEL", "ir": "IRAN", "in": "INDE", "tr": "TURQUIE", "ca": "CANADA", "cu": "CUBA", "ie": "IRLANDE",
              "nl": "PAYS-BAS", "bg": "BULGARIE", "se": "SUEDE", "ps": "PALESTINE", "lb": "LIBAN", "nato": "OTAN"}
LABELS = {"usa": "USA", "uk": "ROYAUME-UNI", "eu": "UE", "nato": "OTAN", "aitech": "IA", "china": "CHINE", "russia": "RUSSIE",
          "germany": "ALLEMAGNE", "italy": "ITALIE", "spain": "ESPAGNE", "france": "FRANCE", "ukraine": "UKRAINE", "japan": "JAPON",
          "india": "INDE", "turkey": "TURQUIE", "mexico": "MEXIQUE", "brazil": "BRESIL", "argentina": "ARGENTINE", "colombia": "COLOMBIE",
          "chile": "CHILI", "peru": "PEROU", "poland": "POLOGNE", "israel": "ISRAEL", "iran": "IRAN", "palestine": "PALESTINE",
          "latam": "AMERIQUE LATINE", "middleeast": "MOYEN-ORIENT", "whitehouse": "MAISON BLANCHE", "kyiv": "KIEV", "moscow": "MOSCOU",
          "putin": "POUTINE", "zelensky": "ZELENSKY", "beijing": "PEKIN", "brussels": "BRUXELLES", "london": "LONDRES"}
UP = re.compile(r" (hausse|augment\w*|record\w*|bondit|bond|grimpe|progress\w*|rise\w*|rising|surge\w*|soar\w*|gain\w*|sube|suben|alza|crece\w*|growth|croissance) ")
DOWN = re.compile(r" (baisse\w*|chute\w*|recul\w*|plonge\w*|effondr\w*|fall\w*|drop\w*|plunge\w*|slump\w*|decline\w*|crisis|crise|cae|caen|caida|baja|desplom\w*|recession) ")
WIN = re.compile(r" (champion\w*|campeon\w*|sacre\w*|titre|title|gagne\w*|wins|won|victoire\w*|victory|vence|gana|trophee|trophy|medaille\w*|medal\w*|record) ")


def describe(title, summary, region):
    """→ {"bg", "time", "cast", "prop", "flags", "label", "dir"} (quelques dizaines d'octets par article)."""
    nt, ns = norm(title), norm(summary)
    best, best_score = None, 0
    for tid, rx, spec in _RX:
        s = 3 * len(rx.findall(nt)) + len(rx.findall(ns))
        if s > best_score:
            best, best_score = (tid, spec), s
    if best:
        tid, (bg, cast, prop, time, label) = best
    else:
        tid, bg, cast, prop, time, label = "info", "city", ["journalist", "citizen"], "mic", "day", "INFO"
    text = nt + ns
    scene = {"topic": tid, "bg": bg, "time": time, "cast": list(cast), "prop": prop, "label": [label]}
    if tid in ("economie", "bourse"):
        up, down = len(UP.findall(text)), len(DOWN.findall(text))
        scene["dir"] = "up" if up > down else "down" if down > up else "up"
    if tid in ("sport", "f1") and WIN.search(text):
        scene["prop"] = "trophy" if tid == "sport" else "car"
    # pays cités → drapeaux ; deuxième étiquette = pays principal, sinon un nom propre fiable
    flags = []
    for w in nt.split() + ns.split():
        code = FLAGS.get(w)
        if code and code not in flags:
            flags.append(code)
    named = None
    shown = [f for f in flags if f != REGION_FLAG.get(region)]
    if shown:
        named = FLAG_NAMES.get(shown[0])
    else:
        # un nom propre écrit avec une majuscule dans le titre ET dans le résumé (les titres anglais mettent des majuscules partout)
        both = entities(title) & entities(summary) if summary else entities(title)
        cands = [w for w in nt.split() if w in both and 3 <= len(w) <= 12 and not w.isdigit()]
        if cands:
            named = LABELS.get(cands[0], cands[0].upper())
    scene["flags"] = (flags or ([REGION_FLAG[region]] if region in REGION_FLAG else []))[:2]
    if named and named != label:
        scene["label"].append(re.sub(r"[^A-Z0-9 -]", "", named)[:14])
    return scene


def refresh(day):
    """(Re)calcule la scène de chaque article d'une édition ; True si quelque chose a changé."""
    changed = False
    for region, articles in day["regions"].items():
        for a in articles:
            scene = describe(a["title"], a["summary"], region)
            if a.get("scene") != scene:
                a["scene"] = scene
                changed = True
    return changed
