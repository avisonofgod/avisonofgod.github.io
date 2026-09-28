"""Catálogo de los 39 libros del Tanaj (orden judío: Torah, Nevi'im, Ketuvim).

Cada entrada une:
- `osis`: archivo base en el WLC (morphhb/wlc/<osis>.xml)
- `slug`: identificador canónico de la API (transliteración hebrea)
- `he`/`es`/`en`: nombres para mostrar
- `section`: torah | neviim | ketuvim (y `sub` para las subdivisiones clásicas)
- `order`: posición en el orden judío (1..39)
- `rv1909`: nombre exacto del libro en la Reina-Valera 1909 (fuente española)

Nota: el Tanaj tiene 24 libros "de sinagoga" (Ezra+Nehemías = uno, los 12 menores = uno);
aquí se usa la división por libro/versículo del WLC (39 archivos), que es la que permite
citar versículo a versículo.
"""

from typing import Any, Dict, List

SECTIONS = {
    "torah": {"es": "Torá", "he": "תּוֹרָה"},
    "neviim": {"es": "Nevi'im", "he": "נְבִיאִים"},
    "ketuvim": {"es": "Ketuvim", "he": "כְּתוּבִים"},
}

_SUB = {
    "neviim_rishonim": {"es": "Profetas anteriores (Nevi'im Rishonim)"},
    "neviim_akharonim": {"es": "Profetas posteriores (Nevi'im Aĥaronim)"},
}

