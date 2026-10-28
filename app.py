import streamlit as st
import pandas as pd
from datetime import datetime

# CONFIGURAZIONE PAGINA AD ALTO CONTRASTO
st.set_page_config(page_title="LabScadenze Pro", layout="wide", initial_sidebar_state="collapsed")

# STILI CSS PER CARATTERI GIGANTI ED ALTO CONTRASTO (DARK MODE)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, p, label, span {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #FFFFFF !important;
    }
    .stButton>button {
        font-size: 26px !important;
        font-weight: bold !important;
        padding: 15px 30px !important;
        background-color: #1E40AF !important;
        color: white !important;
        border-radius: 10px !important;
        border: 2px solid #3B82F6 !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        background-color: #2563EB !important;
        border-color: #60A5FA !important;
    }
    div[data-testid="stTextInput"]>div>div>input {
        font-size: 24px !important;
        background-color: #1E293B !important;
        color: white !important;
        border: 2px solid #475569 !important;
    }
    </style>
""", unsafe_allow_html=True)

# CONNESSIONE AL DATABASE POSTGRESQL ONLINE DI NEON
def init_db():
    conn = st.connection("postgresql", type="sql")
    # Usiamo una sessione SQL per i comandi che non restituiscono righe
    with conn.session as session:
        session.execute("""
            CREATE TABLE IF NOT EXISTS scadenze (
                id SERIAL PRIMARY KEY,
                username TEXT,
                strumento TEXT,
                data_scadenza TEXT,
                stato TEXT,
                note TEXT
            );
        """)
        session.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                username TEXT PRIMARY KEY,
                password TEXT
            );
        """)
        session.commit()
    
    # Controlliamo se inserire gli utenti di prova
    res = conn.query("SELECT COUNT(*) as conteggio FROM utenti;", ttl=0)
    if res.empty or res.iloc[0]['conteggio'] == 0:
        with conn.session as session:
            session.execute("INSERT INTO utenti (username, password) VALUES ('mario', 'cantiere2026') ON CONFLICT DO NOTHING;")
            session.execute("INSERT INTO utenti (username, password) VALUES ('tecnico', 'lab2026') ON CONFLICT DO NOTHING;")
            session.commit()

try:
    init_db()
except Exception as e:
    st.error(f"Errore inizializzazione database: {e}")

# GESTIONE SESSIONE DI LOGIN
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""

if not st.session_state['logged_in']:
    st.title("🔐 ACCESSO LABSCADENZE")
    st.write("Inserisci le tue credenziali per accedere al tuo registro privato.")
    
    username_input = st.text_input("Username utente:").strip().lower()
    password_input = st.text_input("Password:", type="password")
    
    if st.button("ACCEDI ALL'APP"):
        conn = st.connection("postgresql", type="sql")
        user_df = conn.query("SELECT password FROM utenti WHERE username = :user;", params={"user": username_input}, ttl=0)
        
        if not user_df.empty and str(user_df.iloc[0]['password']) == password_input:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username_input
            st.rerun()
        else:
            st.error("❌ Credenziali errate o utente inesistente. Riprova.")
    st.stop()

# --- DA QUI PARTE L'APP DOPO IL LOGIN ---
username = st.session_state['username']

st.title(f"🚀 LABSCADENZE - Registro di {username.upper()}")

if st.button("🚪 ESCI / LOGOUT"):
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.rerun()

# Navigazione Rapida in Alto
col1, col2 = st.columns(2)
with col1:
    if st.button("📋 HOME / REGISTRO"): st.session_state.tab = "home"
with col2:
    if st.button("➕ NUOVO STRUMENTO"): st.session_state.tab = "nuovo"

if 'tab' not in st.session_state:
    st.session_state.tab = "home"

# CONTENUTO FILTRATO PER UTENTE LOGGATO
if st.session_state.tab == "home":
    st.subheader("📌 Scadenze Attrezzature in Cloud")
    
    conn = st.connection("postgresql", type="sql")
    df = conn.query("SELECT id, strumento, data_scadenza, stato, note FROM scadenze WHERE username = :user ORDER BY data_scadenza ASC;", params={"user": username}, ttl=0)
    
    if df.empty:
        st.info("Nessuno strumento registrato. Clicca su 'NUOVO STRUMENTO' per iniziare.")
    else:
        st.dataframe(df, use_container_width=True)

elif st.session_state.tab == "nuovo":
    st.subheader("➕ Registra un Nuovo Strumento nel Cloud")
    
    strum = st.text_input("Nome Strumento / Attrezzatura:")
    data_scad = st.text_input("Data Scadenza (AAAA-MM-GG):", placeholder="Es. 2027-12-31")
    note_strum = st.text_input("Note aggiuntive:")
    
    if st.button("SALVA STRUMENTO NEL CLOUD"):
        if strum and data_scad:
            conn = st.connection("postgresql", type="sql")
            with conn.session as session:
                session.execute(
                    "INSERT INTO scadenze (username, strumento, data_scadenza, stato, note) VALUES (:username, :strumento, :data_scadenza, :stato, :note);",
                    {"username": username, "strumento": strum, "data_scadenza": data_scad, "stato": "In Regola", "note": note_strum}
                )
                session.commit()
            st.success("✅ Strumento salvato per sempre nel database cloud!")
            st.session_state.tab = "home"
            st.rerun()
        else:
            st.error("Compila i campi Nome e Data!")
