"""Synthèse de recherche par un agent IA, sur le modèle de l'épreuve de synthèse de textes de la BCE (ESCP, HEC).

Lancée à la demande depuis l'onglet Recherche : l'application ouvre une demande GitHub (« Synthèse ACTU … ») qui liste
les articles choisis ; ce programme fait le travail puis chiffre le résultat avec le code de lecture
→ app/data/syntheses/<id>.bin, que l'application récupère.

Un article : fiche de lecture, résumé d'environ 250 mots et regard critique. Plusieurs : la fiche de chacun, puis une
synthèse de 300 mots (± 10 %) — une problématique en question, trois parties ouvertes chacune par une sous-question et
qui confrontent tous les auteurs —, contrôlée (longueur, questions, auteurs, ni citation ni avis), relue et notée par un
« jury », corrigée, la meilleure version gardée ; puis un dialogue critique entre les articles.

Gratuit et sans clé : le modèle ouvert GPT-OSS 20B du service Pollinations (une réponse toutes les 45 secondes) et
Jina Reader pour lire les textes en accès libre.
"""
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from common import DATA, UA, log
from fulltext import encrypt, key_from

API = "https://text.pollinations.ai/openai"
READER = "https://r.jina.ai/"
PACE = 46
MAX_PAPERS = 5
MODEL = "GPT-OSS 20B (IA libre, service gratuit Pollinations)"
SYS = ("Tu es professeur de culture générale en classe préparatoire HEC (ECG) et correcteur de l'épreuve de synthèse de textes "
       "de la BCE. Tu lis avec une extrême rigueur, tu ne prêtes jamais à un auteur ce qu'il n'écrit pas, et tu écris un français "
       "précis, clair et élégant. Tu réponds toujours en français, même si les textes sont dans une autre langue.")
_last = [0.0]


# ---------------------------------------------------------------- appels au service gratuit

def llm(messages, tries=10):
    for _ in range(tries):
        wait = PACE - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        body = json.dumps({"model": "openai", "messages": messages, "temperature": 0.4, "reasoning_effort": "low",
                           "max_tokens": 4000, "seed": random.randint(1, 10 ** 9)}).encode()
        req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            _last[0] = time.time()
            text = (data["choices"][0]["message"].get("content") or "").strip()
            if text:
                return text
        except urllib.error.HTTPError as e:
            _last[0] = time.time()
            msg = e.read()[:300].decode("utf-8", "replace")
            after = re.search(r"Retry after (\d+)", msg) or re.search(r"(\d+)", e.headers.get("Retry-After") or "")
            if after:
                _last[0] = time.time() - PACE + int(after.group(1)) + 2
            log(f"  IA : HTTP {e.code} {msg[:90]}")
        except Exception as e:
            _last[0] = time.time()
            log(f"  IA : {type(e).__name__}")
    raise RuntimeError("le service d'IA gratuit ne répond pas")


def ask(prompt):
    return llm([{"role": "system", "content": SYS}, {"role": "user", "content": prompt}])