BOOKS: List[Dict[str, Any]] = [
    # ── Torá ────────────────────────────────────────────────────────────────
    dict(osis="Gen", slug="bereshit", he="בְּרֵאשִׁית", es="Génesis", en="Genesis",
         section="torah", order=1, rv1909="Génesis"),
    dict(osis="Exod", slug="shemot", he="שְׁמוֹת", es="Éxodo", en="Exodus",
         section="torah", order=2, rv1909="Éxodo"),
    dict(osis="Lev", slug="vayikra", he="וַיִּקְרָא", es="Levítico", en="Leviticus",
         section="torah", order=3, rv1909="Levítico"),
    dict(osis="Num", slug="bamidbar", he="בְּמִדְבַּר", es="Números", en="Numbers",
         section="torah", order=4, rv1909="Números"),
    dict(osis="Deut", slug="devarim", he="דְּבָרִים", es="Deuteronomio", en="Deuteronomy",
         section="torah", order=5, rv1909="Deuteronomio"),
    # ── Nevi'im · anteriores ────────────────────────────────────────────────
    dict(osis="Josh", slug="yehoshua", he="יְהוֹשֻׁעַ", es="Josué", en="Joshua",
         section="neviim", sub="neviim_rishonim", order=6, rv1909="Josué"),
    dict(osis="Judg", slug="shoftim", he="שׁוֹפְטִים", es="Jueces", en="Judges",
         section="neviim", sub="neviim_rishonim", order=7, rv1909="Jueces"),
    dict(osis="1Sam", slug="shmuel_a", he="שְׁמוּאֵל א׳", es="1 Samuel", en="1 Samuel",
         section="neviim", sub="neviim_rishonim", order=8, rv1909="1 Samuel"),
    dict(osis="2Sam", slug="shmuel_b", he="שְׁמוּאֵל ב׳", es="2 Samuel", en="2 Samuel",
         section="neviim", sub="neviim_rishonim", order=9, rv1909="2 Samuel"),
    dict(osis="1Kgs", slug="mlakhim_a", he="מְלָכִים א׳", es="1 Reyes", en="1 Kings",
         section="neviim", sub="neviim_rishonim", order=10, rv1909="1 Reyes"),
    dict(osis="2Kgs", slug="mlakhim_b", he="מְלָכִים ב׳", es="2 Reyes", en="2 Kings",
         section="neviim", sub="neviim_rishonim", order=11, rv1909="2 Reyes"),
    # ── Nevi'im · posteriores ───────────────────────────────────────────────
    dict(osis="Isa", slug="yeshayahu", he="יְשַׁעְיָהוּ", es="Isaías", en="Isaiah",
         section="neviim", sub="neviim_akharonim", order=12, rv1909="Isaías"),
    dict(osis="Jer", slug="yirmiyahu", he="יִרְמְיָהוּ", es="Jeremías", en="Jeremiah",
         section="neviim", sub="neviim_akharonim", order=13, rv1909="Jeremías"),
    dict(osis="Ezek", slug="yechezkel", he="יְחֶזְקֵאל", es="Ezequiel", en="Ezekiel",
         section="neviim", sub="neviim_akharonim", order=14, rv1909="Ezequiel"),
    dict(osis="Hos", slug="hoshea", he="הוֹשֵׁעַ", es="Oseas", en="Hosea",
         section="neviim", sub="neviim_akharonim", order=15, rv1909="Oseas"),
    dict(osis="Joel", slug="yoel", he="יוֹאֵל", es="Joel", en="Joel",
         section="neviim", sub="neviim_akharonim", order=16, rv1909="Joel"),
    dict(osis="Amos", slug="amos", he="עָמוֹס", es="Amós", en="Amos",
         section="neviim", sub="neviim_akharonim", order=17, rv1909="Amós"),
    dict(osis="Obad", slug="ovadia", he="עֹבַדְיָה", es="Abdías", en="Obadiah",
         section="neviim", sub="neviim_akharonim", order=18, rv1909="Abdías"),
    dict(osis="Jonah", slug="yona", he="יוֹנָה", es="Jonás", en="Jonah",
         section="neviim", sub="neviim_akharonim", order=19, rv1909="Jonás"),
    dict(osis="Mic", slug="mikha", he="מִיכָה", es="Miqueas", en="Micah",
         section="neviim", sub="neviim_akharonim", order=20, rv1909="Miqueas"),
    dict(osis="Nah", slug="nachum", he="נַחוּם", es="Nahúm", en="Nahum",
         section="neviim", sub="neviim_akharonim", order=21, rv1909="Nahúm"),
    dict(osis="Hab", slug="chavakuk", he="חֲבַקּוּק", es="Habacuc", en="Habakkuk",
         section="neviim", sub="neviim_akharonim", order=22, rv1909="Habacuc"),
    dict(osis="Zeph", slug="tzefania", he="צְפַנְיָה", es="Sofonías", en="Zephaniah",
         section="neviim", sub="neviim_akharonim", order=23, rv1909="Sofonías"),
    dict(osis="Hag", slug="chaggai", he="חַגַּי", es="Hageo", en="Haggai",
         section="neviim", sub="neviim_akharonim", order=24, rv1909="Hageo"),
    dict(osis="Zech", slug="zecharia", he="זְכַרְיָה", es="Zacarías", en="Zechariah",
         section="neviim", sub="neviim_akharonim", order=25, rv1909="Zacarías"),
    dict(osis="Mal", slug="malakhi", he="מַלְאָכִי", es="Malaquías", en="Malachi",
         section="neviim", sub="neviim_akharonim", order=26, rv1909="Malaquías"),
    # ── Ketuvim ─────────────────────────────────────────────────────────────
    dict(osis="Ps", slug="tehilim", he="תְּהִלִּים", es="Salmos", en="Psalms",
         section="ketuvim", order=27, rv1909="Salmos"),
    dict(osis="Prov", slug="mishlei", he="מִשְׁלֵי", es="Proverbios", en="Proverbs",
         section="ketuvim", order=28, rv1909="Proverbios"),
    dict(osis="Job", slug="iyov", he="אִיּוֹב", es="Job", en="Job",
         section="ketuvim", order=29, rv1909="Job"),
    dict(osis="Song", slug="shir_hashirim", he="שִׁיר הַשִּׁירִים", es="Cantares",
         en="Song of Songs", section="ketuvim", order=30, rv1909="Cantares"),
    dict(osis="Ruth", slug="rut", he="רוּת", es="Rut", en="Ruth",
         section="ketuvim", order=31, rv1909="Rut"),
    dict(osis="Lam", slug="eikha", he="אֵיכָה", es="Lamentaciones", en="Lamentations",
         section="ketuvim", order=32, rv1909="Lamentaciones"),
    dict(osis="Eccl", slug="kohelet", he="קֹהֶלֶת", es="Eclesiastés", en="Ecclesiastes",
         section="ketuvim", order=33, rv1909="Eclesiastés"),
    dict(osis="Esth", slug="ester", he="אֶסְתֵּר", es="Ester", en="Esther",
         section="ketuvim", order=34, rv1909="Ester"),
    dict(osis="Dan", slug="daniel", he="דָּנִיֵּאל", es="Daniel", en="Daniel",
         section="ketuvim", order=35, rv1909="Daniel"),
    dict(osis="Ezra", slug="ezra", he="עֶזְרָא", es="Esdras", en="Ezra",
         section="ketuvim", order=36, rv1909="Esdras"),
    dict(osis="Neh", slug="nechemia", he="נְחֶמְיָה", es="Nehemías", en="Nehemiah",
         section="ketuvim", order=37, rv1909="Nehemías"),
    dict(osis="1Chr", slug="divrei_hayamim_a", he="דִּבְרֵי הַיָּמִים א׳", es="1 Crónicas",
         en="1 Chronicles", section="ketuvim", order=38, rv1909="1 Crónicas"),
    dict(osis="2Chr", slug="divrei_hayamim_b", he="דִּבְרֵי הַיָּמִים ב׳", es="2 Crónicas",
         en="2 Chronicles", section="ketuvim", order=39, rv1909="2 Crónicas"),
]

BY_SLUG = {b["slug"]: b for b in BOOKS}
BY_OSIS = {b["osis"]: b for b in BOOKS}
BY_RV = {b["rv1909"]: b for b in BOOKS}

