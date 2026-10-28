import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# CONFIGURAZIONE PAGINA AD ALTO CONTRASTO
st.set_page_config(page_title="LabScadenze Enterprise", layout="wide", initial_sidebar_state="collapsed")

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
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS scadenze (
                id SERIAL PRIMARY KEY,
                username TEXT,
                strumento TEXT,
                cantiere TEXT DEFAULT 'Non Specificato',
                data_scadenza TEXT,
                stato TEXT,
                note TEXT
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS utenti (
                username TEXT PRIMARY KEY,
                password TEXT,
                ruolo TEXT DEFAULT 'operaio'
            );
        """))
        session.commit()
    
    # Controlliamo se inserire gli utenti iniziali
    res = conn.query("SELECT COUNT(*) as conteggio FROM utenti;", ttl=0)
    if res.empty or res.iloc[0]['conteggio'] == 0:
        with conn.session as session:
            # Profilo per il tuo amico AD
            session.execute(text("INSERT INTO utenti (username, password, ruoli) VALUES ('admin', 'admin2026', 'admin') ON CONFLICT DO NOTHING;"))
            # Operaio dimostrativo
            session.execute(text("INSERT INTO utenti (username, password, ruolo) VALUES ('operaio1', 'cantiere2026', 'operaio') ON CONFLICT DO NOTHING;"))
            session.commit()

try:
    init_db()
except Exception as e:
    pass

# GESTIONE SESSIONE DI LOGIN
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.session_state['ruolo'] = "operaio"

if not st.session_state['logged_in']:
    st.title("🔐 COMPAL LABSCADENZE v2.0")
    st.write("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")
    
    username_input = st.text_input("Username o ID Dipendente:").strip().lower()
    password_input = st.text_input("Chiave d'Accesso (Password):", type="password")
    
    if st.button("EFFETTUA IL LOGIN"):
        conn = st.connection("postgresql", type="sql")
        user_df = conn.query("SELECT password, ruolo FROM utenti WHERE username = :user;", params={"user": username_input}, ttl=0)
        
        if not user_df.empty and str(user_df.iloc[0]['password']) == password_input:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username_input
            st.session_state['ruolo'] = str(user_df.iloc[0]['ruolo'])
            st.rerun()
        else:
            st.error("❌ Credenziali errate o utente inesistente. Riprova.")
    st.stop()

# --- BLOCCO OPERATIVO DOPO IL LOGIN ---
username = st.session_state['username']
ruolo = st.session_state['ruolo']

if ruolo == "admin":
    st.title(f"👑 REPARTO MANAGER - Controllo Technogeo")
else:
    st.title(f"👷 PORTALE OPERATIVO - Dipendente: {username.upper()}")

if st.button("🚪 DISCONNETTI SMARTPHONE (LOGOUT)"):
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.session_state['ruolo'] = "operaio"
    st.rerun()

# Navigazione Rapida Dinamica
if ruolo == "admin":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📋 REGISTRO FLOTTA"): st.session_state.tab = "home"
    with col2:
        if st.button("➕ AGGIUNGI MEZZO"): st.session_state.tab = "nuovo"
    with col3:
        if st.button("📊 REPORT GENERATOR"): st.session_state.tab = "report"
    with col4:
        if st.button("👥 ANAGRAFICA OPERAI"): st.session_state.tab = "operai"
else:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 MIEI STRUMENTI"): st.session_state.tab = "home"
    with col2:
        if st.button("➕ SEGNALA ATTREZZO"): st.session_state.tab = "nuovo"

if 'tab' not in st.session_state:
    st.session_state.tab = "home"

# SEZIONE REGISTRO (HOME)
if st.session_state.tab == "home":
    conn = st.connection("postgresql", type="sql")
    
    if ruolo == "admin":
        st.subheader("👁️ Monitoraggio Globale Cantieri Attivi")
        df = conn.query("SELECT id, username as inserito_da, strumento, cantiere, data_scadenza, stato, note FROM scadenze ORDER BY data_scadenza ASC;", ttl=0)
    else:
        st.subheader("📌 Strumenti e Scadenze in tuo carico")
        df = conn.query("SELECT id, strumento, cantiere, data_scadenza, stato, note FROM scadenze WHERE username = :user ORDER BY data_scadenza ASC;", params={"user": username}, ttl=0)
    
    if df.empty:
        st.info("Nessuna attrezzatura censita a sistema.")
    else:
        st.dataframe(df, use_container_width=True)
        
        # Strumenti di cancellazione esclusivi per l'Amministratore
        if ruolo == "admin":
            st.write("---")
            st.write("🗑️ **Elimina o rinnova una scadenza terminata:**")
            id_da_eliminare = st.text_input("Inserisci l'ID numerico dello strumento da rimuovere:")
            if st.button("CONFERMA ELIMINAZIONE"):
                if id_da_eliminare:
                    try:
                        with conn.session as session:
                            session.execute(text("DELETE FROM scadenze WHERE id = :id;"), {"id": int(id_da_eliminare)})
                            session.commit()
                        st.success(f"✅ Strumento con ID {id_da_eliminare} eliminato con successo!")
                        st.rerun()
                    except ValueError:
                        st.error("Inserisci un ID numerico valido!")

# SEZIONE INSERIMENTO (NUOVO)
elif st.session_state.tab == "nuovo":
    st.subheader("➕ Censimento Strumento e Localizzazione")
    
    strum = st.text_input("Nome Strumento / Attrezzatura (es. Teodolite, Carotatrice):")
    cant = st.text_input("Cantiere di Destinazione / Posizione attuale (es. Cantiere S. Maria Apparente):")
    data_scad = st.text_input("Data Scadenza Prossima Verifica (AAAA-MM-GG):", placeholder="Es. 2027-06-15")
    note_strum = st.text_input("Note sulle condizioni del mezzo:")
    
    if st.button("SALVA DATI NEL SISTEMA"):
        if strum and data_scad:
            conn = st.connection("postgresql", type="sql")
            with conn.session as session:
                session.execute(
                    text("INSERT INTO scadenze (username, strumento, cantiere, data_scadenza, stato, note) VALUES (:username, :strumento, :cantiere, :data_scadenza, :stato, :note);"),
                    {"username": username, "strumento": strum, "cantiere": cant if cant else "Non Specificato", "data_scadenza": data_scad, "stato": "In Regola", "note": note_strum}
                )
                session.commit()
            st.success("✅ Dati inviati ed archiviati!")
            st.session_state.tab = "home"
            st.rerun()
        else:
            st.error("I campi Nome Attrezzatura e Data Scadenza sono obbligatori!")

# SEZIONE GENERAZIONE REPORT PDF (ADMIN)
elif st.session_state.tab == "report" and ruolo == "admin":
    st.subheader("📊 Generazione Report Ufficiale per l'Amministrazione")
    st.write("Esporta l'elenco completo in un documento PDF pulito e pronto per la stampa d'ufficio.")
    
    if st.button("GENERA REPORT PDF ORA"):
        conn = st.connection("postgresql", type="sql")
        df = conn.query("SELECT id, username, strumento, cantiere, data_scadenza FROM scadenze ORDER BY data_scadenza ASC;", ttl=0)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, title="Report Scadenze Technogeo")
        styles = getSampleStyleSheet()
        elements = []
        
        elements.append(Paragraph("TECHNOGEO - REGISTRO SCADENZE ATTREZZATURE", styles['Title']))
        elements.append(Spacer(1, 20))
        
        # Preparazione tabella PDF
        data = [["ID", "Operaio", "Strumento", "Cantiere", "Scadenza"]]
        for _, row in df.iterrows():
            data.append([str(row['id']), str(row['username']), str(row['strumento']), str(row['cantiere']), str(row['data_scadenza'])])
            
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E40AF')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.grey)
        ]))


        

