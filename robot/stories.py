"""Schéma « En un coup d'œil » de chaque article : où, qui, quoi, liens, pour comprendre, et après.

Entièrement gratuit (aucune intelligence artificielle payante) : on repère dans le texte les acteurs les plus cités,
le type d'action, les acteurs cités ensemble et les phrases qui annoncent une suite ; context.py ajoute les fiches
Wikipédia et les articles liés des jours précédents. Les textes du schéma reprennent des phrases de l'article :
comme les textes complets, ces schémas sont chiffrés avec votre code de lecture → app/data/stories/AAAA-MM-JJ.bin
"""
import os
import re
from datetime import timedelta

import context
import translate
from common import DATA, STOP, idf_table, log, norm, parallel, read_json, strip_accents, tokens
from config import FEEDS, YOUTUBE_NEWS
from fulltext import decrypt, encrypt, key_from
from news import day_path
from scenes import FLAG_NAMES, FLAGS

SENT_RE = re.compile(r"(?<=[.!?»”])\s+(?=[«“\"A-ZÀ-ÖØ-Þ¿¡])")
NAME_RE = re.compile(r"\b([A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]+(?:\s+(?:de\s+la\s+|de\s+|da\s+|del\s+|du\s+|des\s+|of\s+the\s+|of\s+|von\s+|van\s+|al-)?[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'’\-]+){0,3})")
ACRO_RE = re.compile(r"\b([A-Z]{2,6})\b")
NOT_NAMES = set("""le la les un une des du de en et ou mais il elle ils elles on nous vous ce cette ces son sa ses leur au aux selon pour par
avec dans sur sous après avant depuis lundi mardi mercredi jeudi vendredi samedi dimanche janvier février mars avril mai juin juillet août
septembre octobre novembre décembre the a an and or but he she they we you it this that these his her their in on at for with from by after
before since monday tuesday wednesday thursday friday saturday sunday january february march april may june july august september october
november december el la los las un una y o pero él ella ellos en con por para según tras desde lunes martes miércoles jueves viernes sábado
domingo enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre mr mrs ms dr m mme direct live video photo
afp reuters ap""".split())
ACRO_OK = {"OTAN", "NATO", "ONU", "UN", "UE", "EU", "FMI", "IMF", "OMS", "WHO", "CGT", "CFDT", "RN", "LFI", "PS", "LR", "PSG", "OM", "FBI", "CIA",
           "BCE", "ECB", "FED", "SNCF", "EDF", "OPEP", "OPEC", "UEFA", "FIFA", "NASA", "ESA", "CNRS", "ADNOC", "OPENAI"}
# les médias eux-mêmes ne sont pas des acteurs de l'information
MEDIA = {norm(f["source"].split("(")[0]).strip() for f in FEEDS} | {norm(n).strip() for n, _, _ in YOUTUBE_NEWS} | {
    "afp", "reuters", "ap", "associated press", "nbc", "cbs", "abc", "cnn", "bbc", "france inter", "france info", "franceinfo", "le monde",
    "new york times", "washington post", "the guardian", "guardian", "bloomberg", "politico", "axios", "efe", "europa press", "ansa", "dpa"}


def is_media(key):
    return any(key == m or key.startswith(m + " ") or key.endswith(" " + m) or (" " + m + " ") in (" " + key + " ") for m in MEDIA if m)

