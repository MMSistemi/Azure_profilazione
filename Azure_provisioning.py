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
    Legge dal foglio 'Cloud Only' esclusivamente i gruppi con:

    Section = Defaults
    Tipo = PEL

    Struttura prevista:
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
        column
        for column in required_columns
        if column not in cfg.columns
    ]

    if missing_columns:
        raise ValueError(
            "Nel foglio 'Cloud Only' mancano le colonne: "
            + ", ".join(missing_columns)
        )

    # Normalizzazione dei valori
    for column in required_columns:
        cfg[column] = (
            cfg[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Seleziona esclusivamente le righe PEL del foglio Cloud Only
    pel_df = cfg[
        (cfg["Section"].str.upper() == "DEFAULTS")
        & (cfg["Tipo"].str.upper() == "PEL")
    ]

    gruppi_pel = {}

    for _, row in pel_df.iterrows():
        key = str(row["Key/App"]).strip().lower()
        value = str(row["Label/Gruppi/Value"]).strip()

        if key and value:
            gruppi_pel[key] = value

    # Verifica delle due configurazioni obbligatorie
    required_keys = [
        "teams_base",
        "exchange_base_cloud"
    ]

    missing_keys = [
        key
        for key in required_keys
        if key not in gruppi_pel
    ]

    if missing_keys:
        raise ValueError(
            "Nel foglio 'Cloud Only' mancano le configurazioni PEL: "
            + ", ".join(missing_keys)
        )

    return gruppi_pel


# ------------------------------------------------------------
# Funzioni di utilità
# ------------------------------------------------------------
def normalize_name(value: str) -> str:
    """
    Rimuove accenti, spazi e apostrofi per la generazione
    dell'utenza.

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
    Formatta il nome mantenendo eventuali parole separate.
    """

    if not value:
        return ""

    return " ".join(
        word.capitalize()
        for word in value.strip().split()
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
    Genera il sAMAccountName.

    Per le utenze esterne:
    - parte base massimo 16 caratteri
    - suffisso .ext
    - lunghezza complessiva massima 20 caratteri
    """

    n = normalize_name(nome)
    sn = normalize_name(secondo_nome)
    c = normalize_name(cognome)
    sc = normalize_name(secondo_cognome)

    suffix = ".ext" if esterno else ""
    limit = 16 if esterno else 20

    # Tentativo 1:
    # nome + secondo nome + cognome + secondo cognome
    candidate_1 = f"{n}{sn}.{c}{sc}"

    if len(candidate_1) <= limit:
        return candidate_1 + suffix

    # Tentativo 2:
    # iniziale nome + iniziale secondo nome + cognomi
    candidate_2 = f"{n[:1]}{sn[:1]}.{c}{sc}"

    if len(candidate_2) <= limit:
        return candidate_2 + suffix

    # Tentativo 3:
    # iniziali nomi + primo cognome, troncato
    candidate_3 = f"{n[:1]}{sn[:1]}.{c}"

    return candidate_3[:limit] + suffix


def build_full_name(
    cognome: str,
    secondo_cognome: str,
    nome: str,
    secondo_nome: str,
    esterno: bool = False
) -> str:
    """
    Restituisce il nome nel formato:

    Cognome SecondoCognome Nome SecondoNome
    """

    parts = [
        cognome,
        secondo_cognome,
        nome,
        secondo_nome
    ]

    full_name = " ".join(
        part
        for part in parts
        if part
    )

    if esterno and full_name:
        return f"{full_name} (esterno)"

    return full_name


def normalizza_shared_mailbox(value: str) -> str:
    """
    Se viene inserito solo l'alias aggiunge @consip.it.
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
    Evita che il carattere pipe rompa la tabella Markdown.
    """

    return str(value).replace("|", "\\|")


def genera_tabella_markdown(rows):
    """
    Genera una tabella Markdown Campo/Valore.
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

    # Unici due valori letti dal config.xlsx
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
        sam_account_name = genera_samaccountname(
            nome=nome,
            cognome=cognome,
            secondo_nome=secondo_nome,
            secondo_cognome=secondo_cognome,
            esterno=True
        )

        telefono_formattato = (
            f"+39 {telefono_aziendale}"
            if telefono_aziendale
            else ""
        )

        display_name = build_full_name(
            cognome=cognome,
            secondo_cognome=secondo_cognome,
            nome=nome,
            secondo_nome=secondo_nome,
            esterno=True
        )

        name_formattato = build_full_name(
            cognome=cognome,
            secondo_cognome=secondo_cognome,
            nome=nome,
            secondo_nome=secondo_nome,
            esterno=False
        )

        given_name = " ".join(
            filter(
                None,
                [nome, secondo_nome]
            )
        )

        surname = " ".join(
            filter(
                None,
                [cognome, secondo_cognome]
            )
        )

        email_consip = (
            f"{sam_account_name}@consip.it"
        )

        data_fine_formattata = formatta_data(
            data_fine
        )

        # ----------------------------------------------------
        # Tabella richiesta
        # ----------------------------------------------------
        table = [
            ["Tipo Utenza", "Azure"],
            ["Utenza", sam_account_name],
            ["Alias", sam_account_name],
            ["Name", name_formattato],
            ["DisplayName", display_name],
            ["cn", display_name],
            ["GivenName", given_name],
            ["Surname", surname],
            ["Email aziendale", email_aziendale],
            ["Manager", manager],
            ["Cell", telefono_formattato],
            ["Data Fine (mm/gg/aaaa)", data_fine_formattata],
            ["Codice Fiscale", cf]
        ]

        if casella_personale:
            table.append(
                ["e-mail Consip", email_consip]
            )

        st.divider()
        st.subheader("Anteprima richiesta Azure")

        st.markdown(
            "Ciao, si richiede la definizione di un’utenza "
            "Azure come sotto indicato."
        )

        st.markdown(
            genera_tabella_markdown(table)
        )

        st.markdown(
            "**Nota:** il campo “Data Fine” deve essere "
            "inserito in Azure come “EmployeeHireDate”."
        )

        # ----------------------------------------------------
        # Selezione gruppo PEL
        # ----------------------------------------------------
        st.markdown("### Aggiungere gruppo")

        if casella_personale:
            gruppo_da_aggiungere = gruppo_exchange_cloud
        else:
            gruppo_da_aggiungere = gruppo_teams_base

        st.markdown(
            f"- **{gruppo_da_aggiungere}**"
        )

        # ----------------------------------------------------
        # Profilazione Shared Mailbox
        # ----------------------------------------------------
        if casella_personale and sm_list:
            st.markdown(
                "### Profilare sulle Shared Mailbox"
            )

            for sm in sm_list:
                st.markdown(f"- {sm}")

        # ----------------------------------------------------
        # MFA
        # ----------------------------------------------------
        st.markdown(
            """
### MFA

Aggiungere all’utenza la MFA.  
Gli utenti verranno contattati per supporto MFA da imac@consip.it.

Grazie
"""
        )

        # ----------------------------------------------------
        # Riassegnazione ticket
        # ----------------------------------------------------
        st.divider()

        st.markdown(
            f"""
### Riassegnazione ticket

Definita l’utenza bisogna riassegnare il ticket con:

- **Tipologia:** Software di produttività individuale
- **Descrizione:** Microsoft Office - Assistenza

Il testo da utilizzare è il seguente:

Si richiede cortesemente contatto utente per MFA/accesso utente/webmail:

`{name_formattato} – {telefono_formattato} – {email_aziendale}`

Nota: attenzione alla password.

Grazie, ciao.
"""
        )

        # ----------------------------------------------------
        # Collegamenti Webmail
        # ----------------------------------------------------
        if casella_personale:
            st.markdown("### Webmail")

            link_webmail_personale = (
                f"https://outlook.office.com/mail/{email_consip}"
            )

            st.markdown(
                f"- {link_webmail_personale}"
            )

            for sm in sm_list:
                link_webmail_sm = (
                    f"https://outlook.office.com/mail/{sm}"
                )

                st.markdown(
                    f"- {link_webmail_sm}"
                )

        # ----------------------------------------------------
        # Verifica tecnica
        # ----------------------------------------------------
        with st.expander("Verifica tecnica"):
            st.write(
                f"**Utenza/Alias:** {sam_account_name}"
            )

            st.write(
                f"**Numero caratteri:** "
                f"{len(sam_account_name)}"
            )

            st.write(
                f"**DisplayName/cn:** {display_name}"
            )

            st.write(
                f"**GivenName:** {given_name}"
            )

            st.write(
                f"**Surname:** {surname}"
            )

            st.write(
                f"**Gruppo selezionato:** "
                f"{gruppo_da_aggiungere}"
            )


# ------------------------------------------------------------
# Avvio applicazione
# ------------------------------------------------------------
if __name__ == "__main__":
    gestione_creazione_azure()
