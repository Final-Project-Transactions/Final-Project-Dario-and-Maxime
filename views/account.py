import streamlit as st

import db

user_id = st.session_state["user_id"]
username = st.session_state["username"]
st.title("Account")

# ---------- Part A: delete all transactions ----------
st.subheader("Delete all my transactions")
n = len(db.get_transactions(user_id))
st.write(f"You have **{n}** transactions saved. Your account, friends and groups stay.")

sure_tx = st.checkbox("Yes, delete all my transactions. This can't be undone.")
if st.button(f"Delete all {n} transactions", type="primary", disabled=not (sure_tx and n)):
    db.delete_all_transactions(user_id)
    st.success("All your transactions were deleted.")

st.divider()

# ---------- Part B: delete the whole account ----------
st.subheader("Delete my account")
st.write("This deletes your account, all your transactions, your friendships "
         "and your group memberships. It can't be undone.")

# Typing the username is the confirmation, so nobody deletes by accident
typed = st.text_input(f"Type your username **{username}** to confirm")
if st.button("Delete my account", type="primary", disabled=typed != username):
    db.delete_user(user_id)
    st.session_state.clear()  # log out
    st.rerun()                # back to the login page
