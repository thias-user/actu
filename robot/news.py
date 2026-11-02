"""Collecte des articles et construction des éditions quotidiennes (app/data/days/AAAA-MM-JJ.json).

Une édition = les articles parus depuis l'édition précédente (au plus tard la veille à 10h).
Pour chaque région on garde ~10 candidats classés ; l'application en affiche 3 (selon vos centres d'intérêt).
"""
import math
import re
from datetime import datetime, time as dtime, timedelta
from urllib.parse import urlsplit, urlunsplit

import feedparser

from common import (DATA, PARIS, classify, clean_text, detect_lang, fetch, from_struct, idf_table, iso, log,
                    norm, now_paris, parallel, parse_iso, read_json, short_id, similarity, tokens, write_json)
from config import BLACKLIST, FEEDS, GEO_SETS, LIVE_MARKERS, REGION_ORDER, REGIONS

CANDIDATES_PER_REGION = 10
MAX_PER_SOURCE = 3
CUTOFF_HOUR = 10
BACKFILL_DAYS = 3
_BL = [" " + b + " " for b in BLACKLIST]


# ---------------------------------------------------------------- lecture des flux

def canonical_url(u):
    p = urlsplit(u.strip())
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", ""))


def entry_image(e):
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key) or []:
            url = m.get("url")
            if url and (m.get("medium") in (None, "image") or re.search(r"\.(jpe?g|png|webp)", url, re.I)):
                return url
    for enc in e.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return enc["href"]
    for link in e.get("links") or []:
        if (link.get("type") or "").startswith("image") and link.get("href"):
            return link["href"]
    m = re.search(r'<img[^>]+src="([^"]+)"', (e.get("summary") or "") + str(e.get("content") or ""))
    return m.group(1) if m else None


def read_feed(feed):
    raw = fetch(feed["url"], timeout=25, accept="application/rss+xml, application/xml, text/xml, */*")
    parsed = feedparser.parse(raw)
    items = []
    for e in parsed.entries:
        title = clean_text(e.get("title"), 220)
        link = e.get("link") or ""
        date = from_struct(e.get("published_parsed") or e.get("updated_parsed"))
        if not title or not link.startswith("http") or not date:
            continue
        summary = clean_text(e.get("summary") or e.get("description"), 420)
        if summary.lower().startswith(title.lower()[:60]):
            summary = summary[len(title):].strip(" -–:|") if len(summary) > len(title) + 40 else ""
        items.append({
            "title": title, "summary": summary, "url": link.strip(), "source": feed["source"], "date": date,
            "image": entry_image(e), "region": feed["region"], "weight": feed["weight"], "hint": feed["hint"],
            "geo": feed["geo"], "paywall": feed["paywall"],
        })
    return items


# ---------------------------------------------------------------- filtres

def geo_hits(ntext, words):
    toks = set(ntext.split())
    n = 0
    for w in words:
        if " " in w:
            n += (" " + w + " ") in ntext
        else:
            n += w in toks
    return n


FOREIGN = {r: set().union(*(GEO_SETS[o] for o in GEO_SETS if o != r)) - GEO_SETS[r] for r in REGIONS}


def region_fit(item):
    """True si l'article parle bien de sa région."""
    region = item["region"]
    text = norm(item["title"] + " " + item["summary"])
    own = geo_hits(text, GEO_SETS[region])
    foreign = geo_hits(text, FOREIGN[region])
    item["_france_only"] = region == "eu" and own > 0 and own == geo_hits(text, {"france", "paris", "macron"})
    if item["geo"] == "require":
        return own > 0 and foreign <= 2 * own
    return own > 0 or foreign == 0


def keep(item):
    text = norm(item["title"] + " " + item["summary"])
    if any(b in text for b in _BL):
        return False
    lang = detect_lang(item["title"] + " " + item["summary"])
    if lang and lang != REGIONS[item["region"]]["lang"]:
        return False
    return region_fit(item)


# ---------------------------------------------------------------- regroupement et score

def cluster(items):
    """Regroupe les articles qui traitent du même sujet (union-find sur la similarité des mots)."""
    sets = [set(tokens(i["title"] + " " + i["summary"][:200])) for i in items]
    idf = idf_table(sets)
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    title_sets = [set(tokens(i["title"])) for i in items]
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            if items[a]["source"] == items[b]["source"] and items[a]["url"] == items[b]["url"]:
                continue
            shared = sets[a] & sets[b]
            if len(shared) < 3:
                continue
            sim = similarity(sets[a], sets[b], idf)
            tsim = similarity(title_sets[a], title_sets[b], idf)
            if sim >= 0.42 or tsim >= 0.5:
                parent[find(a)] = find(b)
    groups = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(items[i])
    return list(groups.values())


def score(item, coverage, window_start, window_end):
    span = max((window_end - window_start).total_seconds(), 3600)
    recency = min(max((item["date"] - window_start).total_seconds() / span, 0), 1)
    s = 0.55 * min(1.0, math.log2(coverage) / 3) if coverage > 1 else 0.0
    s += 0.15 * item["weight"]
    s += 0.10 * bool(item["image"]) + 0.05 * (len(item["summary"]) > 80)
    s += 0.10 * recency
    s += 0.10 * bool(item["themes"])
    if any(m in norm(item["title"]) for m in LIVE_MARKERS):
        s -= 0.10
    if item["paywall"]:
        s -= 0.03
    if item.get("_france_only"):
        s -= 0.12
    return round(s, 3)


