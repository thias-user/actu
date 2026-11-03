"""Catalogue des reportages ARTE en accès libre sur YouTube, classés par sujet → app/data/arte.json.

Seulement des documentaires et reportages : ni concerts ni films. La description complète et les mots-clés de chaque
vidéo (pour la recherche et le classement) sont lus une fois sur sa page YouTube (/watch, ouverte aux robots),
quelques centaines par jour au plus.
"""
import codecs
import html
import json
import re
import urllib.request
import zlib
from datetime import datetime, timezone

import feedparser

from common import DATA, PARIS, UA, clean_text, compile_keywords, fetch, from_struct, iso, log, norm, now_paris, parallel, read_json, write_json
from config import ARTE_CHANNELS, ARTE_PLAYLISTS, ARTE_REGIONS, ARTE_SUBJECTS

MAX_VIDEOS = 1500
DESC_PER_RUN = 300
SUBJECT_RX = [(sid, compile_keywords(words.split())) for sid, _, words in ARTE_SUBJECTS]
REGION_RX = [(rid, compile_keywords(words.split())) for rid, _, words in ARTE_REGIONS]
# concerts et fictions : écartés (un documentaire sur un musicien ou sur le cinéma reste)
CONCERT_RX = re.compile(r"\b(concerts?|live (?:at|@|from|in|à|au|aux|session)|live session|en live|r[ée]cital|full concert|unplugged|dj set)\b", re.I)
FICTION_RX = re.compile(r"\b(court[- ]m[ée]trages?|long[- ]m[ée]trages?|t[ée]l[ée]films?|films? complets?|(?<!science[- ])fictions?|"
                        r"bande[- ]annonce|trailer|teaser|extrait du film|short film|film d['’]animation)\b", re.I)
DOC_RX = re.compile(r"\b(documentaires?|reportages?|enqu[êe]tes?|portraits?|histoire)\b", re.I)
ANALYSIS = {"Le Dessous des Cartes", "Le Dessous des images"}  # décryptages : jamais écartés
DESC_RX = re.compile(r'"shortDescription":"((?:[^"\\]|\\.)*)"')
KEYWORDS_RX = re.compile(r'<meta name="keywords" content="([^"]*)"')
DESC_JUNK = re.compile(r"https?://|www\.|^#|abonne[zr]|abonnement|retrouvez|suivez[- ]nous|disponible jusqu|facebook|instagram|tiktok|"
                       r"twitter|newsletter|^\W*$", re.I)


def excluded(v, hints):
    if v.get("channel") == "ARTE Concert" or any(s == "_exclure" for s, _ in hints.get(v["id"], [])):
        return True
    text = f"{v['title']} {v.get('program') or ''}"
    return v.get("channel") not in ANALYSIS and not DOC_RX.search(text) and bool(CONCERT_RX.search(text) or FICTION_RX.search(text))


def clean_desc(text):
    lines = [line.strip() for line in (text or "").replace("\r", "").split("\n")]
    return clean_text(" ".join(line for line in lines if line and not DESC_JUNK.search(line)), 600)


