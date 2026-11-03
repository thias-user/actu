"""Synthèse autonome de chaque article pour le schéma « En un coup d'œil » : quoi, qui fait quoi, quand, comment, pourquoi.

Gratuit : les phrases sont choisies dans l'article (mots rares, liens avec le titre, indices de cause, de moyen, de date).
Quand l'article n'explique pas pourquoi, trois hypothèses présentées comme telles, nourries par le contexte du pays
(profiles.py). Une phrase n'est utilisée qu'une fois dans le schéma.
"""
import re
from datetime import date, timedelta

from common import idf_table, norm, tokens
from scenes import FLAGS

BAD_START = {  # phrases qui renvoient à une phrase précédente : peu lisibles seules
    "fr": r"(il|elle|ils|elles|on|cela|ça|celui|celle|ceux|cette|ces|lui|leur|mais|pourtant|cependant|toutefois|en revanche|"
          r"par ailleurs|de son côté|de leur côté|ainsi|or|donc|et|puis|aussi|là|selon (lui|elle|eux)|pour cela|pour autant|en effet|"
          r"de plus|en outre|dans ce cadre|à cet égard|c['’]est|ce dernier|cette dernière|celui-ci|celle-ci)\b",
    "en": r"(he|she|they|it|its|this|that|these|those|but|however|also|and|so|still|yet|meanwhile|there|here|his|her|their)\b",
    "es": r"(él|ella|ellos|ellas|esto|este|esta|estos|estas|eso|ese|esa|pero|sin embargo|además|también|y|así|allí|aquí|su|sus)\b",
}
BAD_RX = {k: re.compile(r"^[«“\"'\s]*" + v, re.I) for k, v in BAD_START.items()}

WHY_CUES = {
    "fr": r"\b(parce qu|car\b|en raison d|à cause d|a cause d|du fait d|faute d|afin d|dans le but d|pour (?:protester|dénoncer|denoncer|"
          r"obtenir|éviter|eviter|réclamer|reclamer|exiger|contester|lutter|répondre|repondre|financer|protéger|proteger|limiter|"
          r"réduire|reduire|sanctionner|punir|relancer|freiner|empêcher|empecher)|en réponse à|en reponse a|en représailles|"
          r"en represailles|sur fond d|s['’]explique|explique[nt]? (?:par|que)|la raison (?:de|pour|en est)|les raisons (?:de|du|des|pour)|"
          r"pour cette raison|motif (?:de|du|des)|motivée?s? par|provoquée?s? par|causée?s? par|dans un contexte d|en cause|pour que|"
          r"afin que|la cause|les causes|est dûe? à|est due à|sont dus à|tient à|tiennent à|s['’]expliquer par|lié à|liée à|"
          r"vise à|visent à|visant à)",
    "en": r"\b(because|due to|owing to|as a result of|in response to|in retaliation|in order to|so that|aimed at|amid|driven by|"
          r"fueled by|fuelled by|blamed|caused by|the reason|reasons for|motivated by|to protest|to demand|to avoid|to prevent|"
          r"to counter|prompted by|triggered by|the cause|the causes|stems from|stemming from|results from|resulting from|linked to|"
          r"aims to|seeks to|in a bid to)\b",
    "es": r"\b(porque|debido a|a causa de|por culpa de|con el fin de|para (?:protestar|exigir|denunciar|evitar|reclamar|frenar|"
          r"combatir|impedir)|en respuesta a|en represalia|en medio de|el motivo|los motivos|la razón|la razon|las razones|"
          r"causad[oa]s? por|provocad[oa]s? por|impulsad[oa]s? por|lo que explica|se explica|la causa|las causas|se debe a|se deben a|"
          r"vinculad[oa]s? a)",
}
HOW_CUES = {
    "fr": r"(\b(grâce à|grace a|au moyen d|à l['’]aide d|par le biais d|via|à travers|a travers|par (?:décret|decret|ordonnance|"
          r"référendum|referendum|voie|amendement|un vote)|prévoit|prevoit|consiste|dispositif|mécanisme|mecanisme|procédure|"
          r"procedure|d['’]abord|ensuite|étape|etape|plan de)\b|\ben (?!tant\b|avant\b|attendant\b|cours\b)[a-zéèêàâîôûç]{3,}ant\b)",
    "en": r"\b(by (?:using|\w+ing)|through|using|via|with the help of|by means of|mechanism|procedure|the plan|would allow|"
          r"allows|will require|requires|under the (?:plan|deal|agreement|law|bill|proposal)|first|step)\b",
    "es": r"(\b(mediante|a través de|a traves de|gracias a|por medio de|con ayuda de|mecanismo|procedimiento|el plan|prevé|preve|"
          r"consiste|primero|por decreto)\b|\b(?!cuando\b)[a-záéíóúñ]{3,}(?:ando|iendo)\b)",
}
WHY_RX = {k: re.compile(v, re.I) for k, v in WHY_CUES.items()}
HOW_RX = {k: re.compile(v, re.I if k == "en" else 0) for k, v in HOW_CUES.items()}
FIGURE_RX = re.compile(r"\d[\d\s.,]*\s?(%|€|\$|euros?|dollars?|millions?|milliards?|billions?|pesos|personnes|people|personas|morts|"
                       r"dead|muertos|blessés|blesses|injured|heridos|victimes|victims|víctimas|km|kilomètres|tonnes|tons|toneladas|"
                       r"habitants|residents|habitantes|emplois|jobs|empleos|voix|votes|votos|sièges|seats|escaños)", re.I)

