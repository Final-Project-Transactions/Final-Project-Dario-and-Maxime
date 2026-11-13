# Setup guide: getting the project running on your computer

This guide gets you from zero to a working local copy that is connected to our database, so you can build the rest of the app. Follow the steps **in order**. Everything here is for **Windows** with **VS Code**.

Read `CONTRIBUTING.md` too: it explains how we work together.

**Time needed:** about 30–45 minutes.

---

## Overview: what already exists

| File / thing | What it is |
|---|---|
| **Neon database** (online) | Our Postgres database, hosted by Neon in Frankfurt (free plan). The tables already exist. |
| `schema.sql` | The SQL code that created the tables. Documentation; you don't need to run it again. |
| `db.py` | **All** database functions. The rest of the app uses these instead of writing SQL. |
| `requirements.txt` | The Python packages the app needs. |
| `.gitignore` | Files Git must never upload, including the password file. |
| `.streamlit/secrets.toml` | The database password. **Not in the repo.** You create it yourself in step 6. |

**Why a hosted database?** The app will run online on Streamlit Community Cloud, which doesn't keep local files permanently, so a local database file (SQLite) would lose its data on every restart. Neon keeps the data online.

---

## Step 1: Get access to the repo

1. Make sure you have a **GitHub account**, **Git** and **VS Code** installed.


---

## Step 2: Clone the repo