ROLE_WORDS = [
    ("politician", "president presidente president* ministre* minister* ministro* depute* deputy senat* senator* senador* maire mayor alcalde* "
     "gouverneur* governor* gobernador* premier_ministre prime_minister chancelier* chancellor* candidat* candidate* parti partido party"),
    ("soldier", "armee army ejercito militaire* military militar* soldat* soldier* soldado* general* commandant*"),
    ("judge", "juge* judge* jueza juez tribunal* court procureur* prosecutor* fiscal*"),
    ("police", "police* policier* policia* gendarme*"),
    ("athlete", "joueur* player* jugador* attaquant* entraineur* coach* entrenador* pilote* driver* champion* campeon* tennisman* cycliste* skipper*"),
    ("scientist", "chercheur* chercheuse* researcher* scientist* scientifique* investigador* professeur* professor*"),
    ("doctor", "medecin* doctor* medico* infirmi* nurse* chirurgien* surgeon*"),
    ("business", "pdg ceo patron* directeur* director* fondateur* founder* fundador* entreprise* company* empresa* banque* bank* groupe*"),
    ("musician", "chanteu* singer* cantante* rappeu* rapper* musicien* musician* groupe_de_musique"),
    ("artist", "artiste* artist* ecrivain* writer* escritor* realisat* filmmaker* romancier* novelist* peintre* painter* acteur* actrice* actor* actress*"),
    ("protester", "syndicat* union* sindicato* manifestant* protester* militant* activist* activista*"),
]
ACTION_WORDS = [  # en cas d'égalité, le premier de la liste l'emporte
    ("vote", "vote* voto* votacion* elu elue elected electo* scrutin* election* eleccion* referendum* primaire* primaries runoff"),
    ("victoire", "remporte* gagne* champion* sacre* wins won beat* gana* vence* triomphe* victoire* victory decerne* laureat* prix_*"),
    ("defaite", "perd perdu battu* echoue* loses lost fails defeat* pierde* derrota*"),
    ("demission", "demission* demissionne* resign* resignation* dimision* dimite* limog* fired destitu*"),
    ("sante", "hospitalis* hospitaliz* stroke avc malade* illness cancer* infarctus heart_attack sante health salud"),
    ("signe", "signe* accord* adopte* signs signed deal* agreement* firma* acuerdo* traite* treaty"),
    ("juge", "proces juge* condamne* tribunal* trial court sentence* juicio* condena* verdict*"),
    ("arrete", "arrete* interpelle* inculpe* arrested arrest* detenido* capturado* garde_a_vue"),
    ("accident", "crash* collision* incendie* explosion* seisme* earthquake* sismo* terremoto* effondrement* accident* naufrage* inondation* flood*"),
    ("attaque", "attaque* frappe* bombard* tue tues killed kill* airstrike* attack* ataca* ataque* atentado* bombardea* drone* missile* "
     "offensive* tir tirs blesse* par_balle shooting* shot herido* balacera"),
    ("negocie", "negocie* negocia* negotiat* rencontre* sommet* summit* cumbre* discute* talks pourparlers meet* meeting reune* dialogo*"),
    ("manifeste", "manifest* greve* protest* marcha* huelga* mobilis* rassembl* petition*"),
    ("avertit", "alerte* met_en_garde menace* warn* threat* advierte* amenaza* alarme*"),
    ("decouvre", "decouv* discover* descubr* etude* study estudio revele* reveals"),
    ("hausse", "hausse* augmente* bondit* grimpe* record* rise* rising surge* sube* alza* aumenta* raised raises"),
    ("baisse", "baisse* chute* recule* plonge* fall* drop* plunge* cae caen baja* bajo desplom*"),
    ("lance", "lance* lancement launch* lanza* inaugure* unveil*"),
    ("aide", "aide* soutien* verse* finance* aid help* ayuda* apoyo*"),
    ("hommage", "mort meurt deces hommage* dies died death muere murio fallece*"),
    ("annonce", "annonce* declare* affirme* estime* says said announces* anuncia* afirma* dice"),
]
LINK_WORDS = [
    ("oppose", "contre against contra conflit* conflict* guerre war guerra sanction* rival* oppose* adversaire*"),
    ("accuse", "accuse* denonce* reproche* blame* acusa* critique* critic*"),
    ("negocie", "negocie* negotiat* negocia* discute* talks rencontre* meet* reune*"),
    ("aide", "aide* soutien* support* ayuda* apoyo* finance* livre* arme*"),
    ("allie", "allie* ally allies aliado* partenaire* partner* socio* accord agreement acuerdo"),
    ("depend", "depend* fournit* supplies* importe* exporte* client*"),
]
LINK_LABEL = {"oppose": "CONTRE", "accuse": "ACCUSE", "negocie": "NEGOCIE", "aide": "SOUTIENT", "allie": "ALLIES", "depend": "DEPEND", "lien": "LIEN"}
VERB_LABEL = {"attaque": "ATTAQUE", "accident": "DRAME", "negocie": "NEGOCIE", "vote": "VOTE", "victoire": "GAGNE", "defaite": "PERD",
              "signe": "ACCORD", "juge": "JUSTICE", "arrete": "ARRESTATION", "manifeste": "MOBILISATION", "avertit": "ALERTE",
              "decouvre": "DECOUVERTE", "lance": "LANCEMENT", "hausse": "HAUSSE", "baisse": "BAISSE", "aide": "AIDE", "hommage": "HOMMAGE",
              "annonce": "ANNONCE", "demission": "DEMISSION", "sante": "SANTE"}
