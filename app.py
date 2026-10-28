import streamlit as st
import pandas as pd
import sqlite3
import os
import datetime
from io import BytesIO
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="LabScadenze", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
        html, body, [data-testid="stWidgetLabel"], p, span, label {
            font-size: 22px !important;
            font-weight: 500 !important;
        }
        h1 { font-size: 46px !important; font-weight: bold !important; }
        h2 { font-size: 36px !important; font-weight: bold !important; }
        h3 { font-size: 28px !important; font-weight: bold !important; }
        input, textarea, select, .stSelectbox div {
            font-size: 22px !important;
            height: auto !important;
        }
        .stButton button {
            font-size: 24px !important;
            height: 60px !important;
            font-weight: bold !important;
            background-color: #1E3A8A !important;
            color: white !important;
            border-radius: 10px !important;
            border: 2px solid #3B82F6 !important;
        }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "labscadenze.db"
BACKUP_DIR = "backup"

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attrezzature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            matricola TEXT,
            marca TEXT,
            modello TEXT,
            note TEXT,
            archiviato INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scadenze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attrezzatura_id INTEGER,
            tipo_attivita TEXT NOT NULL,
            data_esecuzione TEXT NOT NULL,
            data_scadenza TEXT NOT NULL,
            tecnico TEXT,
            certificato_url TEXT,
            FOREIGN KEY(attrezzatura_id) REFERENCES attrezzature(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def calcola_stato_scadenze():
    conn = get_db_connection()
    query = 'SELECT a.id, a.codice, a.nome, s.tipo_attivita, s.data_scadenza, a.archiviato FROM attrezzature a LEFT JOIN scadenze s ON a.id = s.attrezzatura_id WHERE a.archiviato = 0'
    df = pd.read_sql_query(query, conn)
    conn.close()
    if df.empty:
        return [], [], []
    oggi = datetime.date.today()
    scadute, imminenti, in_regola = [], [], []
    for attr_id, group in df.groupby('id'):
        date_scadenza = group['data_scadenza'].dropna().tolist()
        riga_principale = group.iloc[0]
        if not date_scadenza:
            in_regola.append(riga_principale)
            continue
        piu_critica = min([datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in date_scadenza])
        diff_giorni = (piu_critica - oggi).days
        if diff_giorni < 0:
            scadute.append(riga_principale)
        elif 0 <= diff_giorni <= 30:
            imminenti.append(riga_principale)
        else:
            in_regola.append(riga_principale)
    return scadute, imminenti, in_regola

if 'sezione' not in st.session_state:
    st.session_state.sezione = "Pannello Principale"

st.write("### 🧭 MENU DI NAVIGAZIONE RAPIDA")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    if st.button("📊 HOME / STATO", use_container_width=True):
        st.session_state.sezione = "Pannello Principale"
with c2:
    if st.button("➕ NUOVO STRUMENTO", use_container_width=True):
        st.session_state.sezione = "Nuova Attrezzatura"
with c3:
    if st.button("📅 INSERISCI TARATURA", use_container_width=True):
        st.session_state.sezione = "Inserisci Scadenza / Taratura"
with c4:
    if st.button("🔍 CERCA / QR CODE", use_container_width=True):
        st.session_state.sezione = "Cerca Strumento"
with c5:
    if st.button("💾 REGISTRO CSV", use_container_width=True):
        st.session_state.sezione = "Esportazione & Backup"

st.write("---")
scadute, imminenti, in_regola = calcola_stato_scadenze()

if st.session_state.sezione == "Pannello Principale":
    st.header("📊 Stato del Laboratorio")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="❌ SUPERATE / SCADUTE", value=len(scadute))
    with col2:
        st.metric(label="⚠️ SCADENZE IMMINENTI (30gg)", value=len(imminenti))
    with col3:
        st.metric(label="✅ IN REGOLA", value=len(in_regola))
    st.write("---")
    if scadute:
        st.error("### ❌ ATTREZZATURE CON SCADENZA SUPERATA")
        for item in scadute:
            st.markdown(f"**[{item['codice']}] {item['nome']}**")
    if imminenti:
        st.warning("### ⚠️ ATTREZZATURE IN SCADENZA NEI PROSSIMI 30 GIORNI")
        for item in imminenti:
            st.markdown(f"**[{item['codice']}] {item['nome']}**")
    if not scadute and not imminenti:
        st.success("Tutte le attrezzature registrate risultano al momento in regola.")