# Alias aceptados en las URLs y en el buscador (es/en/he + abreviaturas).
ALIASES = {
    "bereshit": ["genesis", "gen", "genesis", "בראשית"],
    "shemot": ["exodo", "exod", "ex", "exodus", "שמות"],
    "vayikra": ["levitico", "lev", "leviticus", "ויקרא"],
    "bamidbar": ["numeros", "num", "numbers", "במדבר"],
    "devarim": ["deuteronomio", "deut", "deuteronomy", "דברים"],
    "yehoshua": ["josue", "josh", "joshua", "יהושע"],
    "shoftim": ["jueces", "judg", "judges", "שופטים"],
    "shmuel_a": ["1samuel", "1sam", "1s", "שמואל א"],
    "shmuel_b": ["2samuel", "2sam", "2s", "שמואל ב"],
    "mlakhim_a": ["1reyes", "1kgs", "1k", "1kings", "מלכים א"],
    "mlakhim_b": ["2reyes", "2kgs", "2k", "2kings", "מלכים ב"],
    "yeshayahu": ["isaias", "isa", "isaiah", "ישעיהו"],
    "yirmiyahu": ["jeremias", "jer", "jeremiah", "ירמיהו"],
    "yechezkel": ["ezequiel", "ezek", "ezekiel", "יחזקאל"],
    "hoshea": ["oseas", "hos", "hosea", "הושע"],
    "yoel": ["joel", "יוֹאֵל", "יואל"],
    "amos": ["amos", "עמוס"],
    "ovadia": ["abdias", "obad", "obadiah", "עובדיה"],
    "yona": ["jonas", "jonah", "יונה"],
    "mikha": ["miqueas", "mic", "micah", "מיכה"],
    "nachum": ["nahum", "nah", "נחום"],
    "chavakuk": ["habacuc", "hab", "habakkuk", "חבקוק"],
    "tzefania": ["sofonias", "zeph", "zephaniah", "צפניה"],
    "chaggai": ["hageo", "hag", "haggai", "חגי"],
    "zecharia": ["zacarias", "zech", "zechariah", "זכריה"],
    "malakhi": ["malaquias", "mal", "malachi", "מלאכי"],
    "tehilim": ["salmos", "ps", "psalms", "תהילים"],
    "mishlei": ["proverbios", "prov", "proverbs", "משלי"],
    "iyov": ["job", "איוב"],
    "shir_hashirim": ["cantares", "song", "songofsongs", "שיר השירים"],
    "rut": ["rut", "ruth", "רות"],
    "eikha": ["lamentaciones", "lam", "lamentations", "איכה"],
    "kohelet": ["eclesiastes", "eccl", "ecclesiastes", "קהלת"],
    "ester": ["ester", "esth", "esther", "אסתר"],
    "daniel": ["daniel", "dan", "דניאל"],
    "ezra": ["esdras", "ezra", "עזרא"],
    "nechemia": ["nehemias", "neh", "nehemiah", "נחמיה"],
    "divrei_hayamim_a": ["1cronicas", "1chr", "1chronicles", "דברי הימים א"],
    "divrei_hayamim_b": ["2cronicas", "2chr", "2chronicles", "דברי הימים ב"],
}


def resolve(name):
    """Devuelve el slug canónico a partir de slug, alias, nombre es/en o hebreo."""
    if not name:
        return None
    key = name.strip().lower().replace("_", "").replace(" ", "").rstrip(".")
    key = key.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if key in BY_SLUG:
        return key
    for slug, alts in ALIASES.items():
        for a in alts:
            if a.lower().replace(" ", "") == key:
                return slug
    for b in BOOKS:
        for field in ("es", "en", "he"):
            v = str(b[field] or "").lower().replace(" ", "")
            v = v.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            if key == v:
                return b["slug"]
    return None


def index_payload():
    """Metadatos para /v1/index.json."""
    return {
        "version": 1,
        "name": "Tanaj — Torá, Nevi'im y Ketuvim",
        "counts": {
            "books": len(BOOKS),
            "sections": 3,
            "chapters": sum(int(b.get("chapters", 0)) for b in BOOKS),
            "verses": sum(int(b.get("verses", 0)) for b in BOOKS),
        },
        "sections": [
            {"id": sid, "he": meta["he"], "es": meta["es"],
             "books": [b["slug"] for b in BOOKS if b["section"] == sid]}
            for sid, meta in SECTIONS.items()
        ],
        "subsections": [{"id": k, "es": v["es"]} for k, v in _SUB.items()],
        "books": [
            {"slug": b["slug"], "osis": b["osis"], "he": b["he"], "es": b["es"], "en": b["en"],
             "section": b["section"], "sub": b.get("sub"), "order": b["order"],
             "chapters": int(b.get("chapters", 0)), "verses": int(b.get("verses", 0)),
             "aliases": ALIASES.get(b["slug"], [])}
            for b in sorted(BOOKS, key=lambda x: x["order"])
        ],
    }
