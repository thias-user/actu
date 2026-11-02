"""Replays des journaux de 20h de TF1 (TF1+) et France 2 (france.tv) → app/data/replays.json."""
import html
import json
import re
from datetime import date, timedelta

from common import DATA, clean_text, fetch, iso, log, now_paris, parallel, parse_iso, read_json, write_json

KEEP_DAYS = 14
TF1_PAGE = "https://www.tf1.fr/tf1/jt-20h/videos"
F2_PAGE = "https://www.france.tv/france-2/journal-20h00/"
MONTHS = {m: i + 1 for i, m in enumerate(
    "janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre".split())}


def minutes(iso_duration):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not m:
        return None
    h, mi, s = (int(x or 0) for x in m.groups())
    return round(h * 60 + mi + s / 60)


def tf1():
    page = fetch(TF1_PAGE, timeout=30).decode("utf-8", "replace")
    days = {}
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "ItemList":
            continue
        for v in data.get("itemListElement", []):
            up = parse_iso(v.get("uploadDate"))
            if not up or not v.get("url"):
                continue
            item = {"title": clean_text(html.unescape(v.get("name", ""))), "url": v["url"],
                    "image": v.get("thumbnailUrl"), "minutes": minutes(v.get("duration"))}
            jt_day = (up - timedelta(hours=6)).date().isoformat()  # les sujets mis en ligne après minuit = JT de la veille
            entry = days.setdefault(jt_day, {"tf1": None, "tf1_topics": []})
            if re.search(r"JT de 20 ?h(eures)?|journal de 20", item["title"], re.I) and (item["minutes"] or 0) >= 20:
                entry["tf1"] = item
            else:
                entry["tf1_topics"].append(item)
    return days


def f2_image(url):
    page = fetch(url, timeout=20, max_bytes=300_000).decode("utf-8", "replace")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    return html.unescape(m.group(1)) if m else None


def france2(known_images):
    page = fetch(F2_PAGE, timeout=30).decode("utf-8", "replace")
    days = {}
    for path, d, month, y in re.findall(
            r'href="(/france-2/journal-20h00/\d+-edition-du-[a-z]+-(\d{1,2})(?:er)?-([a-z]+)-(\d{4})\.html)"', page):
        if month not in MONTHS:
            continue
        day = date(int(y), MONTHS[month], int(d)).isoformat()
        url = "https://www.france.tv" + path
        days[day] = {"title": f"Journal de 20h – {day}", "url": url, "image": known_images.get(url)}
    missing = [v for v in days.values() if not v["image"]]
    for v, img in zip(missing, parallel(lambda v: f2_image(v["url"]), missing, workers=6)):
        v["image"] = img
    return days


def update():
    path = DATA / "replays.json"
    old = read_json(path, {"days": []})
    by_day = {d["date"]: d for d in old["days"]}
    known = {d["f2"]["url"]: d["f2"].get("image") for d in old["days"] if d.get("f2")}
    sources = {}
    for name, fn in (("tf1", tf1), ("f2", lambda: france2(known))):
        try:
            sources[name] = fn()
        except Exception as e:
            log(f"  ! replays {name} : {type(e).__name__} {str(e)[:80]}")
            sources[name] = {}
    if not sources["tf1"] and not sources["f2"]:
        log("Replays : aucune source joignable, données précédentes conservées")
        return
    for day, v in sources["tf1"].items():
        d = by_day.setdefault(day, {"date": day})
        if v["tf1"]:
            d["tf1"] = v["tf1"]
        if v["tf1_topics"]:
            d["tf1_topics"] = v["tf1_topics"][:14]
    for day, v in sources["f2"].items():
        by_day.setdefault(day, {"date": day})["f2"] = v
    limit = (now_paris().date() - timedelta(days=KEEP_DAYS)).isoformat()
    days = sorted((d for d in by_day.values() if d["date"] >= limit), key=lambda d: d["date"], reverse=True)
    write_json(path, {"updated": iso(now_paris()), "tf1_page": TF1_PAGE, "f2_page": F2_PAGE, "days": days})
    log(f"Replays : {sum(1 for d in days if d.get('tf1'))} JT TF1, {sum(1 for d in days if d.get('f2'))} JT France 2 sur {len(days)} jours")
