"""
db.py - all database access for the spending app.

Rule: this is the ONLY file that contains SQL. Pages and analytics code
call the functions below and get pandas DataFrames (or simple values) back.

Reading:  conn.query(sql, params=..., ttl=...)  -> returns a DataFrame
Writing:  with conn.session as s: s.execute(text(sql), params); s.commit()

Always pass values as parameters (:name), never with f-strings.
That protects against SQL injection.
"""

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Reads the [connections.neon] section of .streamlit/secrets.toml
conn = st.connection("neon", type="sql")


# ----------------------------------------------------------------------
# Helper for writing
# ----------------------------------------------------------------------
def _write(sql, params=None, returning=False):
    """Run an INSERT/UPDATE/DELETE and commit it.

    params can be one dict (one row) or a list of dicts (many rows at once).
    If returning=True, the first value of the first returned row is given back
    (used with 'RETURNING id' to get the id of a new row).
    """
    with conn.session as s:
        result = s.execute(text(sql), params or {})
        value = result.scalar() if returning else None
        s.commit()
    return value


# ----------------------------------------------------------------------
# Categories
# ----------------------------------------------------------------------
def get_categories():
    """List of all category names. Rarely changes, so cached for 1 hour."""
    df = conn.query("SELECT name FROM categories ORDER BY name", ttl="1h")
    return df["name"].tolist()


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------
def create_user(username, password_hash, household_type=None):
    """Create a user. Returns the new user id, or None if the name is taken."""
    try:
        return _write(
            "INSERT INTO users (username, password_hash, household_type) "
            "VALUES (:u, :p, :h) RETURNING id",
            {"u": username, "p": password_hash, "h": household_type},
            returning=True,
        )
    except IntegrityError:          # UNIQUE constraint on username
        return None


def get_user_by_username(username):
    """One user as a dict (incl. password_hash, for the login check), or None."""
    df = conn.query(
        "SELECT id, username, password_hash, household_type "
        "FROM users WHERE username = :u",
        params={"u": username}, ttl=0,
    )
    return None if df.empty else df.iloc[0].to_dict()


def search_users(search_text, exclude_user_id):
    """Find users by (part of) their name, e.g. to send a friend request."""
    return conn.query(
        "SELECT id, username FROM users "
        "WHERE username ILIKE :q AND id <> :me ORDER BY username LIMIT 20",
        params={"q": f"%{search_text}%", "me": exclude_user_id}, ttl=0,
    )

def get_household_type(user_id):
    """Household type of one user ('student', 'single', ...), or None."""
    df = conn.query(
        "SELECT household_type FROM users WHERE id = :id",
        params={"id": user_id}, ttl=0,
    )
    value = None if df.empty else df["household_type"].iloc[0]
    # A NULL from the database can arrive as None or NaN -> always give None
    return value if isinstance(value, str) else None


def get_user_ids_by_household(household_type):
    """Ids of all users with this household type - for 'compare with the same household type'."""
    return conn.query(
        "SELECT id FROM users WHERE household_type = :h",
        params={"h": household_type}, ttl=0,
    )["id"].tolist()

# ----------------------------------------------------------------------
# Transactions
# ----------------------------------------------------------------------
def get_transactions(user_id):
    """All transactions of ONE user. Only ever call this for the logged-in user."""
    return conn.query(
        "SELECT id, date, merchant, amount, category, source "
        "FROM transactions WHERE user_id = :uid ORDER BY date",
        params={"uid": user_id}, ttl=0,
    )


def add_transaction(user_id, date, merchant, amount, category, source="cash"):
    """Add one transaction (e.g. a cash entry). amount > 0 means money spent."""
    return _write(
        "INSERT INTO transactions (user_id, date, merchant, amount, category, source) "
        "VALUES (:u, :d, :m, :a, :c, :s) RETURNING id",
        {"u": user_id, "d": date, "m": merchant,
         "a": amount, "c": category, "s": source},
        returning=True,
    )


def add_transactions_bulk(user_id, df, source="bank"):
    """Add many transactions at once, e.g. from an uploaded bank CSV.

    df needs the columns: date, merchant, amount, category.
    """
    rows = [
        {"u": user_id, "d": r.date, "m": r.merchant,
         "a": float(r.amount), "c": r.category, "s": source}
        for r in df.itertuples()
    ]
    if rows:
        _write(
            "INSERT INTO transactions (user_id, date, merchant, amount, category, source) "
            "VALUES (:u, :d, :m, :a, :c, :s)",
            rows,
        )
    return len(rows)


def update_category(transaction_id, user_id, category):
    """Change the category of a transaction. user_id makes sure people can
    only change their OWN transactions."""
    _write(
        "UPDATE transactions SET category = :c WHERE id = :t AND user_id = :u",
        {"c": category, "t": transaction_id, "u": user_id},
    )


def delete_transaction(transaction_id, user_id):
    _write(
        "DELETE FROM transactions WHERE id = :t AND user_id = :u",
        {"t": transaction_id, "u": user_id},
    )


