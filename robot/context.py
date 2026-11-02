"""Contexte des schémas « En un coup d'œil » : fiches Wikipédia (acteurs, lieu, sujet) et articles liés des jours précédents.

Gratuit et sans clé : l'API publique de Wikipédia, interrogée avec un identifiant de robot honnête et sans excès
(3 requêtes à la fois). Les réponses sont gardées 30 jours dans robot/state/wiki.json : chaque matin, seuls les
nouveaux noms sont demandés. Les fiches sont lues en français ; à défaut, dans la langue de l'article.
"""
import re
import threading
from difflib import SequenceMatcher
import urllib.parse
from datetime import date

from common import STATE, fetch_json, idf_table, log, norm, read_json, similarity, tokens, write_json

CACHE_PATH = STATE / "wiki.json"
TTL = {True: 30, False: 7}  # jours de validité d'une réponse (trouvée / introuvable)
WIKI_LANG = {"fr": "fr", "eu": "en", "us": "en", "latam": "es"}
PROPS = {"prop": "description|extracts|pageprops|langlinks|pageimages|info", "exintro": "1", "explaintext": "1", "exsentences": "3",
         "exlimit": "max", "ppprop": "disambiguation", "lllang": "fr", "lllimit": "max", "piprop": "thumbnail", "pithumbsize": "160",
         "pilimit": "max", "inprop": "url"}
INVISIBLE = re.compile(r"[​‎‏﻿­]")
NOISY_PAREN = re.compile(r"\s*\((?:[^()]|\([^()]*\))*[\d/;:ˈ](?:[^()]|\([^()]*\))*\)")  # (dates, prononciation…)
SENT_END = re.compile(r"(?<=[a-zà-ÿ\)»\d]{2}[.!?])\s+(?=[A-ZÀ-ÖØ-Þ«\"])")
RELATED_DAYS = 14
RELATED_MIN = 0.17  # en dessous, des sujets seulement voisins


def clean(text, n=280, sentences=2):
    text = INVISIBLE.sub("", text or "")
    text = NOISY_PAREN.sub("", text).replace(" ,", ",").replace("  ", " ")
    text = text.split("\n")[0].strip()
    parts = SENT_END.split(text)
    out = " ".join(parts[:sentences])
    if len(out) > n:
        out = out[:n]
        out = out[:out.rfind(" ")].rstrip(",;:") + "…"
    return out


class Wiki:
    def __init__(self):
        self.cache = read_json(CACHE_PATH, {})
        self.lock = threading.Lock()
        self.today = date.today().toordinal()
        self.calls = self.errors = 0

    def save(self):
        keep = {k: v for k, v in self.cache.items() if self.today - v["at"] < TTL[bool(v["v"])]}
        STATE.mkdir(parents=True, exist_ok=True)
        write_json(CACHE_PATH, keep)

    def _cached(self, key, fn):
        with self.lock:
            hit = self.cache.get(key)
        if hit and self.today - hit["at"] < TTL[bool(hit["v"])]:
            return hit["v"]
        if self.errors > 25:  # Wikipédia injoignable : on n'insiste pas
            return None
        try:
            value = fn()
        except Exception:
            with self.lock:
                self.errors += 1
            return None
        with self.lock:
            self.calls += 1
            self.cache[key] = {"at": self.today, "v": value}
        return value

    @staticmethod
    def _pages(lang, params):
        params = {"action": "query", "format": "json", "formatversion": "2", "redirects": "1", **PROPS, **params}
        data = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params), timeout=15)
        return (data.get("query") or {}).get("pages") or []

    @staticmethod
    def _card(p, lang):
        img = (p.get("thumbnail") or {}).get("source", "").split("?")[0]
        fr = next((l["title"] for l in p.get("langlinks") or [] if l.get("lang") == "fr"), "")
        return {"t": p["title"], "d": INVISIBLE.sub("", p.get("description", "")), "x": INVISIBLE.sub("", p.get("extract", ""))[:900],
                "img": img, "u": p.get("canonicalurl") or p.get("fullurl", ""), "l": lang, "fr": fr}

    def candidates(self, query, lang):
        """Jusqu'à 5 pages trouvées par la recherche de Wikipédia (sans les pages d'homonymie)."""
        def run():
            pages = self._pages(lang, {"generator": "search", "gsrsearch": query, "gsrlimit": "5", "gsrnamespace": "0"})
            pages = sorted(pages, key=lambda p: p.get("index", 99))
            return [self._card(p, lang) for p in pages if "disambiguation" not in (p.get("pageprops") or {}) and p.get("extract")]
        return self._cached(f"s|{lang}|{query}", run) or []

    def french(self, card):
        """La même fiche en français quand elle existe."""
        if not card or card["l"] == "fr" or not card["fr"]:
            return card
        def run():
            pages = self._pages("fr", {"titles": card["fr"]})
            return self._card(pages[0], "fr") if pages and pages[0].get("extract") else None
        return self._cached(f"t|fr|{card['fr']}", run) or card


