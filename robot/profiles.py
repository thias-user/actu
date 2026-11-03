"""Le pays en bref : environnement politique, économique et social du lieu de l'article (case « Pour comprendre »).

Gratuit et sans clé :
  - Banque mondiale (api.worldbank.org) : niveau de vie, croissance, inflation, chômage, population, inégalités ;
    un seul téléchargement par semaine pour tous les pays ;
  - Wikidata (pages Special:EntityData, ouvertes aux robots) : régime, chefs de l'État et du gouvernement, partis.
Les réponses sont gardées 7 jours dans robot/state/profiles.json ; le résultat, public, va dans app/data/profiles.json.
"""
import json
from datetime import date

from common import DATA, STATE, fetch, log, parallel, read_json, write_json

CACHE_PATH = STATE / "profiles.json"
TTL = 7
# pays du schéma → élément Wikidata (vérifié par son code ISO, propriété P297)
QID = {"ar": "Q414", "be": "Q31", "bg": "Q219", "br": "Q155", "ca": "Q16", "cl": "Q298", "cn": "Q148", "co": "Q739", "cu": "Q241",
       "de": "Q183", "es": "Q29", "eu": "Q458", "fr": "Q142", "gb": "Q145", "ie": "Q27", "il": "Q801", "in": "Q668", "ir": "Q794",
       "it": "Q38", "jp": "Q17", "lb": "Q822", "mx": "Q96", "nl": "Q55", "pe": "Q419", "pl": "Q36", "ps": "Q219060", "ru": "Q159",
       "se": "Q34", "tr": "Q43", "ua": "Q212", "us": "Q30", "ve": "Q717"}
NAMES = {"ar": "l’Argentine", "be": "la Belgique", "bg": "la Bulgarie", "br": "le Brésil", "ca": "le Canada", "cl": "le Chili",
         "cn": "la Chine", "co": "la Colombie", "cu": "Cuba", "de": "l’Allemagne", "es": "l’Espagne", "eu": "l’Union européenne",
         "fr": "la France", "gb": "le Royaume-Uni", "ie": "l’Irlande", "il": "Israël", "in": "l’Inde", "ir": "l’Iran", "it": "l’Italie",
         "jp": "le Japon", "lb": "le Liban", "mx": "le Mexique", "nl": "les Pays-Bas", "pe": "le Pérou", "pl": "la Pologne",
         "ps": "la Palestine", "ru": "la Russie", "se": "la Suède", "tr": "la Turquie", "ua": "l’Ukraine", "us": "les États-Unis",
         "ve": "le Venezuela"}
EU_MEMBERS = {"be", "bg", "de", "es", "fr", "ie", "it", "nl", "pl", "se"}
LATAM = {"ar", "br", "cl", "co", "cu", "mx", "pe", "ve"}
IND = {"NY.GDP.PCAP.CD": "pib", "NY.GDP.MKTP.KD.ZG": "croissance", "FP.CPI.TOTL.ZG": "inflation", "SL.UEM.TOTL.ZS": "chomage",
       "SL.UEM.1524.ZS": "jeunes", "SP.POP.TOTL": "population", "SI.POV.GINI": "gini"}
WB_URL = ("https://api.worldbank.org/v2/country/all/indicator/" + ";".join(IND) +
          "?source=2&format=json&mrv=7&per_page=20000")
MONTHS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()


# ---------------------------------------------------------------- téléchargements

def world_bank():
    """{code ISO à 2 lettres (et agrégats WLD, EUU, LCN) : {indicateur : [[année, valeur], …] du plus récent au plus ancien]}}"""
    data = json.loads(fetch(WB_URL, timeout=90))
    out = {}
    for r in data[1] if len(data) > 1 else []:
        if r.get("value") is None:
            continue
        ind = IND.get(r["indicator"]["id"])
        for code in {r["country"]["id"].lower(), (r.get("countryiso3code") or "").lower()} - {""}:
            out.setdefault(code, {}).setdefault(ind, []).append([int(r["date"]), r["value"]])
    for series in out.values():
        for s in series.values():
            s.sort(reverse=True)
    return out


