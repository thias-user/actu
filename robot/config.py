"""Toutes les sources d'ACTU. Pour ajouter un journal : ajoutez une ligne F(...) dans FEEDS."""

REGIONS = {
    "fr": {"label": "France", "lang": "fr"},
    "eu": {"label": "Europe", "lang": "en"},
    "us": {"label": "États-Unis", "lang": "en"},
    "latam": {"label": "Amérique latine", "lang": "es"},
}
REGION_ORDER = ["fr", "eu", "us", "latam"]


def F(region, source, url, weight=0.85, hint=None, geo="implicit", paywall=False):
    """geo='implicit' : rubrique déjà centrée sur la région (on écarte seulement l'étranger évident).
    geo='require'  : rubrique généraliste, l'article doit parler explicitement de la région."""
    return dict(region=region, source=source, url=url, weight=weight, hint=hint, geo=geo, paywall=paywall)


FEEDS = [
    # ---------------------------------------------------------------- France (journaux français)
    F("fr", "Le Monde", "https://www.lemonde.fr/politique/rss_full.xml", 1.0, "politique", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/societe/rss_full.xml", 1.0, paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/economie-francaise/rss_full.xml", 1.0, "economie", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/economie/rss_full.xml", 1.0, "economie", geo="require", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/sport/rss_full.xml", 1.0, "sport", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/sciences/rss_full.xml", 1.0, "science", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/sante/rss_full.xml", 1.0, "sante", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/culture/rss_full.xml", 1.0, "art", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/musiques/rss_full.xml", 1.0, "musique", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/pixels/rss_full.xml", 1.0, "innovation", paywall=True),
    F("fr", "Le Monde", "https://www.lemonde.fr/m-mode/rss_full.xml", 1.0, "mode", paywall=True),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/politique.rss", 0.95, "politique"),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/france.rss", 0.95),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/societe.rss", 0.95),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/economie.rss", 0.95, "economie"),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/sante.rss", 0.95, "sante"),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/sciences.rss", 0.95, "science"),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/culture.rss", 0.95, "art"),
    F("fr", "franceinfo", "https://www.francetvinfo.fr/sports.rss", 0.95, "sport"),
    F("fr", "Libération", "https://www.liberation.fr/arc/outboundfeeds/rss/category/politique/?outputType=xml", 0.95, "politique"),
    F("fr", "Libération", "https://www.liberation.fr/arc/outboundfeeds/rss/category/societe/?outputType=xml", 0.95),
    F("fr", "Libération", "https://www.liberation.fr/arc/outboundfeeds/rss/category/economie/?outputType=xml", 0.95, "economie"),
    F("fr", "Libération", "https://www.liberation.fr/arc/outboundfeeds/rss/category/culture/?outputType=xml", 0.95, "art"),
    F("fr", "La Croix", "https://www.la-croix.com/RSS/UNIVERS", 0.85),
    F("fr", "Ouest-France", "https://www.ouest-france.fr/rss/une", 0.85),
    F("fr", "L'Express", "https://www.lexpress.fr/arc/outboundfeeds/rss/alaune.xml", 0.85),
    F("fr", "20 Minutes", "https://www.20minutes.fr/feeds/rss-une.xml", 0.75),
    F("fr", "La Tribune", "https://www.latribune.fr/rss/rubriques/actualite.html", 0.85, "economie"),
    F("fr", "L'Équipe", "https://dwh.lequipe.fr/api/edito/rss?path=/", 0.9, "sport"),
    F("fr", "Numerama", "https://www.numerama.com/feed/", 0.8, "innovation"),
    F("fr", "Télérama", "https://www.telerama.fr/rss/une.xml", 0.8, "art"),
    F("fr", "Les Inrocks", "https://www.lesinrocks.com/feed/", 0.75, "musique"),

    # ---------------------------------------------------------------- Europe (journaux européens, en anglais)
    F("eu", "DW (Allemagne)", "https://rss.dw.com/rdf/rss-en-eu", 1.0),
    F("eu", "Le Monde in English", "https://www.lemonde.fr/en/europe/rss_full.xml", 1.0, paywall=True),
    F("eu", "The Guardian", "https://www.theguardian.com/world/europe-news/rss", 0.95),
    F("eu", "Politico Europe", "https://www.politico.eu/feed/", 0.95, "politique"),
    F("eu", "France 24 English", "https://www.france24.com/en/europe/rss", 0.9),
    F("eu", "Euractiv", "https://www.euractiv.com/feed/", 0.85, "politique"),
    F("eu", "Kyiv Independent", "https://kyivindependent.com/news-archive/rss/", 0.85, "geopolitique"),
    F("eu", "Der Spiegel International", "https://www.spiegel.de/international/index.rss", 0.95, geo="require", paywall=True),
    F("eu", "El País English", "https://feeds.elpais.com/mrss-s/pages/ep/site/english.elpais.com/portada", 0.9, geo="require"),
    F("eu", "ANSA English (Italie)", "https://www.ansa.it/english/news/english_nr_rss.xml", 0.8, geo="require"),
    F("eu", "Euronews", "https://www.euronews.com/rss?level=theme&name=news", 0.85, geo="require"),
    F("eu", "The Irish Times", "https://www.irishtimes.com/arc/outboundfeeds/feed-irish-news/?from=0&size=20", 0.75),
    F("eu", "Notes from Poland", "https://notesfrompoland.com/feed/", 0.75),
    F("eu", "The Local (Allemagne)", "https://www.thelocal.de/feeds/rss.php", 0.7),

    # ---------------------------------------------------------------- États-Unis (journaux américains)
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/US.xml", 1.0, paywall=True),
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", 1.0, "politique", paywall=True),
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", 1.0, "economie", geo="require", paywall=True),
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", 1.0, "science", geo="require", paywall=True),
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml", 1.0, "sante", geo="require", paywall=True),
    F("us", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml", 1.0, "art", geo="require", paywall=True),
    F("us", "The Wall Street Journal", "https://feeds.content.dowjones.io/public/rss/RSSUSnews", 1.0, paywall=True),
    F("us", "NPR", "https://feeds.npr.org/1014/rss.xml", 0.95, "politique"),
    F("us", "NPR", "https://feeds.npr.org/1001/rss.xml", 0.95, geo="require"),
    F("us", "NPR", "https://feeds.npr.org/1128/rss.xml", 0.95, "sante", geo="require"),
    F("us", "NPR", "https://feeds.npr.org/1039/rss.xml", 0.9, "musique", geo="require"),
    F("us", "PBS NewsHour", "https://www.pbs.org/newshour/feeds/rss/headlines", 0.95, geo="require"),
    F("us", "Politico", "https://rss.politico.com/politics-news.xml", 0.9, "politique"),
    F("us", "The Hill", "https://thehill.com/homenews/feed/", 0.85, "politique"),
    F("us", "CBS News", "https://www.cbsnews.com/latest/rss/us", 0.85),
    F("us", "CBS News", "https://www.cbsnews.com/latest/rss/politics", 0.85, "politique"),
    F("us", "ABC News", "https://abcnews.go.com/abcnews/usheadlines", 0.85),
    F("us", "NBC News", "https://feeds.nbcnews.com/nbcnews/public/news", 0.85, geo="require"),
    F("us", "Bloomberg", "https://feeds.bloomberg.com/politics/news.rss", 0.95, "politique", paywall=True),
    F("us", "Bloomberg", "https://feeds.bloomberg.com/markets/news.rss", 0.95, "finance", geo="require", paywall=True),
    F("us", "CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", 0.85, geo="require"),
    F("us", "Axios", "https://api.axios.com/feed/", 0.85, geo="require"),
    F("us", "Los Angeles Times", "https://www.latimes.com/california/rss2.0.xml", 0.8),
    F("us", "The Atlantic", "https://www.theatlantic.com/feed/all/", 0.85, geo="require", paywall=True),
    F("us", "Wired", "https://www.wired.com/feed/rss", 0.8, "innovation", geo="require"),
    F("us", "Vogue", "https://www.vogue.com/feed/rss", 0.7, "mode", geo="require"),
    F("us", "Billboard", "https://www.billboard.com/feed/", 0.7, "musique", geo="require"),

    # ---------------------------------------------------------------- Amérique latine (en espagnol, presse d'Espagne ou d'Amérique latine)
    F("latam", "El País (Espagne)", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada", 1.0, geo="require", paywall=True),
    F("latam", "El Mundo (Espagne)", "https://www.elmundo.es/rss/internacional.xml", 0.9, geo="require"),
    F("latam", "ABC (Espagne)", "https://www.abc.es/rss/2.0/internacional/", 0.85, geo="require"),
    F("latam", "Europa Press (Espagne)", "https://www.europapress.es/rss/rss.aspx?ch=00069", 0.85, geo="require"),
    F("latam", "20minutos (Espagne)", "https://www.20minutos.es/rss/internacional/", 0.7, geo="require"),
    F("latam", "Clarín (Argentine)", "https://www.clarin.com/rss/politica/", 0.9, "politique"),
    F("latam", "Clarín (Argentine)", "https://www.clarin.com/rss/economia/", 0.9, "economie"),
    F("latam", "La Nación (Argentine)", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml", 0.9),
    F("latam", "Infobae (Argentine)", "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml", 0.85),
    F("latam", "El Universal (Mexique)", "https://www.eluniversal.com.mx/arc/outboundfeeds/rss/?outputType=xml", 0.85),
    F("latam", "La Jornada (Mexique)", "https://www.jornada.com.mx/rss/edicion.xml", 0.8),
    F("latam", "El Tiempo (Colombie)", "https://www.eltiempo.com/rss/colombia.xml", 0.85),
    F("latam", "El Tiempo (Colombie)", "https://www.eltiempo.com/rss/politica.xml", 0.85, "politique"),
    F("latam", "Semana (Colombie)", "https://www.semana.com/arc/outboundfeeds/rss/?outputType=xml", 0.75),
    F("latam", "La Tercera (Chili)", "https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml", 0.85),
    F("latam", "El Comercio (Pérou)", "https://elcomercio.pe/arcio/rss/", 0.8),
    F("latam", "El Universo (Équateur)", "https://www.eluniverso.com/arc/outboundfeeds/rss/?outputType=xml", 0.75),
    F("latam", "El Nacional (Venezuela)", "https://www.elnacional.com/feed/", 0.75),
    F("latam", "Prensa Libre (Guatemala)", "https://www.prensalibre.com/feed/", 0.7),
]

# Contenus sans intérêt éditorial (jeux, promos, horoscope…) : jamais retenus. Texte normalisé.
BLACKLIST = [
    "appel a temoignages", "horoscope", "quiz", "mots croises", "mots fleches", "sudoku", "jeu concours", "code promo",
    "codes promo", "bon plan", "bons plans", "black friday", "soldes", "programme tv", "loto", "euromillions",
    "recette", "newsletter", "cdiscount", "amazon prime day", "meteo du", "les titres du",
    "horoscopo", "loteria", "quiniela", "receta", "cupon", "ofertas", "precio y cotizacion", "dolar hoy", "euro hoy",
    "dolar blue", "pronostico del tiempo", "clima en", "resultados del", "portada impresa", "telekino", "numeros ganadores",
    "sorteo", "quini 6", "epicentro y magnitud", "hora exacta", "temblor hoy",
    "wordle", "crossword", "connections hint", "best deals", "promo code", "coupon", "sponsored", "deal of the day",
    "the morning", "today s top news", "quordle", "strands hint", "horoscopes",
]
# Pages « en direct » : très consultées mais changeantes → légère pénalité.
LIVE_MARKERS = [" en direct ", " direct ", " live ", " en vivo ", " minuto a minuto ", " live updates "]

# Mots qui situent un article. Toutes les formes sont normalisées (sans accents, alias de common.py appliqués).
GEO = {
    "fr": """france paris parisien parisienne marseille lyon toulouse nice nantes strasbourg montpellier bordeaux lille rennes
        reims toulon grenoble dijon angers nimes brest limoges amiens perpignan metz besancon orleans rouen caen nancy
        macron elysee matignon bercy hexagone corse bretagne normandie occitanie provence alsace guadeloupe martinique
        mayotte guyane sncf ratp insee prefet prefecture departement mairie municipales assemblee lecornu bayrou
        melenchon bardella le_pen attal philippe glucksmann retailleau ruffin hollande sarkozy ligue_1 psg om cac_40""",
    "eu": """europe european europeen europeenne europeens europeennes europea europeo eu brussels eurozone strasbourg
        germany berlin merz spain madrid sanchez italy rome meloni poland warsaw tusk ukraine kyiv zelensky russia moscow
        putin kremlin uk london starmer ireland dublin netherlands dutch amsterdam belgium belgian austria vienna
        switzerland swiss sweden swedish stockholm norway norwegian oslo denmark danish copenhagen greenland finland
        finnish helsinki portugal lisbon greece greek athens hungary hungarian orban budapest czech prague slovakia
        romania bucharest bulgaria serbia belgrade croatia slovenia bosnia kosovo albania moldova belarus
        lukashenko baltic estonia latvia lithuania iceland luxembourg malta cyprus balkans scandinavia kaliningrad
        crimea donbas von_der_leyen kallas schengen nato france paris macron
        belgique belgica pays_bas paises_bajos holanda autriche viena suisse suiza suede suecia
        norvege noruega danemark dinamarca groenland groenlandia finlande finlandia grece grecia hongrie hungria
        tchequie republica_checa slovaquie eslovaquia roumanie rumania bulgarie serbie croatie croacia slovenie
        eslovenia bosnie albanie moldavie moldavia bielorussie bielorrusia estonie lettonie letonia lituanie lituania
        islande islandia irlande irlanda chypre chipre malte lisbonne lisboa varsovie varsovia roma athenes atenas
        prague praga bucarest stockholm estocolmo copenhague la_haye bruselas de_wever""",
    "us": """usa whitehouse washington trump vance congress senate pentagon wall_street new_york california texas florida
        georgia ohio michigan pennsylvania arizona nevada wisconsin minnesota illinois chicago los_angeles miami boston
        seattle atlanta houston dallas denver philadelphia detroit virginia carolina tennessee kentucky alabama louisiana
        mississippi missouri iowa kansas oklahoma oregon utah colorado indiana maryland massachusetts connecticut
        new_jersey alaska hawaii democrat democrats democratic republican republicans gop midterm midterms biden harris
        obama supreme_court fbi cia ice medicare medicaid thanksgiving maga silicon_valley hollywood broadway newsom
        desantis hochul mamdani schumer johnson jeffries rubio hegseth bessent californie floride nueva_york caroline
        louisiane pensilvania pennsylvanie""",
    "latam": """latam mexico guatemala honduras salvador nicaragua costa_rica panama cuba cubano cubana haiti dominicana
        puerto_rico colombia venezuela ecuador peru bolivia chile argentina uruguay paraguay brazil bogota caracas quito
        lima buenos_aires montevideo asuncion brasilia sao_paulo rio_de_janeiro cdmx ciudad_de_mexico havana habana
        managua tegucigalpa medellin cali guadalajara monterrey cordoba rosario valparaiso milei lula sheinbaum petro
        maduro bukele noboa boric kast ortega kirchner bolsonaro arevalo mulino orsi mercosur celac cepal caribe
        caribbean caraibes andes amazonia patagonia antioquia bolivie equateur republique_dominicaine la_havane
        cauca barranquilla cartagena""",
    "world": """china beijing xi_jinping japan tokyo india modi korea coree corea taiwan iran teheran israel gaza palestine
        hamas hezbollah lebanon liban libano syria syrie siria iraq irak saudi arabie qatar yemen egypt egypte egipto
        africa afrique nigeria sudafrica ethiopia sudan soudan kenya morocco maroc marruecos algeria algerie argelia
        tunisia tunisie libya libye australia australie indonesia pakistan afghanistan vietnam thailand philippines
        canada ottawa hormuz middleeast netanyahu khamenei kim_jong turkey erdogan ankara istanbul indonesie
        thailande tailandia filipinas ethiopie etiopia senegal mali niger burkina cameroun congo rdc sahel""",
}


def _geo_sets():
    out = {}
    for k, v in GEO.items():
        out[k] = {w.replace("_", " ") for w in v.split()}
    return out


GEO_SETS = _geo_sets()

# ---------------------------------------------------------------- réseaux sociaux (publications liées aux articles)
# YouTube : flux RSS publics officiels de chaque chaîne (aucune clé nécessaire).
YOUTUBE_NEWS = [
    ("HugoDécrypte", "UCAcAnMF0OrCtUep3Y4M-ZPw", "fr"),
    ("HugoDécrypte – Grands formats", "UCUo1RqYV8tGjV38sQ8S5p9A", "fr"),
    ("Ulyces", "UCfYCWxCVhk4O5wKWGyEyGnQ", "fr"),
    ("franceinfo", "UCO6K_kkdP-lnSCiO3tPx7WA", "fr"),
    ("Le Monde", "UCYpRDnhk5H8h16jpS84uqsA", "fr"),
    ("BFMTV", "UCXwDLMDV86ldKoFVc_g8P0g", "fr"),
    ("FRANCE 24", "UCCCPCZNChQdGa9EkATeye4g", "fr"),
    ("TF1 INFO", "UCsrPUA0ZSDCNZC6wyRlR7ZA", "fr"),
    ("LCI", "UCewhc0fvja891XkpIPGRMxQ", "fr"),
    ("Brut", "UCYti3yTb2QWvLQExSmxnE2A", "fr"),
    ("Le Figaro", "UCCDz_XYeKWd0OIyjp95dqyQ", "fr"),
    ("Libération", "UC9x4Iyu-D257P0P-VDRwSzw", "fr"),
    ("Mediapart", "UCdnaDhU-LDQrIEEmSIfq0-Q", "fr"),
    ("Public Sénat", "UCTa1bPArjpvNMgSHAb_pflA", "fr"),
    ("Gaspard G", "UCI-8QMy9n3I5Pv6mTmXoAXA", "fr"),
    ("Mister Geopolitix", "UCX9lsdsTKfTi1eqoyL-RS-Q", "fr"),
    ("Le Dessous des Cartes – ARTE", "UCHGMBrXUzClgjEzBMei-Jdw", "fr"),
    ("euronews (français)", "UCW2QcKZiU8aUGg4yxCIditg", "fr"),
    ("FRANCE 24 English", "UCQfwfsi5VrQ8yKZ-UWmAEFg", "en"),
    ("DW News", "UCknLrEdhRCp1aegoMqRaCZg", "en"),
    ("euronews", "UCSrZ3UV4jOidv8ppoVuvW9Q", "en"),
    ("CNN", "UCupvZG-5ko_eiXAupbDfxWw", "en"),
    ("NBC News", "UCeY0bbntWzzVIaj2z3QigXg", "en"),
    ("PBS NewsHour", "UC6ZFN9Tx6xh-skXCuRHCDpQ", "en"),
    ("The New York Times", "UCqnbDFdCpuN8CMEg0VuEBqA", "en"),
    ("Vox", "UCLXo7UDZvByw2ixzpQCufnA", "en"),
    ("FRANCE 24 Español", "UCUdOoVWuWmgo1wByzcsyKDQ", "es"),
    ("DW Español", "UCT4Jg8h03dD0iN3Pb5L0PMA", "es"),
    ("BBC News Mundo", "UCUBIrDsIVzRpKsClMlSlTpQ", "es"),
    ("CNN en Español", "UC_lEiu6917IJz03TnntWUaQ", "es"),
    ("EL PAÍS", "UCnsvJeZO4RigQ898WdDNoBw", "es"),
]
# Bluesky : API publique et gratuite (X, Instagram et TikTok n'autorisent pas la lecture automatique).
BLUESKY = [
    ("Le Monde", "lemonde.fr", "fr"), ("franceinfo", "franceinfo.fr", "fr"), ("Libération", "liberation.fr", "fr"),
    ("AFP", "afp.com", "fr"), ("Mediapart", "mediapart.fr", "fr"), ("Le Point", "lepoint.fr", "fr"),
    ("France 24", "france24.com", "fr"), ("The New York Times", "nytimes.com", "en"),
    ("The Washington Post", "washingtonpost.com", "en"), ("NPR", "npr.org", "en"), ("AP", "apnews.com", "en"),
    ("Reuters", "reuters.com", "en"), ("The Guardian", "theguardian.com", "en"), ("Politico Europe", "politico.eu", "en"),
    ("El País", "elpais.com", "es"),
]

# ---------------------------------------------------------------- ARTE (YouTube, accès libre)
ARTE_CHANNELS = [
    # nom, id de chaîne, durée minimale (minutes), sujet par défaut
    ("ARTE", "UCwI-JbGNsojunnHbFAc0M4Q", 12, None),
    ("Le Dessous des Cartes", "UCHGMBrXUzClgjEzBMei-Jdw", 5, "geopolitique"),
    ("Le Dessous des images", "UC4DJ3WmfGvZv6PlKUuA057A", 5, "societe"),
    ("ARTE Évasion", "UCXV7LUI7G1MaKRN18yQ5y7Q", 12, "voyage"),
    ("TRACKS", "UC__Pj66OeDibNZNN__L913g", 8, "art"),
    ("ARTE Concert", "UC-smeLB9AnOTeypr1YyjJ3A", 20, "musique"),
]
# Quelques playlists thématiques d'ARTE (le titre de la playlist aide à classer les vidéos).
ARTE_PLAYLISTS = [
    ("PLCwXWOyIR22tgYxQjf5Ca4jQQrhauzpQN", "ARTE Reportage", "geopolitique"),
    ("PLCwXWOyIR22tf2dp09L6PgIhCIAhiPxDk", "Iran : histoire et actualité", "geopolitique"),
    ("PLCwXWOyIR22vsFhHUrQe9M3BUnr15GxfG", "Comprendre la guerre au Moyen-Orient", "geopolitique"),
    ("PLCwXWOyIR22tikeSgjDEArrPDAjbpkv0L", "Tout sur la Chine", "geopolitique"),
    ("PLCwXWOyIR22tS6Ngdo0YWMCPYsPJ62TR1", "États-Unis : actu & histoire", "geopolitique"),
    ("PLCwXWOyIR22tfDmlv9uiI1Xg81N8nNul-", "Génération Ukraine", "geopolitique"),
    ("PLCwXWOyIR22s2sRABgau5cD0YpLIH8BvT", "Europe : la montée de l'extrême droite", "politique"),
    ("PLCwXWOyIR22uUy3dbx_DpWkDyaRHlecux", "Masha on Russia", "geopolitique"),
    ("PLCwXWOyIR22uSU7G5rm95h9QneS-rxuHg", "Tchernobyl, anatomie d'une catastrophe", "histoire"),
    ("PLCwXWOyIR22vRrVGhd-47iArtum0DvDKJ", "Pompéi, ses nouveaux secrets", "histoire"),
    ("PLCwXWOyIR22vwTN2rM1R919thCS1wGe7f", "Trésors du patrimoine européen", "histoire"),
    ("PLCwXWOyIR22utulzR2ssDdQ_P2M0eIvLW", "Mobutu – Maître du jeu", "histoire"),
    ("PLCwXWOyIR22tnMQLdUJmRSudQ1qpP08zz", "La fabuleuse histoire de l'argent", "economie"),
    ("PLCwXWOyIR22uuz-6meaOBxKr6XSlUSjp6", "MONEY", "economie"),
    ("PLCwXWOyIR22vilhvzk-UnUkmTLOYeWQZN", "La bourse ? Grave !", "economie"),
    ("PLCwXWOyIR22vsQOA4DatD9NgPHk8MwH_W", "Peinture et sculpture", "art"),
    ("PLCwXWOyIR22tlrcyx7y9kJFEZlJ_IXpL1", "L'oligarque et le marchand d'art", "art"),
    ("PLCwXWOyIR22uueWT6j4aou2__m5NJxorN", "Miyazaki, l'esprit de la nature", "art"),
    ("PLCwXWOyIR22ueD2N_4oYNxE-1GKW9JTBW", "Santé mentale", "sante"),
    ("PLCwXWOyIR22sUQ0yWcpNJBYq6GyX3il3D", "Santé – documentaires complets", "sante"),
    ("PLCwXWOyIR22tFizvcqdhBevYNVny82ysn", "Le sucre, pour la douceur et pour le pire", "sante"),
    ("PLCwXWOyIR22vJ2c1vewT9WyDRmsxJqa0A", "Intelligence artificielle", "innovation"),
    ("PLCwXWOyIR22sNTjQUHl9Ktx7rQ5I1nh_d", "Réseaux sociaux", "innovation"),
    ("PLCwXWOyIR22uk9tS3OppxGVggC4ghnrQF", "L'odyssée des chiffres", "science"),
    ("PLCwXWOyIR22vhaf7Re4PaJ7jBaGVAYVRB", "Autour de Chiroptera", "science"),
    ("PLCwXWOyIR22tmVCUOj29bcC2i_AQ1KY2o", "Guerre au Proche-Orient", "geopolitique"),
    ("PLCwXWOyIR22vFUy3RvdJjgKQSuqivcdGg", "Liban : comprendre le conflit", "geopolitique"),
    ("PLCwXWOyIR22vlGQAxtdslCRbxnA46qbvx", "Gaza", "geopolitique"),
]
# Sujets de l'onglet ARTE (mots-clés en français cherchés dans titre + description ; "_" relie une expression).
ARTE_SUBJECTS = [
    ("geopolitique", "Géopolitique", "geopoliti* guerre guerres conflit* frontiere* nato diplomat* ukraine russia china iran israel gaza palestine taiwan middleeast puissances empire empires armee* militaire* nucleaire* terroris* dictateur* dictature* oligarque* putin trump afrique sahel coree mafia* cartel* usa"),
    ("histoire", "Histoire", "histoire historique* siecle* antiquite antique* moyen_age medieval* renaissance revolution* guerre_mondiale 1914 1918 1939 1945 nazi* hitler napoleon roi reine pharaon* egypte_ancienne rome romain* grec* pompei archeolog* colonial* colonisation esclavage memoire patrimoine chateau* tchernobyl mobutu staline guerre_froide"),
    ("philosophie", "Philosophie & idées", "philosoph* pensee penseur* idees morale ethique sagesse liberte verite bonheur conscience existence religion* croyance* dieu spiritu* sacre mythe* mythologie sens_de_la_vie desir amour"),
    ("art", "Art & culture", "art arts artiste* peinture* peintre* sculpt* musee* exposition* oeuvres cinema film films realisat* photograph* architect* litterature ecrivain* roman romans poesie poete* theatre danse bande_dessinee manga* tolkien miyazaki culture culturel* couture"),
    ("musique", "Musique", "musique* concert* festival* album* chanson* chanteu* rap rock jazz electro orchestre* opera piano symphonie live_session"),
    ("science", "Sciences", "science* scientifique* recherche chercheu* physique chimie biologie genet* adn cerveau neuro* espace univers planete* astronom* cosmos etoile* mathemati* chiffres evolution animal animaux espece* ocean* dinosaure* chiroptera chauve* insecte* abeille*"),
    ("environnement", "Environnement", "climat* ecolog* environnement* pollution* biodiversite plastique* deforestation foret* energie* secheresse ocean* glacier* agricult* pesticide* rechauffement catastrophe* durable"),
    ("societe", "Société", "societe social* femme* feminis* jeunes jeunesse generation* famille* enfant* ecole education travail emploi pauvrete inegalit* migrant* immigration racisme justice police prison* drogue* sante_mentale reseaux_sociaux internet numerique logement* banlieue*"),
    ("economie", "Économie & finance", "econom* argent finance* bourse* banque* capitalisme ultra_riches milliardaire* richesse dette inflation commerce industrie* entreprise* multinationale* monnaie crypto* bitcoin impot* taxe*"),
    ("sante", "Santé", "sante medecine medical medicale* medicaux maladie* hopita* virus vaccin* cancer sucre alimentation nutrition sommeil addiction* sante_mentale depression soins pharma* medicament*"),
    ("innovation", "Technologie & innovation", "technolog* innovation* aitech robot* numerique internet algorithme* cyber* hack* donnees ordinateur* informatique smartphone* jeux_video jeu_video esport startup* futur invention*"),
    ("voyage", "Voyages & découvertes", "voyage* evasion paysage* village* ile iles montagne* desert* tribu* peuple* cuisine* gastronomie aventure* exploration expedition*"),
    ("sport", "Sport", "sport* football olymp* athlete* champion* tennis rugby cyclisme velo ski"),
    ("politique", "Politique", "politique* election* democratie* extreme_droite populisme* president* gouvernement* parlement* vote"),
]

# ---------------------------------------------------------------- recherche scientifique (mise à jour trimestrielle)
RESEARCH_QUERIES = {
    # thème : (mots du titre en anglais, mots du titre en français) — "|" signifie « ou »
    "geopolitique": ("geopolitics|geopolitical", "géopolitique|géopolitiques"),
    "politique": ("democracy|populism|elections", "démocratie|populisme|élections"),
    "economie": ("inequality|macroeconomic|economic", "économie|économique|macroéconomique"),
    "finance": ("monetary|banking|finance", "monétaire|bancaire|finance"),
    "sport": ("sport|sports|athletes", "sport|sportif|sportive"),
    "innovation": ("innovation|artificial intelligence", "innovation|intelligence artificielle"),
    "science": ("climate change|biodiversity", "climat|biodiversité"),
    "sante": ("public health|epidemiology", "santé publique|épidémiologie"),
    "art": ("art history|contemporary art|artists|painting", "art contemporain|histoire de l'art|artistes|peinture"),
    "musique": ("music|musical", "musique|musicale"),
    "mode": ("fashion", "mode vestimentaire|haute couture|vêtement"),
}

# Régions du monde de l'onglet ARTE (mots normalisés, alias de common.py appliqués ; "_" relie une expression).
ARTE_REGIONS = [
    ("france", "France", "france paris marseille lyon bretagne normandie provence alsace corse occitanie outre_mer guadeloupe martinique "
     "ile_de_la_reunion guyane mayotte nouvelle_caledonie tahiti macron"),
    ("europe", "Europe", "europe europeen* europeenne* eu germany berlin italy rome venise naples sicile spain madrid barcelone andalousie "
     "uk london ecosse irlande ireland pologne poland ukraine kyiv russia moscow putin grece athenes portugal lisbonne suisse autriche "
     "vienne belgique bruxelles pays_bas amsterdam suede norvege danemark finlande islande hongrie roumanie bulgarie balkans serbie croatie "
     "bosnie kosovo albanie tchequie prague slovaquie baltes estonie lettonie lituanie scandinavie mediterranee alpes"),
    ("afrique", "Afrique", "afrique africain* sahel mali niger burkina senegal dakar cote_d_ivoire abidjan nigeria ghana cameroun congo rdc "
     "kinshasa rwanda burundi kenya ethiopie somalie soudan egypte caire maroc algerie tunisie libye madagascar mozambique angola namibie "
     "afrique_du_sud zimbabwe tanzanie ouganda mobutu sahara"),
    ("moyen-orient", "Moyen-Orient", "middleeast israel gaza palestine cisjordanie jerusalem liban beyrouth syrie damas irak bagdad iran "
     "teheran arabie golfe qatar dubai emirats yemen jordanie turkey istanbul kurde* kurdistan hamas hezbollah"),
    ("asie", "Asie", "asie asiatique* china beijing shanghai hong_kong taiwan japan tokyo coree seoul india delhi pakistan afghanistan "
     "bangladesh nepal tibet himalaya mongolie vietnam thailande cambodge laos birmanie indonesie philippines malaisie singapour "
     "kazakhstan ouzbekistan siberie"),
    ("amerique-nord", "Amérique du Nord", "usa whitehouse trump washington new_york californie texas floride chicago hollywood "
     "canada quebec montreal alaska"),
    ("amerique-latine", "Amérique latine", "latam mexico bresil brazil argentina colombia venezuela chile peru bolivie equateur cuba "
     "haiti guatemala honduras nicaragua salvador panama costa_rica uruguay paraguay amazonie patagonie andes caraibes"),
    ("oceanie-poles", "Océanie & pôles", "australie nouvelle_zelande oceanie pacifique polynesie arctique antarctique groenland "
     "banquise pole_nord pole_sud"),
]
