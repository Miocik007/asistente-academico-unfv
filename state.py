"""
Estado compartido entre páginas.

Con una app multipágina cada página es una función independiente, así que
en vez de pasar un diccionario de configuración de página en página, los
valores de configuración (API key, modelo, umbrales) viven directamente en
``st.session_state`` y cada página los lee o escribe según lo necesite.
"""

import streamlit as st

import rag_engine as rag
import workspace

DEFAULT_MODEL = "gemini-3.8-flash"

# Modos de OCR (etiqueta mostrada -> valor interno de ingest.ingest_files)
OCR_MODE_LABELS = [
    "Automático (recomendado)",
    "Forzar OCR en todas las páginas",
    "Desactivado",
]
OCR_MODE_VALUES = {
    OCR_MODE_LABELS[0]: "auto",
    OCR_MODE_LABELS[1]: "force",
    OCR_MODE_LABELS[2]: "off",
}

OCR_ENGINE_LABELS = [
    'Automático (Gemini y respaldo local)',
    'Tesseract local (gratis, sin cuota)',
    'Gemini (solo API)',
]
OCR_ENGINE_VALUES = dict(zip(OCR_ENGINE_LABELS, ('auto', 'local', 'gemini')))

PERSISTENT_KEYS = (
    'ocr_engine_label',
    "questions_per_topic",
    "max_topics_per_quiz",
    "ocr_mode_label",
    "ocr_max_pages",
    "agent_mode",
)


def init_session_state():
    defaults = {
        # Documentos / RAG
        "vector_store": None,
        "full_text": "",
        "docs_ready": False,
        "pdf_names": [],
        # Chat (solo de la sesión actual; el historial persistente vive en la BD)
        "chat_messages": [],
        "quiz_feedback": {},
        "quiz_draft": {},
        "quiz_result": [],
        # Parámetros de aprendizaje adaptativo
        "threshold": 3,
        "questions_per_topic": 3,
        "max_topics_per_quiz": 3,
        # Lectura de documentos (OCR) y sistema multiagente
        "ocr_mode_label": OCR_MODE_LABELS[0],
        "ocr_engine_label": OCR_ENGINE_LABELS[0],
        "failed_ingest_report": [],
        "failed_ingest_warnings": [],
        "ocr_max_pages": 60,
        "agent_mode": "completo",
        "ingest_report": [],
        "ingest_warnings": [],
        "process_notice": "",
        "process_fingerprint": None,
        "quiz_notice": "",
        "study_plan": "",
        "plan_signature": None,
        "active_topics": [],
        "workspace_restored": False,
        "uploader_generation": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Streamlit descarta el valor de un widget cuando su página no se dibuja.
    # Reasignarlo en cada ejecución mantiene los ajustes al cambiar de página.
    for key in PERSISTENT_KEYS:
        st.session_state[key] = st.session_state[key]


def _secret(name, required=True, default=None):
    """Mensajes sin exponer claves en pantalla."""
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    if required and (not value or str(value).startswith('PEGA_')):
        raise RuntimeError(f'Configura {name} en .streamlit/secrets.toml')
    return value


def get_current_llm():
    """Tutor principal: NVIDIA Nemotron 3 Ultra (texto)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url='https://integrate.api.nvidia.com/v1',
        api_key=_secret('NVIDIA_API_KEY'),
        model=_secret('NVIDIA_MODEL', required=False,
                      default='nvidia/nemotron-3-ultra-550b-a55b'),
        temperature=1.0,
        max_tokens=2200,
        timeout=90,
        max_retries=2,
        extra_body={'chat_template_kwargs': {'enable_thinking': False}},
    )


def get_verifier_llm():
    """Gemini prioritario + respaldo NVIDIA ante cuota agotada / fallo.

    El respaldo no constituye verificación independiente de proveedor.
    Para OCR se utiliza get_ocr_llm(): Nemotron Ultra no admite imágenes.
    """
    from langchain_openai import ChatOpenAI
    from llm_resilience import TextVerifierFailover
    primary = get_ocr_llm()
    secondary_model = _secret('NVIDIA_VERIFIER_MODEL', required=False,
                              default='nvidia/nemotron-3.5-lightning-30b-a3b')
    secondary = ChatOpenAI(
        base_url='https://integrate.api.nvidia.com/v1',
        api_key=_secret('NVIDIA_API_KEY'), model=secondary_model,
        temperature=1.0, max_tokens=1300, timeout=45, max_retries=0,
        extra_body={'chat_template_kwargs': {'enable_thinking': False}},
    )
    return TextVerifierFailover(primary, secondary, get_current_llm())


def get_ocr_llm():
    return rag.get_llm(_secret('GOOGLE_API_KEY'),
                       _secret('GEMINI_MODEL', required=False,
                               default='gemini-3.8-flash'), temperature=0.1)


def _tuplify(value):
    if isinstance(value, list):
        return tuple(_tuplify(x) for x in value)
    return value


def restore_workspace():
    """Restablece trabajo TERMINADO al iniciar una nueva sesión autenticada.

    El índice persistido no depende de pickle; si está ausente o corrupto se
    recompone a partir de las páginas extraídas, sin volver a gastar OCR.
    """
    if st.session_state.get('workspace_restored'):
        return
    st.session_state.workspace_restored = True
    username = st.session_state.get('student_id')
    if not username:
        return

    import db
    snapshot = workspace.load_processed(username)
    if not snapshot or snapshot['material_hash'] != db.current_material_hash():
        return
    pages = snapshot['pages']
    try:
        vector_store = workspace.load_index(username, snapshot['material_hash'])
    except Exception:
        vector_store = None
    if vector_store is None:
        try:
            with st.spinner('Restaurando tus documentos y preparando la búsqueda local…'):
                vector_store = rag.build_vector_store_from_pages(pages)
            if vector_store is not None:
                workspace.save_index(username, snapshot['material_hash'], vector_store)
        except Exception as exc:
            st.warning('Tus documentos guardados existen, pero el índice no pudo recuperarse. '
                       'Vuelve a procesarlos desde Documentos y configuración. '
                       f'({type(exc).__name__})')
            return
    if vector_store is None:
        return
    import ingest
    st.session_state.vector_store = vector_store
    st.session_state.full_text = ingest.pages_to_text(pages)
    st.session_state.docs_ready = True
    st.session_state.pdf_names = snapshot['names']
    st.session_state.ingest_report = snapshot.get('report') or []
    st.session_state.ingest_warnings = snapshot.get('warnings') or []
    st.session_state.process_fingerprint = snapshot.get('process_fingerprint')
    st.session_state.active_topics = db.get_all_topic_names()
    st.session_state.chat_messages = workspace.load_conversation(username)
    plan = workspace.load_plan(username)
    st.session_state.study_plan = plan.get('text', '')
    st.session_state.plan_signature = _tuplify(plan.get('signature'))
    st.session_state.quiz_draft = workspace.load_quiz_draft(username)
