import pandas as pd
import plotly.express as px
import streamlit as st

import db

user_id = st.session_state["user_id"]
st.title("My spending")

# ---------- Teil A: Daten holen und vorbereiten ----------
df = db.get_transactions(user_id)
if df.empty:
    st.info("No transactions yet. Add some on the page 'Add transactions'.")
    st.stop()

df["amount"] = df["amount"].astype(float)
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.strftime("%Y-%m")

# ---------- Teil B: Zeitraum wählen ----------
months = sorted(df["month"].unique())
start, end = st.select_slider("Period", options=months, value=(months[0], months[-1]))
view = df[(df["month"] >= start) & (df["month"] <= end)]
n_months = view["month"].nunique()

# ---------- Teil C: Kennzahlen ----------
col1, col2, col3 = st.columns(3)
col1.metric("Total", f"CHF {view['amount'].sum():,.0f}")
col2.metric("Per month", f"CHF {view['amount'].sum() / n_months:,.0f}")
col3.metric("Transactions", len(view))

# ---------- Teil D: Kreisdiagramm nach Kategorie ----------
by_cat = view.groupby("category", as_index=False)["amount"].sum()
fig_pie = px.pie(by_cat, names="category", values="amount",
                 title="Spending by category")
st.plotly_chart(fig_pie)

# ---------- Teil E: Verlauf pro Monat ----------
by_month = view.groupby(["month", "category"], as_index=False)["amount"].sum()
fig_month = px.bar(by_month, x="month", y="amount", color="category",
                   title="Spending per month", labels={"amount": "CHF", "month": ""})
st.plotly_chart(fig_month)

# ---------- Teil F: Alle Transaktionen ----------
with st.expander("All transactions"):
    table = view.drop(columns=["month"]).sort_values("date", ascending=False)
    table.insert(0, "delete", False)  # checkbox column, ticked = delete this row

    # The key changes after every delete, so old ticks don't jump to other rows
    st.session_state.setdefault("editor_version", 0)
    edited = st.data_editor(
        table, hide_index=True,
        column_order=["delete", "date", "merchant", "amount", "category", "source"],
        disabled=["date", "merchant", "amount", "category", "source"],
        key=f"tx_editor_{st.session_state['editor_version']}",
    )
    to_delete = edited.loc[edited["delete"], "id"].tolist()
    if st.button(f"Delete {len(to_delete)} selected", disabled=not to_delete):
        db.delete_transactions(to_delete, user_id)
        st.session_state["editor_version"] += 1
        st.rerun()
    st.caption("To delete all your transactions or your account, go to 'Account'.")

# Nur als Titel als Platzhalter. Der rest kommt wie später-> Dient dazu, dass wir wissen dass das Login funktioniert
# -> Hier definiert man die Anfang der Webseite
# -> plotly für diagramme
# -> Datei von Maxime
# -> dadurch weiss Webseite von wem man es anzeigen muss
# -> Hier fragt die Seite der Datenbank gib mir alle Werte vom Nutzer X
# -> Wenn leer wird der rest der Seite nicht ausgeführt
# Spalte mit Beiträge-> sicherheitshalber in normale Kommazahlen umgewandelt
# Zum echten Datum umgewandeöt
# Jahr und Monat nur noch um es nach Monat und Jahr zu gruppieren können
# -> Nach Monat sortieren
# -> Schieberegler der Webseite oben
# -> zählt wie viele Monate vorkommen
# -> 3 verschiedene Spaltem
# -> Totale Ausgaben
# -> Anzahl Transaktionen