1. In VS Code: **Ctrl+Shift+P** → type `Git: Clone` → paste the repo URL (from GitHub's green **Code** button).
2. Choose a folder on your computer (for example your uni folder) and click **Open** when VS Code asks.

You should now see `schema.sql`, `db.py`, `requirements.txt` and the other files in the VS Code explorer.

---

## Step 3: Check your Python version

We both use **Python 3.14**. Old versions don't work: current Streamlit needs at least Python 3.11.

Open a terminal in VS Code (**Terminal → New Terminal**) and run:
```powershell
py -0p
```
This lists every Python installed on your computer. You need a line with **3.14**.

⚠️ The old Python launcher shows 3.14 incorrectly as **`3.1`**, with a path containing `pythoncore-3.14-64`. That one is fine.

**If there is no 3.14:** install it from **python.org → Downloads → Windows** (or the Python install manager linked there), then **close and reopen VS Code** and run `py -0p` again.

**Tip:** if you also see very old versions such as 3.7, they can cause confusion (Maxime had this problem). You can uninstall them via **Windows Settings → Apps** if nothing else needs them.

---

## Step 4: Create the virtual environment (venv)

A venv is a separate Python setup just for this project, so its packages don't mix with other projects.

**4.1 Allow PowerShell to run the activation script** (one time only, otherwise you get "running scripts is disabled on this system"):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Confirm with `J` or `Y` if asked. This only affects your own Windows user and allows scripts you create yourself.

**4.2 Create the venv with Python 3.14** (in the project folder):
```powershell
py -V:3.14 -m venv .venv
```
If that gives an error, use the full path from step 3 instead, for example:
```powershell
& "C:\Users\<YOU>\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv .venv
```

**4.3 Activate it:**
```powershell
.venv\Scripts\activate
```
`(.venv)` should now appear at the start of the terminal line.

**4.4 Check the version:**
```powershell
python --version
```
It must say **Python 3.14.x**. If it shows anything older, delete the venv (`deactivate`, then `Remove-Item -Recurse -Force .venv`) and repeat 4.2.

**4.5 Tell VS Code to use it:** **Ctrl+Shift+P** → `Python: Select Interpreter` → choose the one with `.venv` in its path.

**Remember:** in every **new** terminal, activate the venv again (`.venv\Scripts\activate`) if you don't see `(.venv)`. Once you're in the venv, use `python` rather than `py`.

---

## Step 5: Install the packages

```powershell
python -m pip install -r requirements.txt
```
If pip suggests upgrading itself, you can do it; it only affects the venv.

**Check:**
```powershell
python -c "import streamlit, sqlalchemy, psycopg, bcrypt, pandas; print('all good')"
```
It must print `all good`.

**Note on the database driver:** `requirements.txt` uses `psycopg[binary]` (psycopg **version 3**), not `psycopg2`. Newer SQLAlchemy versions look for psycopg 3 by default. If you ever see `No module named 'psycopg'`, run `python -m pip install "psycopg[binary]"` (keep the quotes).

---

## Step 6: Create your `secrets.toml`

This file holds the connection to the database. It's not in the repo, on purpose.

1. Get the **connection string** from Maxime, privately (see `CONTRIBUTING.md`, rule 2).
2. In the project folder, create a folder named **`.streamlit`** (with the dot).
3. Inside it, create a file named **`secrets.toml`** with this content:
   ```toml
   [connections.neon]
   url = "PASTE_THE_CONNECTION_STRING_HERE"
   ```
4. Replace the placeholder with the connection string. Keep the quotes, and keep everything on **one line**. Save.

It looks like this, with real values:
```toml
[connections.neon]
url = "postgresql://neondb_owner:xxxxx@ep-xxxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require"
```

**Check:** in VS Code's **Source Control** panel, `secrets.toml` must **not** appear in the list of changes. In the explorer it's shown greyed out, meaning Git ignores it. If it does appear, stop: check that `.gitignore` contains `.streamlit/secrets.toml`.

---

## Step 7: Test the connection

1. In the main project folder, create `test_db.py`:
   ```python
   import streamlit as st

   conn = st.connection("neon", type="sql")
   df = conn.query("SELECT * FROM categories;", ttl=0)

   st.write("Connection works! Categories in the database:")
   st.dataframe(df)
   ```
2. Run it:
   ```powershell
   streamlit run test_db.py
   ```
   - The first time, Streamlit may ask for an email in the terminal. Press **Enter** to skip.
   - A browser tab opens at `localhost:8501`.
   - The first load can take a few seconds, because Neon pauses the database after 5 minutes without use and has to wake it up.
3. You should see **"Connection works!"** and a table with **9 categories**.
4. Stop the app with **Ctrl+C** in the terminal.

`test_db.py` is only a throwaway test. Don't commit it: add `test_db.py` to `.gitignore` if it isn't there yet, or delete the file.

🎉 **If you see the 9 categories, your setup is complete.**

---

## Step 8: Understand the database

Six tables. Everything is linked to `users` through the user id.

| Table | Columns | Meaning |
|---|---|---|
| `users` | id, username, password_hash, household_type, created_at | One row per account. Only the **hash** of the password is stored. |
| `categories` | name | The 9 fixed spending categories (Groceries, Restaurants, Transport, Housing, Health, Leisure, Clothing, Communication, Other). |
| `transactions` | id, user_id, date, merchant, amount, category, source | One row per expense. `amount` > 0 means money spent (CHF). `source` is `bank` or `cash`. |
| `friendships` | user_id, friend_id, status | Row (A, B) means "A sent B a request". `status` is `pending` or `accepted`. |
| `user_groups` | id, name, created_by | A group, for example "Flatmates". (Not called `groups`, because GROUPS is an SQL keyword.) |
| `group_members` | group_id, user_id | Who is in which group. |

**Rules built into the database:**
- A transaction must belong to an existing user. Deleting a user deletes their transactions (`ON DELETE CASCADE`).
- `CHECK` rules reject invalid values: a source other than bank/cash, a status other than pending/accepted, or befriending yourself.
- Usernames are unique.

---

## Step 9: Use `db.py` in your code

**Never write SQL in pages.** Import `db` and call its functions. They return **pandas DataFrames** or simple values.

### Available functions

| Area | Function | Returns |
|---|---|---|
| Categories | `get_categories()` | list of names |
| Users | `create_user(username, password_hash, household_type=None)` | new id, or `None` if the name is taken |
| | `get_user_by_username(username)` | dict with id, username, password_hash, household_type, or `None` |
| | `search_users(search_text, exclude_user_id)` | DataFrame: id, username |
| | `get_all_user_ids()` | list of ids |
| Transactions | `get_transactions(user_id)` | DataFrame: id, date, merchant, amount, category, source |
| | `add_transaction(user_id, date, merchant, amount, category, source="cash")` | new id |
| | `add_transactions_bulk(user_id, df, source="bank")` | number of rows added (df needs: date, merchant, amount, category) |
| | `update_category(transaction_id, user_id, category)` | – (only works on the user's own transactions) |
| | `delete_transaction(transaction_id, user_id)` | – (only own transactions) |
| Friends | `send_friend_request(from_id, to_id)` | – (if the other already asked you, you become friends directly) |
| | `get_incoming_requests(user_id)` | DataFrame: id, username |
| | `accept_request(from_id, user_id)` | – |
| | `remove_friendship(user_a, user_b)` | – (decline or unfriend) |
| | `get_friends(user_id)` | DataFrame: id, username |
| Groups | `create_group(name, creator_id)` | new group id (the creator becomes a member) |
| | `add_group_member(group_id, user_id)` / `leave_group(group_id, user_id)` | – |
| | `get_user_groups(user_id)` | DataFrame: id, name, members |
| | `get_group_members(group_id)` | DataFrame: id, username |
| Comparisons | `get_monthly_totals(user_ids)` | DataFrame: user_id, month, category, total |

### Example: a small page using `db.py`

```python
import datetime as dt
import streamlit as st
import db

user_id = st.session_state["user_id"]          # set by the login page

st.title("My spending")

# Show my transactions
df = db.get_transactions(user_id)
st.dataframe(df)

# Add a cash expense
with st.form("cash"):
    merchant = st.text_input("Where?")
    amount = st.number_input("Amount (CHF)", min_value=0.0, step=0.05)
    category = st.selectbox("Category", db.get_categories())
    if st.form_submit_button("Add"):
        db.add_transaction(user_id, dt.date.today(), merchant, amount, category)
        st.success("Added!")
        st.rerun()
```

### Important rules
- **Privacy:** other users' data is only shown through `get_monthly_totals` (sums per month and category), never as single transactions.
- **Need a new query?** Add a new function to `db.py` (agree with its owner first), using parameters (`:name`) and `ttl=0` for changing data. See `CONTRIBUTING.md`, rule 7.

---

## Step 10: What's left to build

| Phase | Tasks |
|---|---|
| ✅ Setup | Neon database, schema, secrets, `db.py` |
| Fake data | `generate_data.py`: 50–100 fictional users with personas (student, family, commuter …), transactions, friendships, 2–3 groups. Fixed random seed. **Run only once.** |
| Login | `auth.py` (hash and check passwords with `bcrypt`) + `views/login.py` (log in / sign up); after login, set `st.session_state["user_id"]` |
| Navigation | `app.py` with `st.navigation`: only the login page until someone is logged in |
| Personal view | Upload a bank CSV, categorise (`categorize.py`: keyword rules, no external APIs), add cash entries, charts by category and over time |
| Social | Find users, friend requests, groups |
| Comparison | Mean **and** median spender (all users / friends / a group), per month, percentiles, you-vs-average charts |
| Deploy | Streamlit Community Cloud: connect the GitHub repo, paste `secrets.toml` into the app's **Secrets** settings |

The planned structure for `app.py`:
```python
import streamlit as st

if "user_id" not in st.session_state:
    pg = st.navigation([st.Page("views/login.py", title="Log in")])
else:
    pg = st.navigation([
        st.Page("views/my_spending.py", title="My spending"),
        st.Page("views/add_transactions.py", title="Add transactions"),
        st.Page("views/friends_groups.py", title="Friends & groups"),
        st.Page("views/compare.py", title="Compare"),
    ])
pg.run()
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `running scripts is disabled on this system` when activating | Windows execution policy | Step 4.1 |
| `No matching distribution found for streamlit>=1.28` | The venv uses an old Python (for example 3.7) | Check `python --version`; rebuild the venv with 3.14 (step 4) |
| `py list` → `can't open file 'list'` | The old Python launcher is used instead of the new install manager | Use `py -0p`, or the full path to 3.14 (step 4.2) |
| `No module named 'psycopg'` | The psycopg 3 driver is missing | `python -m pip install "psycopg[binary]"` |
| `No secrets found` / KeyError `neon` | `secrets.toml` is in the wrong place or misspelled | It must be exactly `.streamlit\secrets.toml` in the project folder, with the section `[connections.neon]` |
| Connection error mentioning `channel_binding` | Driver doesn't accept that option | Delete `&channel_binding=require` from the end of the URL |
| First page load is slow | Neon was paused (after 5 min of inactivity) | Normal; wait a few seconds |
| `secrets.toml` appears in Source Control | `.gitignore` is missing the line | Add `.streamlit/secrets.toml` to `.gitignore` **before** committing |
