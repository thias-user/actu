"""Point d'entrée du robot ACTU, lancé chaque matin par GitHub Actions (et à la demande).

    python robot/run_daily.py           # ne fait rien avant 10h (heure de Paris) ni deux fois par jour
    python robot/run_daily.py --force   # mise à jour immédiate
"""
import argparse
import sys
import traceback
from datetime import datetime, time as dtime, timedelta

import arte
import fulltext
import news
import replays
import research
import scenes
import social
import stories
import translate
from common import DATA, PARIS, iso, log, now_paris, read_json, write_json
from news import day_path

UPDATE_HOUR = 10


def step(name, fn, *args):
    try:
        return fn(*args)
    except Exception:
        log(f"ÉCHEC de l'étape {name} :")
        traceback.print_exc()
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="mettre à jour même si ce n'est pas l'heure")
    ap.add_argument("--only", choices=["news", "traduction", "replays", "arte", "research"], help="une seule partie")
    args = ap.parse_args()

    now = now_paris()
    index_path = DATA / "index.json"
    index = read_json(index_path, {})
    if not args.force:
        if now.hour < UPDATE_HOUR:
            log(f"Il est {now:%H:%M} à Paris : la mise à jour se fait à partir de {UPDATE_HOUR}h.")
            return 0
        if index.get("last_run") == now.date().isoformat():
            log("Déjà mis à jour aujourd'hui.")
            return 0

    failed = []
    if args.only in (None, "news"):
        res = step("articles", news.build)
        if res is None:
            return 1
        built, failed = res
        recent = [datetime.fromisoformat(d).date() for d in sorted(p.stem for p in (DATA / "days").glob("*.json"))[-3:]]
        for d in recent:  # scènes pixel art (règles éventuellement modifiées)
            ed = read_json(day_path(d))
            if ed and scenes.refresh(ed):
                write_json(day_path(d), ed)
        step("réseaux sociaux", social.update, recent)
        step("lecture intégrale", fulltext.update, recent)
        tr = translate.Translator()
        step("traduction", translate.update, recent, tr)
        step("scénarios", stories.update, recent, tr)
    if args.only == "traduction":  # traduction et schémas seulement (essais)
        recent = [datetime.fromisoformat(d).date() for d in sorted(p.stem for p in (DATA / "days").glob("*.json"))[-3:]]
        tr = translate.Translator()
        step("traduction", translate.update, recent, tr)
        step("scénarios", stories.update, recent, tr)
    if args.only in (None, "replays"):
        step("replays", replays.update)
    if args.only in (None, "arte"):
        step("ARTE", arte.update)
    if args.only in (None, "research"):
        step("recherche", research.update, args.only == "research")

    days = sorted((p.stem for p in (DATA / "days").glob("*.json")), reverse=True)
    tomorrow = datetime.combine(now.date() + timedelta(days=1), dtime(UPDATE_HOUR), PARIS)
    index.update({"updated": iso(now), "last_run": now.date().isoformat(), "next": iso(tomorrow), "days": days,
                  "feeds_failed": len(failed)})
    write_json(index_path, index, pretty=True)
    log(f"Terminé : {len(days)} éditions disponibles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
