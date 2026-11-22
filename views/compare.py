import pandas as pd
import plotly.express as px  # -> Für Histogramm und Diagramme
import streamlit as st

import analytics  # -> Für die Rechnungen
import db

me = st.session_state["user_id"]  # -> Die Nutzernummer (wie Notizzettel)
st.title("Compare")

# ---------- Teil A: Mit wem vergleichen? ----------
choice = st.radio("Compare me with", ["All users", "My friends", "A group"], horizontal=True)  # -> Oberer Balken wo man dann wählen kann
if choice == "All users":  # -> Wen man auf all users klickt
    ids = db.get_all_user_ids()  # -> Gib mir alle Nutzer
elif choice == "My friends":  # -> Wenn man auf my friends klickt
    friends = db.get_friends(me)
    ids = friends["id"].tolist()  # -> Erstelle mir eine Liste aus der Nutzerdatenbank die als Freunde aufgelistet sind
else:
    groups = db.get_user_groups(me)  # -> Hole alle Gruppen in denen ich bin
    if groups.empty:
        st.info("You are not in any group yet.")
        st.stop()
    group_name = st.selectbox("Group", groups["name"])  # -> Dropdown mit allen Gruppen und es anwählen
    group_id = int(groups.loc[groups["name"] == group_name, "id"].iloc[0])  # -> Übersetzt die Gruppennamen in Nummer
    ids = db.get_group_members(group_id)["id"].tolist()  # -> Gibt dann die Antwort wer alles in dieser Gruppe ist

res = analytics.compare(me, ids)
if res["n"] == 0:
    st.info("Nobody to compare with yet.")
    st.stop()

# ---------- Teil B: Kennzahlen ----------
c1, c2, c3 = st.columns(3)
c1.metric("Me (per month)", f"CHF {res['my_total']:,.0f}",
          f"{res['my_total'] - res['mean']:+,.0f} CHF vs. mean", delta_color="inverse")  # Für das Vorzeichen; -> Färbung, dass - grün wird
c2.metric("Mean spender", f"CHF {res['mean']:,.0f}")
c3.metric("Median spender", f"CHF {res['median']:,.0f}")
st.write(f"You spend more than **{res['percentile']:.0f}%** of the "
         f"{res['n']} people in this comparison.")

# ---------- Teil C: Rangliste (Freunde/Gruppe) oder Verteilung (alle) ----------
if choice == "All users":
    fig = px.histogram(res["group_totals"], nbins=30,  # Für Balken
                       labels={"value": "CHF per month"}, title="All users")
    fig.add_vline(x=res["my_total"], line_color="crimson", annotation_text="Me")  # -> Senkrechte Linie einzeichnen
    fig.add_vline(x=res["mean"], line_dash="dash", annotation_text="Mean")  # -> Linie beim Durchschnitt
    fig.add_vline(x=res["median"], line_dash="dot", annotation_text="Median",  # -> Dat macht Linie gestrichelt und dot gepunktet
                  annotation_position="bottom right")
    fig.update_layout(showlegend=False, yaxis_title="Number of users")
else:
    # - Baut eine Rangliste für Freunde oder eine Gruppe: Die Nummern werden in Namen übersetzt, der eigene Nutzer kommt als „Me“ dazu, und alle werden nach Betrag sortiert.
    # - Zeichnet daraus liegende Balken: Der eigene Nutzer ist rot markiert, die anderen grau, und eine gestrichelte Linie zeigt den Durchschnitt.
    names = db.get_friends(me) if choice == "My friends" else db.get_group_members(group_id)
    names = names.set_index("id")["username"]  # -> Nun hat man Namen statt Nummern
    ranking = pd.DataFrame({
        "name": [names[i] for i in res["group_totals"].index],
        "total": res["group_totals"].values,
    })
    ranking = pd.concat([ranking, pd.DataFrame({"name": ["Me"], "total": [res["my_total"]]})])
    ranking["who"] = ["Me" if n == "Me" else "Others" for n in ranking["name"]]
    ranking = ranking.sort_values("total")
    fig = px.bar(ranking, x="total", y="name", color="who", orientation="h",
                 color_discrete_map={"Me": "crimson", "Others": "lightgray"},
                 labels={"total": "CHF per month", "name": ""}, title=choice)
    fig.add_vline(x=res["mean"], line_dash="dash", annotation_text="Mean")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(categoryorder="array", categoryarray=ranking["name"].tolist())
st.plotly_chart(fig)

# ---------- Teil D: Pro Kategorie ----------
# - Vergleicht die Ausgaben pro Kategorie: Für jede Kategorie stehen der eigene Betrag, der Durchschnitt und der Median der anderen als drei Balken nebeneinander.
# - Bereitet die Daten dafür vor: Zuerst wird eine Tabelle mit Me, Mean und Median gebaut, dann wird sie umgeformt (melt), damit jeder Balken eine eigene Zeile hat.
# - Wird nur angezeigt, wenn eigene Ausgaben vorhanden sind: Ohne eigene Ausgaben gibt es nichts zu vergleichen.
if res["my_by_category"] is not None:
    by_cat = pd.DataFrame({
        "Me": res["my_by_category"],
        "Mean": res["mean_by_category"],
        "Median": res["median_by_category"],
    }).reset_index(names="category")
    long = by_cat.melt(id_vars="category", var_name="who", value_name="CHF")
    fig_cat = px.bar(long, x="category", y="CHF", color="who", barmode="group",
                     title="Per category (CHF per month)", labels={"category": ""})
    st.plotly_chart(fig_cat)

# Nur als Titel als Platzhalter. Der rest kommt wie später-> Dient dazu, dass wir wissen dass das Login funktioniert
# -> Hier definiert man die Anfang der Webseite
