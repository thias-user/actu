"""Traduction en français des articles en anglais et en espagnol (option « Traduire en français » des Réglages).

Gratuit et sans clé : les modèles libres OPUS-MT de l'université d'Helsinki (anglais → français, espagnol → français),
qui tournent sur la machine de GitHub avec le moteur CTranslate2. Ils sont préparés une seule fois
(`python robot/translate.py prepare`) puis gardés dans le cache de GitHub : rien n'est stocké sur le téléphone.
  - titres et résumés : dans l'édition du jour (champ "tr"), publics comme les originaux ;
  - textes complets : chiffrés avec le code de lecture, comme les originaux → app/data/texts-fr/AAAA-MM-JJ.bin
"""
import html
import os
import re
import sys
import time

from common import DATA, ROOT, detect_lang, log, read_json, write_json
from fulltext import decrypt, encrypt, key_from
from news import day_path

MODELS = ROOT / "robot" / "models"
OPUS = {"en": "Helsinki-NLP/opus-mt-en-fr", "es": "Helsinki-NLP/opus-mt-es-fr"}
REGION_LANG = {"eu": "en", "us": "en", "latam": "es"}
SENT_RE = re.compile(r"(?<=[.!?…»”\"])\s+(?=[«“\"¿¡A-ZÀ-ÖØ-Þ0-9])")
BATCH = 32
TEXT_SECONDS = 14 * 60  # temps de traduction des textes complets par passage (la suite le lendemain)


def split(paragraph):
    return [s.strip() for s in SENT_RE.split(paragraph) if s.strip()]


TR_VERSION = 4


def prepare():
    """Télécharge les modèles OPUS-MT et les convertit pour CTranslate2 (une fois : le résultat est mis en cache)."""
    import ctranslate2.converters
    for src, name in OPUS.items():
        out = MODELS / f"opus-{src}-fr"
        if (out / "model.bin").exists():
            continue
        log(f"Préparation du modèle de traduction {name}")
        ctranslate2.converters.TransformersConverter(name, copy_files=["source.spm", "target.spm"]).convert(
            str(out), quantization="int8", force=True)


WORD_RE = re.compile(r"[A-Za-zÀ-ÿ][\w'’-]*")


ELISION_RE = re.compile(r"(?<=[A-Za-zÀ-ÿ])\s*['’]\s*(?=[A-Za-zÀ-ÿ«\"])")


