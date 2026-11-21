import datetime as dt  # -> Ein Werkzeug für Datum und Zeit

import pandas as pd
import streamlit as st

import db  # Maximes Datenbank
from categorize import categorize  # Von der Datei categorize, nimm die Funktion categorize heraus

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

        # Data Cleaning von Maxime
        df = None

        if df is None:
            st.info("Data cleaning is coming soon.")
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
