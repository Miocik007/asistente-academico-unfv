"""
Tema visual institucional del Asistente Académico Inteligente.

Diseño inspirado en una aplicación universitaria:
- naranja como color de énfasis;
- negro y gris oscuro para identidad institucional;
- fondo claro;
- tarjetas limpias;
- navegación sobria;
- componentes reutilizables.
"""

import html

import streamlit as st

import db


# ============================================================
# PALETA
# ============================================================

UNFV_ORANGE = "#F28C28"
UNFV_ORANGE_DARK = "#D97706"
UNFV_ORANGE_SOFT = "#FFF3E6"

DARK = "#202124"
TEXT = "#28313F"
TEXT_SOFT = "#667085"

BACKGROUND = "#F6F7F9"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F1F3F5"
BORDER = "#E3E6EA"

SUCCESS = "#2E7D5B"
WARNING = "#B7791F"
ERROR = "#B5473C"
INFO = "#3E5C8A"


COLORS = {

    db.STATUS_NUEVO: {
        "ink": "#667085",
        "soft": "#F2F4F7",
        "label": "Nuevo",
    },

    db.STATUS_DEBIL: {
        "ink": "#B7791F",
        "soft": "#FFF4DD",
        "label": "Requiere refuerzo",
    },

    db.STATUS_REFORZADO: {
        "ink": "#3E5C8A",
        "soft": "#EDF2FA",
        "label": "En refuerzo",
    },

    db.STATUS_DOMINADO: {
        "ink": "#2E7D5B",
        "soft": "#EAF5F0",
        "label": "Dominado",
    },
}


PRIMARY = UNFV_ORANGE
CORRECT = SUCCESS
INCORRECT = ERROR


def status_colors(status):
    return COLORS.get(status, COLORS[db.STATUS_NUEVO])


# ============================================================
# CSS GLOBAL
# ============================================================