def plain_keys(obj):
    """Clés sans accents ni majuscules (« Réponses » → « reponses ») : l'application les lit ainsi."""
    if isinstance(obj, dict):
        return {unicodedata.normalize("NFD", str(k)).encode("ascii", "ignore").decode().lower().replace(" ", "_"): plain_keys(v)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [plain_keys(v) for v in obj]
    return obj


def ask_json(prompt):
    for _ in range(3):
        out = ask(prompt + "\nRéponds uniquement par un objet JSON valide, sans texte autour.")
        m = re.search(r"\{.*\}", out, re.S)
        try:
            return plain_keys(json.loads(m.group(0)))
        except Exception:
            log("  IA : JSON illisible, nouvel essai")
    raise RuntimeError("réponse de l'IA inexploitable")


# ---------------------------------------------------------------- lecture des textes

def get(url, timeout=60, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b.decode("utf-8", "replace") if raw else json.loads(b)


def abstract_of(inv):
    if not inv:
        return ""
    w = {}
    for k, ps in inv.items():
        for p in ps:
            w[p] = k
    return " ".join(w[i] for i in sorted(w))


def read(p):
    """Résumé complet (OpenAlex) et texte intégral en accès libre (Jina Reader), quand il existe."""
    abstract, oa = p.get("abstract") or "", p.get("pdf") or ""
    doi = re.search(r"10\.\d{4,9}/[^\s?#]+", p.get("url") or "")
    if doi:
        try:
            w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi.group(0)) +
                    "?select=abstract_inverted_index,open_access,best_oa_location", timeout=30)
            full = abstract_of(w.get("abstract_inverted_index"))
            if len(full) > len(abstract):
                abstract = full
            oa = oa or (w.get("best_oa_location") or {}).get("pdf_url") or (w.get("open_access") or {}).get("oa_url") or ""
        except Exception:
            pass
    text = ""
    for link in [x for x in (oa, p.get("url")) if x]:
        try:
            t = get(READER + link, timeout=120, raw=True).split("Markdown Content:", 1)[-1].strip()
            if len(t) > 4000 and not re.search(r"captcha|access denied|cookies? (policy|settings)", t[:600], re.I):
                text = t
                break
        except Exception:
            continue
    clip = text[:10000] + "\n[…]\n" + text[-5000:] if len(text) > 15000 else text
    return {"kind": "texte intégral (extraits du début et de la fin)" if text else "résumé de l'auteur seulement",
            "body": clip or abstract or p["title"], "full": bool(text)}


# ---------------------------------------------------------------- consignes

def ref(p):
    return f"{p.get('authors') or 'auteur non précisé'} ({p.get('year') or 's. d.'}), « {p['title']} »" + (f", {p['venue']}" if p.get("venue") else "")


def p_fiche(p, src):
    return f"""Voici un article scientifique.
Référence : {ref(p)}.
Texte disponible : {src['kind']}.
---
{src['body']}
---
Rédige sa fiche de lecture, en français, avec ces clés :
"auteur" : la façon de le citer dans une synthèse (nom de famille du premier auteur ; « et » puis le second nom s'il y a deux auteurs ; « et al. » au-delà) ;
"these" : la thèse ou le résultat principal, en une phrase ;
"resume" : un résumé fidèle de 120 à 170 mots, entièrement reformulé (aucune citation), qui suit la logique de l'argumentation : question posée, démarche (données, terrain, méthode), résultats, conclusion ;
"arguments" : 3 à 5 idées clés, une phrase chacune ;
"methode" : la démarche et ses données, en une phrase ;
"limites" : les limites reconnues par l'auteur ou visibles dans la démarche (échantillon, période, pays, méthode), en une ou deux phrases.
N'invente rien : ce qui n'est pas dans le texte s'écrit « non précisé »."""


def p_plan(fiches):
    return f"""Voici les fiches de lecture de {len(fiches)} articles :
{json.dumps(fiches, ensure_ascii=False)}
Prépare le plan d'une synthèse conforme à l'épreuve de synthèse de textes de la BCE (ESCP, HEC) :
"problematique" : une seule question, précise, qui couvre tous les articles (elle pourrait servir de titre à chacun) ;
"type" : "dialectique" si la question appelle une réponse par oui ou non, sinon "thematique" ;
"parties" : exactement 3 objets {{"question": la sous-question qui ouvre la partie, "positions": {{auteur: sa position sur cette sous-question, en une phrase}}, "lien": comment ces positions se répondent (accord, nuance, opposition)}} ; les trois sous-questions s'enchaînent logiquement et, ensemble, répondent à la problématique ; chaque auteur a une position dans chaque partie ;
"convergence" : le point sur lequel tous les auteurs s'accordent."""


def words(t):
    """Un mot : groupe de lettres ou de chiffres séparé par une espace ou une apostrophe (« l'homme » = 2) ; mot composé = 1."""
    t = re.sub(r"aujourd['’]hui", "aujourdhui", t, flags=re.I).replace("’", " ").replace("'", " ")
    return len(re.findall(r"[^\W_]+(?:-[^\W_]+)*", t))


