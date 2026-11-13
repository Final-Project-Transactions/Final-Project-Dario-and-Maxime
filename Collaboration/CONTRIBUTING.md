# How we work together

Rules for Dario and Maxime working on this project, and how to follow each one in practice.

---

## 1. Never commit secrets

`.streamlit/secrets.toml` contains the database password. Anyone who has it can read and delete the whole database. Once a password is on GitHub, treat it as public, even if you delete the file afterwards.

**How to follow this rule**
- `.gitignore` already contains `.streamlit/secrets.toml`, so Git ignores the file. **Never remove that line.**
- **Before every commit**, look at the list of changed files in VS Code's **Source Control** panel. `secrets.toml` and the `.venv` folder must **never** appear there. If one of them does, stop and fix `.gitignore` first.
- Never paste the connection string into code files, comments, screenshots, chats with AI tools, or the README.
- Before sending a screenshot of an error message, check that no password is visible. Black it out if it is.

**If the password leaks anyway**
1. In the Neon console, reset the database password.
2. Copy the new connection string from **Connect**.
3. Both of us update our own `secrets.toml`, and the secrets in Streamlit Cloud once the app is deployed.

---

## 2. Share the connection string only privately

- **Best:** in person, or through a password manager.
- **Acceptable:** a direct private message that the receiver deletes after pasting it into `secrets.toml`.
- **Never:** a group chat, the repo, or an email to several people.

---

## 3. Commit small, often, and only working code

One commit is **one logical step**: "add login page", not "everything from today". Then, if something breaks, we can see where and go back.

**How to follow this rule**
- Run the app before committing (`streamlit run app.py`). If it crashes, fix it first.
- Write messages that say **what changed**, in the present tense:
  - ✅ `Add friend request functions to db.py`
  - ✅ `Fix wrong monthly totals on compare page`
  - ❌ `update`, `stuff`, `asdf`
- In VS Code: **Source Control** → click **+** next to each file you want to commit (staging) → type the message → **Commit**.

---

## 4. Pull before you start, push when you're done

This avoids most conflicts.

**How to follow this rule**

At the **start** of every work session:
```powershell
git pull
```
(or in VS Code: **Source Control** → **⋯** → **Pull**)

At the **end** of every work session, after committing:
```powershell
git push
```
(or in VS Code: **Sync Changes**)

If you get new commits from the other person and `requirements.txt` changed, run:
```powershell
python -m pip install -r requirements.txt
```

---

## 5. Split the work by file

If we both change the same file at the same time, Git produces a **merge conflict**. The project is split into files so we can each own different ones.

**How to follow this rule:** agree on who owns which file. Fill this in together:

| File | Owner | Status |
|---|---|---|
| `schema.sql` | Maxime | done |
| `db.py` | Maxime | done |
| `generate_data.py` | | |
| `auth.py` + `views/login.py` | | |
| `app.py` | | |
| `analytics.py` | | |
| `categorize.py` | | |
| `views/my_spending.py` | | |
| `views/add_transactions.py` | | |
| `views/friends_groups.py` | | |
| `views/compare.py` | | |

If you need to change a file the other person owns, tell them first, for example: "I'm adding a function to db.py, don't touch it for the next hour."

---

## 6. If a merge conflict happens anyway

VS Code marks the conflicting part of the file like this:
```
<<<<<<< HEAD
your version
=======
the other person's version
>>>>>>> ...
```
1. VS Code shows buttons above it: **Accept Current Change** / **Accept Incoming Change** / **Accept Both Changes**. Choose the right one, or edit the text by hand.
2. Make sure no `<<<<<<<`, `=======` or `>>>>>>>` lines are left.
3. Run the app to check that it still works.
4. Stage the file, commit (for example `Resolve merge conflict in db.py`), push.

If you're unsure, don't guess: call the other person.

---

## 7. SQL only in `db.py`

Pages and `analytics.py` never contain SQL. They call functions from `db.py`.

**How to follow this rule**
- Need new data? Add a function to `db.py` (talk to its owner first, see rule 5).
- Always pass values as **parameters** (`:name`), never with f-strings. That protects against SQL injection:
  ```python
  # ✅ correct
  conn.query("SELECT * FROM users WHERE username = :u", params={"u": name}, ttl=0)
  # ❌ never
  conn.query(f"SELECT * FROM users WHERE username = '{name}'")
  ```
- Use `ttl=0` for data that changes (transactions, friends), otherwise users see outdated data.
- Other users' data is only shown as **aggregates** (`get_monthly_totals`), never as single transactions.

---

## 8. Same Python version, same packages

- We both use **Python 3.14** in a virtual environment (`.venv`).
- If you install a new package, **add it to `requirements.txt` in the same commit** and tell the other person. Otherwise their app crashes, and so does the deployed app.

---

## 9. Be careful with the shared database

We both work on the **same** Neon database: what one of us adds, deletes or breaks, the other sees immediately.

**How to follow this rule**
- Never run `DELETE`, `DROP` or `TRUNCATE` in the Neon SQL Editor without agreeing first.
- **`generate_data.py` is run only once, by one person.** Running it twice would create duplicate fake users.
- If the database structure needs to change (a new column or table), change `schema.sql` too and tell the other person.