elif st.session_state.sezione == "Nuova Attrezzatura":
    st.header("➕ Censimento Nuova Attrezzatura")
    codice = st.text_input("1. Codice Interno dello Strumento (es. PR-01) *")
    nome = st.text_input("2. Nome Completo dello Strumento (es. Pressa Calcestruzzi) *")
    matricola = st.text_input("3. Numero di Matricola di Fabbrica")
    marca = st.text_input("4. Produttore / Marca")
    modello = st.text_input("5. Modello")
    note = st.text_area("6. Note operative o collocazione nel laboratorio")
    
    if st.button("SALVA QUESTO STRUMETO NEL DATABASE", use_container_width=True):
        if not codice or not nome:
            st.error("I campi Codice e Nome sono obbligatori per il salvataggio.")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO attrezzature (codice, nome, matricola, marca, modello, note) VALUES (?, ?, ?, ?, ?, ?)", (codice, nome, matricola, marca, modello, note))
            conn.commit()
            conn.close()
            st.success("Strumento salvato con successo!")

elif st.session_state.sezione == "Inserisci Scadenza / Taratura":
    st.header("📅 Registrazione Scadenza o Taratura")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, codice, nome FROM attrezzature WHERE archiviato = 0")
    attrezzature = cursor.fetchall()
    conn.close()
    if not attrezzature:
        st.info("Non ci sono ancora strumenti registrati. Clicca prima su 'NUOVO STRUMENTO' in alto.")
    else:
        opzioni_strumenti = {f"[{a['codice']}] {a['nome']}": a['id'] for a in attrezzature}
        scelta_strumento = st.selectbox("Seleziona lo strumento:", list(opzioni_strumenti.keys()))
        tipo_att = st.selectbox("Tipo di Attività svolta:", ["Taratura Esterna", "Verifica Intermedia Interna", "Manutenzione Programmata"])
        data_es = st.date_input("Data Esecuzione Intervento:", datetime.date.today())
        data_sc = st.date_input("Data Nuova Scadenza Tassativa:", datetime.date.today() + datetime.timedelta(days=365))
        tecnico = st.text_input("Tecnico o Ente Esecutore dell'intervento")
        if st.button("REGISTRA LA SCADENZA", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO scadenze (attrezzatura_id, tipo_attivita, data_esecuzione, data_scadenza, tecnico) VALUES (?, ?, ?, ?, ?)", (opzioni_strumenti[scelta_strumento], tipo_att, data_es.strftime("%Y-%m-%d"), data_sc.strftime("%Y-%m-%d"), tecnico))
            conn.commit()
            conn.close()
            st.success("Scadenza memorizzata correttamente!")

elif st.session_state.sezione == "Cerca Strumento":
    st.header("🔍 Cerca Attrezzatura")
    search_query = st.text_input("Inserisci il Codice o il Nome da cercare:")
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT * FROM attrezzature WHERE (codice LIKE ? OR nome LIKE ?) AND archiviato = 0", (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("SELECT * FROM attrezzature WHERE archiviato = 0")
    attrezzature = cursor.fetchall()
    if attrezzature:
        for attr in attrezzature:
            with st.expander(f"🛠️ [{attr['codice']}] {attr['nome']}"):
                st.write(f"**Matricola:** {attr['matricola']} | **Marca:** {attr['marca']} | **Modello:** {attr['modello']}")
                st.write(f"**Note:** {attr['note']}")
    else:
        st.warning("Nessuno strumento trovato.")
    conn.close()

elif st.session_state.sezione == "Esportazione & Backup":
    st.header("💾 Scarica i Registri")
    conn = get_db_connection()
    df_export = pd.read_sql_query("SELECT a.codice, a.nome, a.matricola, s.tipo_attivita, s.data_scadenza FROM attrezzature a LEFT JOIN scadenze s ON a.id = s.attrezzatura_id WHERE a.archiviato = 0", conn)
    conn.close()
    csv_buffer = df_export.to_csv(index=False).encode('utf-8')
    st.download_button("📥 SCARICA EXCEL (CSV)", data=csv_buffer, file_name="registro_lab.csv", mime="text/csv", use_container_width=True)