TITLE_PAREN = re.compile(r"\s*\([^()]*\)\s*$")


def public(card, n=280):
    """Ce que l'application affiche d'une fiche."""
    if not card:
        return None
    return {"t": TITLE_PAREN.sub("", card["t"]), "d": card["d"][:90], "x": clean(card["x"], n), "img": card["img"], "u": card["u"], "l": card["l"]}


def ctx_overlap(card, ctx, skip):
    page = set(tokens(card["d"] + " " + card["x"][:500])) - skip
    return len(page & ctx)


def stems(words):
    """Début des mots : « cyberattack » et « cyberattacks », « élection » et « élections » se rejoignent."""
    return {w[:6] for w in words if not w.isdigit()}


BIRTH = re.compile(r"\b(né|née|born|nacid[oa]|naci[óo])\b|\([^()]*\b(1[89]|20)\d\d\b[^()]*\)", re.I)
YEAR = re.compile(r"\b(?:1[89]|20)\d\d\b")


def person(wiki, actor, lang, ctx):
    """Fiche d'une personne ou d'une organisation citée."""
    name = actor["name"]
    words = [w for w in norm(name).split() if len(w) > 1]
    if not words:
        return None
    acro = name.isupper() and len(name) <= 6
    best, best_score = None, 0.0
    for i, c in enumerate(wiki.candidates(name, lang)):
        title = norm(TITLE_PAREN.sub("", c["t"])).split()
        overlap = ctx_overlap(c, ctx, set(words))
        if acro:
            if name not in c["x"][:400]:  # « L'Organisation du traité de l'Atlantique nord (OTAN) »
                continue
        elif len(words) == 1:
            # un nom seul (« Kast ») : le nom de famille d'une personne (date de naissance), avec deux indices communs
            if not title or title[-1] != words[0] or len(title) > 4 or overlap < 2 or not BIRTH.search(c["x"][:300]):
                continue
        elif not all(w in title for w in words):
            # orthographes voisines (« Yotova » / « Iotova ») : même nom à une ou deux lettres près
            if SequenceMatcher(None, " ".join(words), " ".join(title)).ratio() < 0.84:
                continue
        elif len(title) > len(words) + 2:
            continue  # « Zona Militar » ≠ « Zona Militar de Comodoro Rivadavia »
        score = 1 + min(overlap, 6) - 0.4 * i - (1.5 if "(" in c["t"] else 0) + (1 if norm(c["t"]).strip() == norm(name).strip() else 0)
        if score > best_score:
            best, best_score = c, score
    return wiki.french(best)


def place(wiki, city, lang):
    if not city:
        return None
    key = norm(city).strip()
    for c in wiki.candidates(city, "fr")[:3] or wiki.candidates(city, lang)[:3]:
        if norm(c["t"]).strip().startswith(key):
            return wiki.french(c)
    return None


def topic(wiki, a, lang, ctx, idf, skip_titles, years, text, names=()):
    """Une page qui explique le sujet (conflit, élection, accident, entreprise…), vérifiée contre l'article :
    son titre se retrouve dans l'article, son résumé partage des mots rares avec le titre, et pas d'autre année."""
    ranked = sorted(dict.fromkeys(tokens(a["title"])), key=lambda t: -idf.get(t, 5))
    words = [t for t in ranked if not t.isdigit()][:4]
    if len(words) < 2:
        return None
    ctx_st = stems(ctx)
    rare = stems(t for t in tokens(a["title"] + " " + a.get("summary", "")) if idf.get(t, 5) >= 3)
    for query in dict.fromkeys((" ".join(words), " ".join(words[:3]))):
        for c in wiki.candidates(query, lang)[:4]:
            title = norm(TITLE_PAREN.sub("", c["t"])).strip()
            if title in skip_titles or (c["fr"] and norm(c["fr"]).strip() in skip_titles) or                     any(" " in t and t in title for t in skip_titles if t not in names):
                continue  # déjà présenté (un acteur, le lieu, « Palmarès de Novak Djokovic »)
            if set(YEAR.findall(c["t"])) - years:
                continue  # « Élection présidentielle de 2015 » pour un article de 2026
            if any(n not in ctx for n in tokens(c["t"]) if n.isdigit() and not YEAR.fullmatch(n)):
                continue  # « Learjet 23 » quand l'article parle d'un Learjet 60
            tw = [w for w in tokens(title) if not w.isdigit()]
            hits = sum(w[:6] in ctx_st for w in tw)
            if not tw or hits / len(tw) < 0.5 or (len(tw) > 1 and hits < 2):
                continue
            plain = TITLE_PAREN.sub("", c["t"])
            if len(tw) == 2 and plain.istitle() and title not in norm(text):
                continue  # « Kevin Murray » pour un article qui cite Kevin Hassett et Bill Murray
            if len(tw) == 1 and not re.search(r"" + re.escape(c["t"]) + r"", text):
                continue  # un seul mot : un nom propre écrit tel quel dans l'article (« CNews »), pas « Pompier »
            if BIRTH.search(c["x"][:300]) and not all(w in ctx for w in tw):
                continue  # une personne : son nom complet doit figurer dans l'article
            if len(stems(tokens(c["x"][:600])) & rare) < 2:
                continue
            return wiki.french(c)
    return None


