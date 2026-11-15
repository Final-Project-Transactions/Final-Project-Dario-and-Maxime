"""
generate_data.py - fills the database with fictional users for development and the demo.

Creates:
  - 150 fictional users (default) built from 6 personas typical for Zurich:
    student, young professional, couple, family, commuter, retiree,
    plus a few "big spenders" so the mean differs from the median
  - 12 months of transactions per user, calibrated to Swiss data (see CALIBRATION)
  - friendships (most accepted, some pending)
  - 4 groups
  - one known demo account for the presentation: username "demo"

Run it ONCE, from the project folder, with the venv active:
    python generate_data.py --dry-run     # only shows what would be created
    python generate_data.py               # writes to the database
    python generate_data.py --users 100   # other number of users

It reads the same .streamlit/secrets.toml as the app. Everything is written in
ONE database transaction: if anything fails, nothing is saved.
It refuses to run if the fake users already exist.

======================================================================
CALIBRATION - where the numbers come from (state: November 2026)
======================================================================
The persona budgets below are anchored to published figures, then adapted
to Zurich. They are still a SIMULATION: the official statistics give means
per household, not the distribution within a household type, so the spread
and the split into single purchases are our own assumptions.

1. BFS Haushaltsbudgeterhebung (HABE) 2022, mean per household (2.08 persons),
   CHF per month (BFS press release, table T1):
     Nahrungsmittel & alkoholfreie Getraenke  629   -> Groceries
     Alkohol & Tabak                           92   -> Groceries
     Gast- & Beherbergungsstaetten            540   -> Restaurants
     Bekleidung & Schuhe                      172   -> Clothing
     Wohnen & Energie                       1 374   -> Housing
     Wohnungseinrichtung/Haushaltsfuehrung    207   -> Other
     Gesundheitsausgaben (out of pocket)      221   -> Health
     Verkehr                                  761   -> Transport
     Nachrichtenuebermittlung                 163   -> Communication
     Unterhaltung, Erholung, Kultur           484   -> Leisure
     Andere Waren & Dienstleistungen          307   -> Other
     Konsumausgaben total                   4 949
     Krankenkassenpraemien Grundversicherung  660   -> booked under Health here
   (Taxes and savings are NOT consumption and are not simulated.)
   HABE 2023 (published Nov 2025): disposable income 7 186 CHF, expenses
   "changed little" - we did not find the 2023 category table, so 2022 is used.

2. Rents: Statistik Stadt Zuerich, Mietpreiserhebung 2026 (Stichtag 1.4.2026),
   median NET rents, all landlords: 2 rooms 1 497, 3 rooms 1 628, 4 rooms 1 955.
   Private landlords only: 2 rooms 1 670, 3 rooms 1 950, 4 rooms 2 434.
   Gross rent (with Nebenkosten) is about 10-15 % above net. We simulate gross.
   WG room for students: roughly 700-1 100 CHF (college-council.com, based on
   ETH/EPFL cost-of-living figures 2025/26).

3. Health insurance 2026, canton Zurich premium region 1 (city), average
   monthly premium (BSV/EDI, "Durchschnittspraemien 2026"):
   adults 640, young adults 459, children 154. People with a high franchise
   pay less, so personas use somewhat lower values.

4. Public transport (prices valid from Dec 2025):
   ZVV NetzPass 1-2 zones (city): adult 88/month, youth 6-24.99 years 64/month.
   SBB GA 2nd class: adult 440/month, GA Jugend 295/month.
   SBB Halbtax: 190/year adults (120 youth).

5. Subscriptions (Swiss prices, 2025/26): Spotify Premium 15.95 (student 8.95),
   Netflix Standard 22.90, Disney+ 16.90, Apple TV 10.90, Amazon Prime 9.99,
   YouTube Premium ~15.90 (approx.), iCloud+ 200 GB 3.00,
   Serafe (radio/TV fee) 335/year = 27.90/month.
   Mobile: Swisscom flat 71.80 (from Apr 2026); discount brands under 20.

Merchants are real businesses in Zurich (Nov 2026). Merchant strings imitate
bank statements ("TWINT *COOP", "COOP-2234 ZUERICH") so that the keyword
categoriser can later be tested on realistic text.
"""

