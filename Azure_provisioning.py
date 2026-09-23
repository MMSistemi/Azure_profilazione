import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import unicodedata


# ------------------------------------------------------------
# Configurazione pagina
# ------------------------------------------------------------
st.set_page_config(
    page_title="Creazione Utenze Azure",
    page_icon="☁️",
    layout="wide"
)


# ------------------------------------------------------------
# Caricamento configurazione da Excel
# ------------------------------------------------------------
def load_config_from_bytes(data: bytes):
    """
    Legge dal foglio 'Cloud Only' esclusivamente i gruppi
    configurati con Section = Defaults e Tipo = PEL.

    Struttura richiesta:
    Section | Key/App | Label/Gruppi/Value | Tipo
    """

    try:
        cfg = pd.read_excel(
            io.BytesIO(data),
            sheet_name="Cloud Only",
            engine="openpyxl"
        )

    except ValueError as exc:
        raise ValueError(
            "Nel file config.xlsx non è presente il foglio 'Cloud Only'."
        ) from exc

    required_columns = [
        "Section",
        "Key/App",
        "Label/Gruppi/Value",
        "Tipo"
    ]

    missing_columns = [
        colonna
        for colonna in required_columns
        if colonna not in cfg.columns
    ]

    if missing_columns:
        raise ValueError(
            "Nel foglio 'Cloud Only' mancano le colonne: "
            + ", ".join(missing_columns)
        )

    # Normalizzazione
    for colonna in required_columns:
        cfg[colonna] = (
            cfg[colonna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Recupera esclusivamente le righe:
    # Section = Defaults
    # Tipo = PEL
    pel_df = cfg[
        (cfg["Section"].str.upper() == "DEFAULTS")
        & (cfg["Tipo"].str.upper() == "PEL")
    ]

    gruppi_pel = {}

    for _, row in pel_df.iterrows():
        chiave = str(row["Key/App"]).strip().lower()
        gruppo = str(row["Label/Gruppi/Value"]).strip()

        if chiave and gruppo:
            gruppi_pel[chiave] = gruppo

    # Verifica delle due configurazioni obbligatorie
    chiavi_obbligatorie = [
        "teams_base",
        "exchange_base_cloud"
    ]

    chiavi_mancanti = [
        chiave
        for chiave in chiavi_obbligatorie
        if chiave not in gruppi_pel
    ]

    if chiavi_mancanti:
        raise ValueError(
            "Nel foglio 'Cloud Only' mancano queste configurazioni PEL: "
            + ", ".join(chiavi_mancanti)
        )

    return gruppi_pel


# ------------------------------------------------------------
# Funzioni di utilità
# ------------------------------------------------------------
def normalize_name(value: str) -> str:
    """
    Rimuove accenti, spazi e apostrofi.

    Esempi:
    D'Angelo -> dangelo
    José -> jose
    """

    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ASCII", "ignore").decode()

    return (
        ascii_value
        .replace(" ", "")
        .replace("'", "")
        .replace("’", "")
        .lower()
    )


def format_name(value: str) -> str:
    """
    Mantiene correttamente nomi composti e apostrofi.
    """

    if not value:
        return ""

    return " ".join(
        parola.capitalize()
        for parola in value.strip().split()
    )


def formatta_data(data: str) -> str:
    """
    Riceve una data nel formato gg/mm/aaaa oppure gg-mm-aaaa,
    aggiunge un giorno e restituisce mm/gg/aaaa 00:00.
    """

    if not data:
        return ""

    for separatore in ["-", "/"\]:
        try:
            giorno, mese, anno = map(
                int,
                data.split(separatore)
            )

            data_convertita = (
                datetime(anno, mese, giorno)
                + timedelta(days=1)
            )

            return data_convertita.strftime(
                "%m/%d/%Y 00:00"
            )

        except (ValueError, TypeError):
            continue

    return data


def genera_samaccountname(
    nome: str,
    cognome: str,
    secondo_nome: str = "",
    secondo_cognome: str = "",
    esterno: bool = False
) -> str:
    """
    Per le utenze esterne:
    - parte iniziale massimo 16 caratteri
    - suffisso .ext
    - massimo complessivo 20 caratteri
    """

    n = normalize_name(nome)
    sn = normalize_name(secondo_nome)
    c = normalize_name(cognome)
    sc = normalize_name(secondo_cognome)

    suffix = ".ext" if esterno else ""
    limit = 16 if esterno else 20

    # Nome completo
    candidato_1 = f"{n}{sn}.{c}{sc}"

    if len(candidato_1) <= limit:
        return candidato_1 + suffix

    # Iniziale nome + iniziale secondo nome + cognomi
    candidato_2 = f"{n[:1]}{sn[:1]}.{c}{sc}"

    if len(candidato_2) <= limit:
        return candidato_2 + suffix

    # Iniziale nome + iniziale secondo nome + primo cognome
    candidato_3 = f"{n[:1]}{sn[:1]}.{c}"

    return candidato_3[:limit] + suffix


def build_full_name(
    cognome: str,
    secondo_cognome: str,
    nome: str,
    secondo_nome: str,
    esterno: bool = False
) -> str:
    """
    Formato:
    Cognome Secondo Cognome Nome Secondo Nome
    """

    parts = [
        cognome,
        secondo_cognome,
        nome,
        secondo_nome
    ]

    full_name = " ".join(
        parte
        for parte in parts
        if parte
    )

    if esterno and full_name:
        return f"{full_name} (esterno)"

    return full_name


def normalizza_shared_mailbox(value: str) -> str:
    """
    Se è presente solo l'alias, aggiunge @consip.it.
    Se è già presente un indirizzo completo, non lo modifica.
    """

    value = value.strip()

    if not value:
        return ""

    if "@" in value:
        return value

    return f"{value}@consip.it"


def escape_markdown_table_value(value: str) -> str:
    """
    Evita problemi nella tabella Markdown.
    """

    return str(value).replace("|", "\\|")


def genera_tabella_markdown(rows):
    """
    Genera la tabella Markdown Campo/Valore.
    """

    markdown = "| Campo | Valore |\n"
    markdown += "|---|---|\n"

    for campo, valore in rows:
        markdown += (
            f"| {escape_markdown_table_value(campo)} "
            f"| {escape_markdown_table_value(valore)} |\n"
        )

    return markdown


# ------------------------------------------------------------
# Sezione Streamlit
# ------------------------------------------------------------
def gestione_creazione_azure():
    st.title("Creazione Utenze Azure")

    # --------------------------------------------------------
    # Caricamento config.xlsx
    # --------------------------------------------------------
    config_file = st.file_uploader(
        "Carica il file di configurazione config.xlsx",
        type=["xlsx"],
        key="Config_Cloud_Only"
    )

    if not config_file:
        st.warning(
            "Caricare il file config.xlsx per continuare."
        )
        st.stop()

    try:
        gruppi_pel = load_config_from_bytes(
            config_file.getvalue()
        )

    except Exception as exc:
        st.error(
            f"Errore nella configurazione: {exc}"
        )
        st.stop()

    # I soli due valori letti dal config.xlsx
    gruppo_teams_base = gruppi_pel["teams_base"]
    gruppo_exchange_cloud = gruppi_pel["exchange_base_cloud"]

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------
    st.subheader("Dati della risorsa")

    colonna_1, colonna_2 = st.columns(2)

    with colonna_1:
        nome = format_name(
            st.text_input(
                "Nome",
                key="Nome_Azure"
            )
        )

        secondo_nome = format_name(
            st.text_input(
                "Secondo Nome",
                key="SecondoNome_Azure"
            )
        )

        telefono_aziendale = (
            st.text_input(
                "Telefono Aziendale senza prefisso",
                key="TelAziendale"
            )
            .replace(" ", "")
            .strip()
        )

        manager = st.text_input(
            "Manager",
            key="Manager_Azure"
        ).strip()

        cf = (
            st.text_input(
                "Codice Fiscale",
                key="Codice_fiscale"
            )
            .strip()
            .upper()
        )

    with colonna_2:
        cognome = format_name(
            st.text_input(
                "Cognome",
                key="Cognome_Azure"
            )
        )

        secondo_cognome = format_name(
            st.text_input(
                "Secondo Cognome",
                key="SecondoCognome_Azure"
            )
        )

        email_aziendale = st.text_input(
            "Email Aziendale",
            key="EmailAziendale"
        ).strip()

        data_fine = st.text_input(
            "Data Fine (gg/mm/aaaa)",
            key="Data_fine_Azure"
        ).strip()

    # --------------------------------------------------------
    # Casella Personale Consip
    # --------------------------------------------------------
    st.subheader("Posta elettronica e profilazione")

    casella_personale = st.checkbox(
        "Casella Personale Consip",
        key="Casella_Personale_Azure"
    )

    sm_list = []

    if casella_personale:
        sm_text = st.text_area(
            "Sulle quali SM va profilato, una per riga",
            key="SM_Azure"
        )

        sm_list = [
            normalizza_shared_mailbox(sm)
            for sm in sm_text.splitlines()
            if sm.strip()
        ]

        st.info(
            f"Gruppo applicato: {gruppo_exchange_cloud}"
        )

    else:
        st.info(
            f"Gruppo applicato: {gruppo_teams_base}"
        )

    # --------------------------------------------------------
    # Generazione richiesta
    # --------------------------------------------------------
    if st.button(
        "Genera Richiesta Azure",
        type="primary",
        use_container_width=True
    ):
        campi_mancanti = []

        if not nome:
            campi_mancanti.append("Nome")

        if not cognome:
            campi_mancanti.append("Cognome")

        if campi_mancanti:
            st.error(
                "Compilare i seguenti campi obbligatori: "
                + ", ".join(campi_mancanti)
            )
            st.stop()

        # ----------------------------------------------------
        # Generazione campi
        # ----------------------------------------------------