def paras_of(text):
    return [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]


def sizes(text):
    return ", ".join(f"{'partie ' + str(k) if k else 'introduction'} : {words(x)} mots" for k, x in enumerate(paras_of(text)))


def p_write(fiches, plan, fixes=None, previous=None):
    parts = " ; ".join(f"partie {k + 1} : {x.get('question', '')}" for k, x in enumerate(plan.get("parties") or []))
    base = f"""Fiches : {json.dumps(fiches, ensure_ascii=False)}
Plan : {json.dumps(plan, ensure_ascii=False)}
Rédige la synthèse selon les exigences de l'épreuve de synthèse de textes de la BCE :
- 300 mots au total, noms d'auteurs compris, répartis ainsi : introduction de 20 à 35 mots, puis trois parties de 85 à 90 mots chacune ;
- l'introduction se réduit à la problématique, formulée en une seule question (éventuellement précédée d'une courte phrase qui situe le débat) : {plan.get('problematique', '')} ;
- chaque partie commence par sa sous-question, mot pour mot ({parts}), et confronte TOUS les auteurs ({', '.join(f['auteur'] for f in fiches)}), nommés à chaque fois, reliés par des connecteurs logiques précis (alors que, de même, à l'inverse, en revanche, plus encore…) ; jamais un article résumé après l'autre ; pas de phrase de bilan en fin de partie ;
- reformulation fidèle, aucune citation, aucun guillemet, aucun avis personnel, aucune connaissance extérieure aux fiches, pas de conclusion ;
- phrases complètes, vocabulaire précis, style dense.
Écris uniquement le texte de la synthèse : 4 paragraphes séparés par une ligne vide, sans titre."""
    if fixes:
        base += (f"\n\nVersion précédente ({words(previous)} mots : {sizes(previous)}) :\n{previous}\n\nReprends cette version en ne "
                 "réécrivant QUE les phrases concernées par ces défauts, sans toucher au reste ni ajouter de phrase ; garde les mêmes "
                 "sous-questions en tête des parties et une longueur totale entre 285 et 315 mots :\n- " + "\n- ".join(fixes))
    return base


def p_condense(text, authors, plan):
    parts = " ".join(f"{k + 1}) {x.get('question', '')}" for k, x in enumerate(plan.get("parties") or []))
    return f"""Voici une synthèse de {words(text)} mots ({sizes(text)}) :
{text}

Elle doit faire 300 mots (entre 285 et 315) : introduction de 20 à 35 mots, puis trois parties de 85 à 90 mots chacune.
Réécris-la à ces longueurs exactes : supprime les redites, les phrases de bilan (« Ainsi, tous… »), les incises et les adverbes inutiles, fusionne les idées proches ; garde la confrontation de tous les auteurs ({', '.join(authors)}) nommés, et la fidélité aux textes.
L'introduction reste une question : {plan.get('problematique', '')}
Chaque partie commence par sa sous-question, mot pour mot : {parts}
Écris uniquement le texte : 4 paragraphes séparés par une ligne vide."""


def p_jury(fiches, text):
    return f"""Fiches des articles : {json.dumps(fiches, ensure_ascii=False)}
Copie à corriger :
{text}
Corrige cette synthèse comme le jury de la BCE : fidélité aux textes (contresens, positions prêtées à tort), pertinence de la problématique, réelle confrontation des auteurs dans chaque partie, enchaînement des sous-questions, précision et élégance de l'expression.
Réponds avec : "note" (sur 20), "defauts" (liste précise des corrections à faire, vide s'il n'y en a pas), "points_forts" (liste courte)."""


