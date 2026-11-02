"""Página: Documentos y Configuración.

Permite gestionar el material académico utilizado por el asistente,
configurar los parámetros del aprendizaje adaptativo y administrar
los datos de progreso del usuario.

La configuración interna del modelo de IA y la API Key no se muestra
en la interfaz. Estos valores se gestionan mediante Streamlit Secrets.
"""

import pandas as pd
import hashlib
import streamlit as st

import db
import ingest
import rag_engine as rag
import state
import theme
import jobs
import workspace
from processing_diagnostics import DocumentProcessingError, describe_empty_extraction


def render():
    """Renderiza la página de documentos y configuración."""

    theme.render_header(
        "Documentos y Configuración",
        "Gestiona el material académico utilizado por el asistente y configura los parámetros del sistema.",
    )

    # ============================================================
    # MATERIAL ACADÉMICO
    # ============================================================

    _render_documents_section()

    st.divider()

    # ============================================================
    # APRENDIZAJE ADAPTATIVO
    # ============================================================

    _render_learning_section()

    st.divider()

    # ============================================================
    # DATOS
    # ============================================================

    _render_data_section()


# ================================================================
# DOCUMENTOS
# ================================================================

# El on_change del uploader se ejecuta ANTES del rerun por cambio de página:
# copiamos el contenido inmediatamente al espacio de trabajo privado.
def _capture_uploads(uploader_key):
    try:
        uploaded = st.session_state.get(uploader_key) or []
        if uploaded:
            workspace.stage_uploads(st.session_state.student_id, uploaded)
            st.session_state.upload_feedback = 'Archivos guardados en la lista preparada. Puedes navegar sin perderlos.'
    except (OSError, ValueError) as exc:
        st.session_state.upload_error = str(exc)


def _reset_uploader():
    st.session_state.uploader_generation += 1