MONTHS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9,
          "octobre": 10, "novembre": 11, "decembre": 12, "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
          "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12, "jan": 1, "feb": 2, "aug": 8,
          "sept": 9, "oct": 10, "nov": 11, "dec": 12, "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
          "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
FR_MONTHS = "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.".split()
FULL_MONTHS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
FR_DAYS = "lundi mardi mercredi jeudi vendredi samedi dimanche".split()
_M = r"(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|enero|febrero|" \
     r"marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|January|February|March|April|May|June|" \
     r"July|August|September|October|November|December)"
_Y = r"((?:1[0-9]|20)\d\d)"
DAY_MONTH = re.compile(r"\b(1er|[0-3]?\d)\s+(?:de\s+)?" + _M + r"(?:,?\s+(?:de\s+)?" + _Y + r")?\b", re.I)
MONTH_DAY = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan\.|Feb\.|Aug\.|"
                       r"Sept\.|Oct\.|Nov\.|Dec\.)\s+([0-3]?\d)(?:st|nd|rd|th)?\b(?:,?\s+" + _Y + r")?")
MONTH_YEAR = re.compile(r"\b" + _M + r"\s+(?:de\s+|of\s+)?" + _Y + r"\b", re.I)
YEAR_ONLY = re.compile(r"\b(?:en|depuis|dès|des|avant|après|apres|fin|début|debut|d['’]ici(?: à)?|jusqu['’]en|in|since|by|before|after|"
                       r"until|from|early|late|desde|hasta|antes de|después de|despues de|a finales de|a principios de|para)\s+" + _Y +
                       r"\b(?![\s ]*(?:[%€$]|euros?|dollars?|pesos|personnes|people|personas|habitants|exemplaires|mètres|metros|"
                       r"meters|km|kg|tonnes|millions?|millones|places|plazas|jobs|emplois))", re.I)
WEEKDAYS = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6, "monday": 0, "tuesday": 1,
            "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6, "lunes": 0, "martes": 1, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}
WEEKDAY_RX = re.compile(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|"
                        r"Sunday|lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b", re.I)
FUTURE_RX = re.compile(r"\b(prochain\w*|va |vont |devra\w*|devr(?:ait|aient)|sera\b|seront\b|aura lieu|next|will|upcoming|scheduled|"
                       r"expected|set to|is due|are due|head to|prévue?s?|doi(?:t|vent) (?:se|être|avoir)|se tiendra|previst[oa]s?|"
                       r"ahead of|run-up to|à l['’]approche d|en vue d|de cara a|"
                       r"se espera|se realizará|tendrá|"
                       r"(?:pour|dès|des|à partir de|starting|from|a partir del|para el) (?:ce |el |this )?(?:lundi|mardi|mercredi|jeudi|"
                       r"vendredi|samedi|dimanche|monday|tuesday|wednesday|thursday|friday|saturday|sunday|lunes|martes|miércoles|"
                       r"jueves|viernes|sábado|domingo)|"
                       r"próxim\w*|proxim\w*|será\b|serán\b|tendrá lugar)", re.I)


PAST_RX = re.compile(r"\b(dernier|dernière|last|pasad[oa]|a eu lieu|ont eu lieu|took place|tuvo lugar)\b", re.I)