def p_dialogue(fiches):
    return f"""Fiches : {json.dumps(fiches, ensure_ascii=False)}
Au-delà de l'épreuve (qui interdit tout avis), fais dialoguer et se critiquer ces articles, uniquement à partir des fiches :
"reponses" : pour chaque auteur, un objet {{"auteur", "critique"}} : ce que les autres articles lui opposent ou lui apportent (données, méthode, terrain, période, portée des conclusions), en 2 ou 3 phrases ;
"accords" : les points d'accord solides (liste) ;
"desaccords" : les désaccords réels et d'où ils viennent (liste) ;
"angles_morts" : ce qu'aucun article n'étudie (liste) ;
"questions" : 2 ou 3 questions que la recherche doit encore trancher (liste)."""


def p_one(fiche, src):
    return f"""Fiche de lecture : {json.dumps(fiche, ensure_ascii=False)}
Texte disponible ({src['kind']}) :
---
{src['body']}
---
Fais de cet article une étude critique, en français, avec ces clés :
"titre" : un titre sobre et clair qui dit la thèse ;
"resume" : un résumé fidèle de 230 à 270 mots, entièrement reformulé, qui suit la logique de l'argumentation (sans citation ni avis) ;
"forces" : ce qui rend les résultats solides (données, méthode, cohérence), liste de 2 à 4 points ;
"limites" : ce qui les fragilise ou en borne la portée (échantillon, période, pays, méthode, angles morts), liste de 2 à 4 points ;
"portee" : ce que l'article apporte au débat et dans quelles conditions ses conclusions valent, en 2 phrases ;
"questions" : 2 ou 3 questions qu'il laisse ouvertes.
Appuie-toi uniquement sur le texte."""


# ---------------------------------------------------------------- contrôles de forme (règles de l'épreuve)

def checks(text, authors):
    paras = paras_of(text)
    errs, n = [], words(text)
    if not 270 <= n <= 330:
        errs.append(f"La synthèse fait {n} mots : il en faut entre 270 et 330 (cible 300).")
    if len(paras) != 4:
        errs.append(f"Il faut exactement 4 paragraphes (l'introduction-problématique puis 3 parties) ; il y en a {len(paras)}.")
    if paras and "?" not in paras[0]:
        errs.append("L'introduction doit formuler la problématique sous forme de question.")
    for i, para in enumerate(paras[1:4], 1):
        if not re.split(r"(?<=[?.!])\s", para, 1)[0].rstrip().endswith("?"):
            errs.append(f"La partie {i} doit commencer par sa sous-question.")
        missing = [a for a in authors if a.split()[0].lower() not in para.lower()]
        if missing:
            errs.append(f"La partie {i} ne confronte pas : {', '.join(missing)}.")
    if re.search(r"[«»“”\"]", text):
        errs.append("Aucune citation entre guillemets n'est admise : reformule.")
    if re.search(r"\b(je|à mon avis|selon moi|nous pensons)\b", text, re.I):
        errs.append("Aucun avis personnel n'est admis.")
    return errs, n


def repair(text, plan):
    """La problématique et les sous-questions en tête, quoi qu'ait écrit l'IA (exigence de l'épreuve)."""
    paras = paras_of(text)
    if len(paras) != 4:
        return text
    if "?" not in paras[0] and plan.get("problematique"):
        paras[0] = plan["problematique"].strip()
    for i, para in enumerate(paras[1:], 1):
        q = ((plan.get("parties") or [{}] * 3)[i - 1] or {}).get("question", "").strip()
        if q and not re.split(r"(?<=[?.!])\s", para, 1)[0].rstrip().endswith("?"):
            paras[i] = f"{q} {para}"
    return "\n\n".join(paras)


def citation_name(f, p):
    name = str(f.get("auteur") or (p.get("authors") or "").split(",")[0] or "Auteur").strip()
    if name == name.upper():  # « BENSLIMANE et LAHRECH » → « Benslimane et Lahrech »
        name = " ".join(w if w in ("et", "al.") else w.capitalize() for w in name.lower().split())
    return name


# ---------------------------------------------------------------- l'agent