def _render_documents_section():
    """Permite cargar, procesar y eliminar los documentos de la sesión."""

    st.markdown("### 📄 Material académico")
    st.caption("Público: estudiantes universitarios de pregrado UNFV · Tutor: NVIDIA Nemotron 3 Ultra · Verificador: Gemini (respaldo NVIDIA) · OCR: Gemini. No cargues información confidencial de terceros.")

    # ------------------------------------------------------------
    # Estado actual de los documentos
    # ------------------------------------------------------------

    if st.session_state.docs_ready:

        st.markdown(
            theme.pdf_chips_html(
                st.session_state.pdf_names
            ),
            unsafe_allow_html=True,
        )

        n_topics = len(
            db.get_all_topic_names()
        )

        st.caption(
            f"{len(st.session_state.pdf_names)} documento(s) procesado(s) · "
            f"{len(st.session_state.full_text):,} caracteres extraídos · "
            f"{n_topics} tema(s) identificados."
        )

        _render_ingest_report()

    else:

        st.caption(
            "Todavía no has procesado ningún documento."
        )

    if st.session_state.docs_ready and not db.get_all_topics() and not jobs.running('topics'):
        if st.button('Reintentar identificación de temas'):
            try:
                llm = state.get_current_llm()
                full_text = st.session_state.full_text
                if jobs.start('topics', lambda: rag.extract_topics(llm, full_text, max_chars=6500),
                              {'material_hash': db.current_material_hash()}):
                    st.rerun()
            except Exception as exc:
                st.error(f'No se pudo iniciar el análisis ({type(exc).__name__}).')

    # ------------------------------------------------------------
    # Carga de archivos
    # ------------------------------------------------------------

    if st.session_state.process_notice:
        notice = st.session_state.process_notice
        (st.warning if notice.startswith('No terminó') else st.success)(notice)
        st.session_state.process_notice = ""

    if st.session_state.get('failed_ingest_report'):
        with st.expander('Ver por qué falló la lectura anterior', expanded=True):
            st.dataframe(pd.DataFrame(st.session_state.failed_ingest_report),
                         hide_index=True, use_container_width=True)
            for warning in st.session_state.get('failed_ingest_warnings', [])[:12]:
                st.caption(str(warning)[:400])

    username = st.session_state.student_id
    if st.session_state.pop('upload_error', None):
        st.error('Algún archivo no pudo prepararse. Comprueba que sea un formato admitido y no supere 20 MB.')
    if st.session_state.get('upload_feedback'):
        st.success(st.session_state.pop('upload_feedback'))

    uploader_key = f"pdf_uploader_{st.session_state.uploader_generation}"
    st.file_uploader(
        "Añadir PDF, Word (.docx) o fotos a la lista preparada",
        accept_multiple_files=True,
        type=["pdf", "docx", "png", "jpg", "jpeg", "webp"],
        key=uploader_key,
        on_change=_capture_uploads,
        args=(uploader_key,),
        disabled=jobs.running('ingest'),
        help='El material seleccionado se guarda localmente en tu cuenta. '
             'Puedes cambiar de apartado o salir y regresar antes de procesarlo.',
    )
    prepared = workspace.staged_list(username)
    if prepared:
        st.markdown(f'**Archivos preparados: {len(prepared)} de {workspace.MAX_FILES}**')
        st.caption('Estos archivos ya están guardados. Puedes salir y regresar; '
                   'no se enviarán a las APIs hasta que pulses «Procesar documentos». '
                   'Para retirarlos utiliza «Quitar» aquí, no la X del selector.')
        for row in prepared:
            a, b = st.columns([6, 1], vertical_alignment='center')
            a.write(f"📄 {row['name']} · {row['size']/1024/1024:.2f} MB")
            if b.button('Quitar', key=f"stage_remove_{row['sha256']}", use_container_width=True,
                        disabled=jobs.running('ingest')):
                workspace.discard_staged(username, row['sha256'])
                _reset_uploader()
                st.rerun()
        if st.button('Vaciar lista preparada', key='remove_all_prepared',
                     disabled=jobs.running('ingest')):
            workspace.clear_staged(username)
            _reset_uploader()
            st.rerun()
    else:
        st.info('Selecciona un archivo para prepararlo. No se perderá al cambiar de pantalla.')

    with st.expander("Opciones de lectura (OCR)"):
        st.selectbox(
            'Motor de OCR', state.OCR_ENGINE_LABELS, key='ocr_engine_label',
            help='Tesseract local no utiliza cuotas de Gemini ni envía imágenes a la API. '
                 'Debe instalarse por separado en Windows.',
        )
        if state.OCR_ENGINE_VALUES.get(st.session_state.ocr_engine_label) == 'local':
            if ingest.tesseract_available():
                st.success('Tesseract detectado: lectura local disponible.')
            else:
                st.warning('Tesseract no está instalado o no se detecta. Instala Tesseract OCR '
                           'con idioma español y reinicia Streamlit antes de procesar.')
        st.selectbox(
            "Cómo leer páginas escaneadas o imágenes",
            state.OCR_MODE_LABELS,
            key="ocr_mode_label",
            help=(
                "Automático: aplica OCR solo a las páginas sin texto seleccionable. "
                "Forzar: transcribe todas las páginas (útil si el texto del PDF sale "
                "mal). Desactivado: solo lee texto nativo."
            ),
        )
        st.slider(
            "Máximo de páginas a transcribir con OCR",
            min_value=5,
            max_value=200,
            step=5,
            key="ocr_max_pages",
            help=(
                "Cada página con OCR es una llamada al modelo. Este tope cuida tu "
                "cuota. Lo ya transcrito queda en caché y no se vuelve a cobrar."
            ),
        )

    # ------------------------------------------------------------
    # Botones
    # ------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        process_clicked = st.button(
            "Procesar documentos",
            type="primary",
            use_container_width=True,
            disabled=jobs.running('ingest'),
        )

    with col2:

        clear_clicked = st.button(
            "Retirar documentos procesados",
            use_container_width=True,
            disabled=not st.session_state.docs_ready or jobs.running('ingest'),
        )

    if jobs.running('ingest'):
        st.info('⏳ Extrayendo texto y ejecutando OCR en segundo plano. '
                'Puedes cambiar de apartado; los archivos y la tarea se conservan '
                'mientras mantengas abierta tu sesión y el servidor funcione.')

    # ------------------------------------------------------------
    # Quitar documentos
    # ------------------------------------------------------------

    if clear_clicked:
        jobs.registry().discard(jobs.ensure_session())
        workspace.clear_processed(st.session_state.student_id)
        st.session_state.chat_messages = []
        st.session_state.study_plan = ''
        st.session_state.plan_signature = None
        st.session_state.quiz_draft = {}
        st.session_state.quiz_result = []

        st.session_state.vector_store = None
        st.session_state.full_text = ""
        st.session_state.docs_ready = False
        st.session_state.pdf_names = []
        st.session_state.ingest_report = []
        st.session_state.ingest_warnings = []
        st.session_state.active_topics = []
        st.session_state.process_fingerprint = None

        st.success(
            "Material procesado retirado de tu cuenta. "
            "La lista preparada y el historial de evaluaciones siguen disponibles."
        )

        st.rerun()

    # ------------------------------------------------------------
    # Procesar documentos
    # ------------------------------------------------------------

    if process_clicked:
        try:
            pdf_docs = workspace.staged_as_files(username)
        except (OSError, ValueError):
            st.error('No se pudieron leer los archivos preparados. Quita el archivo dañado y vuelve a subirlo.')
            return
        if not pdf_docs:

            st.warning(
                "Sube al menos un archivo antes de procesar."
            )

            return

        process_fingerprint = hashlib.sha256(
            ('|'.join(sorted(hashlib.sha256(f.getvalue()).hexdigest() for f in pdf_docs))
             + '|' + st.session_state.ocr_mode_label + '|' + str(st.session_state.ocr_max_pages)
             + '|' + st.session_state.ocr_engine_label)
            .encode('utf-8')).hexdigest()
        if st.session_state.docs_ready and process_fingerprint == st.session_state.get('process_fingerprint'):
            st.info('Estos mismos documentos ya están procesados. No es necesario repetir OCR ni crear el índice.')
            return
        try:

            # La API Key y el modelo ya NO vienen de la interfaz.
            # state.get_current_llm() los obtiene desde st.secrets.
            llm = state.get_current_llm()

        except Exception as exc:

            st.error(
                "No se pudo inicializar el modelo de Inteligencia Artificial."
            )

            st.caption(f"Tipo de error: {type(exc).__name__}. Revisa tus claves, modelo y cuota disponible.")

            return

        try:
            engine = state.OCR_ENGINE_VALUES.get(st.session_state.ocr_engine_label, 'auto')
            if engine == 'local' and not ingest.tesseract_available():
                st.error('Tesseract no está disponible. Instala Tesseract OCR con español '
                         'y reinicia Streamlit, o selecciona OCR automático.')
                return
            ocr_llm = None if engine == 'local' else state.get_ocr_llm()
            mode = state.OCR_MODE_VALUES.get(st.session_state.ocr_mode_label, 'auto')
            max_pages = st.session_state.ocr_max_pages
            username = st.session_state.student_id
            st.session_state.failed_ingest_report = []
            st.session_state.failed_ingest_warnings = []
            def worker():
                return ingest.ingest_files(
                    pdf_docs, llm=ocr_llm, mode=mode,
                    max_ocr_pages=max_pages,
                    progress=None, cache=workspace.StudentOCRCache(username),
                    engine=engine,
                )
            if jobs.start('ingest', worker, {
                'student_id': username,
                'files': pdf_docs,
                'process_fingerprint': process_fingerprint,
                'ocr_mode': st.session_state.ocr_mode_label,
                'max_ocr_pages': max_pages,
            }):
                st.info('Procesamiento iniciado. Puedes navegar a otra sección.')
                st.rerun()

        except Exception as exc:

            st.error(
                "Ocurrió un error al procesar los documentos."
            )

            st.caption(f"Tipo de error: {type(exc).__name__}. Revisa tus claves, modelo y cuota disponible.")