def related(pool, a, d, idf):
    """Articles proches des autres jours (avant comme après) et des autres sources le même jour : la même histoire,
    dans l'ordre chronologique."""
    me = set(tokens(a["title"] + " " + a.get("summary", "")))
    out = []
    for when, region, b, bset in pool:
        if b["id"] == a["id"] or (when == d and b["source"] == a["source"]):
            continue
        s = similarity(me, bset, idf)
        if s >= RELATED_MIN:
            out.append((when, s, region, b))
    out.sort(key=lambda x: x[1], reverse=True)
    seen, res = set(), []
    for when, s, region, b in out:
        key = norm(b["title"])[:60]
        if key in seen:
            continue
        seen.add(key)
        res.append({"d": when.isoformat(), "t": b["title"][:140], "s": b["source"], "id": b["id"], "r": region})
        if len(res) == 3:
            break
    return sorted(res, key=lambda r: r["d"])


def build_pool(editions):
    """editions : [(date, édition)] → articles avec leurs mots, et poids idf communs."""
    pool = []
    for when, ed in editions:
        for region, arts in ed["regions"].items():
            for b in arts:
                pool.append((when, region, b, set(tokens(b["title"] + " " + b.get("summary", "")))))
    return pool, idf_table([p[3] for p in pool])


def prune_actors(story):
    """Un mot seul sans fiche (« Musée », « Route »…) n'est sans doute pas un acteur : on l'enlève s'il reste quelqu'un."""
    actors = story["actors"]
    keep = [i for i, x in enumerate(actors) if x.get("wiki") or x.get("group") or x.get("kind") in ("pays", "org") or len(x["name"].split()) > 1]
    if not keep or len(keep) == len(actors):
        return
    new = {old: k for k, old in enumerate(keep)}
    story["actors"] = [actors[i] for i in keep]
    story["links"] = [{**l, "from": new[l["from"]], "to": new[l["to"]]} for l in story["links"] if l["from"] in new and l["to"] in new]
    act = story["action"]
    act["who"] = new.get(act["who"], 0)
    act["target"] = new.get(act["target"], -1) if act["target"] >= 0 else -1


def enrich(wiki, story, a, region, sents, pool, idf, d):
    """Ajoute au scénario : fiches des acteurs, du lieu, du sujet, et les articles liés."""
    lang = WIKI_LANG.get(region, "fr")
    text = a["title"] + " " + a.get("summary", "") + " " + " ".join(sents[:25])
    ctx = set(tokens(text))
    skip = set()
    for act in story["actors"]:
        if act.get("kind") == "pays" or act.get("group"):
            continue
        card = person(wiki, act, lang, ctx)
        if card:
            act["wiki"] = public(card, 240)
            skip.add(norm(act["wiki"]["t"]).strip())
        skip.add(norm(act["name"]).strip())
    prune_actors(story)
    city = story["place"].get("city")
    if city:
        card = place(wiki, city.title(), lang)
        if card:
            story["place"]["wiki"] = public(card, 200)
            skip.add(norm(card["t"]).strip())
    skip |= {norm(n).strip() for n in (story["place"].get("label", ""),)}
    names = {norm(x["name"]).strip() for x in story["actors"]}
    card = topic(wiki, a, lang, ctx, idf, skip, set(YEAR.findall(text)) | {str(d.year)}, text, names)
    story["context"] = public(card, 320)
    story["related"] = related(pool, a, d, idf)
    story["sources"] = [a["source"]] + list(a.get("also", []))[:4]
    return story


def report(wiki, n):
    log(f"  Contexte Wikipédia : {n} articles, {wiki.calls} requêtes, {wiki.errors} erreurs")
