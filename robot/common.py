"""Outils partagés par le robot ACTU : téléchargement, nettoyage de texte, dates, thèmes."""
import hashlib
import html
import json
import math
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
DATA = APP / "data"
STATE = ROOT / "robot" / "state"
PARIS = ZoneInfo("Europe/Paris")
UA = "ACTU-bot/1.0 (lecteur d'actualites personnel; RSS)"


def log(*args):
    print(datetime.now(PARIS).strftime("%H:%M:%S"), *args, flush=True)


# ---------------------------------------------------------------- réseau

def fetch(url, timeout=20, retries=1, accept="*/*", max_bytes=None):
    """Télécharge une URL (avec un identifiant de robot honnête). Lève l'erreur finale."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(max_bytes) if max_bytes else r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    # decompressobj accepte aussi un flux tronqué (lecture partielle avec max_bytes)
                    raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw)
                return raw
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 401, 403, 404, 405, 410, 451):
                break  # inutile d'insister : le site refuse
        except Exception as e:  # réseau, délai, TLS…
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise last


def fetch_json(url, **kw):
    return json.loads(fetch(url, accept="application/json", **kw))


def parallel(fn, items, workers=12):
    """Applique fn à chaque élément en parallèle ; les erreurs donnent None."""
    def safe(x):
        try:
            return fn(x)
        except Exception as e:
            label = (x.get("url") or x.get("name")) if isinstance(x, dict) else x
            log("  !", str(label)[:90], type(e).__name__, str(e)[:90])
            return None
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(safe, items))


# ---------------------------------------------------------------- fichiers

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj, pretty=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=1 if pretty else None,
                      separators=None if pretty else (",", ":"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def short_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------- dates

def now_paris():
    return datetime.now(PARIS)


def iso(dt):
    return dt.astimezone(PARIS).isoformat(timespec="minutes")


def from_struct(st):
    """time.struct_time (UTC, fourni par feedparser) -> datetime Paris."""
    if not st:
        return None
    return datetime(*st[:6], tzinfo=timezone.utc).astimezone(PARIS)


def parse_iso(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=PARIS)
    except ValueError:
        return None


# ---------------------------------------------------------------- texte

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(s, limit=None):
    """Retire le HTML, décode les entités et coupe proprement à `limit` caractères."""
    if not s:
        return ""
    s = html.unescape(TAG_RE.sub(" ", html.unescape(s)))
    s = WS_RE.sub(" ", s).strip()
    if limit and len(s) > limit:
        cut = s[:limit]
        dot = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        s = cut[:dot + 1] if dot > limit * 0.6 else cut[:cut.rfind(" ")].rstrip(",;:") + "…"
    return s


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


# Les mêmes réalités écrites en français, anglais ou espagnol → un seul mot.
ALIASES = [
    (r"amerique latine|america latina|latin americ\w*|latino americ\w*|latinoameric\w*|amerique du sud|south americ\w*|sudameric\w*|centroameric\w*|amerique centrale|central america\w*", "latam"),
    (r"etats unis|estados unidos|united states|u s a|eeuu|ee uu|eua", "usa"),
    (r"royaume uni|reino unido|united kingdom|grande bretagne|great britain|britain|britanni\w*|british|britanic\w*", "uk"),
    (r"union europeenne|european union|union europea|\bue\b", "eu"),
    (r"russie|rusia|russe|russes|russian|russians|ruso|rusos|rusa|rusas", "russia"),
    (r"ukrainien\w*|ukrainian\w*|ucrania\w*|ucranian\w*", "ukraine"),
    (r"chine|chinois\w*|chinese|chino|chinos|china", "china"),
    (r"allemagne|alemania|allemand\w*|aleman\w*|german\w*", "germany"),
    (r"espagne|espana|espagnol\w*|spanish|spaniard\w*", "spain"),
    (r"italie|italia|italien\w*|italian\w*|italiano\w*", "italy"),
    (r"pologne|polonia|polonais\w*|polish|polaco\w*", "poland"),
    (r"israelien\w*|israeli\w*|israeli", "israel"),
    (r"iranien\w*|iranian\w*|irani\b", "iran"),
    (r"palestinien\w*|palestinian\w*|palestino\w*", "palestine"),
    (r"americain\w*|american\w*|estadounidense\w*|norteamerican\w*", "usa"),
    (r"francais\w*|french|frances\b|francesa\w*|francia", "france"),
    (r"bresil\w*|brasil\w*|brazil\w*", "brazil"),
    (r"mexique|mexicain\w*|mexican\w*|mexicano\w*|mexico", "mexico"),
    (r"argentine\w*|argentino\w*|argentina\w*", "argentina"),
    (r"colombie\w*|colombian\w*|colombiano\w*|colombia", "colombia"),
    (r"venezuelien\w*|venezuelan\w*|venezolano\w*|venezuela", "venezuela"),
    (r"chili\b|chilien\w*|chilean\w*|chileno\w*|chile", "chile"),
    (r"perou|peruvien\w*|peruvian\w*|peruano\w*|peru", "peru"),
    (r"turquie|turquia|turc\b|turque\w*|turkish|turkey|turkiye|turco\w*", "turkey"),
    (r"japon\w*|japan\w*|japones\w*", "japan"),
    (r"inde\b|indien\w*|indian\b|indians\b|india\b", "india"),
    (r"otan|nato|alliance atlantique", "nato"),
    (r"maison blanche|white house|casa blanca", "whitehouse"),
    (r"proche orient|moyen orient|middle east|medio oriente|oriente medio|oriente proximo", "middleeast"),
    (r"intelligence artificielle|inteligencia artificial|artificial intelligence", "aitech"),
    (r"kiev|kyiv|kiew", "kyiv"),
    (r"moscou|moscu|moscow", "moscow"),
    (r"pekin|beijing", "beijing"),
    (r"bruxelles|bruselas|brussels", "brussels"),
    (r"londres|london", "london"),
    (r"poutine|putin", "putin"),
    (r"zelensky\w*|zelenski\w*", "zelensky"),
    (r"ormuz|hormuz|ormuz", "hormuz"),
]
_ALIAS_RE = [(re.compile(r"(?<![a-z0-9])(?:" + p + r")(?![a-z0-9])"), " " + r + " ") for p, r in ALIASES]
# Sigles à reconnaître AVANT de passer en minuscules ("US" ≠ "us", "IA"/"AI" ≠ "j'ai").
_UPPER_RE = [(re.compile(r"\bU\.?S\.?(?:A\.?)?(?![\w.])"), " usa "), (re.compile(r"\b(?:AI|IA)\b"), " aitech ")]


def norm(s, aliases=True):
    """Minuscules sans accents ni ponctuation, entourées d'espaces (pour chercher des expressions)."""
    s = s or ""
    if aliases:
        for rx, rep in _UPPER_RE:
            s = rx.sub(rep, s)
    s = strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    if aliases:
        for rx, rep in _ALIAS_RE:
            s = rx.sub(rep, s)
        s = re.sub(r" +", " ", s)
    return " " + s.strip() + " "


