# Keyword rules: if the merchant text contains the keyword, it gets that category.
# Order matters: specific rules first ("COOP RESTAURANT" before "COOP").
RULES = [
    # specific
    ("RESTAURANT", "Restaurants"),
    ("TANKSTELLE", "Transport"),
    ("DO IT", "Other"),
    ("COOP MOBILE", "Communication"),
    ("VITALITY", "Health"),
    ("KRANKENKASSE", "Health"),
    ("MOTORFAHRZEUG", "Transport"),
    # Groceries
    ("COOP", "Groceries"), ("MIGROS", "Groceries"), ("MIGROLINO", "Groceries"),
    ("DENNER", "Groceries"), ("ALDI", "Groceries"), ("LIDL", "Groceries"),
    ("VOLG", "Groceries"), ("ALNATURA", "Groceries"), ("BAECKEREI", "Groceries"),
    ("KIOSK", "Groceries"), ("WOCHENMARKT", "Groceries"), ("HOFLADEN", "Groceries"),
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
    # Transport
    ("SBB", "Transport"), ("ZVV", "Transport"), ("UBER", "Transport"), ("BOLT", "Transport"),
    ("MOBILITY", "Transport"), ("PUBLIBIKE", "Transport"), ("PARKHAUS", "Transport"),
    ("PARKPLATZ", "Transport"), ("SHELL", "Transport"), ("MIGROL", "Transport"),
    ("AVIA", "Transport"), ("SOCAR", "Transport"), ("AMAG", "Transport"),
    # Housing
    ("MIETE", "Housing"), ("EWZ", "Housing"),
    # Health
    ("APOTHEKE", "Health"), ("SUN STORE", "Health"), ("DROGERIE", "Health"),
    ("ZAHNARZT", "Health"), ("FIELMANN", "Health"), ("VISILAB", "Health"),
    ("PHYSIO", "Health"),
    # Communication
    ("SWISSCOM", "Communication"), ("SUNRISE", "Communication"), ("SALT", "Communication"),
    ("YALLO", "Communication"), ("WINGO", "Communication"), ("QUICKLINE", "Communication"),
    ("DIGITEC CONNECT", "Communication"), ("SERAFE", "Communication"),
    # Leisure
    ("SPOTIFY", "Leisure"), ("NETFLIX", "Leisure"), ("DISNEY", "Leisure"),
    ("APPLE TV", "Leisure"), ("AMAZON PRIME", "Leisure"), ("YOUTUBE", "Leisure"),
    ("ICLOUD", "Leisure"), ("FITNESS", "Leisure"), ("KINO", "Leisure"),
    ("MUSEUM", "Leisure"), ("KUNSTHAUS", "Leisure"), ("OPERNHAUS", "Leisure"),
    ("TONHALLE", "Leisure"), ("ZOO", "Leisure"), ("TICKET", "Leisure"),
    ("HALLENSTADION", "Leisure"), ("BAD", "Leisure"), ("STEAM", "Leisure"),
    ("NINTENDO", "Leisure"), ("ORELL", "Leisure"), ("EINTRITT", "Leisure"),
    ("FLOHMARKT", "Leisure"),
    # Clothing
    ("H&M", "Clothing"), ("ZALANDO", "Clothing"), ("MANOR", "Clothing"),
    ("ZARA", "Clothing"), ("OCHSNER", "Clothing"), ("GLOBUS", "Clothing"),
    ("UNIQLO", "Clothing"), ("DECATHLON", "Clothing"), ("C&A", "Clothing"),
    ("SNIPES", "Clothing"),
]


def categorize(merchant):
    """Return the category for a merchant text, or 'Other' if no rule matches."""
    text = str(merchant).upper()
    for keyword, category in RULES:
        if keyword in text:
            return category
    return "Other"
