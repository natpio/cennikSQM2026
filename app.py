import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA ZASOBÓW ---
# Linki do Twojego arkusza Google Sheets
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide")

# --- FUNKCJE BEZPIECZEŃSTWA ---
def hash_password(password):
    """Generuje hash SHA-256 dla podanego hasła."""
    return hashlib.sha256(password.strip().encode()).hexdigest()

def get_cookie_manager():
    """Zarządza ciasteczkami sesji użytkownika."""
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

@st.cache_data(ttl=5) # Odświeżaj listę użytkowników co 5 sekund
def fetch_user_database():
    """Pobiera bazę użytkowników z zakładki USERS w Google Sheets."""
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        return dict(zip(df['username'], df['password']))
    except Exception as e:
        # Awaryjne dane logowania, jeśli arkusz jest niedostępny
        return {"admin": "7990494490f237f37435f3089d38c1a6007e0c8b055371190458df8d03f0b07b"} # Hasło: SQM2026!

user_db = fetch_user_database()

# Logika autoryzacji sesji
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Sprawdzenie czy użytkownik ma ważne ciasteczko logowania (30 dni)
saved_session = cookie_manager.get(cookie="sqm_v_session_v6")
if saved_session in user_db:
    st.session_state.authenticated = True
    st.session_state.current_user = saved_session

# --- PANEL LOGOWANIA ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-box {
            max-width: 400px; margin: 100px auto; padding: 40px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px; text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE")
        st.subheader("System Logistyczny v6.0")
        
        user_input = st.text_input("Użytkownik", key="login_u").strip()
        pass_input = st.text_input("Hasło", type="password", key="login_p").strip()
        
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if user_input in user_db and user_db[user_input] == hash_password(pass_input):
                st.session_state.authenticated = True
                st.session_state.current_user = user_input
                cookie_manager.set("sqm_v_session_v6", user_input, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd logowania. Sprawdź hasło w Google Sheets.")
                with st.expander("Pomoc techniczna (Debug)"):
                    st.write(f"Wpisany login: `{user_input}`")
                    st.write(f"Hash Twojego hasła: `{hash_password(pass_input)}`")
                    st.info("Ten hash musi być identyczny z tym w kolumnie 'password' w arkuszu.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- GŁÓWNY INTERFEJS LOGISTYCZNY ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    .price-container {
        background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px; padding: 40px; margin-top: 20px; border-left: 10px solid #ed8936;
    }
    .price-label { font-size: 1rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
    .price-value { font-size: 6rem; font-weight: 900; color: #ffffff; line-height: 1; margin: 20px 0; }
    .comp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 30px; }
    .comp-card {
        background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 15px; border-radius: 12px; display: flex; justify-content: space-between;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    """Pobiera dane o stawkach i opłatach stałych."""
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.write(f"Zalogowany: **{st.session_state.current_user}**")
    miasto = st.selectbox("DESTINATION", sorted(df_baza['Miasto'].unique()))
    waga = st.number_input("WAGA SPRZĘTU (kg)", value=500, step=100)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v_session_v6")
        st.session_state.authenticated = False
        st.rerun()

# --- LOGIKA OBLICZENIOWA ---
w_total = waga * cfg.get('WAGA_BUFOR', 1.2)
v_type = "BUS" if w_total <= 1000 else "SOLO" if w_total <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_type)]

if not res.empty:
    e, i = res['Eksport'].mean(), res['Import'].mean()
    p_cost = res['Postoj'].mean() * dni
    park = dni * cfg.get('PARKING_DAY', 30)
    
    # Obsługa stref celnych (UK / CH)
    ata, ferry = 0, 0
    if miasto in ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]:
        ata = cfg.get('ATA_CARNET', 166)
        if any(x in miasto for x in ["Londyn", "Liverpool", "Manchester"]):
            ferry = cfg.get('FERRY_BUS', 332) if v_type == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
            
    total = e + i + p_cost + park + ata + ferry

    # Budowanie widoku
    st.title(f"Logistics Analysis: {miasto}")
    
    # Górne metryki
    c1, c2, c3 = st.columns(3)
    c1.metric("Pojazd", v_type)
    c2.metric("Waga obliczeniowa", f"{w_total:.0f} kg")
    c3.metric("Dni postoju", dni)

    # Główny panel ceny (Naprawiony, bez błędów HTML)
    items = [("Eksport", e), ("Import", i), (f"Standby ({dni}d)", p_cost), ("Parking", park)]
    if ata > 0: items.append(("Karnet ATA", ata))
    if ferry > 0: items.append(("Przeprawa", ferry))
    
    comp_html = "".join([f'<div class="comp-card"><span style="color:#94a3b8">{n}</span><span style="font-weight:bold">€ {v:,.2f}</span></div>' for n, v in items])

    st.markdown(f"""
    <div class="price-container">
        <div class="price-label">Rekomendowana stawka projektu</div>
        <div class="price-value">€ {total:,.2f} <span style="font-size:24px; color:#64748b; font-weight:300">netto</span></div>
        <div class="comp-grid">{comp_html}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.error(f"Brak stawek w bazie dla: {miasto} / {v_type}")
