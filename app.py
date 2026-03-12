import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- SYSTEM BEZPIECZEŃSTWA ---
def hash_password(password):
    """Generuje hash SHA-256 zgodny z systemem debugowania."""
    return hashlib.sha256(password.strip().encode()).hexdigest()

def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

@st.cache_data(ttl=1)
def fetch_user_database():
    """Pobiera użytkowników z Google Sheets."""
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        return dict(zip(df['username'], df['password']))
    except:
        # Rezerwowy admin zgodny z Twoim hashem z debugu
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_user_database()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Sprawdzenie ciasteczka (sesja 30 dni)
saved_session = cookie_manager.get(cookie="sqm_vantage_v6_final")
if saved_session in user_db:
    st.session_state.authenticated = True
    st.session_state.current_user = saved_session

# --- EKRAN LOGOWANIA ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-box {
            max-width: 450px; margin: 80px auto; padding: 40px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px; text-align: center;
            backdrop-filter: blur(10px);
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE")
        
        u_input = st.text_input("Użytkownik", key="l_user").strip()
        p_input = st.text_input("Hasło", type="password", key="l_pass").strip()
        
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            h_input = hash_password(p_input)
            # Weryfikacja loginu i hashu
            if u_input in user_db and user_db[u_input] == h_input:
                st.session_state.authenticated = True
                st.session_state.current_user = u_input
                cookie_manager.set("sqm_vantage_v6_final", u_input, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Nieprawidłowe dane logowania.")
                with st.expander("Panel diagnostyczny (Debug)"):
                    st.write(f"Wpisany login: `{u_input}`")
                    st.write(f"Wygenerowany hash: `{h_input}`")
                    st.info("Ten hash musi znaleźć się w kolumnie password w Twoim arkuszu Google.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- GŁÓWNY INTERFEJS ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    .price-container {
        background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px; padding: 40px; margin-top: 20px; border-left: 10px solid #ed8936;
    }
    .price-label { font-size: 1rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
    .price-value { font-size: 6rem; font-weight: 900; color: #ffffff; line-height: 1; margin: 20px 0; }
    .comp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 30px; }
    .comp-card {
        background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;
    }
    .comp-name { color: #94a3b8; font-size: 0.95rem; }
    .comp-val { color: white; font-weight: 800; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_logistics_data():
    try:
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip()
        o.columns = o.columns.str.strip()
        def cl(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
        o['Wartosc'] = o['Wartosc'].apply(cl)
        return b, o
    except: return None, None

df_baza, df_oplaty = load_logistics_data()

if df_baza is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
        st.write(f"Logistyk: **{st.session_state.current_user}**")
        miasto = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
        waga = st.number_input("WAGA SPRZĘTU (kg)", value=500, step=100)
        d1 = st.date_input("ZAŁADUNEK", datetime.now())
        d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
        dni = max(0, (d2-d1).days)
        if st.button("WYLOGUJ"):
            cookie_manager.delete("sqm_vantage_v6_final")
            st.session_state.authenticated = False
            st.rerun()

    # OBLICZENIA LOGISTYCZNE
    w_calc = waga * cfg.get('WAGA_BUFOR', 1.2)
    v_type = "BUS" if w_calc <= 1000 else "SOLO" if w_calc <= 5500 else "FTL"
    row = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_type)]

    if not row.empty:
        e, i = row['Eksport'].mean(), row['Import'].mean()
        p_cost = row['Postoj'].mean() * dni
        park = dni * cfg.get('PARKING_DAY', 30)
        
        # Dodatki celne i promowe (UK/CH)
        ata, ferry = 0, 0
        if miasto in ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]:
            ata = cfg.get('ATA_CARNET', 166)
            if any(x in miasto for x in ["Londyn", "Liverpool", "Manchester"]):
                ferry = cfg.get('FERRY_BUS', 332) if v_type == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
        
        total = e + i + p_cost + park + ata + ferry

        # RENDEROWANIE WIDOKU
        st.title(f"LOGISTICS VANTAGE / {miasto.upper()}")
        
        # Metryki górne
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Waga (+20%)", f"{w_calc:.0f} kg")
        m2.metric("Pojazd", v_type)
        m3.metric("Dni postoju", dni)
        m4.metric("Odprawa Celna", "TAK" if ata > 0 else "NIE")

        # Główny panel (Naprawione wyświetlanie)
        items = [("Eksport (Średnia)", e), ("Import (Średnia)", i), 
                 (f"Postój przewoźnika ({dni} d)", p_cost), ("Parking SQM", park)]
        if ata > 0: items.append(("Karnet ATA", ata))
        if ferry > 0: items.append(("Prom / Eurotunel", ferry))
        
        cards_html = "".join([f'<div class="comp-card"><span class="comp-name">{n}</span><span class="comp-val">€ {v:,.2f}</span></div>' for n, v in items])

        st.markdown(f"""
        <div class="price-container">
            <div class="price-label">Rekomendowana stawka projektu (netto)</div>
            <div class="price-value">€ {total:,.2f}</div>
            <div style="color: #64748b; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 2px; margin-top: 30px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                Szczegółowe zestawienie kosztów:
            </div>
            <div class="comp-grid">{cards_html}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"Brak danych w cenniku dla: {miasto} / {v_type}")

st.markdown("<br><p style='text-align:center; opacity: 0.2;'>SQM Multimedia Solutions | 2026</p>", unsafe_allow_html=True)
