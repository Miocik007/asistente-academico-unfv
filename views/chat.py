"""Chat asíncrono: cambiar de página no cancela una respuesta en curso."""
import uuid
import streamlit as st
import agents
import db
import jobs
import state
import theme
import workspace


def _generate_answer(llm, verifier_llm, vector_store, topic_rows, pdf_names, question, history):
    """Solo cómputo de los modelos y RAG; sin Streamlit ni escrituras DB."""
    statuses = {t['name']: t['status'] for t in topic_rows}
    try:
        orch = agents.Orchestrator(
            llm, vector_store, list(statuses),
            topic_status_fn=lambda name: statuses.get(name),
            mode='completo', verifier_llm=verifier_llm, doc_names=pdf_names,
        )
        res = orch.answer(question, history=history)
        return dict(question=question, answer=res.answer, topic=res.topic,
                    sources=res.sources, intent=res.intent, confidence=res.confidence,
                    revised=res.revised, trace=res.trace, total_ms=res.total_ms,
                    verification_provider=res.verification_provider,
                    log=res.log, fallback=False)
    except Exception as exc:
        return dict(question=question, answer=agents.NOT_AVAILABLE, topic='General',
                    sources=[], intent='consulta', confidence=None, revised=False,
                    trace=[], total_ms=0, log=False, fallback=True,
                    error_type=type(exc).__name__)


def render():
    theme.render_header('Asistente Académico',
                        'Pregunta sobre tus documentos: NVIDIA responde; Gemini verifica con respaldo NVIDIA si agota su cuota.')
    if not st.session_state.docs_ready:
        theme.render_empty_state('Bienvenido a tu espacio de estudio',
                                 'Ve a «Documentos y configuración» y sube un PDF, Word o imagen.')
        st.markdown('<div class="unfv-start-steps">'
                    '<div><strong>1 · Carga material</strong><span>PDF, Word e imágenes</span></div>'
                    '<div><strong>2 · Procesa</strong><span>El índice RAG busca evidencias</span></div>'
                    '<div><strong>3 · Pregunta</strong><span>NVIDIA responde; Gemini audita</span></div>'
                    '</div>', unsafe_allow_html=True)
        return

    col_l, col_r = st.columns([5, 1])
    with col_l:
        st.markdown(theme.pdf_chips_html(st.session_state.pdf_names), unsafe_allow_html=True)
    with col_r:
        if st.session_state.chat_messages and st.button('Limpiar chat', use_container_width=True,
                                                        disabled=jobs.running('chat')):
            st.session_state.chat_messages = []
            workspace.save_conversation(st.session_state.student_id, [])
            st.rerun()

    if st.session_state.get('job_error'):
        st.warning(st.session_state.pop('job_error'))
    for msg in st.session_state.chat_messages:
        with st.chat_message('user'):
            st.markdown(msg['question'])
        with st.chat_message('assistant'):
            if msg.get('pending'):
                st.info('⏳ Preparando la respuesta y verificando las citas. Puedes cambiar de sección.')
            else:
                _render_answer(msg)

    question = st.chat_input('Haz una pregunta sobre tus documentos', disabled=jobs.running('chat'))
    if question:
        try:
            llm = state.get_current_llm()
            verifier = state.get_verifier_llm()
            question_id = uuid.uuid4().hex
            # Solo mensajes ya terminados se incorporan al contexto.
            history = [dict(m) for m in st.session_state.chat_messages if not m.get('pending')][-6:]
            vs = st.session_state.vector_store
            rows = db.get_all_topics()
            names = list(st.session_state.pdf_names)
            task = lambda: _generate_answer(llm, verifier, vs, rows, names, question, history)
            if jobs.start('chat', task, {'job_id': question_id, 'material_hash': db.current_material_hash()}):
                st.session_state.chat_messages.append(
                    dict(question=question, pending=True, job_id=question_id))
                st.rerun()
        except Exception as exc:
            st.error(f'No se pudo iniciar la consulta ({type(exc).__name__}). Comprueba las claves y tu conexión.')


def _render_answer(msg):
    st.markdown(msg['answer'])
    if msg.get('answer') in (agents.NOT_AVAILABLE, agents.VERIFICATION_UNAVAILABLE):
        report = st.session_state.get('ingest_report') or []
        missing = any(
            (int(r.get('texto', 0)) + int(r.get('ocr', 0)) +
             int(r.get('ocr_local', 0)) < int(r.get('paginas', 0)))
            for r in report
        )
        if missing:
            st.warning('Parte del PDF no pudo leerse mediante OCR. Comprueba las páginas '
                       'sin texto en «Documentos y configuración» y reprocesa cuando '
                       'Gemini tenga cuota o con Tesseract instalado.')
    if msg.get('log') and msg.get('topic'):
        st.markdown(theme.tag_badge_html(f"Tema: {msg['topic']}"), unsafe_allow_html=True)
    if msg.get('confidence') is not None:
        provider = msg.get('verification_provider') or 'modelo configurado'
        st.caption(f"🛡️ Revisión orientativa ({provider}): {msg['confidence']}/100. No garantiza exactitud.")
        if str(provider).startswith('NVIDIA'):
            st.info('Gemini no estuvo disponible. NVIDIA efectuó una revisión de respaldo; '
                    'no es una comprobación independiente de proveedor. Comprueba las citas.')
    if msg.get('revised'):
        st.caption('El Tutor revisó su respuesta tras la auditoría.')
    sources = msg.get('sources') or []
    if sources:
        with st.expander(f'Consultar {len(sources)} fragmento(s) de respaldo'):
            for i, snippet in enumerate(sources, 1):
                st.markdown(f'**Fuente {i}**')
                st.caption(snippet[:700])
    trace = msg.get('trace') or []
    if trace:
        with st.expander(f'Proceso multiagente ({len(trace)} pasos)'):
            st.markdown(agents.trace_to_markdown(trace), unsafe_allow_html=True)
