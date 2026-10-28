import streamlit as st
import pandas as pd
import datetime
import psycopg
from psycopg.rows import dict_row

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="LabScadenze Enterprise",
    page_icon="🔒",
    layout="wide"
)

# 2. CONNESSIONE DATABASE NEON
def get_db_connection():
    conn_string = st.secrets["connections"]["postgresql"]["url"]
    return psycopg.connect(conn_string, row_factory=dict_row)

# 3. FUNZIONE SUPPORTO ESTRAZIONE DATI
def esegui_query(sql, params=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is not None:
                    return cursor.fetchall()
                conn.commit()
                return True
    except Exception as e:
        st.error(f"❌ Errore Database: {e}")
        return None

# INIZIALIZZAZIONE SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = None
if "utente_nome" not in st.session_state:
    st.session_state["utente_nome"] = None

CATEGORIE_AZIENDALI = [
    "👥 Personale", 
    "🏗️ Macchinari", 
    "🚚 Flotta Aziendale", 
    "💻 Digitale & IT", 
    "🏢 Sedi & Logistica", 
    "📜 Gare & Societario"
]

# 4. LOGICA DI LOGIN
if not st.session_state["logged_in"]:
    st.title("🔒 LABSCADENZE ENTERPRISE v2.0")
    st.subheader("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username o ID Dipendente:").strip()
        password = st.text_input("Chiave d'Accesso (Password):", type="password").strip()
        submit_button = st.form_submit_button("EFFETTUA IL LOGIN")

    if submit_button:
        if username == "admin" and password == "admin2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "admin"
            st.session_state["utente_nome"] = "Amministratore"
            st.success("Accesso Amministratore eseguito!")
            st.rerun()
        else:
            res = esegui_query("SELECT nominativo FROM dipendenti WHERE username = %s AND password_accesso = %s;", (username, password))
            if res:
                st.session_state["logged_in"] = True
                st.session_state["ruolo"] = "operaio"
                st.session_state["utente_nome"] = res[0]["nominativo"]
                st.success(f"Accesso eseguito come {res[0]['nominativo']}!")
                st.rerun()
            else:
                if username.startswith("operaio") and password == "operaio2026":
                    st.session_state["logged_in"] = True
                    st.session_state["ruolo"] = "operaio"
                    st.session_state["utente_nome"] = username.capitalize()
                    st.rerun()
                else:
                    st.error("Credenziali non corrette o dipendente non registrato. Riprova.")

# 5. DASHBOARD INTERNA (UTENTE LOGGATO)
else:
    st.sidebar.image("https://icons8.com", width=80)
    st.sidebar.markdown(f"Utente: **{st.session_state['utente_nome']}**<br>Ruolo: **{st.session_state['ruolo'].upper()}**", unsafe_allow_html=True)
    
    if st.sidebar.button("Effettua il Logout"):
        st.session_state["logged_in"] = False
        st.session_state["ruolo"] = None
        st.session_state["utente_nome"] = None
        st.rerun()

    st.title("📊 LabScadenze Enterprise — Sistema di Controllo Globale")
    st.markdown("---")

    # Controllo presenza colonna 'categoria'
    check_col = esegui_query("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='scadenze' AND column_name='categoria';
    """)
    has_categoria_column = len(check_col) > 0 if check_col is not None else False

    # PANNELLO AMMINISTRATORE (KPI + INSERIMENTO)
    if st.session_state["ruolo"] == "admin":
        all_dates = esegui_query("SELECT data_scadenza FROM scadenze;")
        all_dates = all_dates if all_dates is not None else []
        
        oggi = datetime.date.today()
        fra_30_giorni = oggi + datetime.timedelta(days=30)
        critiche, in_arrivo, in_regola = 0, 0, 0
        
        for d in all_dates:
            dt = d['data_scadenza']
            if isinstance(dt, datetime.datetime):
                dt = dt.date()
            if dt < oggi:
                critiche += 1
            elif oggi <= dt <= fra_30_giorni:
                in_arrivo += 1
            else:
                in_regola += 1

        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        col_kpi1.metric(label="🔴 Scadute / Critiche", value=str(critiche), delta="Intervento immediato" if critiche > 0 else "Allineato", delta_color="inverse")
        col_kpi2.metric(label="🟠 In Scadenza (30 gg)", value=str(in_arrivo))
        col_kpi3.metric(label="🟢 In Regola", value=str(in_regola))
        col_kpi4.metric(label="🏢 Asset Totali Monitorati", value=str(len(all_dates)))
        st.markdown("---")

        tab_op1, tab_op2 = st.tabs(["📅 Inserimento e Gestione", "👥 Registro Anagrafica Dipendenti"])
        
        with tab_op1:
            st.subheader("➕ Inserisci un nuovo Elemento nel Monitoraggio Globale")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                nuovo_cantiere = st.text_input("Nome Cantiere / Ubicazione:")
            with col2:
                nuova_desc = st.text_input("Descrizione Attrezzatura o Adempimento:")
            with col3:
                nuova_data = st.date_input("Data di Scadenza Corrente:")
            with col4:
                nuova_cat = st.selectbox("Categoria Asset:", CATEGORIE_AZIENDALI)
            
            if st.button("Salva nel Sistema"):
                if nuovo_cantiere and nuova_desc:
                    if has_categoria_column:
                        esegui_query("INSERT INTO scadenze (cantiere, descrizione, data_scadenza, categoria) VALUES (%s, %s, %s, %s);", (nuovo_cantiere, nuova_desc, nuova_data, nuova_cat))
                    else:
                        esegui_query("INSERT INTO scadenze (cantiere, descrizione, data_scadenza) VALUES (%s, %s, %s);", (nuovo_cantiere, nuova_desc, nuova_data))
                    st.success("Scadenza registrata correttamente!")
                    st.rerun()
        
        with tab_op2:
            st.subheader("👤 Registra Nuovo Dipendente / Operaio")
            col_dep1, col_dep2, col_dep3 = st.columns(3)
            with col_dep1:
                reg_nome = st.text_input("Nome e Cognome Dipendente:")
            with col_dep2:
                reg_user = st.text_input("Username per il Login (es: m.rossi):")
            with col_dep3:
                reg_pass = st.text_input("Password di Accesso:", type="password", key="reg_pass")
            
            if st.button("Abilita e Registra Dipendente"):
                if reg_nome and reg_user and reg_pass:
                    esegui_query("INSERT INTO dipendenti (username, password_accesso, nominativo) VALUES (%s, %s, %s);", (reg_user, reg_pass, reg_nome))
                    st.success(f"Dipendente {reg_nome} registrato con successo!")
                    st.rerun()
        st.markdown("---")

    # VISUALIZZAZIONE TABELLE
    st.subheader("📋 Elenco delle Scadenze Aziendali Attive")
    sql_select = "SELECT id, cantiere, descrizione, data_scadenza, categoria FROM scadenze ORDER BY data_scadenza ASC;" if has_categoria_column else "SELECT id, cantiere, descrizione, data_scadenza FROM scadenze ORDER BY data_scadenza ASC;"
    rows = esegui_query(sql_select)

    if rows:
        raw_df = pd.DataFrame(rows)
        if not has_categoria_column:
            raw_df['categoria'] = "👥 Personale"
        
        if st.session_state["ruolo"] == "admin":
            tab_views = st.tabs(CATEGORIE_AZIENDALI)
            for i, cat_name in enumerate(CATEGORIE_AZIENDALI):
                with tab_views[i]:
                    df_filtrato = raw_df[raw_df['categoria'] == cat_name]
                    if not df_filtrato.empty:
                        df_clean = df_filtrato[["id", "cantiere", "descrizione", "data_scadenza"]].copy()
                        df_clean.columns = ["ID", "Cantiere / Luogo", "Descrizione Oggetto / Adempimento", "Data Scadenza"]
                        st.dataframe(df_clean, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Nessuna scadenza attiva per: {cat_name}")
        else:
            df_operaio = raw_df[["id", "cantiere", "descrizione", "data_scadenza"]].copy()
            df_operaio.columns = ["ID", "Cantiere / Luogo", "Descrizione", "Data Scadenza"]
            st.dataframe(df_operaio, use_container_width=True, hide_index=True)

        if st.session_state["ruolo"] == "admin":
            st.markdown("### 🛠️ Strumenti di Gestione Amministrativa")
            col_del, col_rep = st.columns(2)
            with col_del:
                st.markdown("**Eliminazione Record**")
                id_da_eliminare = st.number_input("Inserisci l'ID del record da rimuovere:", min_value=1, step=1)
                if st.button("Elimina Definitivamente", type="primary"):
                    esegui_query("DELETE FROM scadenze WHERE id = %s;", (id_da_eliminare,))
                    st.error(f"Record ID {id_da_eliminare} rimosso.")
                    st.rerun()
            with col_rep:
                st.markdown("**Report e Export Miner**")
                st.caption("Esporta lo scadenziario aziendale unificato.")
                csv_data = raw_df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Scarica Report Excel / CSV", data=csv_data, file_name=f"report_scadenze_{datetime.date.today()}.csv", mime="text/csv")
    else:
        st.info("Nessuna scadenza presente nel database.")