# ================================================================
# PROCESAMIENTO DE DOCUMENTOS
# ================================================================

def _complete_documents_from_result(result, pdf_docs, llm, process_fingerprint=None,
                                    ocr_mode=None, max_ocr_pages=None):
    """Publicación atómica en el hilo principal tras OCR asíncrono.

    La escritura de DB y los cambios st.session_state nunca ocurren en el hilo OCR.
    """
    pages = result["pages"]
    full_text = ingest.pages_to_text(pages)

    if not full_text.strip():
        st.session_state.failed_ingest_report = result['report']
        st.session_state.failed_ingest_warnings = result['warnings']
        raise DocumentProcessingError(describe_empty_extraction(result))

    # ------------------------------------------------------------
    # Crear fragmentos e índice vectorial
    # ------------------------------------------------------------

    with st.spinner(
        "Construyendo el índice de búsqueda semántica..."
    ):

        try:
            vector_store = rag.build_vector_store_from_pages(pages)
        except Exception as exc:
            st.session_state.failed_ingest_report = result['report']
            st.session_state.failed_ingest_warnings = result['warnings']
            raise DocumentProcessingError(
                'El documento produjo texto, pero falló la creación del índice semántico. '
                'Comprueba las dependencias FAISS y sentence-transformers, la memoria '
                'disponible y la descarga inicial del modelo de embeddings. '
                'No es un error del OCR ni significa que se haya agotado Gemini.'
            ) from exc

    if vector_store is None:
        raise DocumentProcessingError('No se pudieron crear fragmentos de búsqueda a partir del texto.')

    st.session_state.failed_ingest_report = []
    st.session_state.failed_ingest_warnings = []
    st.session_state.ingest_report = result['report']
    st.session_state.ingest_warnings = result['warnings']

    # ------------------------------------------------------------
    # Cambiar ámbito antes de iniciar análisis de temas en segundo plano
    # ------------------------------------------------------------
    fingerprints = sorted(hashlib.sha256(f.getvalue()).hexdigest() for f in pdf_docs)
    material_hash = hashlib.sha256('|'.join(fingerprints).encode()).hexdigest()
    # Guardar páginas EXTRAÍDAS y el índice local ANTES de cambiar de materia.
    # Al volver a iniciar sesión se restauran sin repetir OCR ni pagar llamadas.
    workspace.save_processed(
        st.session_state.student_id,
        material_hash=material_hash,
        process_fingerprint=process_fingerprint,
        pages=pages,
        report=result['report'],
        warnings=result['warnings'],
        names=[f.name for f in pdf_docs],
        ocr_mode=ocr_mode or st.session_state.ocr_mode_label,
        max_ocr_pages=max_ocr_pages if max_ocr_pages is not None else st.session_state.ocr_max_pages,
    )
    index_warning = False
    try:
        workspace.save_index(st.session_state.student_id, material_hash, vector_store)
    except Exception:
        index_warning = True  # Se podrá reconstruir con las páginas guardadas.

    previous_hash = db.current_material_hash()
    if previous_hash != material_hash:
        jobs.registry().discard(jobs.ensure_session())
    changed = db.ensure_material_scope(material_hash)
    if changed:
        workspace.clear_learning_artifacts(st.session_state.student_id)
        st.session_state.chat_messages = []
        st.session_state.quiz_feedback = {}
        st.session_state.quiz_draft = {}
        st.session_state.quiz_result = []
        st.session_state.study_plan = ''
        st.session_state.plan_signature = None
    # La llamada larga de NVIDIA para identificar temas NO bloquea la navegación.
    st.session_state.active_topics = db.get_all_topic_names()
    if not st.session_state.active_topics:
        jobs.start('topics', lambda: rag.extract_topics(llm, full_text, max_chars=6500),
                   {'material_hash': material_hash})

    # ------------------------------------------------------------
    # Guardar sesión
    # ------------------------------------------------------------

    st.session_state.vector_store = vector_store
    st.session_state.full_text = full_text
    st.session_state.docs_ready = True

    st.session_state.pdf_names = [
        pdf.name
        for pdf in pdf_docs
    ]

    # También dejamos disponibles los temas de esta sesión.
    # Los temas aparecerán en cuanto termine la llamada asíncrona a NVIDIA.
    st.session_state.process_fingerprint = process_fingerprint

    n_ocr = sum(r["ocr"] + r["ocr_local"] for r in result["report"])

    st.session_state.process_notice = (
        "Documentos procesados y guardados para futuras sesiones. "
        'Ya puedes navegar sin perder el material; los temas se detectan en segundo plano.'
        + (f' Se transcribieron {n_ocr} página(s) mediante OCR.' if n_ocr else '')
        + (' Al regresar se reconstruirá el índice local con el texto guardado.' if index_warning else '')
    )



