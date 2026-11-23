import datetime as dt  # -> Ein Werkzeug für Datum und Zeit

import pandas as pd
import streamlit as st

import db  # Maximes Datenbank
from categorize import categorize  # Von der Datei categorize, nimm die Funktion categorize heraus
from cleaning import clean_bank_csv, guess_expenses_negative  # Maximes Data Cleaning

user_id = st.session_state["user_id"]  # Notizzettel
st.title("Add transactions")

tab_cash, tab_csv = st.tabs(["Cash expense", "Bank CSV"])  # Der obere Teil Cash oder Bankspesen in CSV

# ---------- Teil A: Eine Barausgabe erfassen ----------
with tab_cash:
    with st.form("cash", clear_on_submit=True):  # Das with sagt alles darunter gehört hinein, clear hier wenn man es abschickt
        date = st.date_input("Date", value=dt.date.today())  # -> daüfr da wenn man es eintippt nimmt es das heutige Datum
        merchant = st.text_input("Where? (e.g. Baeckerei)")  # -> Textfeld welches man eintippen kann. Das where einfach als Hinweis
        amount = st.number_input("Amount (CHF)", min_value=0.0, step=0.05)  # -> kleinster wert bei 0 und immer 5Rp schritte
        category = st.selectbox("Category", db.get_categories())  # -> Kategorien der Datenbank.
        if st.form_submit_button("Add"):
            if amount <= 0:
                st.error("Please enter an amount above 0.")
            else:
                db.add_transaction(user_id, date, merchant, amount, category, source="cash")
                st.success(f"Saved: CHF {amount:.2f} for {category}.")  # -> 2f heisst 2 Stellen nach dem Komma in diesem Fall

# ---------- Teil B: Bank-CSV hochladen ----------
with tab_csv:  # -> Alles innerhalb
    uploaded = st.file_uploader("Bank export (CSV)", type="csv")  # -> Ein Feld zum hochladen und nur CSV Files
    if uploaded is not None:
        sep = st.radio("Separator", [";", ","], horizontal=True)  # Runde Knöpfe und nur eine kann man auswählen kann und sind horizontal-> nebeneinander
        raw = pd.read_csv(uploaded, sep=sep)
        st.write("Preview of your file:")  # -> Vorschau einer Datei
        st.dataframe(raw.head(), hide_index=True)  # -> Beim Preview nur die ersten 5 Zeilen sollen gezeigt werden und der index soll nicht gezeigt werden

        # Jede Bank benennt die Spalten anders: der Nutzer ordnet sie zu
        cols = raw.columns.tolist()  # Raw colums Spaltenüberschriften soll daraus eine nomale Liste gemacht werden
        c1, c2, c3 = st.columns(3)  # Webseite soll 3 Spalten nebeneinander
        col_date = c1.selectbox("Date column", cols)
        col_merchant = c2.selectbox("Merchant column", cols)
        col_amount = c3.selectbox("Amount column", cols)  # Selectbox-> für dropdowns

        # Data Cleaning von Maxime (the logic is in cleaning.py)
        if len({col_date, col_merchant, col_amount}) < 3:
            st.warning("Please choose three different columns.")
            st.stop()

        # Most banks write expenses as negative numbers. We guess from the
        # file, and the user can correct it.
        guessed = guess_expenses_negative(raw, col_amount)
        sign = st.radio(
            "In your file, expenses are ...",
            ["negative numbers (e.g. -12.50)", "positive numbers (e.g. 12.50)"],
            index=0 if guessed else 1, horizontal=True,
        )
        df, report = clean_bank_csv(
            raw, col_date, col_merchant, col_amount,
            expenses_negative=sign.startswith("negative"),
        )

        # Tell the user which rows were left out and why
        skipped = []
        if report["unreadable"]:
            skipped.append(f"{report['unreadable']} without a readable date or amount")
        if report["income_or_refund"]:
            skipped.append(f"{report['income_or_refund']} income or refunds")
        if report["zero"]:
            skipped.append(f"{report['zero']} with amount 0")
        if report["future"]:
            skipped.append(f"{report['future']} with a date in the future")
        if skipped:
            st.caption(f"{report['rows_in_file']} rows in the file. Left out: " + ", ".join(skipped) + ".")

        if df.empty:
            st.error("No expenses found. Check the column choice and the setting above.")
            st.stop()

        st.write("Check the categories and correct them if needed:")
        edited = st.data_editor(
            df, hide_index=True,
            column_config={"category": st.column_config.SelectboxColumn(
                "category", options=db.get_categories(), required=True)},
            disabled=["date", "merchant", "amount"],
        )
        if st.button(f"Import {len(edited)} transactions"):
            n = db.add_transactions_bulk(user_id, edited, source="bank")
            st.success(f"{n} transactions saved.")

# Nur als Titel als Platzhalter. Der rest kommt wie später-> Dient dazu, dass wir wissen dass das Login funktioniert
# -> Hier definiert man die Anfang der Webseite