def watch_details(vid):
    """Description complète et mots-clés d'une vidéo, lus sur sa page (la lecture s'arrête dès qu'ils sont trouvés)."""
    req = urllib.request.Request(f"https://www.youtube.com/watch?v={vid}", headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    page = ""
    with urllib.request.urlopen(req, timeout=25) as r:
        unzip = zlib.decompressobj(16 + zlib.MAX_WBITS) if r.headers.get("Content-Encoding") == "gzip" else None
        text = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while len(page) < 4_000_000:
            chunk = r.read(65536)
            if not chunk:
                break
            page += text.decode(unzip.decompress(chunk) if unzip else chunk)
            if DESC_RX.search(page):
                break
    m = DESC_RX.search(page)
    if not m:
        return None  # page sans description (contrôle anti-robot, consentement…) : on n'insiste pas
    kw = KEYWORDS_RX.search(page)
    tags = [t.strip() for t in html.unescape(kw.group(1)).split(",") if t.strip()][:12] if kw else []
    return clean_desc(json.loads('"' + m.group(1) + '"')), [t for t in tags if len(t) > 2 and t.lower() not in ("arte", "documentaire", "reportage")]


def fill_descriptions(videos):
    """Descriptions complètes des vidéos qui n'en ont pas encore, les plus récentes d'abord, par lots."""
    todo = [v for v in sorted(videos.values(), key=lambda v: v.get("date") or "", reverse=True) if not v.get("dfull")][:DESC_PER_RUN]
    done = 0
    for i in range(0, len(todo), 30):
        batch = todo[i:i + 30]
        results = parallel(lambda v: (v["id"], watch_details(v["id"])), batch, workers=4)
        ok = [r for r in results if r and r[1]]
        for vid, (desc, tags) in ok:
            v = videos[vid]
            v["desc"] = desc or v.get("desc", "")
            v["tags"] = tags
            v["dfull"] = 1
        done += len(ok)
        if len(ok) < len(batch) / 2:
            log(f"ARTE : YouTube ne donne plus les descriptions ({len(ok)}/{len(batch)}), suite au prochain passage")
            break
    return done


def ytdlp_entries(url, limit):
    """Liste (sans rien télécharger) les vidéos d'une chaîne ou d'une playlist YouTube."""
    import yt_dlp
    opts = {"extract_flat": "in_playlist", "quiet": True, "no_warnings": True, "skip_download": True, "socket_timeout": 20,
            "playlistend": limit, "extractor_args": {"youtubetab": {"approximate_date": [""]}}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return [e for e in (info or {}).get("entries") or [] if e and e.get("id")]


def rss_entries(cid):
    f = feedparser.parse(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", timeout=20))
    return [{"id": e.get("yt_videoid"), "title": clean_text(e.get("title")), "desc": clean_desc(e.get("summary")),
             "date": from_struct(e.get("published_parsed"))} for e in f.entries if e.get("yt_videoid")]


def split_title(title):
    """« Sujet | ARTE Reportage » → ("Sujet", "ARTE Reportage")."""
    parts = [p.strip() for p in re.split(r"\s+[|│]\s+", title) if p.strip()]
    if len(parts) > 1 and re.search(r"arte|tracks|dessous|28 ?minutes|reportage|regards|documentaire", parts[-1], re.I):
        return " | ".join(parts[:-1]), parts[-1]
    return title, None


def classify(v, default=None, hint=None):
    text = norm(" ".join([v["title"], v.get("program") or "", v.get("desc", "")[:600], " ".join(v.get("playlists", [])),
                          " ".join(v.get("tags", []))]))
    scores = {}
    for sid, rx in SUBJECT_RX:
        n = len(rx.findall(text)) + 2 * len(rx.findall(norm(v["title"])))
        if n:
            scores[sid] = n
    for s in (hint, default):
        if s:
            scores[s] = scores.get(s, 0) + 3
    best = [s for s, n in sorted(scores.items(), key=lambda kv: -kv[1]) if n >= 2][:2]
    return best or ["societe"]


def regions_of(v):
    """Régions du monde dont parle le reportage (2 au plus), d'après les lieux cités."""
    title = norm(v["title"])
    text = norm(" ".join([v["title"], v.get("desc", "")[:400], " ".join(v.get("playlists", []))]))
    scores = {rid: 2 * len(rx.findall(title)) + len(rx.findall(text)) for rid, rx in REGION_RX}
    return [r for r, n in sorted(scores.items(), key=lambda kv: -kv[1]) if n >= 2][:2]


def update(full=False):
    path = DATA / "arte.json"
    old = read_json(path, {"videos": []})
    videos = {v["id"]: v for v in old["videos"]}
    full = full or len(videos) < 200 or now_paris().weekday() == 0
    hints = {}  # id vidéo → (sujet, nom de playlist)

    def list_channel(ch):
        name, cid, min_minutes, default = ch
        return ch, ytdlp_entries(f"https://www.youtube.com/channel/{cid}/videos", 300 if full else 60)

    listed = parallel(list_channel, ARTE_CHANNELS, workers=3)
    if full:
        pls = parallel(lambda p: (p, ytdlp_entries(f"https://www.youtube.com/playlist?list={p[0]}", 80)), ARTE_PLAYLISTS, workers=4)
        for r in pls:
            if r:
                (pid, pname, subject), entries = r
                for e in entries:
                    hints.setdefault(e["id"], []).append((subject, pname))
    rss = parallel(lambda ch: (ch, rss_entries(ch[1])), ARTE_CHANNELS, workers=6)
    if not any(listed) and not any(rss):
        log("ARTE : YouTube injoignable, catalogue précédent conservé")
        return

    added = 0
    for res in listed:
        if not res:
            continue
        (name, cid, min_minutes, default), entries = res
        for e in entries:
            dur = e.get("duration") or 0
            if dur < min_minutes * 60 or not e.get("title"):
                continue
            title, program = split_title(clean_text(e["title"]))
            v = videos.get(e["id"]) or {"id": e["id"], "added": now_paris().date().isoformat()}
            added += e["id"] not in videos
            ts = e.get("timestamp")
            v.update({"title": title, "program": program, "channel": name, "duration": int(dur),
                      "views": e.get("view_count") or v.get("views")})
            if ts and not v.get("date"):
                v["date"] = datetime.fromtimestamp(ts, timezone.utc).astimezone(PARIS).date().isoformat()
            v["_default"] = default
            videos[e["id"]] = v
    for res in rss:  # dates exactes et descriptions des 15 dernières vidéos de chaque chaîne
        if not res:
            continue
        (name, cid, min_minutes, default), entries = res
        for e in entries:
            v = videos.get(e["id"])
            if v:
                if not v.get("dfull"):
                    v["desc"] = e["desc"]
                if e["date"]:
                    v["date"] = e["date"].date().isoformat()
    # ni concerts ni films (y compris ceux gardés des passages précédents)
    dropped = [vid for vid, v in videos.items() if excluded(v, hints)]
    for vid in dropped:
        videos.pop(vid)
    described = fill_descriptions(videos)
    for vid, v in videos.items():
        if vid in hints:
            v["playlists"] = sorted({p for s, p in hints[vid] if s != "_exclure"})
        hint = next((s for s, _ in hints.get(vid, []) if s != "_exclure"), None)
        v["subjects"] = classify(v, v.pop("_default", None) or next((c[3] for c in ARTE_CHANNELS if c[0] == v.get("channel")), None), hint)
        v["desc"] = (v.get("desc") or "")[:600]
        v["regions"] = regions_of(v)
        v.setdefault("date", v.get("added"))
    ordered = sorted(videos.values(), key=lambda v: v.get("date") or "", reverse=True)[:MAX_VIDEOS]
    subjects = [{"id": sid, "label": label, "count": sum(sid in v["subjects"] for v in ordered)} for sid, label, _ in ARTE_SUBJECTS]
    regions = [{"id": rid, "label": label, "count": sum(rid in v["regions"] for v in ordered)} for rid, label, _ in ARTE_REGIONS]
    keep = ("id", "title", "program", "channel", "duration", "views", "date", "desc", "tags", "subjects", "regions", "added", "playlists", "dfull")
    slim = [{k: v[k] for k in keep if v.get(k)} for v in ordered]
    if slim == old.get("videos") and subjects == old.get("subjects") and regions == old.get("regions"):
        log("ARTE : aucun nouveau reportage")
        return
    write_json(path, {"updated": iso(now_paris()), "subjects": subjects, "regions": regions, "videos": slim})
    ok = sum(r is not None for r in listed)
    log(f"ARTE : {len(ordered)} reportages ({added} nouveaux, {len(dropped)} concerts ou films écartés, {described} descriptions "
        f"complètes lues, {sum(bool(v.get('dfull')) for v in ordered)} en tout ; chaînes lues {ok}/{len(ARTE_CHANNELS)}, "
        f"mode {'complet' if full else 'rapide'})")