def shorten(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[:cut.rfind(" ")].rstrip(",;:") + "…"


QUOTED = re.compile(r"[«“\"][^«“”»\"]{8,}[»”\"]")
END_OK = tuple(".!?…»”\")")


def quoted(s):
    """Phrase surtout faite de citation (ou citation coupée) : peu explicative seule."""
    inside = sum(len(m.group(0)) for m in QUOTED.finditer(s))
    opens, closes = sum(s.count(c) for c in "«“"), sum(s.count(c) for c in "»”")
    return inside > 0.5 * len(s) or opens != closes


def similar(a, b):
    return len(a & b) / max(1, min(len(a), len(b))) > 0.55


class Picker:
    """Classe les phrases de l'article et retient celles déjà utilisées dans le schéma."""

    def __init__(self, sents, title, lang):
        self.sents = sents
        self.sets = [set(tokens(s)) for s in sents]
        self.idf = idf_table(self.sets) if sents else {}
        self.tset = set(tokens(title))
        self.bad = BAD_RX.get(lang, BAD_RX["fr"])
        self.used = set()
        self.core = self.tset | (self.sets[0] if self.sets else set())

    def relevant(self, i):
        """La phrase parle bien du sujet de l'article (mots du titre ou du chapeau)."""
        return len(self.sets[i] & self.core) >= 2

    def score(self, i):
        s, st = self.sents[i], self.sets[i]
        if not st:
            return -99
        sc = sum(self.idf.get(t, 1) for t in st) / (len(st) ** 0.5) + 2.5 * len(st & self.tset) - 0.12 * i
        if self.bad.match(s):
            sc -= 4
        if quoted(s):
            sc -= 1.5
        if not s.rstrip().endswith(END_OK):
            sc -= 3  # intertitre ou légende
        if len(s) > 420 or len(s) < 50:
            sc -= 2
        return sc

    def best(self, k, test=None, start=0, keep_order=True):
        cand = [i for i in range(start, len(self.sents)) if i not in self.used and (test is None or test(self.sents[i]))]
        top = sorted(cand, key=self.score, reverse=True)[:k]
        return sorted(top) if keep_order else top

    def take(self, idx):
        self.used.update(idx)
        return [self.sents[i] for i in idx]


def summary(p, max_chars=640):
    """Quoi : l'essentiel en 2 à 4 phrases, lisibles sans l'article (le chapeau d'abord, s'il se suffit à lui-même)."""
    if not p.sents:
        return ""
    lead = [0] if len(p.sents[0]) >= 60 and not p.bad.match(p.sents[0]) else []
    picked, total = list(lead), sum(len(p.sents[i]) for i in lead)
    for i in p.best(6, start=1, keep_order=False):
        if total + len(p.sents[i]) > max_chars or len(picked) >= 4:
            continue
        if p.score(i) < -1 and picked:
            continue
        if any(similar(p.sets[i], p.sets[j]) for j in picked):
            continue  # la même information, redite plus loin
        picked.append(i)
        total += len(p.sents[i])
    picked = sorted(picked)[:4] or [0]
    return " ".join(p.take(picked))


def mentions(actor, sentence):
    if actor.get("kind") == "pays":
        return any(FLAGS.get(t) == actor["country"] for t in tokens(sentence)) or actor["name"] in sentence
    key = actor["name"].split()[-1]
    return bool(re.search(r"(?<![\wÀ-ÿ])" + re.escape(key) + r"(?![\wÀ-ÿ])", sentence))


def role_of(p, actor):
    """Qui : ce que fait ou dit cet acteur dans l'histoire (une phrase de l'article où il est sujet, de préférence)."""
    if actor.get("group"):
        return ""
    key = actor["name"].split()[-1]

    def subject(s):
        pos = s.find(key)
        return mentions(actor, s) and (pos < 0 or pos < len(s) * 0.6)
    idx = p.best(1, subject) or p.best(1, lambda s: mentions(actor, s))
    return p.take(idx)[0] if idx else ""


def _date_in(s, d):
    """Première date d'une phrase → (clé de tri, libellé) ou None."""
    future = bool(FUTURE_RX.search(s))
    m = DAY_MONTH.search(s)
    if m:
        day = 1 if m.group(1).lower() == "1er" else int(m.group(1))
        mon = MONTHS.get(norm(m.group(2)).strip())
        year = int(m.group(3)) if m.group(3) else None
    else:
        m = MONTH_DAY.search(s)
        if m:
            mon, day = MONTHS.get(norm(m.group(1)).strip().rstrip(".")), int(m.group(2))
            year = int(m.group(3)) if m.group(3) else None
    if m and mon and 1 <= day <= 31:
        if year is None:
            year = d.year
            try:
                if date(year, mon, day) > d + timedelta(days=31) and not future:
                    year -= 1
            except ValueError:
                return None
        try:
            when = date(year, mon, day)
        except ValueError:
            return None
        label = f"{'1er' if day == 1 else day} {FR_MONTHS[mon - 1]}" + (f" {year}" if year != d.year else "")
        return when.isoformat(), label
    m = MONTH_YEAR.search(s)
    if m and MONTHS.get(norm(m.group(1)).strip()):
        mon, year = MONTHS[norm(m.group(1)).strip()], int(m.group(2))
        return f"{year}-{mon:02d}-00", f"{FULL_MONTHS[mon - 1]} {year}"
    m = YEAR_ONLY.search(s)
    if m:
        year = int(m.group(1))
        if 1000 <= year <= d.year + 30:
            return f"{year}-00-00", str(year)
    m = WEEKDAY_RX.search(s)
    if m:
        wd = WEEKDAYS[norm(m.group(1)).strip()]
        ahead, back = (wd - d.weekday()) % 7, (d.weekday() - wd) % 7
        if PAST_RX.search(s):
            future = False
        elif not future:
            future = ahead < back  # sans indice, le jour le plus proche (« mardi » dans un article du lundi : demain)
        when = d + timedelta(days=ahead) if future and ahead else d - timedelta(days=back)
        return when.isoformat(), f"{FR_DAYS[wd]} {when.day if when.day > 1 else '1er'} {FR_MONTHS[when.month - 1]}"
    return None


def timeline(p, d, k=4):
    """Quand : les dates citées dans l'article (événements passés, échéances à venir), dans l'ordre."""
    found = {}
    order = sorted(range(len(p.sents)), key=lambda i: (i in p.used, -p.score(i)))
    for i in order:
        hit = _date_in(p.sents[i], d)
        if not hit or hit[0] in found:
            continue
        found[hit[0]] = (i, hit[1])
        if len(found) == k:
            break
    items = []
    for key, (i, label) in sorted(found.items()):
        items.append({"k": key, "d": label, "t": p.sents[i]})
    return items


def cue(rx, s):
    """Premier indice trouvé hors des citations (une cause citée entre guillemets n'est qu'un avis)."""
    spans = [m.span() for m in QUOTED.finditer(s)]
    return next((m for m in rx.finditer(s) if not any(a <= m.start() < b for a, b in spans)), None)


def how(p, lang):
    """Comment : les moyens, le déroulé, et un chiffre clé."""
    rx = HOW_RX.get(lang, HOW_RX["fr"])
    ok = {i for i in range(len(p.sents)) if not quoted(p.sents[i]) and p.relevant(i)}
    out = [{"t": s, "k": "moyen"} for s in p.take([i for i in p.best(4, lambda s: bool(cue(rx, s))) if i in ok][:2])]
    fig = [i for i in p.best(3, lambda s: bool(FIGURE_RX.search(s)) and not re.match(r"^\W*\d{4}\b", s)) if i in ok][:1]
    out += [{"t": s, "k": "chiffre"} for s in p.take(fig)]
    return out


def why(p, lang):
    """Pourquoi : les causes que donne l'article."""
    rx = WHY_RX.get(lang, WHY_RX["fr"])
    idx = [i for i in p.best(4, lambda s: bool(cue(rx, s))) if p.score(i) > -1 and p.relevant(i) and not quoted(p.sents[i])][:2]
    out = p.take(idx)
    if not out:  # la cause est dans une phrase déjà reprise (souvent le chapeau) : on la redonne en entier
        for i in sorted(p.used):
            m = cue(rx, p.sents[i])
            if m and p.relevant(i) and len(cause_clause(p.sents[i], m.start())) >= 40:
                return [p.sents[i]]
    return out


def cause_clause(s, start):
    """La proposition qui donne la cause (sert à juger si elle est assez précise)."""
    rest = s[start:]
    end = re.search(r"[.;!?](\s|$)", rest)
    rest = rest[:end.start()] if end else rest
    comma = rest.find(",", 25)
    return (rest[:comma] if comma > 0 else rest).strip(" ,;:")


HYPOTHESES = {
    "attaque": ["{qui} chercherait à prendre l’avantage sur le terrain{contre}, pour peser sur d’éventuelles négociations.",
                "Il pourrait s’agir d’une riposte à une action précédente, dans un engrenage de représailles.",
                "L’objectif pourrait aussi être politique : montrer sa force à sa population, à ses alliés ou à l’adversaire."],
    "accident": ["Une défaillance technique ou un défaut d’entretien.",
                 "Des conditions extérieures défavorables : météo, terrain, surcharge.",
                 "Une erreur humaine ou un manquement aux règles de sécurité ; seule l’enquête pourra trancher."],
    "manifeste": ["Le rejet d’une réforme ou d’une décision des autorités{chef}.",
                  "Des difficultés économiques ressenties au quotidien{eco}.",
                  "Une mobilisation calée sur le calendrier : peser avant un vote, une négociation ou une échéance."],
    "vote": ["La situation économique{eco} pèse souvent sur le choix des électeurs.",
             "Le bilan du pouvoir en place{chef} et l’usure du pouvoir{instable}.",
             "Les alliances entre partis et le niveau de participation."],
    "marche": ["Un déséquilibre entre l’offre et la demande : production, stocks, consommation.",
               "Le niveau des taux d’intérêt et la politique des banques centrales{eco}.",
               "Le contexte international : prix de l’énergie, tensions commerciales, conflits."],
    "juge": ["Les faits reprochés et les preuves réunies pendant l’enquête.",
             "Une procédure lancée par une plainte ou un signalement, qui suit son propre calendrier.",
             "La volonté de la justice de marquer les esprits sur ce type d’affaires."],
    "arrete": ["Des soupçons accumulés au fil d’une enquête.",
               "Un flagrant délit ou un signalement précis.",
               "Une opération plus large visant un réseau."],
    "negocie": ["Le coût de la situation actuelle pousse les parties à discuter.",
                "Une pression extérieure : alliés, médiateurs ou opinion publique.",
                "Chaque camp cherche des garanties avant une échéance."],
    "signe": ["Un intérêt commun, économique ou sécuritaire, plus fort que les désaccords.",
              "La pression du calendrier ou d’un partenaire extérieur.",
              "La volonté de montrer des résultats concrets à l’opinion."],
    "demission": ["Une pression politique ou médiatique devenue trop forte{instable}.",
                  "Un désaccord de fond avec la ligne suivie.",
                  "Une affaire en cours ou des raisons personnelles."],
    "avertit": ["Des signaux inquiétants relevés dans les données ou par les experts.",
                "La volonté de faire réagir les autorités ou l’opinion.",
                "Une prise de position avant une décision ou une négociation."],
    "decouvre": ["De nouveaux outils ou de nouvelles données ont permis d’aller plus loin.",
                 "L’aboutissement d’un travail de longue haleine.",
                 "Une observation inattendue, parfois due au hasard."],
    "lance": ["Répondre à une demande ou à la concurrence.",
              "Prendre de l’avance sur un marché ou sur un sujet.",
              "Un calendrier politique ou commercial : annoncer avant une échéance."],
    "aide": ["Une situation d’urgence qui l’exige.",
             "Des intérêts politiques ou stratégiques communs.",
             "La pression de l’opinion ou des partenaires."],
    "hommage": ["La place que la personne ou l’événement occupe dans la mémoire collective.",
                "Un anniversaire ou une cérémonie qui rassemble.",
                "La volonté de transmettre ce souvenir aux générations suivantes."],
    "sport": ["La forme du moment et la préparation.",
              "Le rapport de force et les choix tactiques.",
              "Les circonstances : blessures, conditions de jeu, détails décisifs."],
    "sante": ["Des moyens de santé sous tension : personnels, budgets{eco}.",
              "L’évolution d’une maladie ou d’une épidémie.",
              "Des décisions des autorités sanitaires ou des laboratoires."],
    "annonce": ["Répondre à une attente ou à une pression : opinion, partenaires, concurrents.",
                "Prendre l’initiative avant une échéance : vote, négociation, publication de résultats.",
                "Un changement de situation qui oblige à réagir."],
}
# pour les actions peu précises (annonce, alerte, lancement…), des pistes propres au thème de l'article
TOPIC_HYPOTHESES = {
    "politique": ["Un calcul politique : se positionner avant une échéance électorale ou un vote{instable}.",
                  "La pression de l’opinion, des alliés ou de l’opposition sur le pouvoir en place{chef}.",
                  "La situation économique{eco_plain}, qui pèse sur les choix des responsables."],
    "economie": ["Une stratégie pour gagner des clients, des parts de marché ou de la rentabilité.",
                 "La pression de la concurrence ou des coûts : énergie, salaires, taux d’intérêt.",
                 "La conjoncture économique{eco_plain}."],
    "guerre": ["Une évolution du rapport de force sur le terrain.",
               "Une stratégie pour peser sur d’éventuelles négociations.",
               "La recherche de soutiens : alliés, aide militaire, opinion internationale."],
    "culture": ["Une stratégie pour attirer le public ou gagner en visibilité.",
                "Des tensions internes ou financières dans le milieu concerné.",
                "Le calendrier culturel : sortie, festival, saison, anniversaire."],
    "diplomatie": ["Renforcer une relation ou rassurer un partenaire.",
                   "Des intérêts communs, économiques ou militaires.",
                   "Un message adressé à un pays tiers ou à l’opinion."],
    "sante": ["Les progrès de la recherche ou d’une technologie rendent possible ce qui ne l’était pas.",
              "Un besoin des patients ou des soignants resté sans réponse.",
              "Des moyens de santé sous tension : personnels, budgets."],
    "catastrophe": ["Des phénomènes météorologiques extrêmes, plus fréquents avec le réchauffement climatique.",
                    "Des constructions ou des infrastructures mal adaptées aux risques.",
                    "Un manque de prévention ou d’alerte ; les enquêtes devront le dire."],
    "tech": ["La course à l’innovation entre entreprises et entre pays.",
             "Un besoin des utilisateurs ou un nouveau marché à prendre.",
             "Une réglementation qui se durcit, ou qui tarde à venir."],
    "cyber": ["L’appât du gain : rançon, revente de données.",
              "De l’espionnage ou une opération soutenue par un État.",
              "Des failles de sécurité connues mais pas encore corrigées."],
    "transport": ["Des infrastructures vieillissantes ou saturées.",
                  "Des choix budgétaires ou un conflit social{eco}.",
                  "Une hausse de la demande ou un changement des habitudes."],
    "climat": ["Les effets du réchauffement climatique.",
               "Des engagements internationaux ou une pression citoyenne.",
               "Des intérêts économiques et le coût de l’énergie{eco}."],
    "education": ["Des moyens jugés insuffisants : postes, budgets{eco}.",
                  "Une réforme contestée ou mal comprise.",
                  "Des inégalités entre territoires ou entre élèves."],
    "religion": ["Des tensions entre convictions religieuses et règles de la société.",
                 "Une évolution des pratiques et du nombre de fidèles.",
                 "Un enjeu politique autour de la religion."],
}
TOPIC_ALIAS = {"election": "politique", "gouvernement": "politique", "bourse": "economie", "musique": "culture", "espace": "tech",
               "science": "tech", "energie": "climat", "environnement": "climat", "manifestation": "politique"}
TOPIC_KIND = {"justice": "juge", "police": "arrete", "sport": "sport", "f1": "sport", "manifestation": "manifeste"}
VAGUE = {"annonce", "avertit", "lance", "aide", "negocie", "sante"}


def eco_note(prof):
    v, c = (prof or {}).get("valeurs", {}), (prof or {}).get("classes", {})
    if v.get("inflation_n", 0) >= 6:
        return f", dans un contexte de forte inflation ({v['inflation']})"
    if v.get("chomage_n", 0) >= 10:
        return f", dans un contexte de chômage élevé ({v['chomage']})"
    if c.get("croissance") == "en récession":
        return f", dans un contexte de récession ({v.get('croissance', '')})"
    if c.get("croissance") == "à croissance faible" and v.get("croissance"):
        return f", dans un contexte de croissance faible ({v['croissance']})"
    return ""


def hypotheses(story, topic, prof):
    """Trois pistes quand l'article ne dit pas pourquoi. Aucune sur la santé d'une personne nommée."""
    kind = story["action"]["kind"]
    actors = story["actors"]
    who = actors[story["action"]["who"]] if actors else None
    if kind == "sante" and who and who.get("kind") == "nom" and not who.get("group"):
        return []
    if kind in ("victoire", "defaite"):
        kind = "vote" if topic in ("politique", "election", "gouvernement") else "sport"
    if topic in ("sport", "f1") and kind not in ("accident", "juge", "arrete", "hommage", "demission"):
        kind = "sport"
    if kind in ("hausse", "baisse"):
        kind = "marche" if topic in ("economie", "bourse", None) else "annonce"
    theme = TOPIC_ALIAS.get(topic, topic)
    if theme == "politique" and kind == "manifeste":
        theme = None
    if kind in VAGUE and theme in TOPIC_HYPOTHESES:
        templates = TOPIC_HYPOTHESES[theme]
    elif kind in VAGUE and topic in TOPIC_KIND:
        templates = HYPOTHESES[TOPIC_KIND[topic]]
    else:
        templates = HYPOTHESES.get(kind) or HYPOTHESES["annonce"]
    target = actors[story["action"]["target"]]["name"] if story["action"]["target"] >= 0 and len(actors) > story["action"]["target"] else ""
    chef = (prof or {}).get("valeurs", {}).get("chef")
    fill = {"qui": (who or {}).get("name", "L’un des camps"), "contre": f" face à {target}" if target else "",
            "eco": eco_note(prof), "eco_plain": eco_note(prof).replace(", dans un contexte de", " :"),
            "chef": f" (gouvernement de {chef})" if chef else "",
            "instable": ", dans un contexte d’instabilité gouvernementale" if (prof or {}).get("classes", {}).get("instable") else ""}
    return [t.format(**fill) for t in templates]


# ---------------------------------------------------------------- regard critique
# Ce que l'article dit, mais aussi comment il le dit : qui parle, ce qui n'est pas établi, ce qui est contesté.
SAID_CUES = {
    "fr": r"\b(?:a|ont|avait|avaient) (?:déclaré|indiqué|affirmé|expliqué|précisé|annoncé|estimé|assuré|souligné|confié|dit|ajouté|"
          r"répondu|dénoncé|reconnu|admis|averti|jugé)|\b(?:déclare|affirme|explique|estime|assure|souligne|ajoute|indique|selon|"
          r"d['’]après|témoigne|raconte)\b|-t-(?:il|elle|ils|elles)\b",
    "en": r"\b(?:said|says|told|according to|stated|announced|added|wrote|argued|explained|noted|claimed|insisted|warned)\b",
    "es": r"\b(?:dijo|afirmó|señaló|indicó|aseguró|según|explicó|declaró|sostuvo|añadió|agregó|precisó|manifestó|advirtió)\b",
}
ANON_CUES = {
    "fr": r"\b(?:une source|des sources|plusieurs sources|source proche|sources proches|selon nos informations|sous couvert d['’]anonymat|"
          r"requis l['’]anonymat|requérant l['’]anonymat|souhaité garder l['’]anonymat|un proche du dossier|un connaisseur du dossier)",
    "en": r"\b(?:a source|sources said|sources told|people familiar|person familiar|on condition of anonymity|requested anonymity|"
          r"asked not to be named|declined to be named|speaking anonymously|an official who)",
    "es": r"\b(?:una fuente|fuentes cercanas|fuentes consultadas|fuentes oficiales|bajo condición de anonimato|pidió no ser identificad\w+|"
          r"prefirió el anonimato)",
}
DOUBT_CUES = {
    "fr": r"\b(?:aurai(?:t|ent) (?:été|eu|fait|tué|reçu)|serai(?:t|ent) (?:responsable|impliqu\w+|à l['’]origine)|non confirmé\w*|"
          r"pas (?:encore )?(?:été )?confirmé\w*|pas (?:pu être )?vérifié\w*|présumée?s?|supposée?s?|reste(?:nt)? à (?:établir|confirmer|"
          r"déterminer|prouver)|on ignore|on ne sait pas|incertitude\w*|zones? d['’]ombre|flou\w*|selon des informations)",
    "en": r"\b(?:reportedly|allegedly|alleged|unconfirmed|could not (?:be )?(?:independently )?(?:verify|verified|confirm|confirmed)|"
          r"it is (?:not|un)clear|remains? unclear|it was not immediately clear|apparently|may have been|might have)\b",
    "es": r"\b(?:presunt\w+|supuestamente|al parecer|sin confirmar|no (?:ha sido|fue) confirmad\w+|no está claro|se desconoce|"
          r"habría(?:n)? (?:sido|sufrido|recibido|matado))\b",
}
DISPUTE_CUES = {
    "fr": r"\b(?:dément\w*|démenti\w*|nie(?:nt)?|a nié|ont nié|conteste\w*|contesté\w*|récuse\w*|réfute\w*|s['’]inscrit en faux|"
          r"se (?:dit|disent|déclare) innocent\w*|dénonce\w* (?:des|une|un) (?:accusations?|mensonges?|manipulation))",
    "en": r"\b(?:denied|denies|disputed|disputes|rejected the|rejects the|refuted|pushed back|baseless|false claims|maintains? (?:his|her|their) innocence)\b",
    "es": r"\b(?:negó|niega|niegan|desmintió|desmiente|rechazó las|rechaza las|refutó|cuestionó|inocencia)\b",
}
STRONG_RX = re.compile(r"\b(choc|historique|scandale|polémique|incroyable|explosi(?:f|ve)|fiasco|chaos|humiliation|terrifiant\w*|"
                       r"inédit\w*|shocking|stunning|slams|blasts|historic|bombshell|outrage|furious|devastating|unprecedented|"
                       r"escándalo|polémica|históric[oa]|impactante|insólit[oa]|brutal)\b", re.I)
OPINION_RX = re.compile(r"\b(letters?|opinion|editorial|éditorial|édito|tribune|chronique|point de vue|analysis|column|commentary|"
                        r"op-ed|carta|columna|critique|review)\b|on vient de voir|/(?:opinion|idees|tribunes?|chroniques?|"
                        r"editorial|commentisfree|opinion-|blogs?)/", re.I)
FIG_RX = re.compile(r"(?<![\d,.])(\d{1,3}(?:[\s  .,]\d{3})+|\d+(?:[.,]\d+)?)\s*(%|[a-zà-ÿ]{5,})", re.I)
RX = {name: {k: re.compile(v, re.I) for k, v in table.items()}
      for name, table in (("said", SAID_CUES), ("anon", ANON_CUES), ("doubt", DOUBT_CUES), ("dispute", DISPUTE_CUES))}


def _rx(name, lang):
    return RX[name].get(lang, RX[name]["fr"])


def _num(s):
    s = re.sub(r"[\s  ]", "", s)
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def figures_gap(title, sents):
    """Un chiffre du titre que le texte ne reprend pas, alors qu'il en donne un autre pour la même chose."""
    in_title = {m.group(2).lower()[:6]: m for m in FIG_RX.finditer(title)}
    for unit, tm in in_title.items():
        tv = _num(tm.group(1))
        if tv is None or (1900 <= tv <= 2100 and unit != "%"):
            continue
        seen = [m for s in sents for m in FIG_RX.finditer(s) if m.group(2).lower()[:6] == unit]
        values = {_num(m.group(1)) for m in seen}
        if seen and tv not in values:
            other = next(m for m in seen if _num(m.group(1)) is not None)
            if abs(_num(other.group(1)) - tv) > 0.05 * max(tv, 1):
                return f"Le titre annonce {tm.group(0).strip()}, le texte parle de {other.group(0).strip()} : un chiffre a peut-être changé, ou l’un des deux est arrondi."
    return ""


def names(xs):
    xs = list(dict.fromkeys(xs))
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " et " + xs[-1]


def critique(p, a, story, lang):
    """Regard critique tiré de l'article lui-même : genre, titre, sources, doutes, versions contestées, voix, chiffres."""
    out = []
    title = a["title"]
    opinion = bool(OPINION_RX.search(title) or OPINION_RX.search(a.get("url", "")))
    if opinion:
        out.append({"k": "opinion", "t": "Texte d’opinion, de critique ou d’analyse : il défend un point de vue, à lire comme tel."})
    # une citation (au moins trois mots, ou en tête suivie de « : ») ; « “Club Kid”, une comédie… » est un titre d'œuvre
    quotes = re.findall(r"[«“\"]\s*([^»”\"]{3,}?)\s*[»”\"]", title) + re.findall(r"^\s*['‘]([^'’]{3,})['’]", title)
    if any(len(q.split()) >= 3 for q in quotes) or re.match(r"^\s*[«“\"'‘][^»”\"'’]+[»”\"'’]\s*:", title):
        out.append({"k": "titre", "t": "Le titre reprend une citation : c’est la parole de quelqu’un, pas un fait établi par le journal."})
    elif title.rstrip().endswith("?"):
        out.append({"k": "titre", "t": "Le titre pose une question : l’article ne tranche pas forcément."})
    strong = STRONG_RX.search(title)
    if strong:
        out.append({"k": "titre", "t": f"Le titre emploie un mot fort (« {strong.group(0)} ») : il dit l’importance que le journal donne au sujet, pas un fait."})
    if len(p.sents) < 5:
        return out
    said = _rx("said", lang)
    share = sum(bool(said.search(s)) for s in p.sents) / len(p.sents)
    anon = next((s for s in p.sents if _rx("anon", lang).search(s)), None)
    if anon:
        out.append({"k": "anonyme", "t": "Une partie des informations vient de sources anonymes, que le lecteur ne peut pas vérifier :", "q": anon})
    if share == 0 and len(p.sents) >= 8 and not opinion:
        out.append({"k": "sources", "t": "Aucune affirmation n’est attribuée à une source : l’article repose sur le seul récit de son auteur."})
    elif share >= 0.5:
        out.append({"k": "sources", "t": f"L’article s’appuie beaucoup sur des déclarations ({round(share * 100)} % des phrases) : ce sont des positions, "
                                         "à confronter aux faits."})
    for key, label in (("doubt", "Ce qui n’est pas établi :"), ("dispute", "Une version est contestée :")):
        idx = [i for i, s in enumerate(p.sents) if _rx(key, lang).search(s) and p.relevant(i) and s != anon]
        if idx:
            out.append({"k": "doute" if key == "doubt" else "version", "t": label, "q": p.sents[max(idx, key=p.score)]})
    # qui parle, qui ne parle pas (seulement les personnes et organisations vérifiées sur Wikipédia)
    people = [x for x in story["actors"] if x.get("kind") in ("nom", "org") and x.get("wiki")]

    def speaks(x):
        return any(mentions(x, s) and (said.search(s) or QUOTED.search(s)) for s in p.sents)
    heard = [(x.get("wiki") or {}).get("t") or x["name"] for x in people if speaks(x)]
    silent = [(x.get("wiki") or {}).get("t") or x["name"] for x in people if not speaks(x)]
    if heard and silent:
        out.append({"k": "voix", "t": f"On entend {names(heard)}, mais pas {names(silent)} : un point de vue manque peut-être."})
    # combien de personnes s'expriment nommément
    speakers = {m.group(1).split()[-1] for s in p.sents if said.search(s) for m in SPEAKER_RX.finditer(s)
                if norm(m.group(1)).strip() not in NOT_SPEAKERS and not INSTITUTION_RX.search(m.group(1))}
    if len(speakers) == 1 and share >= 0.2:
        out.append({"k": "voix", "t": f"Une seule personne est citée nommément ({next(iter(speakers))}) : un seul regard sur les faits."})
    elif len(speakers) >= 4:
        out.append({"k": "voix", "t": f"{len(speakers)} personnes sont citées nommément : l’article confronte plusieurs points de vue."})
    # mots chargés employés par le journal lui-même (pas dans les citations)
    spans = lambda s: [m.span() for m in QUOTED.finditer(s)]
    loaded = list(dict.fromkeys(m.group(0).lower() for s in p.sents for m in _rx("loaded", lang).finditer(s)
                                if not any(a_ <= m.start() < b_ for a_, b_ in spans(s))))
    if len(loaded) >= 2:
        out.append({"k": "termes", "t": "Le texte emploie des mots chargés (" + ", ".join(f"« {w} »" for w in loaded[:3]) +
                                         ") : ils portent un jugement, que tous ne partagent pas forcément."})
    gap = figures_gap(title, p.sents)
    if gap:
        out.append({"k": "chiffres", "t": gap})
    # ce que l'article laisse sans réponse
    missing = [w for w, ok in (("d’explication sur les causes", bool((story.get("why") or {}).get("facts"))),
                               ("de précision sur le déroulé", bool(story.get("how"))),
                               ("d’indication sur la suite", story.get("_cons_cue", True))) if not ok]
    if len(missing) >= 2:
        out.append({"k": "angles", "t": f"Angles morts possibles : ACTU n’a pas trouvé dans l’article {names(missing)}."})
    # des faits anciens derrière l'actualité du jour
    years = sorted(int(w["k"][:4]) for w in story.get("when") or [] if w["k"][:4].isdigit())
    d_year = int(story["place"]["iso"][:4])
    old = [y for y in years if y < d_year - 1]
    if len(old) >= 2 and len(old) * 2 >= len(years):
        span = f"{old[0]}" if old[0] == old[-1] else f"{old[0]} à {old[-1]}"
        out.append({"k": "anciennete", "t": f"Une bonne part des faits évoqués date de {span} : l’actualité du jour s’inscrit dans une histoire plus longue."})
    return out


SPEAKER_RX = re.compile(r"\b([A-ZÀ-ÖØ-Þ][a-zà-ÿ'’-]+(?:\s+(?:de\s+|del\s+|da\s+|van\s+|von\s+|di\s+)?[A-ZÀ-ÖØ-Þ][a-zà-ÿ'’-]+)+)")
NOT_SPEAKERS = {"new york", "le monde", "united states", "etats unis", "white house", "maison blanche", "la moneda", "kyiv independent",
                "associated press", "agence france presse", "national guard", "supreme court", "corte suprema", "union europeenne",
                "european union", "le figaro", "la tercera", "el pais", "the guardian", "new york times", "washington post"}
INSTITUTION_RX = re.compile(r"\b(Staff|Service|Ministry|Force|Forces|Council|Party|Office|Department|Agency|Police|Guard|Army|Court|"
                            r"House|Bank|Union|Committee|Commission|Ministère|Conseil|Parti|Agence|Garde|Armée|Cour|Banque|Comité|"
                            r"Ministerio|Consejo|Partido|Gobierno|Fuerzas|Policía|Ejército|Tribunal|Banco|Assemblée|Senate|Sénat|"
                            r"Congress|Congrès|Congreso|Institute|Institut|Instituto|University|Université|Universidad|Group|Groupe|"
                            r"Grupo|Association|Asociación|Foundation|Fondation|Fundación|News|Times|Post|Press|Presse|Radio|TV)\b")
LOADED_CUES = {
    "fr": r"\b(?:massacres?|génocides?|terroristes?|régimes? (?:de|du|des|autoritaire)|dictateurs?|dictatures?|propagande|extrémistes?|"
          r"islamistes?|complotistes?|fascistes?|honteu(?:x|se)|scandaleu(?:x|se)|désastreu(?:x|se)|catastrophiques?|inacceptables?|"
          r"ultras?|voyous?|délirant\w*)\b",
    "en": r"\b(?:massacres?|genocide|terrorists?|regime|dictators?|dictatorship|propaganda|extremists?|thugs?|disgrace\w*|"
          r"disastrous|catastrophic|outrageous|shameful|radical left|far-left|far-right|extremism)\b",
    "es": r"\b(?:masacres?|genocidio|terroristas?|régimen|dictador\w*|dictadura|propaganda|extremistas?|vergonzos[oa]s?|"
          r"desastros[oa]s?|catastrófic[oa]s?|inaceptables?|delirante\w*)\b",
}
RX["loaded"] = {k: re.compile(v, re.I) for k, v in LOADED_CUES.items()}


def perspective(story, prof, topic):
    """Mise en perspective avec le pays : ce qui, dans le contexte, pèse sur l'événement."""
    if not prof:
        return []
    c = prof.get("classes", {})
    theme = TOPIC_ALIAS.get(topic, topic)
    out = []
    if theme == "politique" and c.get("instable"):
        out.append("forte instabilité politique : plusieurs chefs du gouvernement se sont succédé en deux ans")
    if theme in ("politique", "economie", "transport", "education", "climat"):
        note = eco_note(prof).replace(", dans un contexte de ", "")
        if note:
            out.append(note)
    if not out:
        return []
    return [{"k": "perspective", "t": f"À mettre en regard, pour {prof['nom']} : " + " ; ".join(out) + "."}]