def _render_ingest_report():
    """Resumen de cómo se leyó cada archivo (texto nativo / OCR / avisos)."""

    report = st.session_state.get("ingest_report") or []

    if not report:
        return

    df = pd.DataFrame(report).rename(
        columns={
            "archivo": "Archivo",
            "paginas": "Páginas",
            "texto": "Con texto",
            "ocr": "OCR (IA)",
            "ocr_local": "OCR local",
            "vacias": "Vacías",
            "omitidas": "Sin leer",
            "errores": "Errores",
            "caracteres": "Caracteres",
        }
    )

    read_pages = sum(int(r.get('texto', 0)) + int(r.get('ocr', 0)) +
                     int(r.get('ocr_local', 0)) for r in report)
    expected_pages = sum(int(r.get('paginas', 0)) for r in report)
    if read_pages < expected_pages or any(int(r.get('errores', 0)) for r in report):
        st.warning(f'Lectura incompleta: {read_pages} de {expected_pages} páginas con texto. '
                   'Algunas respuestas pueden faltar aunque el documento exista. '
                   'Revisa el detalle y vuelve a procesar cuando se recupere la cuota OCR.')
    else:
        st.caption(f'Lectura: {read_pages} de {expected_pages} páginas con texto reconocido.')

    with st.expander("Detalle de lectura de los documentos"):

        st.dataframe(df, hide_index=True, use_container_width=True)

        for warning in (st.session_state.get("ingest_warnings") or [])[:8]:
            st.warning(warning)

    # Herramienta diagnóstica local: permite comprobar si una cifra, rol u hora
    # está realmente en el texto OCR, sin gastar llamadas adicionales a la API.
    with st.expander('Inspeccionar texto reconocido por página (sin usar IA)'):
        snapshot = workspace.load_processed(st.session_state.student_id) or {}
        pages = snapshot.get('pages') or []
        if not pages:
            st.caption('No hay transcripciones guardadas para este material.')
        for page in pages[:80]:
            label = (f"{page.get('source', 'documento')} · "
                     f"página {page.get('page') or 'sin página'} · "
                     f"{page.get('method') or 'desconocido'}")
            st.markdown(f'**{label}**')
            if (page.get('text') or '').strip():
                st.code((page.get('text') or '')[:1600], language=None)
            else:
                st.warning('Esta página no contiene texto recuperado.')


