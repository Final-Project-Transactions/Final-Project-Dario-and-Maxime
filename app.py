import streamlit as st

st.set_page_config(page_title="Social Spending", layout="wide")

if "user_id" not in st.session_state:
    # Not logged in: only the login page exists
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
