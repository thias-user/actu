"""Analyse critique argumentée, rédigée par une IA libre (case « Regard critique » du schéma « En un coup d'œil »).

Gratuit et sans clé : le modèle ouvert Qwen3-4B-Instruct (licence Apache 2.0), lancé avec llama.cpp sur la machine de
GitHub ; il est téléchargé une fois (`python robot/critique_ai.py prepare`) puis gardé dans le cache de GitHub. Les textes
des articles ne quittent pas la machine du robot, et l'analyse est chiffrée avec le code de lecture, comme le schéma.
Seuls les premiers articles de chaque région sont analysés, dans une limite de temps par passage ; une analyse faite
n'est pas refaite. Garde-fou : une phrase de l'IA qui cite un nom ou un chiffre absent de l'article est retirée.
"""
import os
import re
import sys
import time
import urllib.request

from common import ROOT, UA, log, norm
from profiles import NAMES
from scenes import FLAGS

MODEL_DIR = ROOT / "robot" / "llm"
MODEL_FILE = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
MODEL_URL = "https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/" + MODEL_FILE
MODEL_NAME = "Qwen3-4B (IA libre)"
AI_VERSION = 1
PER_REGION = 3              # les articles « à la une » de chaque région
SECONDS = 18 * 60           # temps d'analyse par passage (la suite au passage suivant)
TEXT_CHARS = 3600           # longueur d'article confiée à l'IA

SYSTEM = ("Tu es un journaliste chevronné et un formateur en éducation aux médias. Tu écris en français, avec précision et "
          "nuance, sans jamais inventer un fait.")
PROMPT = """Article publié par {source} ({date}).
Titre : {title}
Texte :
{text}

Repères vérifiés par ACTU :
{facts}

Rédige une analyse critique de cet article, en un seul paragraphe de 5 à 7 phrases, sans titre, sans liste ni astérisques :
– ce qui est solidement établi et sur quoi cela repose (sources, documents, témoins) ;
– ce qui reste fragile, invérifiable, contesté ou absent ;
– le point de vue adopté par l'article, et les voix ou les explications qui manquent ;
– ce que cela révèle des enjeux politiques, économiques ou sociaux en jeu.
Règles : ne résume pas l'article, analyse-le ; n'invente aucun fait, aucun nom, aucun chiffre ; appuie-toi seulement sur le texte et les repères ci-dessus ; ne donne à une personne ni étiquette politique ni fonction que le texte ou les repères ne lui donnent pas ; n'affirme pas qu'une information est vérifiée ailleurs ; traduis en français les expressions étrangères ; si une information manque, dis-le."""

NUM_RX = re.compile(r"\d[\d  .,]*\d|\d")
COMMON = set(norm("Le La Les Un Une Des Ce Cette Ces Il Elle Ils Elles On Si Mais Or Ainsi Enfin Pourtant Cependant Toutefois "
                  "Article Texte Etat État Europe Union Gouvernement Président Ministre Parlement Assemblée Sénat Congrès "
                  "Commission Conseil Cour Justice Banque Kremlin Maison-Blanche OTAN ONU FMI OMS BCE UE ACTU").split())
COMMON |= set(FLAGS) | {w for name in NAMES.values() for w in norm(name).split() if len(w) > 2}