def entity(qid):
    e = json.loads(fetch(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", timeout=40))["entities"]
    return next(iter(e.values()))


def label(e):
    labels = e.get("labels") or {}
    for lang in ("fr", "mul", "en", "es"):
        if lang in labels:
            return labels[lang]["value"]
    return next((v["value"] for v in labels.values()), "")


def _time(claim, prop):
    for q in (claim.get("qualifiers") or {}).get(prop, []):
        v = (q.get("datavalue") or {}).get("value") or {}
        if v.get("time"):
            return v["time"].lstrip("+")[:10]
    return ""


def current(e, prop):
    """Valeur actuelle d'une propriété (sans date de fin), la plus récente : (élément, début)."""
    today = date.today().isoformat()
    best = None
    for c in (e.get("claims") or {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        end = _time(c, "P582")
        if end and end < today:
            continue
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if not isinstance(v, dict) or not v.get("id"):
            continue
        key = (c.get("rank") == "preferred", _time(c, "P580"))
        if not best or key > best[0]:
            best = (key, v["id"], key[1])
    return (best[1], best[2]) if best else (None, "")


def starts(e, prop):
    return sorted(s for c in (e.get("claims") or {}).get(prop, []) if (s := _time(c, "P580")))


def politics(code):
    """Régime, chefs de l'État et du gouvernement (avec leur parti), nombre de chefs du gouvernement en deux ans."""
    e = entity(QID[code])
    iso = [((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") for c in e["claims"].get("P297", [])]
    if code != "eu" and code.upper() not in iso:
        raise ValueError(f"{QID[code]} n'est pas {code}")
    out = {}
    gov, _ = current(e, "P122")
    if gov:
        out["regime"] = label(entity(gov))
    people = {}
    for role, prop in (("etat", "P35"), ("gouv", "P6")):
        who, since = current(e, prop)
        if not who and role == "gouv":  # Union européenne : la présidence de la Commission
            office, _ = current(e, "P1313")
            if office:
                who, since = current(entity(office), "P1308")
                out["gouv_titre"] = label(entity(office))
        if who:
            if who not in people:
                p = entity(who)
                party, _ = current(p, "P102")
                people[who] = {"nom": label(p), "parti": label(entity(party)) if party else ""}
            out[role] = {**people[who], "depuis": since}
    two_years_ago = date.fromordinal(date.today().toordinal() - 730).isoformat()
    out["gouv_recents"] = sum(s >= two_years_ago for s in starts(e, "P6"))
    return out


# ---------------------------------------------------------------- mise en mots

def num(x, digits=1):
    s = f"{x:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s[:-2] if digits == 1 and s.endswith(",0") else s


def money(x):
    return num(round(x, -1 if x < 10000 else -2), 0) + " $"


def people_count(x):
    if x >= 1e9:
        return f"{num(x / 1e9, 2)} milliards d’habitants"
    if x >= 1e6:
        return f"{num(x / 1e6, 1)} millions d’habitants"
    return f"{num(x, 0)} habitants"


def since(iso):
    if not iso or len(iso) < 7:
        return ""
    y, m = iso[:4], int(iso[5:7] or 0)
    return f"depuis {MONTHS[m - 1]} {y}" if m else f"depuis {y}"


def latest(series, key):
    s = series.get(key) or []
    return s[0] if s else None


def level(value, steps):
    for limit, word in steps:
        if value < limit:
            return word
    return steps[-1][1]


def build(code, wb, pol):
    me = wb.get("eu" if code == "eu" else code) or {}
    if code == "eu":
        group, gname = wb.get("wld", {}), "moyenne mondiale"
    elif code in EU_MEMBERS:
        group, gname = wb.get("euu", {}), "moyenne de l’UE"
    elif code in LATAM:
        group, gname = wb.get("lcn", {}), "moyenne de l’Amérique latine"
    else:
        group, gname = wb.get("wld", {}), "moyenne mondiale"
    v = {k: latest(me, k) for k in IND.values()}
    p = {"code": code, "nom": NAMES.get(code, ""), "lignes": [], "classes": {}, "valeurs": {}}
    # pouvoir
    if pol:
        parts = []
        if pol.get("regime"):
            parts.append(pol["regime"][0].upper() + pol["regime"][1:] + ".")
        st, gv = pol.get("etat"), pol.get("gouv")
        def who(x):
            return x["nom"] + (f" ({x['parti']})" if x.get("parti") else "")
        if st and gv and st["nom"] == gv["nom"]:
            parts.append(f"Chef de l’État et du gouvernement : {who(st)}, {since(st['depuis'])}.".replace(", .", "."))
        else:
            if st:
                parts.append(f"Chef de l’État : {who(st)}, {since(st['depuis'])}.".replace(", .", "."))
            if gv:
                title = pol.get("gouv_titre") or "Chef du gouvernement"
                parts.append(f"{title[0].upper() + title[1:]} : {who(gv)}, {since(gv['depuis'])}.".replace(", .", "."))
        n = pol.get("gouv_recents", 0)
        if n >= 3:
            parts.append(f"{n} chefs du gouvernement se sont succédé en deux ans : forte instabilité politique.")
            p["classes"]["instable"] = True
        if parts:
            p["lignes"].append({"k": "pouvoir", "t": " ".join(parts)})
        if gv or st:
            p["valeurs"]["chef"] = (gv or st)["nom"]
    # économie
    eco = []
    if v["pib"]:
        y, x = v["pib"]
        g = latest(group, "pib")
        ratio = x / g[1] if g else None
        comp = f" ({gname} : {money(g[1])})" if g else ""
        eco.append(f"Niveau de vie : {money(x)} de PIB par habitant en {y}{comp}.")
        kind = "ensemble" if code == "eu" else "pays"
        p["classes"]["revenu"] = level(x, [(1200, f"{kind} à faible revenu"), (4600, f"{kind} à revenu intermédiaire, tranche basse"),
                                            (14000, f"{kind} à revenu intermédiaire, tranche haute"), (1e12, f"{kind} à haut revenu")])
        if ratio:
            p["classes"]["rang"] = level(ratio, [(0.8, f"sous la {gname}"), (1.25, f"proche de la {gname}"), (1e9, f"au-dessus de la {gname}")])
    if v["croissance"]:
        y, x = v["croissance"]
        eco.append(f"Croissance : {num(x)} % en {y}.")
        p["classes"]["croissance"] = level(x, [(0, "en récession"), (1.5, "à croissance faible"), (4, "à croissance modérée"), (1e9, "à croissance forte")])
        p["valeurs"]["croissance"] = f"{num(x)} % en {y}"
    if v["inflation"]:
        y, x = v["inflation"]
        prev = next((s for s in me.get("inflation", []) if s[0] <= y - 2), None)
        trend = ""
        if prev and abs(prev[1] - x) >= 1.5:
            trend = f", {'en recul' if x < prev[1] else 'en hausse'} par rapport à {prev[0]} ({num(prev[1])} %)"
        eco.append(f"Inflation : {num(x)} % en {y}{trend}.")
        p["classes"]["inflation"] = level(x, [(0, "des prix en baisse"), (3, "des prix stables"), (6, "une inflation modérée"),
                                              (15, "une inflation élevée"), (1e9, "une très forte inflation")])
        p["valeurs"]["inflation"] = f"{num(x)} % en {y}"
        p["valeurs"]["inflation_n"] = x
    if v["chomage"]:
        y, x = v["chomage"]
        young = f" ; {num(v['jeunes'][1])} % chez les 15-24 ans" if v["jeunes"] and v["jeunes"][0] == y else ""
        eco.append(f"Chômage : {num(x)} % en {y}{young}.")
        p["classes"]["chomage"] = level(x, [(4, "un quasi plein emploi"), (8, "un chômage modéré"), (12, "un chômage élevé"), (1e9, "un chômage très élevé")])
        p["valeurs"]["chomage"] = f"{num(x)} % en {y}"
        p["valeurs"]["chomage_n"] = x
    if eco:
        p["lignes"].append({"k": "economie", "t": " ".join(eco)})
    # société
    soc = []
    if v["population"]:
        soc.append(people_count(v["population"][1]) + f" ({v['population'][0]}).")
    if v["gini"]:
        y, x = v["gini"]
        word = level(x, [(30, "faibles"), (40, "moyennes"), (50, "fortes"), (1e9, "très fortes")])
        soc.append(f"Inégalités de revenus {word} (indice de Gini : {num(x)} en {y}, de 0 = égalité parfaite à 100).")
        p["classes"]["inegalites"] = f"des inégalités {word}"
    if soc:
        p["lignes"].append({"k": "societe", "t": " ".join(soc)})
    # lecture d'ensemble
    c = p["classes"]
    bits = [c["croissance"]] if c.get("croissance") else []
    traits = [x for x in (c.get("inflation"), c.get("chomage"), c.get("inegalites")) if x]
    if c.get("revenu") or bits or traits:
        head = ", ".join(x for x in (c.get("revenu") or "économie", c.get("rang"), bits[0] if bits else "") if x)
        head = head[0].upper() + head[1:]
        tail = ", avec " + ", ".join(traits[:-1]) + (" et " if len(traits) > 1 else "") + traits[-1] if traits else ""
        p["lignes"].append({"k": "lecture", "t": f"{head}{tail}."})
    years = sorted({s[0] for s in v.values() if s})
    p["sources"] = "Banque mondiale" + (f" ({years[-1]})" if years else "") + (", Wikidata" if pol else "")
    return p if p["lignes"] else None


# ---------------------------------------------------------------- cache et publication

class Profiles:
    def __init__(self):
        self.cache = read_json(CACHE_PATH, {})
        self.today = date.today().toordinal()
        self.built = {}

    def _fresh(self, key):
        hit = self.cache.get(key)
        return hit if hit and self.today - hit["at"] < TTL else None

    def prepare(self, codes):
        """Télécharge ce qui manque (Banque mondiale une fois, Wikidata pour les pays demandés)."""
        codes = [c for c in dict.fromkeys(codes) if c in QID]
        if not self._fresh("wb"):
            try:
                self.cache["wb"] = {"at": self.today, "v": world_bank()}
            except Exception as e:
                log(f"  Banque mondiale injoignable : {type(e).__name__}")
        todo = [c for c in codes if not self._fresh("wd|" + c)]

        def one(c):
            return c, politics(c)
        for r in parallel(one, todo, workers=3):
            if r:
                self.cache["wd|" + r[0]] = {"at": self.today, "v": r[1]}
        wb = (self.cache.get("wb") or {}).get("v") or {}
        for c in codes:
            pol = (self.cache.get("wd|" + c) or {}).get("v")
            try:
                self.built[c] = build(c, wb, pol)
            except Exception as e:
                log(f"  Profil {c} impossible : {type(e).__name__} {str(e)[:60]}")
                self.built[c] = None

    def get(self, code):
        return self.built.get(code)

    def save(self):
        STATE.mkdir(parents=True, exist_ok=True)
        keep = {k: v for k, v in self.cache.items() if self.today - v["at"] < 30}
        write_json(CACHE_PATH, keep)
        public = {c: {k: p[k] for k in ("code", "nom", "lignes", "sources")} for c, p in self.built.items() if p}
        old = read_json(DATA / "profiles.json", {})
        merged = {**old.get("pays", {}), **public}
        if merged != old.get("pays"):
            write_json(DATA / "profiles.json", {"maj": date.today().isoformat(), "pays": merged})
        log(f"  Pays en bref : {len(public)} profils ({', '.join(sorted(public))})")