CONSEQ_CUES = re.compile(r"\b(devrai\w*|pourrai\w*|risqu\w*|va |vont |entra[iî]n\w*|cons[ée]quence\w*|afin de|d[ée]sormais|prochain\w*|"
                         r"would|could|will|may|expected|likely|leading to|as a result|podr[íi]\w*|deber[áa]\w*|se espera|lo que|provocar\w*|"
                         r"menace de|suite|bient[ôo]t|soon|next)\b", re.I)
CONSEQ_KIND = [
    ("hausse", "hausse* augment* rise* sube* alza*"), ("baisse", "baisse* chute* fall* drop* cae* baja*"),
    ("election", "election* vote* scrutin* eleccion* elector*"), ("loi", "loi law ley texte* decret* reform*"),
    ("argent", "milliard* million* euros dollars budget* cout* cost* prix price* precio*"), ("sante", "sante health salud hopita* malad*"),
    ("guerre", "guerre war guerra frappe* attaque* armee* military*"), ("paix", "paix peace paz cessez_le_feu ceasefire"),
    ("justice", "proces trial juicio tribunal* condamn* peine*"), ("climat", "climat* climate clima* secheresse* drought"),
    ("emploi", "emploi* jobs empleo* licenci* salari* chomage"), ("alerte", "alerte* danger* menace* risque* risk* riesgo*"),
]


def _rx(words):
    from common import compile_keywords
    return compile_keywords(words.split())


ROLE_RX = [(k, _rx(w)) for k, w in ROLE_WORDS]
ACTION_RX = [(k, _rx(w)) for k, w in ACTION_WORDS]
LINK_RX = [(k, _rx(w)) for k, w in LINK_WORDS]
CONS_RX = [(k, _rx(w)) for k, w in CONSEQ_KIND]


JUNK_RE = re.compile(r"^\s*([-•▶►·]|lire aussi|à lire|a lire|read more|related|lea también|lee también|ver también|te puede interesar|"
                     r"newsletter|abonnez|suscr[ií]bete|publicit[ée]|photo ?:|cr[ée]dit)", re.I)


def sentences(text):
    out = []
    for para in (text or "").split("\n"):
        if JUNK_RE.match(para):
            continue
        out += [s.strip() for s in SENT_RE.split(para) if len(s.strip()) > 30]
    return out


