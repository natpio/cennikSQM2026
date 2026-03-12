import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- CONFIG ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE", layout="wide")

def hash_pw(v): return hashlib.sha256(v.encode()).hexdigest()

cookie_manager = stx.CookieManager()

@st.cache_data(ttl=60)
def get_users():
    try:
        df = pd.read_csv(URL_USERS)
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        # Ratunkowy admin (jeśli arkusz padnie)
        return {"admin": "7990494490f237f37435f3089d38c1a6007e0c8b055371190458df8d03f0b07b"}

user_db = get_users()

if "auth" not in st.session_state: st.session_state.auth = False

# Sprawdzanie ciasteczka (pamięć 30 dni)
s_user = cookie_manager.get(cookie="sqm_v_session")
if s_user in user_db:
    st.session_state.auth = True
    st.session_state.user = s_user

if not st.session_state.auth:
    st.markdown("<style>.stApp {background: #0f172a;}</style>", unsafe_allow_html=True)
    _, c, _ = st.columns([1,2,1])
    with c:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE LOGIN")
        u = st.text_input("Login")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ SIĘ"):
            if u in user_db and user_db[u] == hash_pw(p):
                st.session_state.auth = True
                st.session_state.user = u
                cookie_manager.set("sqm_v_session", u, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd! Wpisane hasło nie pasuje do hashu w Google Sheets.")
    st.stop()

# --- INTERFEJS LOGISTYKA ---
@st.cache_data(ttl=300)
def load_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.write(f"Zalogowany: **{st.session_state.user}**")
    m = st.selectbox("DESTINATION", sorted(df_baza['Miasto'].unique()))
    w = st.number_input("WAGA (kg)", value=500)
    dz = st.date_input("ZAŁADUNEK", datetime.now())
    dp = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (dp-dz).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v_session")
        st.session_state.auth = False
        st.rerun()

# Logika wyceny
w_t = w * cfg.get('WAGA_BUFOR', 1.2)
v_t = "BUS" if w_t <= 1000 else "SOLO" if w_t <= 5500 else "FTL"
r = df_baza[(df_baza['Miasto'] == m) & (df_baza['Typ_Pojazdu'] == v_t)]

if not r.empty:
    e, i, p_b = r['Eksport'].mean(), r['Import'].mean(), r['Postoj'].mean() * dni
    park = dni * cfg.get('PARKING_DAY', 30)
    total = e + i + p_b + park
    
    # Renderowanie bez tagów HTML na wierzchu
    st.subheader(f"Logistics Analysis: {m} ({v_t})")
    
    # Główne kafelki Streamlit (zamiast psującego się HTML)
    k1, k2, k3 = st.columns(3)
    k1.metric("Waga z buforem", f"{w_t:.0f} kg")
    k2.metric("Dni postoju", dni)
    k3.metric("Strefa", "UE" if m not in ["Londyn", "Genewa"] else "CELNA")

    st.markdown(f"""
    <div style="background:#1e293b; padding:30px; border-radius:15px; border-left: 10px solid #ed8936;">
        <h1 style="color:white; margin:0;">€ {total:,.2f} netto</h1>
        <p style="color:#94a3b8;">Sugerowana stawka transportowa</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("### Składowe ceny:")
    st.dataframe(pd.DataFrame({
        "Komponent": ["Eksport", "Import", "Postój Przewoźnika", "Parking SQM"],
        "Koszt": [f"€ {e:,.2f}", f"€ {i:,.2f}", f"€ {p_b:,.2f}", f"€ {park:,.2f}"]
    }), hide_index=True)
