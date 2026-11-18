import streamlit as st

st.set_page_config(page_title="Social Spending", layout="wide")

if "user_id" not in st.session_state:
    pg = st.navigation([st.Page("views/login.py", title="Log in")])
else:
    pg = st.navigation([
        st.Page("views/my_spending.py", title="My spending"),
        st.Page("views/add_transactions.py", title="Add transactions"),
        st.Page("views/friends_groups.py", title="Friends & groups"),
        st.Page("views/compare.py", title="Compare"),
    ])
    st.sidebar.write(f"Logged in as **{st.session_state['username']}**")
    if st.sidebar.button("Log out"):
        st.session_state.clear()
        st.rerun()

pg.run()


# ->Streamlit library dazu und ab jetzt st als abkürzung
# St.set page config erlaubt das layout der app zu einstellen, page titel-> setzt den titel social spending und layout wide sagt-> Nutze verfügbare Breite -> Aber für den Browsertab
# St.session ist wie eine Datenbank, wo die user ID (beschriftung des Kontos) gespeichert wird und hier ist das if wenn die ID nicht vorhanden
# -> Zeile von innen nach aussen lesen: st page -> heisst eine seite der Webseite
# Views/login.py bedeutet zeigt: wo der Code der Seite liegt im Ordner views und datei login.py, title sagt den titel der Seite
# St.navigation-> Liste. Zeigt die wie viele Elemente/Seiten bei einem bestimmten "Weg"/Zustand hat. Die login seite hat nur 1 Seite, deshalb 1 Element in der Liste
# Bei else haben wir bereits 4
# -> 4 Seiten bei diesem "Weg"-> Zustand
# -> Bei diesem Zustand sehen wir 4 verschiedene Seiten (4x St. Page, gleicher Aufbau)
# -> Für Sidebar-> Hier fragt Python als was wir eingeloggt sind und gibt dann den username ein
# Wenn auf log out nicht gecklickt wird der rest geskippt, Hingegen wenn er gedrpückt wird
# Die ID wird wie gelöscht webseite weiss nicht mehr wer du bist
# Rerun-> Am anfang zur login seite wird man geschickt
# -> Webseite zeigt hier auf das was man geclickt hat (wenn man nicht ausgeloggt ist)
