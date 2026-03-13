import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import pydeck as pdk

# --- KONFIGURACJA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Baza SQM Komorniki
START_COORDS = [16.8122, 52.3358] 

# Współrzędne (Uzupełnij w Excelu lub tu dla lepszej mapy)
CITY_GEO = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Barcelona": [2.1734, 41.3851]
}

st.set_page_config(page_title="SQM VANTAGE v11.0", layout="wide")

# --- CSS: TOTALNY RESET WIZUALNY ---
# Używamy nowych klas (np. .v11-box), aby wymusić odświeżenie stylów
st.markdown("""
    <style>
    /* Wymuszenie tła */
    .stApp {
        background: #0a0f1a !important;
        background-image: radial-gradient(circle at 20% 20%, #1e3a8a 0%, #030508 100%) !important;
    }
    
    /* Nowy kontener wyceny - całkowicie inny od v6.0 */
    .v11-card {
        background: rgba(0, 0, 0, 0.8) !important;
        border: 2px solid #ed8936 !important;
        border-radius: 15px;
        padding: 35px !important;
        margin: 10px 0;
        box-shadow: 0 0 30px rgba(237, 137, 54, 0.2);
    }

    .v11-price {
        font-size: 85px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }

    .v11-label {
        color: #ed8936;
        text-transform: uppercase;
        letter-spacing: 3px;
        font-weight: bold;
    }

    /* Ukrycie starych elementów Streamlit */
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM LOGOWANIA (Zmiana klucza ciasteczka wymusi przelogowanie) ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=5)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()
if "auth" not in st.session_state: st.session_state.auth = False

# Nowy token sesji v11
token = cookie_manager.get(cookie="sqm_v11_token")
if token in user_db:
    st.session_state.auth = True
    st.session_state.user = token

if not st.session_state.auth:
    _, c, _ = st.columns([1,1.5,1])
    with c:
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VANTAGE v11</h1>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik").strip()
        p = st.text_input("Hasło", type="password").strip()
        if st.button("ZALOGUJ", use_container_width=True):
            if u in user_db and user_db[u] == make_hash(p):
                st.session_state.auth = True
                st.session_state.user = u
                cookie_manager.set("sqm_v11_token", u, expires_at=datetime.now()+timedelta(days=30))
                st.rerun()
            else: st.error("Błąd! Sprawdź dane w Google Sheets.")
    st.stop()

# --- DANE ---
@st.cache_data(ttl=30)
def fetch_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    mode = st.radio("STRATEGIA", ["DEDYKOWANY (Pełne auto)", "DOŁADUNEK (z wagi)"])
    dest = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    w_input = st.number_input("WAGA (kg)", value=500, step=50)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v11_token")
        st.session_state.auth = False
        st.rerun()

# --- KALKULACJA ---
w_calc = w_input * cfg.get('WAGA_BUFOR', 1.2)
# Dobór auta na podstawie wagi (nawet w doładunku musimy wiedzieć jakim autem jedziemy)
v_type = "BUS" if w_calc <= 1200 else "SOLO" if w_calc <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == dest) & (df_baza['Typ_Pojazdu'] == v_type)]

if not res.empty:
    r = res.iloc[0]
    if "DEDYKOWANY" in mode:
        exp, imp = r['Eksport'], r['Import']
    else:
        exp, imp = r['Eksport'] * w_calc, r['Import'] * w_calc

    postoj = r['Postoj'] * dni
    oplaty = (dni * cfg.get('PARKING_DAY', 30)) + (cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Zurych"] else 0)
    total = exp + imp + postoj + oplaty

    # --- WIDOK ---
    st.markdown(f"<h2 style='color:white;'>Trasa: Komorniki ➔ {dest.upper()}</h2>", unsafe_allow_html=True)
    
    col_price, col_map = st.columns([1.2, 1])
    
    with col_price:
        st.markdown(f"""
            <div class="v11-card">
                <div class="v11-label">{mode} / {v_type}</div>
                <div class="v11-price">€ {total:,.2f}</div>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <table style="width:100%; color:white;">
                    <tr><td>Eksport:</td><td style="text-align:right">€ {exp:,.2f}</td></tr>
                    <tr><td>Import:</td><td style="text-align:right">€ {imp:,.2f}</td></tr>
                    <tr><td>Postój ({dni} d):</td><td style="text-align:right">€ {postoj:,.2f}</td></tr>
                    <tr><td>Opłaty dodatkowe:</td><td style="text-align:right">€ {oplaty:,.2f}</td></tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

    with col_map:
        # MAPA - Pydeck musi się tu wyrenderować
        coords = CITY_GEO.get(dest, [13.4, 52.5])
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(START_COORDS[1] + coords[1])/2,
                longitude=(START_COORDS[0] + coords[0])/2,
                zoom=4, pitch=45
            ),
            layers=[
                pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": START_COORDS, "t": coords}]),
                          get_source_position="s", get_target_position="t",
                          get_source_color=[237, 137, 54], get_target_color=[255, 255, 255], get_width=5)
            ]
        ))
else:
    st.error(f"Brak stawek w bazie dla {dest} / {v_type}")
