import streamlit as st

import db

me = st.session_state["user_id"]
st.title("Friends & groups")

# ---------- Teil A: Offene Anfragen an mich ----------
requests = db.get_incoming_requests(me)  # -> Soll in der Datenbank alles suchen die mir eine Freundschaftsanfrage geschickt haben
if not requests.empty:
    st.subheader(f"Friend requests ({len(requests)})")
    for _, r in requests.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])  # Spaltenverhältnis die 3,1,1
        c1.write(r["username"])
        if c2.button("Accept", key=f"accept_{r['id']}"):
            db.accept_request(int(r["id"]), me)
            st.rerun()  # -> Nehme Kollegen an und fange alles wieder von vorne
        if c3.button("Decline", key=f"decline_{r['id']}"):
            db.remove_friendship(int(r["id"]), me)
            st.rerun()

# ---------- Teil B: Nutzer suchen und Anfrage senden ----------
st.subheader("Find people")
search = st.text_input("Search by username")
if search:
    results = db.search_users(search, me)  # -> Me soll nicht drin sein
    if results.empty:
        st.write("Nobody found.")
    for _, u in results.iterrows():  # -> für die suchfunktion heisst geht so lange durch bis nutzer gefunden wird
        c1, c2 = st.columns([4, 1])
        c1.write(u["username"])
        if c2.button("Add friend", key=f"add_{u['id']}"):
            db.send_friend_request(me, int(u["id"]))
            st.success(f"Request sent to {u['username']}.")  # -> accept button

# ---------- Teil C: Meine Freunde ----------
st.subheader("My friends")
friends = db.get_friends(me)
if friends.empty:
    st.write("No friends yet.")
for _, f in friends.iterrows():  # -> Dafür da jeden freund anuzuzeigen mit einem Remove button
    c1, c2 = st.columns([4, 1])
    c1.write(f["username"])
    if c2.button("Remove", key=f"remove_{f['id']}"):
        db.remove_friendship(me, int(f["id"]))
        st.rerun()

# ---------- Teil D: Gruppen ----------
st.subheader("My groups")
groups = db.get_user_groups(me)
for _, g in groups.iterrows():
    with st.expander(f"{g['name']} ({g['members']} members)"):  # -> Name der Gruppe und Anzahl Mitglieder
        members = db.get_group_members(int(g["id"]))
        st.write(", ".join(members["username"]))

        # Freunde, die noch nicht in der Gruppe sind
        not_in_group = friends[~friends["id"].isin(members["id"])]
        if not not_in_group.empty:
            new_member = st.selectbox("Add a friend", not_in_group["username"],
                                      key=f"pick_{g['id']}")
            if st.button("Add to group", key=f"addgrp_{g['id']}"):
                new_id = not_in_group.loc[not_in_group["username"] == new_member, "id"].iloc[0]
                db.add_group_member(int(g["id"]), int(new_id))
                st.rerun()
        if st.button("Leave group", key=f"leave_{g['id']}"):
            db.leave_group(int(g["id"]), me)
            st.rerun()

with st.form("new_group", clear_on_submit=True):
    name = st.text_input("New group name")
    if st.form_submit_button("Create group") and name:
        db.create_group(name, me)
        st.rerun()

# Nur als Titel als Platzhalter. Der rest kommt wie später-> Dient dazu, dass wir wissen dass das Login funktioniert
# -> Hier definiert man die Anfang der Webseite