import argparse
import datetime as dt
import random
import tomllib
from collections import Counter

import bcrypt
from sqlalchemy import create_engine, text

# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------
SEED = 42                          # fixed seed -> the same data every time
START = dt.date(2025, 11, 1)       # fixed period (not "today") -> reproducible
END = dt.date(2026, 10, 31)
DEMO_PASSWORD = "demo1234"         # password of ALL fake accounts (demo only!)

FIRST_NAMES = [
    "anna", "luca", "mia", "noah", "lea", "leon", "lara", "elias", "sara", "jan",
    "nina", "david", "laura", "simon", "julia", "nico", "elena", "fabio", "alina",
    "marco", "chiara", "tim", "sofia", "jonas", "emma", "levin", "lina", "robin",
    "zoe", "samuel", "ella", "matteo", "livia", "yannick", "selina", "dario",
    "maxime", "olivia", "andrin", "nora", "gian", "aurelia", "timo", "melanie",
    "reto", "ursula", "beat", "heidi", "peter", "ruth", "flavia", "cedric",
    "ladina", "silvan", "jasmin", "rafael", "seraina", "lukas", "noemi", "moritz",
    "vera", "pascal", "amélie", "basil", "salome", "joel", "tamara", "remo",
    "nadine", "fabienne", "adrian", "celine", "manuel", "vanessa", "sandro",
]