# ----------------------------------------------------------------------
# Friendships
# A row (user_id=A, friend_id=B) means "A sent B a request".
# status 'accepted' means they are friends (in both directions).
# ----------------------------------------------------------------------
def send_friend_request(from_id, to_id):
    """Send a request. If the other person already asked you, you become
    friends right away. Sending twice does nothing."""
    with conn.session as s:
        reverse = s.execute(
            text("SELECT 1 FROM friendships WHERE user_id = :to AND friend_id = :me"),
            {"to": to_id, "me": from_id},
        ).first()
        if reverse:
            s.execute(
                text("UPDATE friendships SET status = 'accepted' "
                     "WHERE user_id = :to AND friend_id = :me"),
                {"to": to_id, "me": from_id},
            )
        else:
            s.execute(
                text("INSERT INTO friendships (user_id, friend_id) VALUES (:me, :to) "
                     "ON CONFLICT DO NOTHING"),
                {"me": from_id, "to": to_id},
            )
        s.commit()


def get_incoming_requests(user_id):
    """Pending requests that OTHER people sent to this user."""
    return conn.query(
        "SELECT u.id, u.username FROM friendships f "
        "JOIN users u ON u.id = f.user_id "
        "WHERE f.friend_id = :me AND f.status = 'pending' ORDER BY u.username",
        params={"me": user_id}, ttl=0,
    )


def accept_request(from_id, user_id):
    _write(
        "UPDATE friendships SET status = 'accepted' "
        "WHERE user_id = :f AND friend_id = :me",
        {"f": from_id, "me": user_id},
    )


def remove_friendship(user_a, user_b):
    """Decline a request or unfriend - works in both directions."""
    _write(
        "DELETE FROM friendships WHERE (user_id = :a AND friend_id = :b) "
        "OR (user_id = :b AND friend_id = :a)",
        {"a": user_a, "b": user_b},
    )


def get_friends(user_id):
    """All accepted friends, no matter who sent the request."""
    return conn.query(
        "SELECT u.id, u.username FROM friendships f "
        "JOIN users u ON u.id = CASE WHEN f.user_id = :me "
        "                       THEN f.friend_id ELSE f.user_id END "
        "WHERE (f.user_id = :me OR f.friend_id = :me) AND f.status = 'accepted' "
        "ORDER BY u.username",
        params={"me": user_id}, ttl=0,
    )


# ----------------------------------------------------------------------
# Groups
# ----------------------------------------------------------------------
def create_group(name, creator_id):
    """Create a group; the creator becomes its first member. Returns group id."""
    with conn.session as s:
        group_id = s.execute(
            text("INSERT INTO user_groups (name, created_by) VALUES (:n, :c) RETURNING id"),
            {"n": name, "c": creator_id},
        ).scalar()
        s.execute(
            text("INSERT INTO group_members (group_id, user_id) VALUES (:g, :u)"),
            {"g": group_id, "u": creator_id},
        )
        s.commit()
    return group_id


def add_group_member(group_id, user_id):
    _write(
        "INSERT INTO group_members (group_id, user_id) VALUES (:g, :u) "
        "ON CONFLICT DO NOTHING",
        {"g": group_id, "u": user_id},
    )


def leave_group(group_id, user_id):
    _write(
        "DELETE FROM group_members WHERE group_id = :g AND user_id = :u",
        {"g": group_id, "u": user_id},
    )


def get_user_groups(user_id):
    """The groups this user is a member of, with member counts."""
    return conn.query(
        "SELECT g.id, g.name, COUNT(m2.user_id) AS members "
        "FROM user_groups g "
        "JOIN group_members m  ON m.group_id = g.id AND m.user_id = :me "
        "JOIN group_members m2 ON m2.group_id = g.id "
        "GROUP BY g.id, g.name ORDER BY g.name",
        params={"me": user_id}, ttl=0,
    )


def get_group_members(group_id):
    return conn.query(
        "SELECT u.id, u.username FROM group_members m "
        "JOIN users u ON u.id = m.user_id WHERE m.group_id = :g ORDER BY u.username",
        params={"g": group_id}, ttl=0,
    )


def get_all_user_ids():
    """Ids of all users - for the 'compare with everyone' mean spender."""
    return conn.query("SELECT id FROM users", ttl=0)["id"].tolist()


# ----------------------------------------------------------------------
# Aggregates for comparisons (privacy: no single transactions!)
# ----------------------------------------------------------------------
def get_monthly_totals(user_ids):
    """Spending per user, month and category - never individual transactions.

    This is what the comparison page uses for friends, groups and all users.
    Returns columns: user_id, month, category, total
    """
    if not user_ids:
        return conn.query(
            "SELECT NULL::int AS user_id, NULL::date AS month, "
            "NULL::text AS category, NULL::numeric AS total WHERE false", ttl=0)
    df = conn.query(
        "SELECT user_id, date_trunc('month', date)::date AS month, "
        "       category, SUM(amount) AS total "
        "FROM transactions WHERE user_id = ANY(:ids) "
        "GROUP BY user_id, month, category ORDER BY user_id, month",
        params={"ids": list(user_ids)}, ttl=0,
    )
    df["total"] = df["total"].astype(float)   # NUMERIC arrives as Decimal
    return df