def inject_css():

    st.markdown(
        f"""
        <style>

        /* ===================================================
           VARIABLES
        =================================================== */

        :root {{

            --unfv-orange: {UNFV_ORANGE};
            --unfv-orange-dark: {UNFV_ORANGE_DARK};
            --unfv-orange-soft: {UNFV_ORANGE_SOFT};

            --background: {BACKGROUND};
            --surface: {SURFACE};
            --surface-alt: {SURFACE_ALT};

            --dark: {DARK};
            --text: {TEXT};
            --text-soft: {TEXT_SOFT};

            --border: {BORDER};

        }}


        /* ===================================================
           GENERAL
        =================================================== */

        html,
        body,
        [class*="css"] {{
            font-family:
                Inter,
                "Segoe UI",
                Arial,
                sans-serif;
        }}


        .stApp {{
            background-color: var(--background);
        }}


        [data-testid="stAppViewContainer"] {{
            color: var(--text);
        }}


        .block-container {{

            max-width: 1280px;

            padding-top: 2rem;

            padding-bottom: 4rem;

        }}


        h1,
        h2,
        h3,
        h4 {{

            font-family:
                Inter,
                "Segoe UI",
                Arial,
                sans-serif !important;

            color: var(--dark);

            font-weight: 700 !important;

        }}


        p {{
            color: var(--text);
        }}


        /* ===================================================
           SIDEBAR
        =================================================== */

        section[data-testid="stSidebar"] {{

            background-color: #FFFFFF;

            border-right: 1px solid var(--border);

        }}


        section[data-testid="stSidebar"] .block-container {{

            padding-top: 1.4rem;

        }}


        .unfv-sidebar-brand {{

            padding:
                0.5rem
                0.35rem
                1.2rem
                0.35rem;

        }}


        .unfv-sidebar-university {{

            color: var(--unfv-orange);

            font-size: 0.70rem;

            font-weight: 800;

            letter-spacing: 0.08em;

            margin-bottom: 0.45rem;

        }}


        .unfv-sidebar-title {{

            font-size: 1.15rem;

            font-weight: 750;

            line-height: 1.2;

            color: var(--dark);

            margin-bottom: 0.3rem;

        }}


        .unfv-sidebar-subtitle {{

            color: var(--text-soft);

            font-size: 0.78rem;

            line-height: 1.4;

        }}


        .unfv-sidebar-footer {{

            margin-top: 0.35rem;

            padding-top: 0.6rem;

            border-top: 1px solid var(--border);

            font-size: 0.72rem;

            line-height: 1.5;

            color: var(--text-soft);

        }}


        /* ===================================================
           NAVEGACIÓN
        =================================================== */

        [data-testid="stNavSectionHeader"] {{

            font-size: 0.68rem;

            text-transform: uppercase;

            letter-spacing: 0.08em;

            color: var(--text-soft);

            font-weight: 700;

            margin-top: 0.7rem;

        }}


        section[data-testid="stSidebar"]
        a[data-testid*="NavLink"] {{

            border-radius: 8px;

            margin:
                0.10rem
                0;

            font-weight: 500;

        }}


        section[data-testid="stSidebar"]
        a[aria-current="page"] {{

            background-color:
                var(--unfv-orange-soft) !important;

            color:
                var(--unfv-orange-dark) !important;

            font-weight:
                650 !important;

        }}


        /* ===================================================
           HEADER
        =================================================== */

        .unfv-header {{

            background:
                var(--surface);

            border:
                1px solid
                var(--border);

            border-left:
                5px solid
                var(--unfv-orange);

            border-radius:
                12px;

            padding:
                1.5rem
                1.7rem;

            margin-bottom:
                1.6rem;

            box-shadow:
                0 3px 14px
                rgba(20, 25, 35, 0.04);

        }}


        .unfv-header-label {{

            color:
                var(--unfv-orange-dark);

            font-size:
                0.72rem;

            font-weight:
                800;

            letter-spacing:
                0.08em;

            text-transform:
                uppercase;

            margin-bottom:
                0.5rem;

        }}


        .unfv-header-title {{

            color:
                var(--dark);

            font-size:
                2rem;

            font-weight:
                750;

            line-height:
                1.15;

            margin:
                0 0
                0.45rem
                0;

        }}


        .unfv-header-subtitle {{

            color:
                var(--text-soft);

            font-size:
                0.96rem;

            line-height:
                1.55;

            max-width:
                760px;

            margin:
                0;

        }}


        /* ===================================================
           BOTONES
        =================================================== */

        .stButton > button,
        .stFormSubmitButton > button {{

            border-radius:
                8px;

            min-height:
                42px;

            font-weight:
                600;

            border:
                1px solid
                var(--border);

            transition:
                all
                0.15s
                ease-in-out;

        }}


        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{

            border-color:
                var(--unfv-orange);

            color:
                var(--unfv-orange-dark);

        }}


        [data-testid="stBaseButton-primary"] {{

            background-color:
                var(--unfv-orange) !important;

            border-color:
                var(--unfv-orange) !important;

            color:
                white !important;

        }}


        [data-testid="stBaseButton-primary"]:hover {{

            background-color:
                var(--unfv-orange-dark) !important;

            border-color:
                var(--unfv-orange-dark) !important;

            color:
                white !important;

        }}


        /* ===================================================
           INPUTS
        =================================================== */

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div {{

            border-radius:
                8px !important;

        }}


        .stTextInput input,
        .stTextArea textarea {{

            border-radius:
                8px !important;

        }}


        /* ===================================================
           FILE UPLOADER
        =================================================== */

        [data-testid="stFileUploader"] {{

            background:
                var(--surface);

            border-radius:
                10px;

        }}


        /* ===================================================
           CHAT
        =================================================== */

        [data-testid="stChatMessage"] {{

            background:
                #FFFFFF;

            border:
                1px solid
                var(--border);

            border-radius:
                12px;

            margin-bottom:
                0.8rem;

            box-shadow:
                0 2px 8px
                rgba(20, 25, 35, 0.035);

        }}


        [data-testid="stChatMessage"]
        [data-testid="stChatMessageAvatarAssistant"] {{

            background:
                var(--unfv-orange-soft);

        }}


        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageAvatarAssistant"]
        ) {{

            border-left:
                4px solid
                var(--unfv-orange);

        }}


        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageAvatarUser"]
        ) {{

            border-left:
                4px solid
                #79808B;

        }}


        /* ===================================================
           TARJETAS ESTADÍSTICAS
        =================================================== */

        .stat-row {{

            display:
                grid;

            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(155px, 1fr)
                );

            gap:
                1rem;

            margin-bottom:
                1.5rem;

        }}


        .stat-tile {{

            background:
                var(--surface);

            border:
                1px solid
                var(--border);

            border-top:
                4px solid
                var(
                    --color-tone,
                    var(--unfv-orange)
                );

            border-radius:
                10px;

            padding:
                1rem 1.1rem;

            box-shadow:
                0 3px 12px
                rgba(20, 25, 35, 0.035);

        }}


        .stat-value {{

            font-size:
                1.7rem;

            font-weight:
                750;

            color:
                var(--dark);

        }}


        .stat-label {{

            font-size:
                0.78rem;

            color:
                var(--text-soft);

            margin-top:
                0.35rem;

        }}


        /* ===================================================
           TEMAS
        =================================================== */

        .topic-grid {{

            display:
                grid;

            grid-template-columns:
                repeat(
                    auto-fill,
                    minmax(245px, 1fr)
                );

            gap:
                1rem;

            margin-top:
                0.7rem;

        }}


        .topic-card {{

            background:
                var(--surface);

            border:
                1px solid
                var(--border);

            border-left:
                4px solid
                var(
                    --color-tone,
                    var(--unfv-orange)
                );

            border-radius:
                10px;

            padding:
                1rem;

            box-shadow:
                0 2px 10px
                rgba(20, 25, 35, 0.03);

        }}


        .topic-card-top {{

            display:
                flex;

            justify-content:
                space-between;

            align-items:
                flex-start;

            gap:
                0.5rem;

            margin-bottom:
                0.35rem;

        }}


        .topic-name {{

            color:
                var(--dark);

            font-weight:
                650;

            font-size:
                0.98rem;

        }}


        .topic-meta {{

            color:
                var(--text-soft);

            font-size:
                0.78rem;

            margin-bottom:
                0.55rem;

        }}


        .mastery-track {{

            height:
                7px;

            background:
                var(--surface-alt);

            border-radius:
                10px;

            overflow:
                hidden;

        }}


        .mastery-fill {{

            height:
                100%;

            background:
                var(
                    --color-tone,
                    var(--unfv-orange)
                );

            border-radius:
                10px;

        }}


        /* ===================================================
           BADGES
        =================================================== */

        .badge {{

            display:
                inline-block;

            font-size:
                0.75rem;

            font-weight:
                600;

            padding:
                0.20rem
                0.55rem;

            border-radius:
                20px;

            white-space:
                nowrap;

        }}


        .pdf-chip {{

            display:
                inline-block;

            font-size:
                0.78rem;

            color:
                var(--text);

            background:
                var(--surface-alt);

            border:
                1px solid
                var(--border);

            border-radius:
                20px;

            padding:
                0.28rem
                0.7rem;

            margin:
                0
                0.35rem
                0.35rem
                0;

        }}


        /* ===================================================
           BARRAS
        =================================================== */

        .bar-row {{

            display:
                grid;

            grid-template-columns:
                minmax(130px, 12rem)
                1fr
                3rem;

            align-items:
                center;

            gap:
                0.75rem;

            margin-bottom:
                0.55rem;

        }}


        .bar-label {{

            font-size:
                0.84rem;

            color:
                var(--text);

            overflow:
                hidden;

            text-overflow:
                ellipsis;

            white-space:
                nowrap;

        }}


        .bar-track {{

            height:
                9px;

            background:
                var(--surface-alt);

            border-radius:
                10px;

            overflow:
                hidden;

        }}


        .bar-fill {{

            height:
                100%;

            border-radius:
                10px;

            background:
                var(
                    --color-tone,
                    var(--unfv-orange)
                );

        }}


        .bar-value {{

            font-size:
                0.78rem;

            color:
                var(--text-soft);

            text-align:
                right;

        }}


        /* ===================================================
           QUIZ
        =================================================== */

        [data-testid="stForm"] {{

            background:
                var(--surface);

            border:
                1px solid
                var(--border);

            border-left:
                4px solid
                var(--unfv-orange);

            border-radius:
                10px;

            padding:
                1.3rem
                1.4rem;

            box-shadow:
                0 2px 9px
                rgba(20, 25, 35, 0.03);

        }}


        /* ===================================================
           EXPANDERS
        =================================================== */

        [data-testid="stExpander"] {{

            background:
                var(--surface);

            border:
                1px solid
                var(--border);

            border-radius:
                9px;

        }}


        /* ===================================================
           ESTADOS VACÍOS
        =================================================== */

        .empty-state {{

            background:
                var(--surface);

            border:
                1px dashed
                #C9CED6;

            border-radius:
                12px;

            padding:
                2.6rem
                1.5rem;

            text-align:
                center;

            margin-top:
                0.7rem;

        }}


        .empty-state-title {{

            color:
                var(--dark);

            font-size:
                1.1rem;

            font-weight:
                700;

            margin-bottom:
                0.4rem;

        }}


        .empty-state-body {{

            color:
                var(--text-soft);

            font-size:
                0.9rem;

            max-width:
                520px;

            margin:
                auto;

        }}


        /* ===================================================
           ALERTAS / FEEDBACK
        =================================================== */

        .feedback-banner {{

            border-left:
                4px solid
                var(
                    --color-tone,
                    var(--unfv-orange)
                );

            background:
                var(--surface-alt);

            border-radius:
                8px;

            padding:
                0.75rem
                1rem;

            font-size:
                0.87rem;

            color:
                var(--text);

            margin-top:
                0.6rem;

        }}


        .weak-topic-line {{

            padding:
                0.5rem
                0.8rem;

            border-left:
                3px solid
                {WARNING};

            background:
                #FFF9ED;

            border-radius:
                0 7px 7px 0;

            margin-bottom:
                0.4rem;

            font-size:
                0.88rem;

        }}


        /* ===================================================
           STREAMLIT UI
        =================================================== */

        footer {{
            visibility: hidden;
        }}


        #MainMenu {{
            visibility: hidden;
        }}


        hr {{

            border-color:
                var(--border) !important;

        }}


        /* ===================================================
           CONTROLES LEGIBLES EN STREAMLIT, INDEPENDIENTE
           DE LAS PREFERENCIAS OSCURAS DEL NAVEGADOR
        =================================================== */

        html, body, .stApp, [data-testid="stAppViewContainer"] {{
            color-scheme: light !important;
        }}

        .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: #F6F7F9 !important;
            color: #202124 !important;
        }}

        /* Botones secundarios: fondo blanco y texto oscuro. */
        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {{
            background: #FFFFFF !important;
            border: 1px solid #C7CDD6 !important;
            color: #202124 !important;
            min-height: 44px;
            border-radius: 9px;
            font-weight: 650;
        }}

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {{
            background: #FFF3E6 !important;
            border-color: #A64B00 !important;
            color: #8A3D00 !important;
        }}

        /* Botones primarios: naranja oscuro para alto contraste. */
        button[data-testid="stBaseButton-primary"],
        button[kind="primary"],
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {{
            background: #A64B00 !important;
            border-color: #A64B00 !important;
            color: #FFFFFF !important;
        }}

        button[data-testid="stBaseButton-primary"]:hover,
        button[kind="primary"]:hover {{
            background: #833A00 !important;
            border-color: #833A00 !important;
            color: #FFFFFF !important;
        }}

        /* Los párrafos internos de botones no deben heredar el
           color de texto oscuro global del tema. */
        .stButton button p,
        .stButton button span,
        .stFormSubmitButton button p,
        .stFormSubmitButton button span,
        .stDownloadButton button p,
        .stDownloadButton button span {{
            color: inherit !important;
        }}

        .stButton > button:focus-visible,
        .stFormSubmitButton > button:focus-visible,
        .stDownloadButton > button:focus-visible {{
            outline: 3px solid #F28C28 !important;
            outline-offset: 2px;
        }}

        /* Los inputs oscuros eran el defecto principal en el login. */
        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stTextArea"] [data-baseweb="textarea"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stChatInput"] {{
            background: #FFFFFF !important;
            border: 1px solid #BCC5D0 !important;
            border-radius: 9px !important;
        }}

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stChatInput"] textarea {{
            color: #202124 !important;
            -webkit-text-fill-color: #202124 !important;
            background: transparent !important;
            caret-color: #A64B00 !important;
        }}

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stChatInput"] textarea::placeholder {{
            color: #667085 !important;
            opacity: 1;
            -webkit-text-fill-color: #667085 !important;
        }}

        [data-testid="stTextInput"]:focus-within [data-baseweb="input"],
        [data-testid="stTextArea"]:focus-within [data-baseweb="textarea"] {{
            border-color: #A64B00 !important;
            box-shadow: 0 0 0 2px #FADAB8 !important;
        }}

        [data-testid="stTextInput"] svg,
        [data-testid="stDateInput"] svg {{
            color: #374151 !important;
        }}

        [data-testid="stForm"] {{
            background: #FFFFFF !important;
            color: #202124 !important;
        }}

        [data-testid="stFileUploaderDropzone"],
        [data-testid="stFileUploader"] section {{
            background: #FFFFFF !important;
            color: #202124 !important;
        }}

        /* Evitar barra lateral/nav mientras aparece el formulario
           de acceso, incluso al volver de una sesión anterior. */
        body:has(.unfv-login-view) [data-testid="stSidebar"],
        body:has(.unfv-login-view) [data-testid="stSidebarCollapsedControl"],
        body:has(.unfv-login-view) [data-testid="stSidebarCollapseButton"] {{
            display: none !important;
        }}

        body:has(.unfv-login-view) .block-container {{
            max-width: 1120px;
            padding-top: clamp(3rem, 7vh, 6rem);
        }}

        .unfv-login-heading {{
            text-align: center;
            margin-bottom: 1.6rem;
        }}

        .unfv-login-icon {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 68px;
            height: 68px;
            border-radius: 20px;
            font-size: 2rem;
            background: #FFF3E6;
            margin-bottom: 0.8rem;
        }}

        .unfv-login-heading h1 {{
            font-size: clamp(1.65rem, 3vw, 2.25rem) !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            color: #202124 !important;
            margin: 0.2rem 0 0.55rem;
        }}

        .unfv-login-heading p, .unfv-login-hint {{
            font-size: 0.88rem;
            line-height: 1.5;
            color: #576273;
            text-align: center;
        }}

        .unfv-login-hint {{
            margin-top: 1rem;
        }}

        body:has(.unfv-login-view) [data-testid="stForm"] {{
            padding: 1.8rem !important;
            border: 1px solid #E3E6EA !important;
            border-top: 4px solid #F28C28 !important;
            border-left: 1px solid #E3E6EA !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 26px rgba(20, 25, 35, 0.06) !important;
        }}

        body:has(.unfv-login-view) [data-testid="stForm"]
        [data-testid="stFormSubmitButton"] button {{
            width: 100%;
        }}

        .unfv-session-label {{
            font-size: 0.81rem;
            color: #374151;
            background: #F4F7F6;
            border: 1px solid #E1E8E3;
            border-radius: 9px;
            padding: 0.6rem 0.75rem;
            margin-bottom: 0.7rem;
        }}

        .unfv-session-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #2E7D5B;
            border-radius: 50%;
            margin-right: 5px;
        }}

        @media (max-width: 740px) {{
            body:has(.unfv-login-view) .block-container {{
                padding-top: 2rem;
            }}
            body:has(.unfv-login-view) [data-testid="stForm"] {{
                padding: 1rem !important;
            }}
        }}

        .unfv-start-steps {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 1rem;
        }}
        .unfv-start-steps > div {{
            background: #FFFFFF;
            border: 1px solid #E3E6EA;
            border-radius: 12px;
            padding: 1rem 1.15rem;
            min-height: 86px;
        }}
        .unfv-start-steps strong {{
            display: block;
            color: #202124;
            margin-bottom: 0.35rem;
            font-size: 0.90rem;
        }}
        .unfv-start-steps span {{
            color: #667085;
            font-size: 0.80rem;
            line-height: 1.45;
        }}
        @media (max-width: 790px) {{
            .unfv-start-steps {{ grid-template-columns: 1fr; }}
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ENCABEZADO DE PÁGINA
# ============================================================

def render_header(title, subtitle):
    header_html = (
        '<div class="unfv-header">'
        '<div class="unfv-header-label">'
        'UNIVERSIDAD NACIONAL FEDERICO VILLARREAL'
        '</div>'
        f'<div class="unfv-header-title">{html.escape(title)}</div>'
        f'<div class="unfv-header-subtitle">{html.escape(subtitle)}</div>'
        '</div>'
    )

    st.markdown(
        header_html,
        unsafe_allow_html=True
    )


# ============================================================
# MARCA DEL SIDEBAR
# ============================================================

def render_sidebar_brand():
    """Logotipo compacto arriba de la navegación, no a media altura."""
    try:
        st.logo('assets/unfv_wordmark.png', size='large')
    except Exception:
        # Versiones de Streamlit sin st.logo pueden seguir mostrando la app.
        st.sidebar.caption('Universidad Nacional Federico Villarreal · UNFV')


# ============================================================
# ESTADO DE SESIÓN EN SIDEBAR
# ============================================================

def render_sidebar_status():

    if st.session_state.get("docs_ready"):
        pdf_names = st.session_state.get("pdf_names", [])
        status_text = f"{len(pdf_names)} documento(s) procesado(s)"
        status_icon = "●"
    else:
        status_text = "Sin documentos procesados"
        status_icon = "○"

    sidebar_status_html = (
        '<div class="unfv-sidebar-footer">'
        '<div style="font-weight:700; color:#202124; margin-bottom:5px;">'
        'Sesión académica · Ingeniería de Sistemas</div>'
        '<div style="font-size:12px; color:#667085;">'
        f'{status_icon} {html.escape(status_text)}'
        '</div></div>'
    )
    st.sidebar.markdown(
        sidebar_status_html,
        unsafe_allow_html=True
    )


# ============================================================
# BADGES
# ============================================================

def status_badge_html(status):

    cfg = status_colors(status)

    return (
        f'<span class="badge" '
        f'style="background:{cfg["soft"]};'
        f'color:{cfg["ink"]};">'
        f'{html.escape(cfg["label"])}'
        f"</span>"
    )


def tag_badge_html(text):

    return (
        '<span class="badge" '
        'style="background:#FFF3E6;'
        'color:#C96A00;">'
        f'{html.escape(str(text))}'
        "</span>"
    )


# ============================================================
# CHIPS DE PDF
# ============================================================

def pdf_chips_html(pdf_names):

    if not pdf_names:
        return ""

    return "".join(
        f'<span class="pdf-chip">📄 {html.escape(name)}</span>'
        for name in pdf_names
    )


# ============================================================
# TARJETAS DE ESTADÍSTICAS
# ============================================================

def render_stat_row(items):
    """Muestra tarjetas con estadísticas resumidas."""

    cards = []

    for label, value, color in items:

        tone = color or UNFV_ORANGE

        card_html = (
            f'<div class="stat-tile" style="--color-tone:{tone};">'
            f'<div class="stat-value">{html.escape(str(value))}</div>'
            f'<div class="stat-label">{html.escape(str(label))}</div>'
            '</div>'
        )

        cards.append(card_html)

    stats_html = (
        '<div class="stat-row">'
        + "".join(cards)
        + '</div>'
    )

    st.markdown(
        stats_html,
        unsafe_allow_html=True
    )

# ============================================================
# GRID DE TEMAS
# ============================================================

def render_topic_grid(topics):
    """Aciertos reales en lugar de mostrar el contador de dominio como porcentaje."""
    cards = []
    for topic in topics:
        cfg = status_colors(topic['status'])
        name = html.escape(str(topic['name']))
        query_count = int(topic.get('query_count', 0))
        correct = int(topic.get('correct_count', 0))
        wrong = int(topic.get('incorrect_count', 0))
        attempts = correct + wrong
        accuracy = round(100 * correct / attempts) if attempts else None
        proportion = (100 * correct / attempts) if attempts else 0
        label = (f'{correct}/{attempts} aciertos · {accuracy}% de precisión' if attempts
                 else 'Sin evaluación todavía')
        badge = status_badge_html(topic['status'])
        cards.append(
            f'<div class="topic-card" style="--color-tone:{cfg["ink"]};">'
            '<div class="topic-card-top">'
            f'<div class="topic-name">{name}</div>{badge}'
            '</div>'
            f'<div class="topic-meta">{query_count} consulta(s) · {label}</div>'
            '<div class="mastery-track">'
            f'<div class="mastery-fill" style="width:{proportion:.1f}%; --color-tone:{cfg["ink"]};"></div>'
            '</div></div>'
        )
    st.markdown('<div class="topic-grid">' + ''.join(cards) + '</div>',
                unsafe_allow_html=True)


# ============================================================
# BARRAS DE FRECUENCIA
# ============================================================

def render_frequency_bars(topics):
    """Muestra barras horizontales según la frecuencia de consultas."""

    if not topics:
        return

    max_count = max(
        topic["query_count"]
        for topic in topics
    )

    if max_count <= 0:
        max_count = 1

    rows = []

    for topic in topics:

        cfg = status_colors(
            topic["status"]
        )

        count = topic["query_count"]

        width = (count / max_count) * 100 if count else 0

        name = html.escape(
            str(topic["name"])
        )

        row_html = (
            '<div class="bar-row">'
            f'<div class="bar-label">{name}</div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" '
            f'style="width:{width}%; --color-tone:{cfg["ink"]};">'
            '</div>'
            '</div>'
            f'<div class="bar-value">{count}</div>'
            '</div>'
        )

        rows.append(
            row_html
        )

    st.markdown(
        "".join(rows),
        unsafe_allow_html=True
    )

# ============================================================
# TEMAS DÉBILES
# ============================================================

def weak_topic_line_html(topic):

    if isinstance(topic, dict):
        name = topic["name"]
    else:
        name = str(topic)

    return (
        '<div class="weak-topic-line">'
        f'{html.escape(name)}'
        "</div>"
    )


# ============================================================
# FEEDBACK DE QUIZ
# ============================================================

def feedback_banner_html(is_correct, explanation):

    tone = (
        CORRECT
        if is_correct
        else INCORRECT
    )

    title = (
        "Respuesta correcta"
        if is_correct
        else "Respuesta incorrecta"
    )

    return (
        f'<div class="feedback-banner" '
        f'style="--color-tone:{tone};">'
        f"<strong>{title}</strong><br>"
        f"{html.escape(explanation or '')}"
        "</div>"
    )


# ============================================================
# ESTADO VACÍO
# ============================================================

def render_empty_state(title, body):

    empty_html = (
        '<div class="empty-state">'
        f'<div class="empty-state-title">{html.escape(title)}</div>'
        f'<div class="empty-state-body">{html.escape(body)}</div>'
        '</div>'
    )

    st.markdown(
        empty_html,
        unsafe_allow_html=True
    )