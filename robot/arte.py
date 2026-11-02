"""Catalogue des reportages ARTE en accès libre sur YouTube, classés par sujet → app/data/arte.json."""
import re
from datetime import datetime, timezone

import feedparser

from common import DATA, PARIS, clean_text, compile_keywords, fetch, from_struct, iso, log, norm, now_paris, parallel, read_json, write_json
from config import ARTE_CHANNELS, ARTE_PLAYLISTS, ARTE_SUBJECTS

MAX_VIDEOS = 1500
SUBJECT_RX = [(sid, compile_keywords(words.split())) for sid, _, words in ARTE_SUBJECTS]


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
    return [{"id": e.get("yt_videoid"), "title": clean_text(e.get("title")), "desc": clean_text(e.get("summary"), 600),
             "date": from_struct(e.get("published_parsed"))} for e in f.entries if e.get("yt_videoid")]


def split_title(title):
    """« Sujet | ARTE Reportage » → ("Sujet", "ARTE Reportage")."""
    parts = [p.strip() for p in re.split(r"\s+[|│]\s+", title) if p.strip()]
    if len(parts) > 1 and re.search(r"arte|tracks|dessous|28 ?minutes|reportage|regards|documentaire", parts[-1], re.I):
        return " | ".join(parts[:-1]), parts[-1]
    return title, None


def classify(v, default=None, hint=None):
    text = norm(" ".join([v["title"], v.get("program") or "", v.get("desc", "")[:400], " ".join(v.get("playlists", []))]))
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
                v["desc"] = e["desc"][:300]
                if e["date"]:
                    v["date"] = e["date"].date().isoformat()
    for vid, v in videos.items():
        if vid in hints:
            v["playlists"] = sorted({p for _, p in hints[vid]})
        hint = hints[vid][0][0] if vid in hints else None
        v["subjects"] = classify(v, v.pop("_default", None) or next((c[3] for c in ARTE_CHANNELS if c[0] == v.get("channel")), None), hint)
        v["desc"] = (v.get("desc") or "")[:300]
        v.setdefault("date", v.get("added"))
    ordered = sorted(videos.values(), key=lambda v: v.get("date") or "", reverse=True)[:MAX_VIDEOS]
    subjects = [{"id": sid, "label": label, "count": sum(sid in v["subjects"] for v in ordered)} for sid, label, _ in ARTE_SUBJECTS]
    keep = ("id", "title", "program", "channel", "duration", "views", "date", "desc", "subjects", "added", "playlists")
    slim = [{k: v[k] for k in keep if v.get(k)} for v in ordered]
    if slim == old.get("videos") and subjects == old.get("subjects"):
        log("ARTE : aucun nouveau reportage")
        return
    write_json(path, {"updated": iso(now_paris()), "subjects": subjects, "videos": slim})
    ok = sum(r is not None for r in listed)
    log(f"ARTE : {len(ordered)} reportages ({added} nouveaux, chaînes lues {ok}/{len(ARTE_CHANNELS)}, mode {'complet' if full else 'rapide'})")