def select(items, window_start, window_end):
    """Garde le meilleur article de chaque sujet, puis les CANDIDATES_PER_REGION meilleurs sujets."""
    for it in items:
        it["themes"] = classify(it["title"], it["summary"], it["hint"])
    picks = []
    for group in cluster(items):
        coverage = len({g["source"] for g in group})
        for g in group:
            g["score"] = score(g, coverage, window_start, window_end)
        best = max(group, key=lambda g: (g["score"], g["weight"]))
        best["coverage"] = coverage
        best["also"] = sorted({g["source"] for g in group} - {best["source"]})
        # thèmes du meilleur article + ceux partagés par au moins deux articles du même sujet
        counts = {}
        for g in group:
            for t in g["themes"]:
                counts[t] = counts.get(t, 0) + 1
        best["themes"] = (best["themes"] + [t for t, n in sorted(counts.items(), key=lambda kv: -kv[1])
                                            if n >= 2 and t not in best["themes"]])[:3]
        picks.append(best)
    picks.sort(key=lambda p: -p["score"])
    out, per_source = [], {}
    for p in picks:
        if per_source.get(p["source"], 0) >= MAX_PER_SOURCE:
            continue
        per_source[p["source"]] = per_source.get(p["source"], 0) + 1
        out.append(p)
        if len(out) >= CANDIDATES_PER_REGION:
            break
    return out


# ---------------------------------------------------------------- images manquantes (balise og:image de la page)

OG_RE = re.compile(r'<meta[^>]+(?:property|name)=["\'](og:image|og:description|twitter:image)["\'][^>]*>', re.I)
CONTENT_RE = re.compile(r'content=["\']([^"\']+)["\']', re.I)


def enrich(item):
    if item["image"] and len(item["summary"]) > 60:
        return
    page = fetch(item["url"], timeout=12, retries=0, max_bytes=250_000).decode("utf-8", "replace")
    found = {}
    for m in OG_RE.finditer(page):
        c = CONTENT_RE.search(m.group(0))
        if c:
            found.setdefault(m.group(1).lower(), clean_text(c.group(1)))
    if not item["image"]:
        item["image"] = found.get("og:image") or found.get("twitter:image")
    if len(item["summary"]) <= 60 and found.get("og:description"):
        item["summary"] = clean_text(found["og:description"], 420)


# ---------------------------------------------------------------- éditions

def to_public(it):
    return {
        "id": short_id(canonical_url(it["url"])), "title": it["title"], "summary": it["summary"], "url": it["url"],
        "source": it["source"], "date": iso(it["date"]), "image": it["image"], "themes": it["themes"],
        "score": it["score"], "coverage": it["coverage"], "also": it["also"][:6], "paywall": it["paywall"],
        "posts": [],
    }


def day_path(d):
    return DATA / "days" / f"{d.isoformat()}.json"


def build(force_today=True):
    now = now_paris()
    today = now.date()
    log(f"Lecture de {len(FEEDS)} flux…")
    results = parallel(read_feed, FEEDS, workers=16)
    failed = [f["url"] for f, r in zip(FEEDS, results) if r is None]
    items = [i for r in results if r for i in r]
    log(f"{len(items)} articles lus ({len(FEEDS) - len(failed)}/{len(FEEDS)} flux OK)")
    if len(failed) > len(FEEDS) / 2:
        raise RuntimeError("plus de la moitié des journaux injoignables : réseau en panne ? éditions inchangées")

    # dédoublonnage par URL
    seen, uniq = set(), []
    for it in sorted(items, key=lambda i: -i["weight"]):
        key = canonical_url(it["url"])
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    items = [i for i in uniq if keep(i)]
    log(f"{len(items)} articles retenus après filtres (langue, région, rubriques inutiles)")

    def cutoff(d):
        return datetime.combine(d, dtime(CUTOFF_HOUR), PARIS)

    # éditions à (re)construire : rattrapage des jours manquants + aujourd'hui
    targets = [today - timedelta(days=k) for k in range(BACKFILL_DAYS, 0, -1) if not day_path(today - timedelta(days=k)).exists()]
    if force_today or not day_path(today).exists():
        targets.append(today)

    built = []
    for d in targets:
        prev = read_json(day_path(d - timedelta(days=1)))
        start = parse_iso(prev["cutoff"]) if prev and prev.get("cutoff") else cutoff(d - timedelta(days=1))
        start = max(start, cutoff(d - timedelta(days=1)) - timedelta(hours=12))
        end = now if d == today else cutoff(d)
        published = set()
        for k in (1, 2, 3):
            old = read_json(day_path(d - timedelta(days=k)))
            if old:
                published |= {a["url"] for r in old["regions"].values() for a in r}
        window = [i for i in items if start < i["date"] <= end and i["url"] not in published]
        regions = {}
        for reg in REGION_ORDER:
            sel = select([dict(i) for i in window if i["region"] == reg], start, end)
            parallel(enrich, sel, workers=8)
            regions[reg] = [to_public(i) for i in sel]
        counts = {r: len(v) for r, v in regions.items()}
        if sum(counts.values()) == 0:
            log(f"Édition {d} : aucun article dans la fenêtre, ignorée")
            continue
        edition = {"date": d.isoformat(), "cutoff": iso(end), "built": iso(now), "regions": regions}
        old = read_json(day_path(d))
        if old:  # on garde les publications déjà trouvées pour les articles inchangés
            old_posts = {a["id"]: a.get("posts", []) for r in old["regions"].values() for a in r}
            for r in regions.values():
                for a in r:
                    a["posts"] = old_posts.get(a["id"], [])
        write_json(day_path(d), edition)
        built.append(d)
        log(f"Édition {d} ({start:%d/%m %H:%M} → {end:%d/%m %H:%M}) : {counts}")
    return built, failed
