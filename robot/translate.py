"""Traduction en français des articles en anglais et en espagnol (option « Traduire en français » des Réglages).

Gratuit et sans clé : les modèles libres d'Argos Translate, qui tournent sur la machine de GitHub (moteur CTranslate2).
Anglais → français directement ; espagnol → anglais → français (il n'existe pas de modèle direct). Les modèles
(≈ 350 Mo) sont téléchargés une fois puis gardés dans le cache de GitHub : rien n'est stocké sur le téléphone.
  - titres et résumés : dans l'édition du jour (champ "tr"), publics comme les originaux ;
  - textes complets : chiffrés avec le code de lecture, comme les originaux → app/data/texts-fr/AAAA-MM-JJ.bin
"""
import io
import os
import re
import time
import zipfile

from common import DATA, ROOT, detect_lang, fetch, log, read_json, write_json
from fulltext import decrypt, encrypt, key_from
from news import day_path

MODELS = ROOT / "robot" / "models"
PACKAGES = {("en", "fr"): "https://argos-net.com/v1/translate-en_fr-1_9.argosmodel",
            ("es", "en"): "https://argos-net.com/v1/translate-es_en-1_9.argosmodel"}
ROUTE = {"en": [("en", "fr")], "es": [("es", "en"), ("en", "fr")]}
REGION_LANG = {"eu": "en", "us": "en", "latam": "es"}
SENT_RE = re.compile(r"(?<=[.!?…»”\"])\s+(?=[«“\"¿¡A-ZÀ-ÖØ-Þ0-9])")
BATCH = 32
MAX_TEXT_SENTENCES = 7000  # par passage, pour rester dans le temps alloué (la suite le lendemain)


def split(paragraph):
    return [s.strip() for s in SENT_RE.split(paragraph) if s.strip()]


class Translator:
    """Traduit des textes phrase par phrase ; une phrase déjà traduite pendant ce passage n'est pas refaite."""

    def __init__(self):
        self.models = {}
        self.cache = {}
        self.broken = False
        self.sentences = 0
        self.seconds = 0.0

    def _load(self, pair):
        if pair in self.models:
            return self.models[pair]
        import ctranslate2
        import sentencepiece
        folder = MODELS / f"{pair[0]}_{pair[1]}"
        if not (folder / "ok").exists():
            log(f"  Téléchargement du modèle de traduction {pair[0]} → {pair[1]} (une seule fois)")
            blob = fetch(PACKAGES[pair], timeout=120, retries=2)
            folder.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                z.extractall(folder)
            (folder / "ok").write_text("ok")
        model_dir = next(folder.rglob("model.bin")).parent
        spm = next(folder.rglob("sentencepiece.model"))
        engine = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8", intra_threads=os.cpu_count() or 2)
        self.models[pair] = (engine, sentencepiece.SentencePieceProcessor(model_file=str(spm)))
        return self.models[pair]

    def _run(self, pair, sentences):
        engine, sp = self._load(pair)
        out = []
        for i in range(0, len(sentences), BATCH):
            pieces = [p[:250] for p in sp.encode(sentences[i:i + BATCH], out_type=str)]
            results = engine.translate_batch(pieces, beam_size=2, max_decoding_length=320, replace_unknowns=True)
            out += [sp.decode(r.hypotheses[0]).strip() for r in results]
        return out

    def translate(self, texts, src):
        """Liste de textes (paragraphes séparés par des retours à la ligne) → même liste en français."""
        if src not in ROUTE or self.broken:
            raise RuntimeError("traduction indisponible")
        layout = [[split(p) for p in (t or "").split("\n")] for t in texts]
        todo = list(dict.fromkeys(s for paras in layout for p in paras for s in p if (src, s) not in self.cache))
        if todo:
            start = time.time()
            try:
                cur = todo
                for pair in ROUTE[src]:
                    cur = self._run(pair, cur)
            except Exception:
                self.broken = True  # modèle introuvable ou illisible : on n'insiste pas pendant ce passage
                raise
            self.cache.update({(src, s): t for s, t in zip(todo, cur)})
            self.sentences += len(todo)
            self.seconds += time.time() - start
        return ["\n".join(" ".join(self.cache[(src, s)] for s in p) for p in paras) for paras in layout]


