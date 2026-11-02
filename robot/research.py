"""Sélection trimestrielle d'articles de recherche par thème (OpenAlex, HAL, Crossref) → app/data/research.json.

OpenAlex fonctionne sans clé (quota gratuit partagé). Pour un quota personnel gratuit, créez une clé sur
https://openalex.org/settings/api et enregistrez-la dans le secret GitHub OPENALEX_API_KEY.
"""
import os
import time
from datetime import date, timedelta
from urllib.parse import quote

from common import DATA, THEMES, clean_text, fetch_json, iso, log, norm, now_paris, read_json, write_json
from config import RESEARCH_QUERIES

OA_FIELDS = "id,display_name,publication_year,authorships,primary_location,cited_by_count,doi,open_access,language,abstract_inverted_index"
OA_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()


def quarter(d):
    return f"{d.year}-T{(d.month - 1) // 3 + 1}"


def next_quarter_start(d):
    m = ((d.month - 1) // 3 + 1) * 3 + 1
    return date(d.year + (m > 12), (m - 1) % 12 + 1, 1)


def abstract(inv):
    if not inv:
        return ""
    words = sorted((p, w) for w, ps in inv.items() for p in ps)
    return clean_text(" ".join(w for _, w in words), 420)


def authors(names):
    names = [n for n in names if n]
    return ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")


def openalex(title_terms, flt, n):
    """Articles dont le TITRE contient l'un des termes ("a|b"), du plus cité au moins cité."""
    url = (f"https://api.openalex.org/works?filter=title.search:{quote(title_terms)},{flt}&sort=cited_by_count:desc"
           f"&per_page={n}&select={OA_FIELDS}" + (f"&api_key={OA_KEY}" if OA_KEY else ""))
    time.sleep(0.6)  # politesse envers l'API gratuite
    out = []
    for w in fetch_json(url, timeout=30).get("results", []):
        loc = w.get("primary_location") or {}
        oa = w.get("open_access") or {}
        out.append({
            "title": clean_text(w.get("display_name"), 260),
            "authors": authors([a.get("author", {}).get("display_name") for a in w.get("authorships", [])]),
            "year": w.get("publication_year"), "venue": (loc.get("source") or {}).get("display_name"),
            "cited": w.get("cited_by_count"), "url": w.get("doi") or loc.get("landing_page_url") or w.get("id"),
            "pdf": oa.get("oa_url"), "lang": w.get("language"), "abstract": abstract(w.get("abstract_inverted_index")),
            "src": "OpenAlex",
        })
    return out


def hal(title_terms, n, since):
    """Archive ouverte française HAL : articles récents dont le titre contient l'un des termes."""
    terms = " OR ".join(f'"{t}"' if " " in t else t for t in title_terms.split("|"))
    q = f"title_t:({terms}) AND producedDateY_i:[{since} TO {now_paris().year}]"
    url = (f"https://api.archives-ouvertes.fr/search/?q={quote(q)}&wt=json&rows={n}&fq=docType_s:ART"
           f"&sort=producedDate_tdate%20desc&fl=title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,doiId_s,abstract_s,fileMain_s,language_s")
    out = []
    for d in fetch_json(url, timeout=30).get("response", {}).get("docs", []):
        out.append({
            "title": clean_text((d.get("title_s") or [""])[0], 260), "authors": authors(d.get("authFullName_s") or []),
            "year": d.get("producedDateY_i"), "venue": d.get("journalTitle_s"), "cited": None,
            "url": ("https://doi.org/" + d["doiId_s"]) if d.get("doiId_s") else d.get("uri_s"), "pdf": d.get("fileMain_s"),
            "lang": (d.get("language_s") or [None])[0], "abstract": clean_text((d.get("abstract_s") or [""])[0], 420),
            "src": "HAL",
        })
    return out


def crossref(title_terms, n):
    """Secours si OpenAlex est indisponible : on ne garde que les titres contenant vraiment l'un des termes."""
    terms = [norm(t, aliases=False) for t in title_terms.split("|")]
    url = (f"https://api.crossref.org/works?query.title={quote(title_terms.replace('|', ' '))}&rows=60"
           f"&filter=type:journal-article&select=title,author,issued,container-title,is-referenced-by-count,DOI,abstract")
    items = [w for w in fetch_json(url, timeout=30).get("message", {}).get("items", [])
             if any(t in norm((w.get("title") or [""])[0], aliases=False) for t in terms)]
    items.sort(key=lambda w: -(w.get("is-referenced-by-count") or 0))
    out = []
    for w in items[:n]:
        out.append({
            "title": clean_text((w.get("title") or [""])[0], 260),
            "authors": authors([" ".join(filter(None, [a.get("given"), a.get("family")])) for a in w.get("author", [])]),
            "year": ((w.get("issued") or {}).get("date-parts") or [[None]])[0][0], "venue": (w.get("container-title") or [None])[0],
            "cited": w.get("is-referenced-by-count"), "url": "https://doi.org/" + w["DOI"], "pdf": None,
            "lang": None, "abstract": clean_text(w.get("abstract"), 420), "src": "Crossref",
        })
    return out


def for_theme(tid, en, fr, previous):
    today = now_paris().date()
    recent = (today - timedelta(days=3 * 365)).isoformat()
    groups = []
    try:
        groups.append(("Les classiques", openalex(en, "type:article", 5)))
        groups.append(("Récents et très cités", openalex(en, f"type:article,from_publication_date:{recent}", 5)))
        groups.append(("En français", openalex(fr, "type:article,language:fr,from_publication_date:1990-01-01", 4)))
    except Exception as e:
        log(f"  ! OpenAlex ({tid}) : {e} → Crossref")
        try:
            groups = [("Les plus cités", crossref(en, 8))]
        except Exception as e2:
            log(f"  ! Crossref ({tid}) : {e2} → sélection précédente conservée")
            if previous:
                return previous
    try:
        groups.append(("Nouveautés françaises (HAL)", hal(fr, 4, today.year - 3)))
    except Exception as e:
        log(f"  ! HAL ({tid}) : {e}")
    seen, out = set(), []
    for label, papers in groups:
        for p in papers:
            key = (p["title"] or "").lower()[:80]
            if p["title"] and key not in seen and (p["year"] or 0) <= today.year:
                seen.add(key)
                out.append(dict(p, group=label))
    return out


def update(force=False):
    path = DATA / "research.json"
    old = read_json(path) or {}
    today = now_paris().date()
    if old and not force and old.get("quarter") == quarter(today):
        return False
    themes = {}
    for t in THEMES:
        q = RESEARCH_QUERIES.get(t["id"])
        if q:
            themes[t["id"]] = for_theme(t["id"], *q, old.get("themes", {}).get(t["id"]))
    if sum(map(len, themes.values())) < 3 * len(themes):
        log("Recherche : trop peu de données récupérées, ancienne sélection conservée")
        return False
    write_json(path, {"updated": iso(now_paris()), "quarter": quarter(today),
                      "next": next_quarter_start(today).isoformat(), "themes": themes})
    log(f"Recherche : {sum(len(v) for v in themes.values())} publications sélectionnées pour {len(themes)} thèmes")
    return True