def synthesize(papers):
    t0 = time.time()
    out = {}
    srcs = []
    for i, p in enumerate(papers):
        srcs.append(read(p))
        out[f"read{i}"] = {"kind": srcs[-1]["kind"], "full": srcs[-1]["full"]}
        log(f"  Article {i + 1} lu : {'texte intégral' if srcs[-1]['full'] else 'résumé'} ({len(srcs[-1]['body'])} signes)")
    fiches = []
    for i, p in enumerate(papers):
        f = ask_json(p_fiche(p, srcs[i]))
        f["auteur"] = citation_name(f, p)
        out[f"fiche{i}"] = f
        fiches.append(f)
        log(f"  Fiche {i + 1} : {f['auteur']}")
    if len(papers) == 1:
        out["one"] = ask_json(p_one(fiches[0], srcs[0]))
    else:
        plan = ask_json(p_plan(fiches))
        out["plan"] = plan
        authors = [f["auteur"] for f in fiches]
        text = repair(ask(p_write(fiches, plan)), plan)
        out["write"] = text
        best, rounds = None, []
        for _ in range(7):  # longueur d'abord, puis forme, puis jury ; on garde la meilleure version
            errs, n = checks(text, authors)
            if not 270 <= n <= 330:
                rounds.append({"n": n, "errs": errs})
                text = repair(ask(p_condense(text, authors, plan)), plan)
                continue
            j = None if errs else ask_json(p_jury(fiches, text))
            rounds.append({"n": n, "errs": errs, "note": (j or {}).get("note"), "defauts": (j or {}).get("defauts") or []})
            score = (float((j or {}).get("note") or 0) if j else 0) - 3 * len(errs)
            if not best or score > best["score"]:
                best = {"text": text, "words": n, "errs": errs, "jury": j, "score": score}
            fixes = errs + (((j or {}).get("defauts") or []) if j and float(j.get("note") or 0) < 17 else [])
            if not fixes:
                break
            text = repair(ask(p_write(fiches, plan, fixes, text)), plan)
        if not best:
            errs, n = checks(text, authors)
            best = {"text": text, "words": n, "errs": errs, "jury": ask_json(p_jury(fiches, text))}
        best.pop("score", None)
        out["review"] = {**best, "rounds": rounds}
        log(f"  Synthèse : {best['words']} mots, note du jury {(best['jury'] or {}).get('note')}, {len(rounds)} tour(s)")
        out["dialogue"] = ask_json(p_dialogue(fiches))
    log(f"  Synthèse terminée en {(time.time() - t0) / 60:.1f} min")
    return out


def request_from(body):
    """La demande écrite par l'application dans le corps de la demande GitHub (bloc JSON)."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", body or "", re.S)
    req = json.loads(m.group(1) if m else body)
    sid = re.sub(r"[^a-z0-9-]", "", str(req.get("id", "")).lower())[:40]
    papers = [{k: str(p.get(k) or "")[:3000] for k in ("title", "authors", "year", "venue", "url", "pdf", "abstract")}
              for p in (req.get("papers") or [])[:MAX_PAPERS] if p.get("title")]
    if not sid or not papers:
        raise ValueError("demande incomplète")
    return sid, papers


def main():
    code = os.environ.get("ACTU_READ_KEY", "").strip()
    if not code:
        log("Synthèse : pas de code de lecture (secret ACTU_READ_KEY)")
        return 1
    sid, papers = request_from(os.environ.get("REQUEST", ""))
    log(f"Synthèse {sid} : {len(papers)} article(s)")
    try:
        result = {"id": sid, "papers": papers, "out": synthesize(papers), "model": MODEL, "finished": int(time.time() * 1000)}
    except Exception as e:
        result = {"id": sid, "papers": papers, "error": f"{e}", "finished": int(time.time() * 1000)}
        log(f"Synthèse impossible : {e}")
    path = DATA / "syntheses" / f"{sid}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encrypt(key_from(code), result))
    print(f"::notice::{'erreur' if result.get('error') else 'ok'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