# ----------------------------------------------------------------------
# Personas: monthly budgets in CHF.
#   fixed costs:    (typical value, relative spread)       -> one payment/month
#   variable costs: (monthly budget, spread, purchases/month)
# "scale" (per user) multiplies the variable budgets; rent stays within -25 %/+35 %.
# ----------------------------------------------------------------------
PERSONAS = {
    # UZH/ETH student in a WG room, youth NetzPass, Mensa, student Spotify
    "student": {
        "household_type": "student", "weight": 0.28, "persons": 1,
        "rent": (850, 0.18), "rent_label": "WG-Zimmer Miete",
        "insurance": (380, 0.12),             # young adult, high franchise
        "phone": (22, 0.35), "phone_providers": ["Yallo", "Wingo", "Digitec Connect", "Coop Mobile", "Salt"],
        "electricity": None,                  # included in WG rent
        "subscriptions": ["Spotify Student", "Netflix Standard", "iCloud+ 200GB"],
        "n_subs": (1, 2),
        "transport_pass": ("ZVV NetzPass Jugend", 64.00), "car_prob": 0.03,
        "groceries": (340, 0.30, 11), "restaurants": (210, 0.45, 9),
        "leisure": (130, 0.50, 3), "clothing": (65, 0.80, 1),
        "health": (35, 1.0, 1), "other": (70, 0.8, 1),
        "restaurant_pool": "student", "cash_share": 0.14,
    },
    # single, 2-room flat, employed in the city
    "young_professional": {
        "household_type": "single", "weight": 0.24, "persons": 1,
        "rent": (1800, 0.18), "rent_label": "Miete 2-Zimmer",
        "insurance": (560, 0.10),
        "phone": (45, 0.35), "phone_providers": ["Swisscom", "Sunrise", "Salt", "Yallo", "Wingo"],
        "electricity": (45, 0.3),
        "subscriptions": ["Spotify Premium", "Netflix Standard", "Disney+", "Apple TV",
                          "YouTube Premium", "iCloud+ 200GB", "ACTIV Fitness"],
        "n_subs": (2, 4),
        "transport_pass": ("ZVV NetzPass", 88.00), "car_prob": 0.25,
        "groceries": (460, 0.30, 12), "restaurants": (520, 0.40, 11),
        "leisure": (330, 0.50, 5), "clothing": (170, 0.70, 2),
        "health": (70, 1.0, 1), "other": (180, 0.8, 2),
        "restaurant_pool": "city", "cash_share": 0.05,
    },
    # two adults, 3-room flat, one shared account
    "couple": {
        "household_type": "couple", "weight": 0.16, "persons": 2,
        "rent": (2000, 0.18), "rent_label": "Miete 3-Zimmer",
        "insurance": (1150, 0.10),
        "phone": (85, 0.30), "phone_providers": ["Swisscom", "Sunrise", "Salt", "Quickline"],
        "electricity": (65, 0.3),
        "subscriptions": ["Spotify Duo", "Netflix Standard", "Disney+", "Apple TV",
                          "Amazon Prime", "iCloud+ 200GB", "ACTIV Fitness"],
        "n_subs": (2, 4),
        "transport_pass": ("ZVV NetzPass", 176.00), "car_prob": 0.45,   # 2 passes
        "groceries": (820, 0.25, 14), "restaurants": (620, 0.40, 9),
        "leisure": (450, 0.50, 5), "clothing": (260, 0.70, 2),
        "health": (130, 1.0, 2), "other": (320, 0.8, 3),
        "restaurant_pool": "city", "cash_share": 0.05,
    },
    # two adults + two children, 4-room flat, car
    "family": {
        "household_type": "family", "weight": 0.13, "persons": 4,
        "rent": (2350, 0.18), "rent_label": "Miete 4-Zimmer",
        "insurance": (1500, 0.08),            # 2 adults + 2 children (ZVV passes for kids below)
        "phone": (110, 0.30), "phone_providers": ["Swisscom", "Sunrise", "Salt"],
        "electricity": (95, 0.3),
        "subscriptions": ["Spotify Family", "Netflix Standard", "Disney+", "Amazon Prime",
                          "iCloud+ 200GB"],
        "n_subs": (2, 4),
        "transport_pass": None, "car_prob": 0.90,
        "groceries": (1300, 0.22, 17), "restaurants": (360, 0.50, 5),
        "leisure": (520, 0.45, 5), "clothing": (310, 0.60, 3),
        "health": (210, 0.9, 2), "other": (420, 0.7, 3),
        "restaurant_pool": "family", "cash_share": 0.08,
    },
    # lives outside the city (cheaper rent), commutes with GA
    "commuter": {
        "household_type": "single", "weight": 0.11, "persons": 1,
        "rent": (1500, 0.18), "rent_label": "Miete 3-Zimmer",
        "insurance": (540, 0.10),
        "phone": (45, 0.35), "phone_providers": ["Swisscom", "Sunrise", "Salt", "Yallo"],
        "electricity": (50, 0.3),
        "subscriptions": ["Spotify Premium", "Netflix Standard", "Disney+", "YouTube Premium",
                          "iCloud+ 200GB"],
        "n_subs": (1, 3),
        "transport_pass": ("SBB GA 2. Klasse", 440.00), "car_prob": 0.30,
        "groceries": (480, 0.30, 11), "restaurants": (430, 0.40, 10),
        "leisure": (280, 0.50, 4), "clothing": (160, 0.70, 2),
        "health": (70, 1.0, 1), "other": (170, 0.8, 2),
        "restaurant_pool": "city", "cash_share": 0.06,
    },
    # single pensioner, long-term tenant (cheaper old rent), Halbtax, more cash
    "retiree": {
        "household_type": "retiree", "weight": 0.08, "persons": 1,
        "rent": (1350, 0.22), "rent_label": "Miete 2-Zimmer",
        "insurance": (640, 0.08),             # low franchise
        "phone": (38, 0.35), "phone_providers": ["Swisscom", "Sunrise"],
        "electricity": (50, 0.3),
        "subscriptions": ["Netflix Standard", "Apple TV"],
        "n_subs": (0, 1),
        "transport_pass": ("SBB Halbtax (Jahr/12)", 15.85), "car_prob": 0.30,
        "groceries": (520, 0.25, 13), "restaurants": (240, 0.50, 5),
        "leisure": (240, 0.50, 3), "clothing": (100, 0.70, 1),
        "health": (260, 0.8, 3), "other": (160, 0.8, 2),
        "restaurant_pool": "retiree", "cash_share": 0.25,
    },
}