def prepare():
    """Télécharge le modèle une fois (le cache de GitHub le garde ensuite)."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / MODEL_FILE
    if path.exists() and path.stat().st_size > 1_000_000_000:
        return
    log(f"Téléchargement du modèle {MODEL_FILE}")
    tmp = path.with_suffix(".part")
    req = urllib.request.Request(MODEL_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(path)


def grounded(answer, source):
    """Retire les phrases qui citent un chiffre ou un nom propre absent des textes fournis."""
    src_nums = {re.sub(r"\D", "", n) for n in NUM_RX.findall(source)}
    src_words = set(norm(source).split())
    keep = []
    for s in re.split(r"(?<=[.!?])\s+", answer.strip()):
        if not s.rstrip().endswith((".", "!", "?", "»", "\"")):
            continue  # phrase coupée par la limite de longueur : jamais de texte tronqué
        if any(re.sub(r"\D", "", n) not in src_nums for n in NUM_RX.findall(s)):
            continue  # un chiffre que l'article ne donne pas
        words = re.findall(r"[\wÀ-ÿ'’-]+", s)
        names = [w for w in words[1:] if w[:1].isupper() and len(w) > 2]
        if any(norm(w).strip() not in COMMON and not set(norm(w).split()) <= src_words for w in names):
            continue  # un nom que l'article ne cite pas
        keep.append(s)
    return " ".join(keep)


class Critic:
    def __init__(self):
        self.llm = None
        self.failed = False
        self.done = 0
        self.seconds = 0.0

    def _load(self):
        if self.llm is None and not self.failed:
            try:
                from llama_cpp import Llama
                path = MODEL_DIR / MODEL_FILE
                if not path.exists():
                    raise FileNotFoundError(f"{path} absent (python robot/critique_ai.py prepare)")
                self.llm = Llama(model_path=str(path), n_ctx=4096, n_threads=os.cpu_count() or 4, verbose=False)
            except Exception as e:
                self.failed = True
                log(f"  Analyse critique par l'IA indisponible : {type(e).__name__} {str(e)[:100]}")
        return self.llm

    def analyse(self, a, sents, story, date_label):
        llm = self._load()
        if not llm:
            return None
        text, n = [], 0
        for s in sents:
            if n + len(s) > TEXT_CHARS:
                break
            text.append(s)
            n += len(s) + 1
        facts = []
        who = [f"{(x.get('wiki') or {}).get('t') or x['name']} : {x['wiki']['d']}" for x in story.get("actors") or []
               if (x.get("wiki") or {}).get("d")]
        if who:
            facts.append("Qui est qui (Wikipédia) : " + " ; ".join(who) + ".")
        others = list(a.get("also") or [])
        facts.append("Autres médias qui en parlent : " + (", ".join(others[:6]) if others else "aucun dans ACTU pour l’instant") + ".")
        for c in story.get("critique") or []:
            if c["k"] not in ("perspective", "medias"):
                facts.append(c["t"].rstrip(" :") + ".")
        prompt = PROMPT.format(source=a["source"], date=date_label, title=a["title"], text=" ".join(text), facts="\n".join(f"- {f}" for f in facts))
        t = time.time()
        out = llm.create_chat_completion(messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                                         temperature=0.2, top_p=0.9, max_tokens=560, repeat_penalty=1.08)
        self.seconds += time.time() - t
        answer = out["choices"][0]["message"]["content"]
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S)
        answer = re.sub(r"[*#_`]+", "", answer).replace("\n", " ").strip()
        kept = grounded(answer, prompt)
        if len(re.findall(r"[.!?](?:\s|$)", kept)) < 3:
            return None
        self.done += 1
        return {"t": kept, "m": MODEL_NAME, "v": AI_VERSION}

    def run(self, stories, items, old, sents_of, date_label, deadline):
        """Analyse les premiers articles de chaque région ; garde les analyses déjà faites."""
        for reg, a in items:
            prev = (old or {}).get(a["id"], {}).get("ai")
            if prev and prev.get("v") == AI_VERSION and a["id"] in stories:
                stories[a["id"]]["ai"] = prev
        for reg, a in items:
            st = stories.get(a["id"])
            if not st or st.get("ai") or time.time() > deadline or self.failed:
                continue
            sents = sents_of(a)
            if len(sents) < 5:
                continue
            try:
                res = self.analyse(a, sents, st, date_label)
            except Exception as e:
                log(f"  Analyse IA de « {a['title'][:50]} » impossible : {type(e).__name__}")
                res = None
            if res:
                st["ai"] = res


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