def shorten(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[:cut.rfind(" ")].rstrip(",;:") + "…"


GENERIC_LAST = {"UNIDOS", "UNIS", "UNITED", "REPUBLIC", "REPUBLIQUE", "REPUBLICA", "KINGDOM", "UNI", "UNIE"}


def tag_of(name):
    words = strip_accents(name).upper().replace("’", "'").split()
    connector = any(w in ("DE", "DEL", "DA", "DES", "DU", "OF") for w in words)
    t = words[0] if words and (connector or words[-1] in GENERIC_LAST) else words[-1] if len(words) > 1 and len(words[-1]) > 2 else (words[0] if words else "")
    return re.sub(r"[^A-Z0-9-]", "", t)[:10]


TITLES = set("""senator sen rep representative gov governor president presidente presidenta prime premier minister ministre ministro king
roi rey reine queen pope pape general chancellor chancelier republican republicans democrat democratic democrats republicain democrate
mayor maire alcalde judge juge juez m mme mr mrs ms dr dra sir lord le la el the former ancien ex leader chef jefe belgian french american
british german spanish italian russian ukrainian chinese mexican argentine brazilian chilean colombian venezuelan peruvian bulgarian polish
sr sra don dona pm ceo pdg strategist analyst commentator host anchor spokesman spokeswoman spokesperson secretary attorney ambassador
envoy coach rapper singer star candidate candidat candidata dirigeant dirigente""".split())
PLACE_PREP = re.compile(r"\b(à|a|au|aux|en|dans|près de|pres de|in|at|near|from|de|desde|del|en el|en la)\s*$", re.I)
ELISION = re.compile(r"^[CDJLMNSTQcdjlmnstq][u]?['’]")


def find_actors(title, sents, region_country, title_case=False):
    """Personnes, pays et organisations les plus cités. Les titres anglais mettent des majuscules partout : on ne
    s'y fie que pour des noms déjà présents dans le texte."""
    counts, display, first_pos, place_votes = {}, {}, {}, {}
    body = list(sents or [])
    if not title_case:
        body = [title] + body
    pos = 0
    for text in body:
        for m in NAME_RE.finditer(text):
            raw = m.group(1).strip(" -'’")
            if ELISION.match(raw):
                continue
            words = raw.split()
            while words and norm(words[0]).strip() in TITLES | NOT_NAMES:
                words = words[1:]
            if not words:
                continue
            at_start = m.start() == 0 or text[:m.start()].rstrip()[-1:] in ".!?:«\"“"
            if at_start and len(words) == 1:
                continue  # majuscule de début de phrase : pas un nom
            while words and norm(words[-1]).strip() in STOP:
                words = words[:-1]
            if not words:
                continue
            name = " ".join(words)
            key = norm(name).strip()
            if len(key) < 4 or key in NOT_NAMES or key == "aitech" or key.isdigit() or is_media(key):
                continue
            code = FLAGS.get(key) if len(words) == 1 else None
            ident = ("pays", code) if code else ("nom", key)
            counts[ident] = counts.get(ident, 0) + 1
            display.setdefault(ident, PLACE_NAMES.get(code, name) if code else name)
            first_pos.setdefault(ident, pos)
            if PLACE_PREP.search(text[:m.start()]):
                place_votes[ident] = place_votes.get(ident, 0) + 1
            pos += 1
        for m in ACRO_RE.finditer(text):
            if m.group(1) in ACRO_OK:
                ident = ("org", m.group(1))
                counts[ident] = counts.get(ident, 0) + 1
                display.setdefault(ident, m.group(1))
                first_pos.setdefault(ident, pos)
                pos += 1
    # les lieux (souvent précédés de « à », « dans », « in »…) ne sont pas des acteurs
    for ident in list(counts):
        if ident[0] == "nom" and place_votes.get(ident, 0) * 2 > counts[ident]:
            counts.pop(ident)
    # un nom de famille seul compte pour le nom complet (« Macron » → « Emmanuel Macron »)
    names = [i for i in counts if i[0] == "nom"]
    for i in names:
        for j in names:
            if i != j and i in counts and j in counts and len(j[1].split()) > 1 and j[1].endswith(" " + i[1]):
                counts[j] += counts.pop(i)
                break
    # bonus pour ce qui figure aussi dans le titre
    nt = norm(title)
    for ident in counts:
        if (" " + ident[1].lower().split()[-1] + " ") in nt or (ident[0] == "pays" and any(FLAGS.get(w) == ident[1] for w in nt.split())):
            counts[ident] += 3
    ranked = sorted(counts, key=lambda i: (-counts[i], first_pos[i]))
    actors = []
    for ident in ranked:
        if counts[ident] < 2 and actors:
            break
        kind, val = ident
        name = display[ident]
        if kind == "nom" and len(name.split()) == 1 and counts[ident] < 3:
            continue  # un mot seul, peu cité : trop incertain
        if any(x["tag"] == tag_of(name) for x in actors):
            continue
        if kind == "pays":
            actors.append({"name": name, "tag": FLAG_NAMES.get(val, tag_of(name))[:10], "role": "politician", "country": val, "kind": kind})
        elif kind == "org":
            actors.append({"name": name, "tag": name[:10], "role": "politician", "country": "eu" if name in ("UE", "EU", "BCE", "ECB") else
                           "nato" if name in ("OTAN", "NATO") else region_country, "kind": kind})
        else:
            actors.append({"name": name, "tag": tag_of(name), "role": None, "country": region_country, "kind": kind})
        if len(actors) == 4:
            break
    return actors


TOPIC_ROLE = {"culture": "artist", "sport": "athlete", "f1": "racer", "sante": "doctor", "science": "scientist", "justice": "judge",
              "police": "police", "guerre": "soldier", "musique": "musician", "mode": "model", "bourse": "business", "economie": "business"}
GROUP_NAME = {"politician": "Gouvernement", "citizen": "Habitants", "police": "Police", "firefighter": "Secours", "doctor": "Médecins",
              "athlete": "Athlètes", "racer": "Pilotes", "soldier": "Armée", "business": "Entreprises", "worker": "Salariés",
              "protester": "Manifestants", "student": "Élèves", "teacher": "Enseignants", "judge": "Justice", "scientist": "Chercheurs",
              "artist": "Artistes", "musician": "Musiciens", "model": "Mannequins", "hacker": "Pirates", "farmer": "Agriculteurs",
              "astronaut": "Astronautes", "priest": "Église", "journalist": "Journalistes"}


def guess_role(actor, sents, default, preferred=None):
    last = norm(actor["name"]).split()[-1]
    window = []
    for sent in sents:
        words = norm(sent).split()
        for i, w in enumerate(words):
            if w == last:
                window += words[max(0, i - 6):i + 7]
    text = " " + " ".join(window) + " "
    best, score = default, 0
    for k, rx in ROLE_RX:
        n = len(rx.findall(text)) + (2 if k == preferred else 0) * bool(rx.findall(text))
        if n > score:
            best, score = k, n
    return best


def best_kind(text, table, default, title=""):
    nt, nh = norm(text), norm(title)
    best, score = default, 0
    for k, rx in table:  # max strict : à égalité, le premier de la liste gagne
        n = len(rx.findall(nt)) + 3 * len(rx.findall(nh))
        if n > score:
            best, score = k, n
    return best


def central(sents, title, k=3):
    """Les phrases qui résument le mieux l'article (mots rares partagés avec le titre et le reste du texte)."""
    if not sents:
        return []
    sets = [set(tokens(s)) for s in sents]
    idf = idf_table(sets)
    tset = set(tokens(title))
    scored = []
    for i, st in enumerate(sets):
        if not st:
            continue
        score = sum(idf.get(t, 1) for t in st) / (len(st) ** 0.5) + 2.5 * len(st & tset) - 0.15 * i
        scored.append((score, i))
    top = sorted(i for _, i in sorted(scored, reverse=True)[:k])
    return [sents[i] for i in top]


def make_story(a, region, sents, date_label):
    scene = a.get("scene") or {}
    country = scene.get("country") or {"fr": "fr", "us": "us", "eu": "eu"}.get(region, "latam")
    actors = find_actors(a["title"], sents[:60], country, title_case=region in ("eu", "us"))
    cast = scene.get("cast") or ["citizen"]
    for i, act in enumerate(actors):
        if not act["role"]:  # une personne : son rôle se lit dans les phrases qui la citent
            act["role"] = guess_role(act, sents, cast[min(i, len(cast) - 1)], TOPIC_ROLE.get(scene.get("topic")))
        if scene.get("topic") == "guerre" and act["country"] not in ("eu", "nato") and FLAGS.get(norm(act["name"]).strip()):
            act["role"] = "soldier"
    if not actors:  # aucun nom fiable : les groupes de la scène (« Police », « Secours »…)
        actors = [{"name": GROUP_NAME.get(c, "Habitants"), "tag": tag_of(GROUP_NAME.get(c, "Habitants")), "role": c, "country": country,
                   "group": True} for c in dict.fromkeys(cast)][:2]
    kind = best_kind(" ".join(sents[:2]) or a["summary"], ACTION_RX, "annonce", a["title"])
    nt = norm(a["title"])
    order = sorted(range(len(actors)), key=lambda i: nt.find(" " + norm(actors[i]["name"]).strip().split()[-1] + " ") % 10000)
    who = order[0]
    target = order[1] if len(order) > 1 and kind in ("attaque", "negocie", "aide", "signe", "victoire", "defaite", "accuse") else -1
    # liens : acteurs cités dans les mêmes phrases
    links, link_sentence = [], ""
    for i in range(len(actors)):
        for j in range(i + 1, len(actors)):
            ki, kj = actors[i]["name"].split()[-1], actors[j]["name"].split()[-1]
            both = [s for s in sents if ki in s and kj in s]
            if both:
                nature = best_kind(" ".join(both), LINK_RX, "lien")
                links.append({"from": i, "to": j, "rel": LINK_LABEL[nature], "nature": nature if nature != "lien" else "depend", "_n": len(both)})
                if not link_sentence:
                    link_sentence = both[0]
    links = [{k: v for k, v in l.items() if k != "_n"} for l in sorted(links, key=lambda l: -l["_n"])[:3]]
    # conséquences : phrases qui annoncent une suite
    cons = [s for s in sents[1:] if CONSEQ_CUES.search(s)]
    cons = central(cons, a["title"], 2) if len(cons) > 2 else cons[:2]
    if not cons and len(sents) >= 5:
        cons = central(sents[len(sents) // 2:], a["title"], 1)
    consequences = [{"text": shorten(s, 160), "kind": best_kind(s, CONS_RX, "autre")} for s in cons] or \
                   [{"text": "Aucune suite annoncée dans l’article pour l’instant.", "kind": "autre"}]
    key = central(sents, a["title"], 2)
    city = (scene.get("city") or "").title()
    pname = PLACE_NAMES.get(country, "")
    place = f"{city} ({pname})" if city and pname and city.lower() != pname.lower() else (city or pname or "Dans le monde")
    captions = {
        "ou": f"{place} · {date_label}",
        "qui": "En jeu : " + ", ".join(x["name"] for x in actors[:4]) + ".",
        "quoi": shorten(" ".join(key) if key else a["title"], 260),
        "liens": shorten(link_sentence, 220) if link_sentence else "Sujet aussi traité par " + (", ".join(a.get("also", [])[:3]) or a["source"]) + ".",
        "consequences": " ".join(c["text"] for c in consequences),
    }
    return {
        "place": {"country": country, "city": scene.get("city", ""), "label": place, "date": date_label},
        "actors": actors,
        "action": {"who": who, "verb": VERB_LABEL.get(kind, "ACTU"), "kind": kind, "target": target},
        "links": links, "consequences": consequences, "captions": captions,
    }


PLACE_NAMES = {"fr": "France", "us": "États-Unis", "gb": "Royaume-Uni", "de": "Allemagne", "ru": "Russie", "ua": "Ukraine", "cn": "Chine",
               "it": "Italie", "es": "Espagne", "be": "Belgique", "eu": "Union européenne", "br": "Brésil", "ar": "Argentine", "mx": "Mexique",
               "jp": "Japon", "in": "Inde", "il": "Israël", "ps": "Palestine", "ir": "Iran", "tr": "Turquie", "lb": "Liban", "co": "Colombie",
               "ve": "Venezuela", "cl": "Chili", "pe": "Pérou", "cu": "Cuba", "ca": "Canada", "pl": "Pologne", "bg": "Bulgarie", "se": "Suède",
               "nl": "Pays-Bas", "ie": "Irlande", "latam": "Amérique latine", "nato": "OTAN"}
MONTHS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()


def update(days, tr=None):
    code = os.environ.get("ACTU_READ_KEY", "").strip()
    if not code:
        log("Schémas « En un coup d'œil » : pas de code de lecture, étape ignorée")
        return
    key = key_from(code)
    wiki = context.Wiki()
    total = 0
    for d in days:
        ed = read_json(day_path(d))
        if not ed:
            continue
        # articles des deux semaines précédentes et des jours suivants : chaque article est relié au reste de son histoire
        editions = [(x, e) for x in (d + timedelta(days=k) for k in range(-context.RELATED_DAYS, 4)) if (e := read_json(day_path(x)))]
        pool, idf = context.build_pool(editions)
        tpath, spath = DATA / "texts" / f"{d.isoformat()}.bin", DATA / "stories" / f"{d.isoformat()}.bin"
        try:
            texts = decrypt(key, tpath.read_bytes()) if tpath.exists() else {}
        except Exception:
            texts = {}
        date_label = f"{d.day} {MONTHS[d.month - 1]} {d.year}"

        def one(item):
            reg, a = item
            sents = sentences(texts.get(a["id"], "")) or sentences(a["summary"]) or [a["title"]]
            story = make_story(a, reg, sents, date_label)
            return a["id"], context.enrich(wiki, story, a, reg, sents, pool, idf, d)

        items = [(reg, a) for reg, arts in ed["regions"].items() for a in arts]
        stories = dict(r for r in parallel(one, items, workers=3) if r)
        if tr and not tr.broken:  # version française pour l'option « Traduire en français »
            try:
                translate.translate_stories(tr, stories, {a["id"]: translate.source_lang(reg, a) for reg, a in items})
            except Exception as e:
                log(f"  Traduction des schémas impossible : {type(e).__name__} {str(e)[:80]}")
        old = None
        if spath.exists():
            try:
                old = decrypt(key, spath.read_bytes())
            except Exception:
                old = None
        if old != stories:
            spath.parent.mkdir(parents=True, exist_ok=True)
            spath.write_bytes(encrypt(key, stories))
        total += len(stories)
    wiki.save()
    context.report(wiki, total)
    log(f"Schémas « En un coup d'œil » : {total} articles résumés")