# ----------------------------------------------------------------------
# Real Zurich merchants (checked Nov 2026) and typical single amounts
# ----------------------------------------------------------------------
MERCHANTS = {
    "Groceries": ["Coop", "Migros", "Denner", "Aldi Suisse", "Lidl", "Coop Pronto",
                  "Migrolino", "Volg", "Alnatura", "Coop City"],
    "Transport": ["SBB Mobile", "ZVV-App", "Uber", "Bolt", "Mobility Carsharing",
                  "PubliBike", "Parkhaus Urania"],
    "Leisure": ["Kino Arena Sihlcity", "Riffraff Kino", "Orell Fuessli", "Hallenstadion",
                "Kunsthaus Zuerich", "Landesmuseum", "Hallenbad Oerlikon", "Seebad Enge",
                "Steam", "Nintendo eShop", "FCZ Ticketing", "Opernhaus Zuerich",
                "Tonhalle Zuerich", "Zoo Zuerich", "Ticketcorner"],
    "Clothing": ["H&M", "Zalando", "Manor", "Zara", "Ochsner Sport", "Globus",
                 "Uniqlo", "Decathlon", "C&A", "Snipes"],
    "Health": ["Amavita Apotheke", "Sun Store", "Coop Vitality", "Zahnarzt Dr. Keller",
               "Fielmann", "Visilab", "Physiotherapie Seefeld", "Drogerie Mueller"],
    "Other": ["Post CH", "Digitec Galaxus", "Brack.ch", "IKEA Spreitenbach", "Coiffeur",
              "Interdiscount", "Fust", "Jumbo", "Migros Do it + Garden", "Microspot",
              "Depot", "Muji"],
}
RESTAURANTS = {
    "student": ["Mensa UZH Zentrum", "Mensa ETH Polyterrasse", "Kebab Haus Langstrasse",
                "Dieci Pizza", "Holy Cow!", "Starbucks", "Nooch Asian Kitchen",
                "Tibits", "Coop Restaurant", "Kafi Schnaps", "Burger King"],
    "city": ["Tibits", "Hiltl", "Zeughauskeller", "Holy Cow!", "Yooji's", "Yardbird",
             "Cafe Spruengli", "Vapiano", "Frau Gerolds Garten", "Rosso", "Brasserie Lipp",
             "Nooch Asian Kitchen", "Starbucks", "Dieci Pizza", "Bebek", "Bar 63"],
    "family": ["Coop Restaurant", "Migros Restaurant", "Dieci Pizza", "Burger King",
               "McDonald's", "Vapiano", "Zeughauskeller", "Holy Cow!", "Cafe Spruengli"],
    "retiree": ["Cafe Spruengli", "Migros Restaurant", "Coop Restaurant", "Zeughauskeller",
                "Confiserie Honold", "Restaurant Zunfthaus zur Waag", "Kronenhalle"],
}
RESTAURANT_TICKET = {"student": (9, 0.45), "city": (28, 0.6), "family": (45, 0.5),
                     "retiree": (22, 0.5)}        # typical bill (CHF, spread)
SUBSCRIPTIONS = {
    "Spotify Student": 8.95, "Spotify Premium": 15.95, "Spotify Duo": 20.95,
    "Spotify Family": 24.95, "Netflix Standard": 22.90, "Disney+": 16.90,
    "Apple TV": 10.90, "Amazon Prime": 9.99, "YouTube Premium": 15.90,
    "iCloud+ 200GB": 3.00, "ACTIV Fitness": 49.00,
}
INSURERS = ["CSS", "Helsana", "Swica", "Sanitas", "Visana", "Assura", "KPT", "Concordia"]
CAR_FUEL = ["Shell", "Migrol", "Avia", "Coop Pronto Tankstelle", "Socar"]
CAR_INSURERS = ["AXA Motorfahrzeug", "Mobiliar Motorfahrzeug", "Zurich Versicherung"]
CASH_MERCHANTS = {
    "Groceries": ["Wochenmarkt Buerkliplatz", "Baeckerei", "Kiosk", "Hofladen"],
    "Restaurants": ["Cafe (bar)", "Imbiss (bar)", "Bar (bar)", "Take-away (bar)"],
    "Leisure": ["Flohmarkt Kanzlei", "Eintritt (bar)", "Badi (bar)"],
    "Other": ["Trinkgeld", "Sonstiges (bar)", "Coiffeur (bar)"],
}