def tidy(text):
    """Sortie du modèle → texte propre : « L &apos; Agence » (codes hérités de ses données d'entraînement) → « L'Agence »."""
    text = html.unescape(html.unescape(text))
    text = re.sub(r"'{2,}", "'", text)
    text = re.sub(r"\s*>\s*>", " »", re.sub(r"<\s*<\s*", "« ", text))  # « < < un but > > » → « un but »
    text = re.sub(r"«\s*", "« ", re.sub(r"\s*»", " »", text))
    text = ELISION_RE.sub("'", text)
    return re.sub(r"\s+([,.])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()


def vocabulary(texts):
    """Mots vus en minuscules, et mots vus avec une majuscule en milieu de phrase (noms propres), dans des textes normaux."""
    lower, proper = set(), set()
    for t in texts:
        for m in WORD_RE.finditer(t or ""):
            w = m.group(0)
            if w[0].islower():
                lower.add(w)
            elif m.start() and not re.search(r"[.!?:«\"“—–-]\s*$", t[:m.start()]):
                proper.add(w)
    return lower, proper


def sentence_case(title, vocab):
    """Titres anglais « Title Case » (« Nine Killed In Florida Jet Crash ») → casse normale, que le modèle de traduction
    comprend mieux. Seuls les mots courants (vus en minuscules dans les résumés du jour) perdent leur majuscule."""
    words = WORD_RE.findall(title)
    long_words = [w for w in words if len(w) > 3]
    if len(long_words) < 3 or sum(w[0].isupper() for w in long_words) / len(long_words) < 0.7:
        return title
    lower, proper = vocab

    def fix(m):
        w = m.group(0)
        start = not re.search(r"\w", title[:m.start()]) or re.search(r"[.!?:]\s*$", title[:m.start()])
        wl = w.lower()
        forms = {wl, wl[:-1] if wl.endswith(("s", "d")) else wl, wl[:-2] if wl.endswith(("es", "ed")) else wl,
                 wl[:-3] if wl.endswith("ing") else wl}  # « Crashes », « Killed », « Killing » → crash, kill
        if start or not w[0].isupper() or w.isupper() or w in proper or not any(len(f) > 2 and f in lower for f in forms):
            return w
        return wl
    return WORD_RE.sub(fix, title)


class Translator:
    """Traduit des textes phrase par phrase ; une phrase déjà traduite pendant ce passage n'est pas refaite."""

    def __init__(self):
        self.models = {}
        self.cache = {}
        self.failed = set()  # langues dont le modèle n'a pas pu être chargé pendant ce passage
        self.sentences = 0
        self.seconds = 0.0

    @property
    def broken(self):
        return len(self.failed) == len(OPUS)

    def _load(self, src):
        if src not in self.models:
            import ctranslate2
            import sentencepiece
            folder = MODELS / f"opus-{src}-fr"
            if not (folder / "model.bin").exists():
                raise RuntimeError(f"modèle {OPUS[src]} absent (python robot/translate.py prepare)")
            engine = ctranslate2.Translator(str(folder), device="cpu", compute_type="int8", intra_threads=os.cpu_count() or 2)
            self.models[src] = (engine, sentencepiece.SentencePieceProcessor(model_file=str(folder / "source.spm")))
        return self.models[src]

    def _run(self, src, sentences, beam):
        engine, sp = self._load(src)
        out = []
        for i in range(0, len(sentences), BATCH):
            pieces = [p[:250] + ["</s>"] for p in sp.encode(sentences[i:i + BATCH], out_type=str)]
            results = engine.translate_batch(pieces, beam_size=beam, max_decoding_length=320)
            out += [tidy("".join(r.hypotheses[0]).replace("▁", " ")) for r in results]
        return out

    def translate(self, texts, src, beam=4):
        """Liste de textes (paragraphes séparés par des retours à la ligne) → même liste en français."""
        if src not in OPUS or src in self.failed:
            raise RuntimeError(f"traduction {src} → fr indisponible")
        layout = [[split(p) for p in (t or "").split("\n")] for t in texts]
        todo = list(dict.fromkeys(s for paras in layout for p in paras for s in p if (src, s) not in self.cache))
        if todo:
            start = time.time()
            try:
                cur = self._run(src, todo, beam)
            except Exception:
                self.failed.add(src)  # modèle introuvable ou illisible : on n'insiste pas pendant ce passage
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
    # 1. titres et résumés de toutes les éditions (courts, publics comme les originaux)
    for d in days:
        ed = read_json(day_path(d))
        if not ed:
            continue
        arts = [(reg, a) for reg, lst in ed["regions"].items() for a in lst]
        english = {a["id"] for reg, a in arts if source_lang(reg, a) == "en"}
        full = {}
        tpath = DATA / "texts" / f"{d.isoformat()}.bin"
        if key and tpath.exists():
            try:
                full = decrypt(key, tpath.read_bytes())
            except Exception:
                full = {}
        vocab = vocabulary([a.get("summary") for reg, a in arts if a["id"] in english] + [t for i, t in full.items() if i in english])
        changed = False
        for src in ("en", "es"):
            items = [a for reg, a in arts if a.get("tr", {}).get("v") != TR_VERSION and source_lang(reg, a) == src]
            if not items:
                continue
            try:
                out = tr.translate([x for a in items for x in (sentence_case(a["title"], vocab) if src == "en" else a["title"],
                                                               a.get("summary") or "")], src)
            except Exception as e:
                log(f"  Traduction {src} → fr impossible : {type(e).__name__} {str(e)[:120]}")
                continue
            for i, a in enumerate(items):
                a["tr"] = {"t": out[2 * i], "s": out[2 * i + 1], "l": src, "v": TR_VERSION}
            log(f"  ex. ({src}) {items[0]['title'][:70]} → {out[0][:70]}")
            titles += len(items)
            changed = True
        if changed:
            write_json(day_path(d), ed)
    # 2. textes complets, chiffrés avec le code de lecture ; l'édition la plus récente d'abord, dans le temps alloué
    limited, start = False, time.time()
    for d in sorted(days, reverse=True) if key else []:
        ed = read_json(day_path(d))
        tpath, fpath = DATA / "texts" / f"{d.isoformat()}.bin", DATA / "texts-fr" / f"{d.isoformat()}.bin"
        if not ed or not tpath.exists():
            continue
        try:
            texts = decrypt(key, tpath.read_bytes())
        except Exception:
            continue
        try:
            done = decrypt(key, fpath.read_bytes()) if fpath.exists() else {}
        except Exception:
            done = {}
        if done.get("_v") != TR_VERSION:
            done = {}  # traductions d'une version précédente : refaites
        langs = {a["id"]: source_lang(reg, a) for reg, lst in ed["regions"].items() for a in lst}
        fresh = 0
        for i, t in texts.items():
            src = langs.get(i)
            if not t or src not in OPUS or src in tr.failed or i in done:
                continue
            if time.time() - start > TEXT_SECONDS:
                limited = True
                break
            try:
                done[i] = tr.translate([t], src, beam=2)[0]
                fresh += 1
            except Exception as e:
                log(f"  Traduction des textes {src} → fr impossible : {type(e).__name__} {str(e)[:120]}")
        done = {i: t for i, t in done.items() if i in texts}
        texts_done += len(done)
        done["_v"] = TR_VERSION
        if fresh or not fpath.exists():
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(encrypt(key, done))
    log(f"Traduction : {titles} titres et résumés, {texts_done} textes complets disponibles en français "
        f"({tr.sentences} phrases traduites en {tr.seconds:.0f} s)" + (" — temps écoulé, la suite au prochain passage" if limited else ""))


def translate_stories(tr, stories, langs):
    """Traduit les textes des schémas « En un coup d'œil » (phrases de l'article, fiches Wikipédia en langue étrangère)
    → champ "tr" de chaque schéma ; l'application l'affiche quand l'option de traduction est activée."""
    jobs = {"en": [], "es": []}  # (schéma, (rubrique, rang), texte)
    for sid, st in stories.items():
        src = langs.get(sid)
        if src in jobs:
            cap = st.get("captions") or {}
            for k in ("quoi", "liens"):
                if cap.get(k):
                    jobs[src].append((st, (k, None), cap[k]))
            for i, c in enumerate(st.get("consequences") or []):
                jobs[src].append((st, ("cons", i), c["text"]))
            for i, act in enumerate(st.get("actors") or []):
                if act.get("does"):
                    jobs[src].append((st, ("does", i), act["does"]))
            for i, w in enumerate(st.get("when") or []):
                jobs[src].append((st, ("when", i), w["t"]))
            for i, h in enumerate(st.get("how") or []):
                jobs[src].append((st, ("how", i), h["t"]))
            for i, f in enumerate((st.get("why") or {}).get("facts") or []):
                jobs[src].append((st, ("why", i), f))
            for i, c in enumerate(st.get("critique") or []):
                if c.get("q"):
                    jobs[src].append((st, ("crit", i), c["q"]))
        for i, act in enumerate(st.get("actors") or []):
            w = act.get("wiki")
            if w and w.get("l") in jobs and w.get("x"):
                jobs[w["l"]].append((st, ("act", i), w["x"]))
        c = st.get("context")
        if c and c.get("l") in jobs and c.get("x"):
            jobs[c["l"]].append((st, ("ctx", None), c["x"]))
    for src, items in jobs.items():
        if not items or src in tr.failed:
            continue
        for (st, (kind, k), _), text in zip(items, tr.translate([x for _, _, x in items], src)):
            t = st.setdefault("tr", {})
            if k is None:
                t[kind] = text
            else:
                t.setdefault(kind, {})[str(k)] = text


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
