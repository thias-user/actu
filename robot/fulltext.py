"""Texte intégral des articles en accès libre, pour les lire dans l'application → app/data/texts/AAAA-MM-JJ.bin

Le site d'ACTU est public : les textes des journaux n'y sont donc jamais publiés en clair. Ils sont chiffrés
(AES-256-GCM) avec votre code de lecture personnel (secret GitHub ACTU_READ_KEY), que seule votre application connaît.
On ne prend que ce que le journal donne librement : rien de payant, rien sur un site qui refuse les robots (robots.txt).
"""
import gzip
import hashlib
import json
import os
import re
import secrets
import urllib.error
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from common import DATA, fetch, log, parallel, read_json, write_json
from news import day_path

SALT = b"actu-lecture-v1"
ITERATIONS = 150_000
MIN_WORDS = 150
_robots = {}


def normalize_code(code):
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def new_code():
    """Code de lecture lisible : 16 caractères (80 bits), ex. K7QD-M2XP-9FTA-HV3N."""
    alphabet = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def key_from(code):
    return hashlib.pbkdf2_hmac("sha256", normalize_code(code).encode(), SALT, ITERATIONS, 32)


def encrypt(key, obj):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    data = gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode())
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def decrypt(key, blob):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return json.loads(gzip.decompress(AESGCM(key).decrypt(blob[:12], blob[12:], None)))


def allowed(url):
    """Respecte le fichier robots.txt du journal (norme RFC 9309)."""
    p = urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        try:
            rp.parse(fetch(base + "/robots.txt", timeout=10, retries=0).decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            rp.parse([] if 400 <= e.code < 500 else ["User-agent: *", "Disallow: /"])
        except Exception:
            rp.parse(["User-agent: *", "Disallow: /"])  # injoignable : dans le doute, on s'abstient
        _robots[base] = rp
    return _robots[base].can_fetch("ACTU-bot", url)


def paywalled(html):
    """Le journal déclare-t-il l'article payant (données schema.org isAccessibleForFree) ?"""
    for block in re.findall(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", html, re.S | re.I):
        m = re.search(r'"isAccessibleForFree"\s*:\s*"?(true|false)"?', block, re.I)
        if m and m.group(1).lower() == "false":
            return True
    return False


def read_full(article):
    import trafilatura
    url = article["url"]
    if not allowed(url):
        return ""
    html = fetch(url, timeout=15, retries=0, max_bytes=2_500_000).decode("utf-8", "replace")
    if paywalled(html):
        return ""
    text = trafilatura.extract(html, url=url, favor_precision=True, include_comments=False, include_tables=False,
                               deduplicate=True) or ""
    title = article["title"].strip().lower()
    paras = [p.strip() for p in text.split("\n") if p.strip() and p.strip().lower() != title]
    if sum(len(p.split()) for p in paras) < MIN_WORDS:
        return ""  # trop court : simple chapeau d'un article réservé aux abonnés
    return "\n".join(paras)[:40000]


def update(days):
    code = os.environ.get("ACTU_READ_KEY", "").strip()
    if not code:
        log("Lecture intégrale : pas de code (secret ACTU_READ_KEY), étape ignorée")
        return
    key = key_from(code)
    total = readable = 0
    for d in days:
        ed = read_json(day_path(d))
        if not ed:
            continue
        path = DATA / "texts" / f"{d.isoformat()}.bin"
        texts = {}
        if path.exists():
            try:
                texts = decrypt(key, path.read_bytes())
            except Exception:
                texts = {}  # code de lecture changé : on refait tout
        arts = [a for r in ed["regions"].values() for a in r]
        todo = [a for a in arts if a["id"] not in texts]
        for a, t in zip(todo, parallel(read_full, todo, workers=8)):
            texts[a["id"]] = t or ""  # "" = indisponible (payant, refusé ou trop court)
        ids = {a["id"] for a in arts}
        texts = {k: v for k, v in texts.items() if k in ids}
        changed = False
        for a in arts:
            full = bool(texts.get(a["id"]))
            if a.get("full") != full:
                a["full"] = full
                changed = True
        if todo or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encrypt(key, texts))
        if changed:
            write_json(day_path(d), ed)
        total += len(arts)
        readable += sum(bool(v) for v in texts.values())
    log(f"Lecture intégrale : {readable}/{total} articles lisibles en entier dans l'app")


if __name__ == "__main__":
    print(new_code())
