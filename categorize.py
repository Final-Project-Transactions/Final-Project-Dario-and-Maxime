import re
import unicodedata

# Keyword rules: if the merchant text contains the keyword, it gets that category.
# Order matters: the FIRST rule that matches wins, so specific rules come first
# ("COOP RESTAURANT" before "COOP", "MEDIA MARKT" before "MARKT").
#
# Keywords are written in CAPITALS and without accents: the merchant text is
# converted the same way first ("Café Zähringer" -> "CAFE ZAEHRINGER").
#
# Short keywords (4 letters or less) must be a whole word, so "BAD" doesn't
# match "BADEN" and "SALT" doesn't match "SALTO". Longer keywords may be part
# of a word ("PIZZA" matches "PIZZERIA").
RULES = [
    # specific (must come before the general rules below)
    ("RESTAURANT", "Restaurants"),
    ("TANKSTELLE", "Transport"),
    ("DO IT", "Other"),
    ("COOP MOBILE", "Communication"),
    ("M-BUDGET MOBILE", "Communication"),
    ("VITALITY", "Health"),
    ("KRANKENKASSE", "Health"),
    ("MOTORFAHRZEUG", "Transport"),
    ("MIGROS FITNESS", "Leisure"), ("ACTIV FITNESS", "Leisure"),
    ("MANOR FOOD", "Groceries"),
    ("MEDIA MARKT", "Other"), ("MEDIAMARKT", "Other"),
    ("DIGITEC CONNECT", "Communication"),
    ("COOP PRONTO", "Groceries"),
    ("HALLENBAD", "Leisure"), ("FREIBAD", "Leisure"), ("SEEBAD", "Leisure"),
    ("STRANDBAD", "Leisure"), ("BADI", "Leisure"),
    # Groceries
    ("COOP", "Groceries"), ("MIGROS", "Groceries"), ("MIGROLINO", "Groceries"),
    ("DENNER", "Groceries"), ("ALDI", "Groceries"), ("LIDL", "Groceries"),
    ("VOLG", "Groceries"), ("ALNATURA", "Groceries"), ("BAECKEREI", "Groceries"),
    ("KIOSK", "Groceries"), ("WOCHENMARKT", "Groceries"), ("HOFLADEN", "Groceries"),
    ("SPAR", "Groceries"), ("AVEC", "Groceries"), ("FARMY", "Groceries"),
    ("BAECKER", "Groceries"), ("METZGEREI", "Groceries"), ("LANDI", "Groceries"),
    ("PRIMO", "Groceries"), ("TOP CC", "Groceries"),
    # Restaurants
    ("MENSA", "Restaurants"), ("CAFE", "Restaurants"), ("PIZZA", "Restaurants"),
    ("BURGER", "Restaurants"), ("MCDONALD", "Restaurants"), ("STARBUCKS", "Restaurants"),
    ("HILTL", "Restaurants"), ("TIBITS", "Restaurants"), ("KEBAB", "Restaurants"),
    ("IMBISS", "Restaurants"), ("TAKE-AWAY", "Restaurants"), ("HOLY COW", "Restaurants"),
    ("YOOJI", "Restaurants"), ("ZEUGHAUSKELLER", "Restaurants"), ("KRONENHALLE", "Restaurants"),
    ("SPRUENGLI", "Restaurants"), ("HONOLD", "Restaurants"), ("VAPIANO", "Restaurants"),
    ("BRASSERIE", "Restaurants"), ("NOOCH", "Restaurants"), ("YARDBIRD", "Restaurants"),
    ("ROSSO", "Restaurants"), ("BEBEK", "Restaurants"), ("GEROLDS", "Restaurants"),
    ("KAFI", "Restaurants"), ("BAR 63", "Restaurants"), ("BAR (BAR)", "Restaurants"),
    ("RISTORANTE", "Restaurants"), ("TRATTORIA", "Restaurants"), ("OSTERIA", "Restaurants"),
    ("PIZZERIA", "Restaurants"), ("GASTRO", "Restaurants"), ("BISTRO", "Restaurants"),
    ("CAFFE", "Restaurants"), ("COFFEE", "Restaurants"), ("KAFFEE", "Restaurants"),
    ("CONFISERIE", "Restaurants"), ("SUSHI", "Restaurants"), ("RAMEN", "Restaurants"),
    ("THAI", "Restaurants"), ("KEBAP", "Restaurants"), ("DOENER", "Restaurants"),
    ("FALAFEL", "Restaurants"), ("SUBWAY", "Restaurants"), ("KFC", "Restaurants"),
    ("FIVE GUYS", "Restaurants"), ("ZFV", "Restaurants"),
    ("PUB", "Restaurants"), ("BRAUEREI", "Restaurants"), ("BIERHALLE", "Restaurants"),
    ("LOUNGE", "Restaurants"), ("KANTINE", "Restaurants"),
    # Transport
    ("SBB", "Transport"), ("ZVV", "Transport"), ("UBER", "Transport"), ("BOLT", "Transport"),
    ("MOBILITY", "Transport"), ("PUBLIBIKE", "Transport"), ("PARKHAUS", "Transport"),
    ("PARKPLATZ", "Transport"), ("SHELL", "Transport"), ("MIGROL", "Transport"),
    ("AVIA", "Transport"), ("SOCAR", "Transport"), ("AMAG", "Transport"),
    ("VERKEHRSBETRIEBE", "Transport"), ("VERKEHRSVERBUND", "Transport"), ("VBZ", "Transport"),
    ("POSTAUTO", "Transport"), ("FLIXBUS", "Transport"), ("TAXI", "Transport"),
    ("EASYJET", "Transport"), ("SWISS INTERNATIONAL", "Transport"), ("EDELWEISS AIR", "Transport"),
    ("PARKING", "Transport"), ("VIGNETTE", "Transport"), ("TCS", "Transport"),
    ("LIME", "Transport"), ("TIER", "Transport"), ("VOI", "Transport"),
    ("BP", "Transport"), ("ESSO", "Transport"), ("TAMOIL", "Transport"),
    # Housing
    ("MIETE", "Housing"), ("EWZ", "Housing"), ("EKZ", "Housing"),
    ("IMMOBILIEN", "Housing"), ("LIEGENSCHAFT", "Housing"), ("VERWALTUNG", "Housing"),
    ("HAUSRAT", "Housing"),
    # Health
    ("APOTHEKE", "Health"), ("SUN STORE", "Health"), ("DROGERIE", "Health"),
    ("ZAHNARZT", "Health"), ("FIELMANN", "Health"), ("VISILAB", "Health"),
    ("PHYSIO", "Health"), ("AMAVITA", "Health"), ("TOPPHARM", "Health"),
    ("PHARMACIE", "Health"), ("PHARMACY", "Health"), ("ARZT", "Health"),
    ("PRAXIS", "Health"), ("SPITAL", "Health"), ("KLINIK", "Health"),
    ("CSS", "Health"), ("HELSANA", "Health"), ("SANITAS", "Health"), ("SWICA", "Health"),
    ("CONCORDIA", "Health"), ("ASSURA", "Health"), ("VISANA", "Health"), ("KPT", "Health"),
    ("OPTIK", "Health"),
    # Communication
    ("SWISSCOM", "Communication"), ("SUNRISE", "Communication"), ("SALT", "Communication"),
    ("YALLO", "Communication"), ("WINGO", "Communication"), ("QUICKLINE", "Communication"),
    ("SERAFE", "Communication"), ("INIT7", "Communication"), ("LEBARA", "Communication"),
    ("UPC", "Communication"),
    # Leisure
    ("SPOTIFY", "Leisure"), ("NETFLIX", "Leisure"), ("DISNEY", "Leisure"),
    ("APPLE TV", "Leisure"), ("AMAZON PRIME", "Leisure"), ("YOUTUBE", "Leisure"),
    ("ICLOUD", "Leisure"), ("FITNESS", "Leisure"), ("KINO", "Leisure"),
    ("MUSEUM", "Leisure"), ("KUNSTHAUS", "Leisure"), ("OPERNHAUS", "Leisure"),
    ("TONHALLE", "Leisure"), ("ZOO", "Leisure"), ("TICKET", "Leisure"),
    ("HALLENSTADION", "Leisure"), ("BAD", "Leisure"), ("STEAM", "Leisure"),
    ("NINTENDO", "Leisure"), ("ORELL", "Leisure"), ("EINTRITT", "Leisure"),
    ("FLOHMARKT", "Leisure"),
    ("CINEMA", "Leisure"), ("PATHE", "Leisure"), ("THEATER", "Leisure"),
    ("SCHAUSPIELHAUS", "Leisure"), ("EVENTFROG", "Leisure"), ("JAZZ", "Leisure"),
    ("CLUB", "Leisure"), ("GARDEROBE", "Leisure"), ("GYM", "Leisure"),
    ("BERGBAHN", "Leisure"), ("SEILBAHN", "Leisure"), ("SKIPASS", "Leisure"),
    ("HOTEL", "Leisure"), ("AIRBNB", "Leisure"), ("BOOKING.COM", "Leisure"),
    ("PLAYSTATION", "Leisure"), ("XBOX", "Leisure"), ("THALIA", "Leisure"),
    ("BUCHHANDLUNG", "Leisure"),
    # Clothing
    ("H&M", "Clothing"), ("ZALANDO", "Clothing"), ("MANOR", "Clothing"),
    ("ZARA", "Clothing"), ("OCHSNER", "Clothing"), ("GLOBUS", "Clothing"),
    ("UNIQLO", "Clothing"), ("DECATHLON", "Clothing"), ("C&A", "Clothing"),
    ("SNIPES", "Clothing"),
    ("PKZ", "Clothing"), ("JELMOLI", "Clothing"), ("BESTSELLER", "Clothing"),
    ("NIKE", "Clothing"), ("ADIDAS", "Clothing"), ("MANGO", "Clothing"),
    ("TALLY WEIJL", "Clothing"), ("VOEGELE", "Clothing"), ("CHICOREE", "Clothing"),
    ("FOOTLOCKER", "Clothing"), ("PRIMARK", "Clothing"),
    # very general words last, so the more specific rules above win
    ("SPORT", "Leisure"), ("MARKT", "Groceries"),
]


def _normalize(text):
    """'Café Zürich' -> 'CAFE ZUERICH': capitals, umlauts as AE/OE/UE, no accents."""
    text = str(text).upper()
    for umlaut, plain in [("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE")]:
        text = text.replace(umlaut, plain)
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _pattern(keyword):
    """Short keywords must be a whole word (no letter or digit right before or after)."""
    if len(keyword) <= 4:
        return re.compile(r"(?<![A-Z0-9])" + re.escape(keyword) + r"(?![A-Z0-9])")
    return re.compile(re.escape(keyword))


_COMPILED = [(_pattern(keyword), category) for keyword, category in RULES]


def categorize(merchant):
    """Return the category for a merchant text, or 'Other' if no rule matches."""
    text = _normalize(merchant)
    for pattern, category in _COMPILED:
        if pattern.search(text):
            return category
    return "Other"
