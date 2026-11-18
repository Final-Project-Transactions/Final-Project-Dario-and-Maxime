import streamlit as st

import auth
import db

st.title("Social Spending")
st.write("Compare your spending with your friends and other users.")

tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

with tab_login:
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            user = db.get_user_by_username(username)
            if user is not None and auth.check_password(password, user["password_hash"]):
                st.session_state["user_id"] = int(user["id"])
                st.session_state["username"] = user["username"]
                st.rerun()
            else:
                st.error("Wrong username or password.")

with tab_signup:
    with st.form("signup"):
        new_username = st.text_input("Choose a username")
        new_password = st.text_input("Choose a password", type="password")
        household = st.selectbox("Household type",
                                 ["student", "single", "couple", "family", "retiree"])
        if st.form_submit_button("Create account"):
            if len(new_username) < 3 or len(new_password) < 8:
                st.error("Username: at least 3 characters. Password: at least 8.")
            else:
                new_id = db.create_user(new_username, auth.hash_password(new_password), household)
                if new_id is None:
                    st.error("This username is already taken.")
                else:
                    st.success("Account created. You can log in now.")

# -> Datei welche login prüft
# -> Datenbank von Maxime
# -> Überschrift
# -> Titel darunter
# -> 2 Balken
# -> Alles was darunter ist gehört in einem Formular-> Formular ist ein Kasten, ohne dies würde Streamlit direkt versuchen sich einloggen obwohl das Passwort noch nicht eingegeben wurde. Formular ist wie ein Brief wird erst abgeschickt wenn er fertig geschrieben wurde, ohne formular würde man jedes wort einzeln abschicken
# -> dies passiert wenn man auf login klickt
# -> Wenn man auf den Butto login klickt passiert
# -> Hier schaut das System nach ob es den Nutzer gibt
# Wenn das passwort auch mit dem gespeicherten Hash übereinstimmt
# -> Nehme die Zahl des Nutzers aus der Datenbank
# Speichert den Namen für die Anzeige
# -> lässt app.py laufen
# Wenn etwas nicht übereinstimmt bitte gib dies aus
# st.session_state ist wie ein Notizzettel bei der Nutzung
# Neues Formular
# -> Dropdown mit folgenden Elemente zur Auswahl
# Beide müssen mehr als 3 Elemente haben
# Neue ID soll ststellt werden
# Wenn username es bereits gibt