STOP = set("""
a ai aie aient aies ait alors as au aucun aucune aupres aura aurai auraient aurais aurait aux avaient avais avait avant avec avez aviez avions avoir avons ayant bien c ca car ce ceci cela celle celles celui cependant ces cet cette ceux chaque chez ci comme comment d dans de des deja depuis dès deux devant doit donc dont du durant elle elles en encore entre es est et etaient etais etait etant ete etre eu eux fait faire fois font hors i il ils j je jusqu l la le les leur leurs lors lui m ma mais me meme memes mes moi moins mon n ne ni nos notre nous on ont ou par parce pas pendant peu peut peuvent plus plusieurs pour pourquoi qu quand que quel quelle quelles quels qui quoi sa sans se selon ses si sien soi soit son sont sous sur ta te tes toi ton tous tout toute toutes tres tu un une unes uns vers via vos votre vous y apres contre entre chez ainsi aussi autre autres celui sera seront serait seraient
nouveau nouvelle nouveaux nouvelles premier premiere premiers dernier derniere derniers ans an annee annees jour jours mois semaine heure heures fin debut veut faut dit dire selon face lundi mardi mercredi jeudi vendredi samedi dimanche janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre video videos direct live photos images comment pourquoi ce qu il faut savoir explique enquete reportage interview entretien tribune analyse info infos actu actus
the of and to in on for is are was were be been being by with as at from that this these those it its it s an or not but if then than so such can could will would should may might must has have had having do does did done he she they them their his her we our you your i me my who whom whose which what when where why how all any both each few more most other some no nor only own same too very just also into over under after before about against between through during above below up down out off again further once here there new says said say one two three first last year years day days week month time after
el la los las lo un una unos unas de del al y o u e en por para con sin sobre entre que como mas pero sus su se le les ya es son fue ser han ha hay muy tambien este esta estos estas ese esa eso esos esas aqui alli cuando donde quien quienes cual cuales porque segun tras desde hasta ante bajo durante otro otra otros otras mismo misma nuevo nueva nuevos nuevas primer primera anos ano dia dias mes semana hoy ayer manana dijo dice asi solo cada todo todos toda todas uno dos tres vivo minuto
""".split())