# ----------------------------------------------------------------------
# Generating the data (pure Python, nothing is written yet)
# ----------------------------------------------------------------------
def months(start, end):
    """First day of every month between start and end."""
    d = start.replace(day=1)
    while d <= end:
        yield d
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def days_in_month(first_day):
    nxt = (first_day.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return (nxt - first_day).days


def vary(rng, value, spread):
    """value * random factor (log-normal around 1), never below 1 CHF."""
    return max(1.0, value * rng.lognormvariate(0, spread))


def statement_text(rng, merchant):
    """Make the merchant look like a real bank statement line."""
    r = rng.random()
    if r < 0.55:
        return merchant
    if r < 0.80:
        return f"TWINT *{merchant.upper()}"
    return f"{merchant.upper()}-{rng.randint(1000, 9999)} ZUERICH"


def make_users(rng, n_users):
    names = list(FIRST_NAMES)
    rng.shuffle(names)
    personas = list(PERSONAS)
    weights = [PERSONAS[p]["weight"] for p in personas]

    users = [{"username": "demo", "persona": "student", "scale": 1.0}]
    taken = {"demo"}
    for i in range(n_users - 1):
        base = names[i % len(names)]
        username = f"{base}_{rng.randint(10, 99)}"
        while username in taken:
            username = f"{base}_{rng.randint(10, 99)}"
        taken.add(username)
        users.append({
            "username": username,
            "persona": rng.choices(personas, weights)[0],
            # individual spending level: some are frugal, some generous
            "scale": rng.lognormvariate(0, 0.25),
        })
    # ~3 % "big spenders": pull the mean up, the median barely moves
    for u in rng.sample(users[1:], max(3, n_users // 30)):
        u["scale"] *= 2.5
    for u in users:
        u["household_type"] = PERSONAS[u["persona"]]["household_type"]
    return users


def make_transactions(rng, user):
    p = PERSONAS[user["persona"]]
    s = user["scale"]
    tx = []

    def add(date, merchant, amount, category, source="bank"):
        tx.append({"date": date, "merchant": merchant,
                   "amount": round(amount, 2), "category": category, "source": source})

    # fixed choices per user (same landlord, insurer, provider, subscriptions)
    # rent: typical value, varied and nudged by the spending level, kept within -25 % / +35 %
    rent = p["rent"][0] * min(max(rng.lognormvariate(0, p["rent"][1]) * s ** 0.5, 0.75), 1.35)
    insurer = rng.choice(INSURERS)
    insurance = vary(rng, p["insurance"][0], p["insurance"][1])
    phone_provider = rng.choice(p["phone_providers"])
    phone = vary(rng, p["phone"][0], p["phone"][1])
    electricity = vary(rng, *p["electricity"]) if p["electricity"] else None
    subs = rng.sample(p["subscriptions"], rng.randint(*p["n_subs"]))
    sub_days = {name: rng.randint(1, 28) for name in subs}
    has_car = rng.random() < p["car_prob"]
    fuel_station = rng.choice(CAR_FUEL)
    car_insurer = rng.choice(CAR_INSURERS)

    for m in months(START, END):
        n_days = days_in_month(m)

        # --- recurring payments -----------------------------------------
        add(m, p["rent_label"], rent, "Housing")
        if electricity:
            add(m.replace(day=min(10, n_days)), "ewz Strom", vary(rng, electricity, 0.15), "Housing")
        add(m.replace(day=min(5, n_days)), f"{insurer} Krankenkasse", insurance, "Health")
        add(m.replace(day=min(20, n_days)), phone_provider, phone, "Communication")
        if m.month == 1:                       # Serafe is billed yearly
            add(m.replace(day=15), "Serafe AG", 335.00, "Communication")
        for name in subs:
            add(m.replace(day=sub_days[name]), name, SUBSCRIPTIONS[name], "Leisure")
        if p["transport_pass"]:
            name, price = p["transport_pass"]
            add(m.replace(day=1), name, price, "Transport")
        if p["household_type"] == "family":
            add(m.replace(day=1), "ZVV NetzPass Jugend", 64.00, "Transport")
        if has_car:                            # HABE: private cars ~600 CHF/month per household
            add(m.replace(day=min(3, n_days)), car_insurer, vary(rng, 110, 0.1), "Transport")
            add(m.replace(day=1), "Parkplatz Miete", vary(rng, 150, 0.2), "Transport")
            for _ in range(rng.randint(2, 4)):
                add(m.replace(day=rng.randint(1, n_days)), fuel_station,
                    vary(rng, 75, 0.3), "Transport")
            if rng.random() < 0.15:            # garage / service now and then
                add(m.replace(day=rng.randint(1, n_days)), "AMAG Garage",
                    vary(rng, 450, 0.5), "Transport")

        # --- variable spending: monthly budget split into purchases ------
        for key, category in [("groceries", "Groceries"), ("leisure", "Leisure"),
                              ("clothing", "Clothing"), ("health", "Health"),
                              ("other", "Other")]:
            budget, spread, per_month = p[key]
            total = vary(rng, budget * s, spread * 0.5)
            n = max(0, round(rng.gauss(per_month, per_month * 0.3)))
            if n == 0:
                continue
            parts = [rng.random() + 0.2 for _ in range(n)]
            for part in parts:
                amount = total * part / sum(parts)
                day = m.replace(day=rng.randint(1, n_days))
                if category in CASH_MERCHANTS and rng.random() < p["cash_share"]:
                    add(day, rng.choice(CASH_MERCHANTS[category]),
                        min(amount, 80), category, "cash")
                else:
                    add(day, statement_text(rng, rng.choice(MERCHANTS[category])),
                        amount, category)

        # restaurants: number of visits x typical bill of that persona
        budget, spread, per_month = p["restaurants"]
        ticket, t_spread = RESTAURANT_TICKET[p["restaurant_pool"]]
        n_visits = max(0, round(budget * s / ticket * rng.lognormvariate(0, spread * 0.5)))
        for _ in range(n_visits):
            day = m.replace(day=rng.randint(1, n_days))
            amount = vary(rng, ticket, t_spread)
            if rng.random() < p["cash_share"]:
                add(day, rng.choice(CASH_MERCHANTS["Restaurants"]), min(amount, 60),
                    "Restaurants", "cash")
            else:
                add(day, statement_text(rng, rng.choice(RESTAURANTS[p["restaurant_pool"]])),
                    amount, "Restaurants")

        # a few single tickets / rides on top of the pass
        for _ in range(rng.randint(0, 4)):
            add(m.replace(day=rng.randint(1, n_days)), rng.choice(MERCHANTS["Transport"]),
                vary(rng, 14, 0.6) * s, "Transport")
    return tx


def make_friendships(rng, users):
    """Friendships between user indices. People of the same persona are more
    likely to know each other. Returns (a, b, status) tuples."""
    n = len(users)
    pairs = set()
    for a in range(n):
        same = [i for i in range(n) if i != a and users[i]["persona"] == users[a]["persona"]]
        for _ in range(rng.randint(2, 6)):
            b = rng.choice(same) if same and rng.random() < 0.6 else rng.randrange(n)
            if a != b and (a, b) not in pairs and (b, a) not in pairs:
                pairs.add((a, b))
    result = [(a, b, "accepted" if rng.random() < 0.85 else "pending")
              for a, b in sorted(pairs)]
    # give the demo account (index 0) 2 open requests to show in the presentation
    strangers = [i for i in range(1, n) if (0, i) not in pairs and (i, 0) not in pairs]
    result += [(i, 0, "pending") for i in rng.sample(strangers, 2)]
    return result


def make_groups(rng, users):
    """4 groups (name, creator index, member indices). The demo user is in two."""
    by = lambda *ps: [i for i, u in enumerate(users) if u["persona"] in ps and i != 0]
    students, singles, families = by("student"), by("young_professional", "commuter"), by("family", "couple")
    return [
        ("WG Kreis 4", 0, [0] + rng.sample(students, min(3, len(students)))),
        ("Lerngruppe VWL UZH", 0, [0] + rng.sample(students, min(5, len(students)))),
        ("Buero Team Oerlikon", singles[0], rng.sample(singles, min(7, len(singles)))),
        ("Familien Quartier Wipkingen", families[0], rng.sample(families, min(6, len(families)))),
    ]


# ----------------------------------------------------------------------
# Writing to the database
# ----------------------------------------------------------------------
def read_db_url(path=".streamlit/secrets.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)["connections"]["neon"]["url"]


def write_to_db(users, transactions, friendships, groups):
    engine = create_engine(read_db_url())
    names = [u["username"] for u in users]

    with engine.begin() as con:       # one transaction: all or nothing
        existing = con.execute(
            text("SELECT COUNT(*) FROM users WHERE username = ANY(:names)"),
            {"names": names},
        ).scalar()
        if existing:
            raise SystemExit(
                f"Stopped: {existing} of the fake users already exist in the database. "
                "The script only runs once. To start over, agree with your teammate and "
                "run TRUNCATE (see SETUP.md / CONTRIBUTING.md).")

        print("Hashing the demo password ...")
        pw_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()

        print(f"Inserting {len(users)} users ...")
        ids = []
        for u in users:
            ids.append(con.execute(
                text("INSERT INTO users (username, password_hash, household_type) "
                     "VALUES (:u, :p, :h) RETURNING id"),
                {"u": u["username"], "p": pw_hash, "h": u["household_type"]},
            ).scalar())

        print(f"Inserting {len(transactions)} transactions (may take a minute) ...")
        rows = [{"u": ids[i], **t} for i, t in transactions]
        for start in range(0, len(rows), 5000):          # in chunks
            con.execute(
                text("INSERT INTO transactions (user_id, date, merchant, amount, category, source) "
                     "VALUES (:u, :date, :merchant, :amount, :category, :source)"),
                rows[start:start + 5000],
            )

        print(f"Inserting {len(friendships)} friendships ...")
        con.execute(
            text("INSERT INTO friendships (user_id, friend_id, status) VALUES (:a, :b, :s)"),
            [{"a": ids[a], "b": ids[b], "s": s} for a, b, s in friendships],
        )

        print(f"Inserting {len(groups)} groups ...")
        for name, creator, members in groups:
            gid = con.execute(
                text("INSERT INTO user_groups (name, created_by) VALUES (:n, :c) RETURNING id"),
                {"n": name, "c": ids[creator]},
            ).scalar()
            con.execute(
                text("INSERT INTO group_members (group_id, user_id) VALUES (:g, :u)"),
                [{"g": gid, "u": ids[m]} for m in sorted(set(members))],
            )
    print("Done! Everything was saved.")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Fill the database with fake users.")
    parser.add_argument("--users", type=int, default=150, help="number of users (default 150)")
    parser.add_argument("--dry-run", action="store_true",
                        help="only print a summary, write nothing")
    args = parser.parse_args()

    rng = random.Random(SEED)
    users = make_users(rng, args.users)
    transactions = [(i, t) for i, u in enumerate(users) for t in make_transactions(rng, u)]
    friendships = make_friendships(rng, users)
    groups = make_groups(rng, users)

    # ---- summary -------------------------------------------------------
    n_months = len(list(months(START, END)))
    totals, by_persona, by_cat = Counter(), Counter(), Counter()
    for i, t in transactions:
        totals[i] += t["amount"]
        by_persona[users[i]["persona"]] += t["amount"]
        by_cat[t["category"]] += t["amount"]
    monthly = sorted(v / n_months for v in totals.values())
    mean = sum(monthly) / len(monthly)
    median = monthly[len(monthly) // 2]
    persona_count = Counter(u["persona"] for u in users)

    print(f"Period: {START} to {END} ({n_months} months)")
    print(f"Users: {len(users)}  {dict(persona_count)}")
    print(f"Transactions: {len(transactions)} "
          f"(cash: {sum(t['source'] == 'cash' for _, t in transactions)})")
    print(f"Spending per user and month: mean CHF {mean:,.0f}, median CHF {median:,.0f}, "
          f"min CHF {monthly[0]:,.0f}, max CHF {monthly[-1]:,.0f}")
    print("Mean per month by persona:",
          {p: round(by_persona[p] / persona_count[p] / n_months) for p in persona_count})
    print("Share by category:",
          {c: f"{100 * v / sum(by_cat.values()):.0f}%" for c, v in by_cat.most_common()})
    print(f"Friendships: {len(friendships)} "
          f"({sum(s == 'pending' for *_, s in friendships)} pending)")
    print(f"Groups: {[(g[0], len(set(g[2]))) for g in groups]}")
    print(f"Demo login: username 'demo', password '{DEMO_PASSWORD}' "
          "(all fake accounts use this password)")

    if args.dry_run:
        print("\nDry run: nothing was written.")
    else:
        write_to_db(users, transactions, friendships, groups)


if __name__ == "__main__":
    main()