# ================================================================
# APRENDIZAJE ADAPTATIVO
# ================================================================

def _render_learning_section():
    """Configuración de las reglas del aprendizaje adaptativo."""

    st.markdown(
        "### 🎯 Parámetros de aprendizaje"
    )

    st.caption(
        "Las consultas muestran interés; los temas débiles se identifican "
        "por errores en evaluaciones, no solo por preguntar varias veces."
    )

    st.info('Los temas débiles se detectan por respuestas incorrectas del quiz. Las consultas se registran como actividad, no como prueba de bajo rendimiento.')

    st.slider(
        "Preguntas de evaluación por tema",
        min_value=2,
        max_value=6,
        key="questions_per_topic",
        help=(
            "Número de preguntas que se generarán para cada tema "
            "seleccionado en la evaluación."
        ),
    )

    st.session_state.agent_mode = 'completo'
    st.caption('Verificación de respuestas y claves de cuestionarios: obligatoria.')

    st.slider(
        "Temas a incluir por evaluación",
        min_value=1,
        max_value=5,
        key="max_topics_per_quiz",
        help=(
            "Número máximo de temas que pueden incluirse "
            "en una misma evaluación adaptativa."
        ),
    )


# ================================================================
# DATOS
# ================================================================

def _render_data_section():
    """Muestra estadísticas y permite reiniciar el progreso guardado."""

    st.markdown(
        "### 🗂️ Gestión de datos"
    )

    stats = db.get_stats_summary()

    st.caption(
        f"{stats['total_questions']} consulta(s) realizadas · "
        f"{stats['total_answered']} evaluación(es) respondida(s) · "
        f"{stats['total_topics']} tema(s) registrado(s)."
    )

    st.warning(
        "Reiniciar eliminará el historial, las evaluaciones y la caché OCR "
        "de esta cuenta. Al cargar otros documentos, el progreso anterior "
        "se reiniciará para evitar mezclar materias."
    )

    confirm = st.checkbox(
        "Confirmo que quiero borrar todo mi progreso."
    )

    if st.button(
        "Reiniciar progreso",
        disabled=not confirm,
    ):

        jobs.registry().discard(jobs.ensure_session())
        db.reset_all()
        workspace.clear_staged(st.session_state.student_id)
        workspace.clear_processed(st.session_state.student_id)
        _reset_uploader()

        st.session_state.chat_messages = []
        st.session_state.quiz_feedback = {}
        st.session_state.quiz_draft = {}
        st.session_state.quiz_result = []

        # Si estos datos existen en la sesión también los limpiamos.
        st.session_state.vector_store = None
        st.session_state.full_text = ""
        st.session_state.docs_ready = False
        st.session_state.pdf_names = []
        st.session_state.active_topics = []
        st.session_state.ingest_report = []
        st.session_state.ingest_warnings = []
        st.session_state.study_plan = ""
        st.session_state.process_fingerprint = None

        st.success(
            "El progreso fue reiniciado correctamente."
        )

        st.rerun()