def tokens(text):
    """Mots significatifs (normalisés) d'un texte."""
    return [t for t in norm(text).split() if (len(t) > 2 or t in {"eu", "uk", "f1", "om", "rn", "jo"} or t.isdigit()) and t not in STOP]


CAP_RE = re.compile(r"\b(?:[A-ZÀ-ÖØ-Þ][\w'’-]{2,}|[A-Z]{2,})")


def entities(text):
    """Mots écrits avec une majuscule (noms propres, sigles…), déjà normalisés."""
    return set(tokens(" ".join(CAP_RE.findall(text or ""))))


# ---------------------------------------------------------------- thèmes

THEMES = read_json(APP / "themes.json", [])


def compile_keywords(keywords):
    """Liste de mots-clés ("mot", "expression", "prefixe*") → une regex sur texte normalisé."""
    parts = []
    for kw in keywords:
        prefix = kw.endswith("*")
        k = norm(kw.rstrip("*").replace("_", " ")).strip()
        if k:
            parts.append(re.escape(k).replace(r"\ ", " ") + (r"[a-z0-9]*" if prefix else ""))
    return re.compile(r"(?<= )(?:" + "|".join(sorted(set(parts), key=len, reverse=True)) + r")(?= )")


_THEME_RX = [(t["id"], compile_keywords(t["keywords"])) for t in THEMES]


def classify(title, summary="", hint=None, max_themes=3):
    """Renvoie les identifiants de thèmes d'un texte, du plus au moins marqué."""
    nt, ns = norm(title), norm(summary)
    scores = {}
    for tid, rx in _THEME_RX:
        s = 2 * len(rx.findall(nt)) + len(rx.findall(ns))
        if hint and tid in (hint if isinstance(hint, (list, tuple)) else [hint]):
            s += 2
        if s >= 2:
            scores[tid] = s
    return [t for t, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:max_themes]]


# ---------------------------------------------------------------- langue

LANG_WORDS = {
    "fr": set("le la les des une est dans pour pas qui sur avec que du au aux ce cette sont ont elle il nous plus par".split()),
    "en": set("the and of to is in for that with on are was by as at from this be has have will its after over".split()),
    "es": set("el la los las de del que en y por para con una un es se su al como mas lo sus fue han".split()),
}


def detect_lang(text):
    words = re.findall(r"[a-záéíóúñüàâçèêëîïôûù]+", (text or "").lower())
    counts = {lang: sum(w in vocab for w in words) for lang, vocab in LANG_WORDS.items()}
    best = max(counts, key=counts.get)
    return best if counts[best] >= 2 else None


# ---------------------------------------------------------------- similarité

def idf_table(docs):
    """docs : liste d'ensembles de mots → poids idf (mots rares = poids fort)."""
    df = {}
    for d in docs:
        for t in d:
            df[t] = df.get(t, 0) + 1
    n = max(len(docs), 1)
    return {t: math.log(1 + n / c) for t, c in df.items()}


def similarity(a, b, idf):
    """Cosinus pondéré entre deux ensembles de mots."""
    if not a or not b:
        return 0.0
    shared = a & b
    if not shared:
        return 0.0
    num = sum(idf.get(t, 1.0) for t in shared)
    da = math.sqrt(sum(idf.get(t, 1.0) for t in a))
    db = math.sqrt(sum(idf.get(t, 1.0) for t in b))
    return num / (da * db)
