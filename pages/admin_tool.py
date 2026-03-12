import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA DANYCH ---
# Linki do Twojego arkusza Google Sheets
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- SYSTEM BEZPIECZEŃSTWA (Hasła w Google Sheets) ---
def hash_password(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

@st.cache_data(ttl=5) # Odświeżaj listę użytkowników co 5 sekund
def fetch_user_database():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        return dict(zip(df['username'], df['password']))
    except:
        # Rezerwowy admin (zgodny z Twoim hashem f3e99d...)
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_user_database()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Sprawdzenie ciasteczka (sesja 30 dni)
saved_session = cookie_manager.get(cookie="sqm_vantage_v6_final")
if saved_session in user_db:
    st.session_state.authenticated = True
    st.session_state.current_user = saved_session

# --- NOWE, ZAAWANSOWANE CSS ---
# Ulepszone tło, siatka Grid dla czytelności kosztów i animacje
st.markdown("""
    <style>
    /* Główne tło: Zaawansowany gradient z głębią */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #1e3a8a 0%, #030508 100%);
        background-color: #030508;
        color: #e2e8f0;
    }

    /* Ulepszone kafelki metryk górnych */
    [data-testid="stMetricValue"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    [data-testid="stMetricValue"]:hover {
        transform: translateY(-3px);
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Główne tło "szklane" z czytelnym tłem */
    .price-container {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 30px;
        padding: 50px;
        margin-top: 30px;
        backdrop-filter: blur(20px);
        box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        position: relative;
        overflow: hidden;
    }
    .price-container::before {
        content: ""; position: absolute; top: 0; left: 0; width: 10px; height: 100%;
        background: linear-gradient(to bottom, #ed8936, #f6ad55);
    }

    /* Ulepszona czcionka głównej ceny: Większa czytelność */
    .price-label { font-size: 1.1rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 3px; }
    .price-value { font-size: 7rem; font-weight: 900; color: #ffffff; line-height: 0.9; margin: 25px 0; letter-spacing: -4px; }
    
    /* Naprawiona siatka Grid dla czytelności kosztów */
    .components-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); /* Równe kolumny */
        gap: 15px; /* Duży odstęp */
        margin-top: 40px;
    }
    .component-item {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 18px 22px;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .comp-name { font-size: 1rem; color: #94a3b8; }
    .comp-price { font-size: 1.2rem; font-weight: 800; color: #f8fafc; }

    /* Ukrycie paska Menu i Stopki Streamlit */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- EKRAN LOGOWANIA (Z zachowaniem tła) ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-box {
            max-width: 450px; margin: 100px auto; padding: 40px;
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
        st.subheader("Login / Nebraska2026")
        
        user_input = st.text_input("Użytkownik", key="l_user").strip()
        pass_input = st.text_input("Hasło", type="password", key="l_pass").strip()
        
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if user_input in user_db and user_db[user_input] == hash_password(pass_input):
                st.session_state.authenticated = True
                st.session_state.current_user = user_input
                cookie_manager.set("sqm_vantage_v6_final", user_input, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd logowania. Sprawdź hasło w Google Sheets.")
                # Debug (tylko dla admina)
                with st.expander("Panel diagnostyczny"):
                    st.write(f"Wpisany login: `{user_input}`")
                    st.write(f"Hash: `{hash_password(pass_input)}`")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ŁADOWANIE DANYCH LOGISTYCZNYCH ---
@st.cache_data(ttl=300)
def load_logistics_data():
    try:
        baza = pd.read_csv(URL_BAZA); oplaty = pd.read_csv(URL_OPLATY)
        baza.columns = baza.columns.str.strip()
        oplaty.columns = oplaty.columns.str.strip()
        def cl(x):
            s = re.sub(r'[^\d.]', '', str(x).replace(',', '.'))
            return float(s) if s else 0.0
        for col in ['Eksport', 'Import', 'Postoj']: baza[col] = baza[col].apply(cl)
        oplaty['Wartosc'] = oplaty['Wartosc'].apply(cl)
        return baza, oplaty
    except: return None, None

df_baza, df_oplaty = load_logistics_data()

if df_baza is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
        st.write(f"Zalogowany logistyk: **{st.session_state.current_user}**")
        
        miasto_input = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
        waga_input = st.number_input("WAGA SPRZĘTU (kg)", min_value=1, value=500, step=100)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1: d_zal = st.date_input("ZAŁADUNEK", datetime.now())
        with col_d2: d_roz = st.date_input("POWRÓT", datetime.now() + timedelta(days=3))
        
        dni_p = max(0, (d_roz - d_zal).days)
        
        st.markdown("---")
        if st.button("WYLOGUJ Z SYSTEMU"):
            cookie_manager.delete("sqm_vantage_v6_final")
            st.session_state.authenticated = False
            st.rerun()

    # Logika wyceny
    w_calc = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    v_type = "BUS" if w_calc <= 1000 else "SOLO" if w_calc <= 5500 else "FTL"
    row = df_baza[(df_baza['Miasto'] == miasto_input) & (df_baza['Typ_Pojazdu'] == v_type)]

    if not row.empty:
        # Średnie z bazy
        e_st = row['Eksport'].mean(); i_st = row['Import'].mean(); p_st = row['Postoj'].mean()
        cost_postoj = p_st * dni_p; cost_park = dni_p * cfg.get('PARKING_DAY', 30)
        
        # Cło i dodatki (UK/CH)
        ata_v, ferry_v = 0, 0
        kraje_celne = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if miasto_input in kraje_celne:
            ata_v = cfg.get('ATA_CARNET', 166)
            if any(uk in miasto_input for uk in ["Londyn", "Liverpool", "Manchester"]):
                ferry_v = cfg.get('FERRY_BUS', 332) if v_type == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
        
        suma = e_st + i_st + cost_postoj + cost_park + ata_v + ferry_v

        # --- PREZENTACJA RAPORTU ---
        st.title(f"Logistics Analysis: {miasto_input.upper()}")
        
        # Metryki górne (Czytelniejsze, z tłem)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Waga operacyjna", f"{w_calc:.0f} kg")
        m2.metric("Pojazd docelowy", v_type)
        m3.metric("Czas na projekcie", f"{dni_p} dni")
        m4.metric("Odprawa celna", "TAK" if miasto_input in kraje_celne else "NIE DOTYCZY")

        # Główne zestawienie (Naprawiona czytelność)
        skladowe = [("Transport: Eksport", e_st), ("Transport: Import", i_st), 
                    (f"Standby przewoźnika ({dni_p}d)", cost_postoj), ("Miejsce parkingowe SQM", cost_park)]
        if ata_v > 0: skladowe.append(("Karnet ATA", ata_v))
        if ferry_v > 0: skladowe.append(("Przeprawa promowa / Eurotunel", ferry_v))

        komponenty_html = "".join([f'<div class="component-item"><span class="comp-name">{n}</span><span class="comp-price">€ {kwota:,.2f}</span></div>' for n, kwota in skladowe])

        full_html = f"""
        <div class="price-container">
            <div class="price-label">Rekomendowana kwota projektu</div>
            <div class="price-value">€ {suma:,.2f} <span style="font-size:24px; color:#64748b; font-weight:300;">netto</span></div>
            
            <div style="color: #64748b; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 40px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                Szczegółowe zestawienie składowych:
            </div>
            
            <div class="components-grid">{komponenty_html}</div>
        </div>
        """.replace("\n", " ").strip()

        st.markdown(full_html, unsafe_allow_html=True)
    else:
        st.error(f"Brak stawek w bazie dla kierunku: {miasto_input} / {v_type}")

st.markdown("<br><p style='text-align:right; opacity: 0.2; font-size: 0.8rem;'>SQM Vantage v6.2 | Advanced Graphics Engine</p>", unsafe_allow_html=True)
