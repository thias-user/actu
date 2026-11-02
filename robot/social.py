"""Publications des médias et créateurs (YouTube, Bluesky) rattachées aux articles qu'elles commentent."""
import re
from datetime import timedelta
from urllib.parse import quote

import feedparser

from common import (STATE, clean_text, entities, fetch, fetch_json, from_struct, idf_table, iso, log, now_paris,
                    parallel, parse_iso, read_json, similarity, tokens, write_json)
from config import BLUESKY, REGIONS, YOUTUBE_NEWS
from news import canonical_url, day_path

KEEP_DAYS = 5
LIVE_RE = re.compile(r"24/7|24h/24|en continu|live stream|\ben vivo 24|🔴\s*(?:live|direct)", re.I)


def read_youtube(channel):
    name, cid, lang = channel
    f = feedparser.parse(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", timeout=20))
    out = []
    for e in f.entries:
        vid = e.get("yt_videoid")
        title = clean_text(e.get("title"))
        if not vid or not title or LIVE_RE.search(title):
            continue
        out.append({
            "kind": "yt", "key": "yt:" + vid, "id": vid, "title": title, "text": clean_text(e.get("summary"), 400),
            "author": name, "lang": lang, "date": iso(from_struct(e.get("published_parsed"))),
        })
    return out


def read_bluesky(account):
    name, handle, lang = account
    d = fetch_json("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?filter=posts_no_replies&limit=100&actor="
                   + quote(handle), timeout=20)
    out = []
    for item in d.get("feed", []):
        if item.get("reason"):  # republication d'un autre compte
            continue
        p = item["post"]
        rec = p.get("record", {})
        text = clean_text(rec.get("text"), 400)
        emb = p.get("embed") or {}
        ext = emb.get("external") or (emb.get("media") or {}).get("external") or {}
        imgs = emb.get("images") or (emb.get("media") or {}).get("images") or []
        rkey = p["uri"].rsplit("/", 1)[-1]
        date = parse_iso(rec.get("createdAt") or p.get("indexedAt"))
        if not text or not date:
            continue
        out.append({
            "kind": "bs", "key": "bs:" + p["uri"], "url": f"https://bsky.app/profile/{p['author']['handle']}/post/{rkey}",
            "text": text, "author": p["author"].get("displayName") or name, "handle": p["author"]["handle"],
            "avatar": p["author"].get("avatar"), "lang": lang, "date": iso(date),
            "link": ext.get("uri") if str(ext.get("uri", "")).startswith("http") else None,
            "link_title": clean_text(ext.get("title"), 160),
            "link_text": clean_text(ext.get("description"), 240),
            "thumb": ext.get("thumb") or (imgs[0].get("thumb") if imgs else None),
            "likes": p.get("likeCount", 0),
        })
    return out


def refresh_cache():
    """Récupère les publications récentes et les fusionne avec celles déjà connues (5 derniers jours)."""
    path = STATE / "social.json"
    cache = {p["key"]: p for p in read_json(path, {"posts": []})["posts"]}
    yt = parallel(read_youtube, YOUTUBE_NEWS, workers=12)
    bs = parallel(read_bluesky, BLUESKY, workers=8)
    fresh = [p for r in yt + bs if r for p in r]
    for p in fresh:
        cache[p["key"]] = p
    limit = now_paris() - timedelta(days=KEEP_DAYS)
    posts = [p for p in cache.values() if parse_iso(p["date"]) and parse_iso(p["date"]) >= limit]
    write_json(path, {"updated": iso(now_paris()), "posts": posts})
    ok_yt = sum(r is not None for r in yt)
    ok_bs = sum(r is not None for r in bs)
    log(f"Réseaux sociaux : {len(fresh)} publications récentes (YouTube {ok_yt}/{len(yt)}, Bluesky {ok_bs}/{len(bs)}), {len(posts)} en mémoire")
    return posts


def post_text(p):
    if p["kind"] == "yt":
        return p["title"] + " " + p["text"][:300]
    return p["text"] + " " + (p.get("link_title") or "") + " " + (p.get("link_text") or "")


def public(p):
    if p["kind"] == "yt":
        return {"kind": "yt", "id": p["id"], "title": p["title"], "author": p["author"], "date": p["date"]}
    return {k: p.get(k) for k in ("kind", "url", "text", "author", "handle", "avatar", "date", "link", "link_title", "thumb")}


def match(articles, posts):
    """Pour chaque article : les publications les plus proches (mêmes mots rares, même période)."""
    a_sets = [set(tokens(a["title"] + " " + a["summary"])) for a in articles]
    a_ents = [entities(a["title"] + " " + a["summary"]) for a in articles]
    p_sets = [set(tokens(post_text(p))) for p in posts]
    p_ents = [entities(post_text(p)) for p in posts]
    p_dates = [parse_iso(p["date"]) for p in posts]
    p_links = [canonical_url(p["link"]) if p.get("link") else None for p in posts]
    idf = idf_table(a_sets + p_sets)
    for i, a in enumerate(articles):
        a_date = parse_iso(a["date"])
        a_url = canonical_url(a["url"])
        lang = REGIONS[a["_region"]]["lang"]
        found = []
        for j, p in enumerate(posts):
            if not (a_date - timedelta(hours=18) <= p_dates[j] <= a_date + timedelta(hours=60)):
                continue
            if p_links[j] and p_links[j] == a_url:
                found.append((2.0, p))
                continue
            shared = a_sets[i] & p_sets[j]
            if len(shared) < 3 or not ((a_ents[i] & p_sets[j]) or (p_ents[j] & a_sets[i])):
                continue
            sim = similarity(a_sets[i], p_sets[j], idf)
            need = 0.24 if p["lang"] == lang else 0.30
            if sim >= need:
                found.append((sim + (0.05 if p["lang"] == lang else 0) + (0.04 if "Hugo" in p["author"] else 0), p))
        found.sort(key=lambda x: -x[0])
        chosen, authors, kinds = [], set(), {"yt": 0, "bs": 0}
        for s, p in found:
            if p["author"] in authors or kinds[p["kind"]] >= 2:
                continue
            authors.add(p["author"])
            kinds[p["kind"]] += 1
            chosen.append(public(p))
            if len(chosen) >= 4:
                break
        a["posts"] = chosen


def update(days):
    """Recalcule les publications liées pour les éditions indiquées (les plus récentes)."""
    posts = refresh_cache()
    if not posts:
        return
    total = 0
    for d in days:
        ed = read_json(day_path(d))
        if not ed:
            continue
        arts = []
        for reg, lst in ed["regions"].items():
            for a in lst:
                a["_region"] = reg
                arts.append(a)
        match(arts, posts)
        for a in arts:
            a.pop("_region", None)
            total += bool(a["posts"])
        write_json(day_path(d), ed)
    log(f"Publications rattachées : {total} articles enrichis sur {len(days)} éditions")
