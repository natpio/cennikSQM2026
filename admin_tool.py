import streamlit as st
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

st.title("SQM | Password Generator")
user = st.text_input("Nazwa użytkownika")
pw = st.text_input("Hasło do zakodowania", type="password")

if st.button("GENERUJ HASH"):
    if user and pw:
        h = hash_password(pw)
        st.success(f"Dla użytkownika: {user}")
        st.code(h)
        st.info("Skopiuj powyższy kod i wklej go do kolumny 'password' w arkuszu USERS.")