def source_lang(region, a):
    """Langue d'un article : celle de sa région, sauf si son titre et son résumé disent autre chose."""
    lang = detect_lang(a["title"] + " " + (a.get("summary") or ""))
    return lang if lang in ("fr", "en", "es") else REGION_LANG.get(region, "fr")


def update(days, tr):
    code = os.environ.get("ACTU_READ_KEY", "").strip()
    key = key_from(code) if code else None
    titles = texts_done = 0
    budget, limited = MAX_TEXT_SENTENCES, False
    for d in days:
        ed = read_json(day_path(d))
        if not ed:
            continue
        arts = [(reg, a) for reg, lst in ed["regions"].items() for a in lst]
        # titres et résumés (publics, comme les originaux)
        changed = False
        for src in ("en", "es"):
            items = [a for reg, a in arts if "tr" not in a and source_lang(reg, a) == src]
            if not items:
                continue
            out = tr.translate([x for a in items for x in (a["title"], a.get("summary") or "")], src)
            for i, a in enumerate(items):
                a["tr"] = {"t": out[2 * i], "s": out[2 * i + 1], "l": src}
            titles += len(items)
            changed = True
        if changed:
            write_json(day_path(d), ed)
        # textes complets (chiffrés avec le code de lecture)
        if not key:
            continue
        tpath, fpath = DATA / "texts" / f"{d.isoformat()}.bin", DATA / "texts-fr" / f"{d.isoformat()}.bin"
        if not tpath.exists():
            continue
        try:
            texts = decrypt(key, tpath.read_bytes())
        except Exception:
            continue
        try:
            done = decrypt(key, fpath.read_bytes()) if fpath.exists() else {}
        except Exception:
            done = {}
        langs = {a["id"]: source_lang(reg, a) for reg, a in arts}
        fresh = 0
        for src in ("en", "es"):
            ids = [i for i, t in texts.items() if t and langs.get(i) == src and i not in done]
            batch = []
            for i in ids:
                n = len(split(texts[i]))
                if n > budget:
                    limited = True
                    break
                budget -= n
                batch.append(i)
            if batch:
                for i, t in zip(batch, tr.translate([texts[i] for i in batch], src)):
                    done[i] = t
                fresh += len(batch)
        done = {i: t for i, t in done.items() if i in texts}
        if fresh or (done and not fpath.exists()):
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(encrypt(key, done))
        texts_done += len(done)
    log(f"Traduction : {titles} titres et résumés, {texts_done} textes complets disponibles en français "
        f"({tr.sentences} phrases traduites en {tr.seconds:.0f} s)" + (" — limite atteinte, la suite demain" if limited else ""))


def translate_stories(tr, stories, langs):
    """Traduit les textes des schémas « En un coup d'œil » (phrases de l'article, fiches Wikipédia en langue étrangère)
    → champ "tr" de chaque schéma ; l'application l'affiche quand l'option de traduction est activée."""
    jobs = {"en": [], "es": []}  # (schéma, chemin, texte)
    for sid, st in stories.items():
        src = langs.get(sid)
        if src in jobs:
            cap = st.get("captions") or {}
            for k in ("quoi", "liens"):
                if cap.get(k):
                    jobs[src].append((st, ("cap", k), cap[k]))
            for i, c in enumerate(st.get("consequences") or []):
                jobs[src].append((st, ("cons", i), c["text"]))
        for i, act in enumerate(st.get("actors") or []):
            w = act.get("wiki")
            if w and w.get("l") in jobs and w.get("x"):
                jobs[w["l"]].append((st, ("act", i), w["x"]))
        c = st.get("context")
        if c and c.get("l") in jobs and c.get("x"):
            jobs[c["l"]].append((st, ("ctx", 0), c["x"]))
    for src, items in jobs.items():
        if not items:
            continue
        for (st, (kind, k), _), text in zip(items, tr.translate([x for _, _, x in items], src)):
            t = st.setdefault("tr", {})
            if kind == "cap":
                t[k] = text
            elif kind == "cons":
                t.setdefault("cons", {})[str(k)] = text
            elif kind == "act":
                t.setdefault("act", {})[str(k)] = text
            else:
                t["ctx"] = text
