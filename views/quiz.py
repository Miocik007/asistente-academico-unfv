"""Evaluación de opción múltiple: un único envío, resultado único y corrección clara."""
import streamlit as st
import agents
import db
import jobs
import state
import theme
import workspace


def _make_quiz_worker(llm, verifier, vector_store, specs):
    """Sin Streamlit ni SQLite; el hilo devuelve datos que guarda la sesión propietaria."""
    orch = agents.Orchestrator(llm, vector_store, [], mode='completo', verifier_llm=verifier)
    outcome = []
    for item in specs:
        questions, trace, summary = orch.make_quiz(
            item['name'], item['n'], mastery=item['mastery'],
            avoid=item['avoid'], mistakes=item['mistakes'])
        outcome.append((item['name'], questions, trace, summary))
    return outcome


def _remember_choice(qid):
    st.session_state.quiz_draft[qid] = st.session_state[f'quiz_choice_{qid}']
    workspace.save_quiz_draft(st.session_state.student_id, st.session_state.quiz_draft)


def _render_results():
    results = st.session_state.get('quiz_result') or []
    if not results:
        return
    correct = sum(q['correct'] for q in results)
    total = len(results)
    st.markdown('### Resultado de tu evaluación')
    st.metric('Respuestas correctas', f'{correct} de {total}',
              help='Porcentaje de aciertos de este intento, no nivel de dominio general.')
    st.progress(correct / total if total else 0, text=f'{100 * correct / total:.0f}% de aciertos')
    if correct < total:
        st.info('Revisa las respuestas incorrectas y sus explicaciones. Los temas correspondientes se priorizarán para reforzar.')
    for i, q in enumerate(results, 1):
        icon = '✅' if q['correct'] else '❌'
        label = f"{icon} {i}. {q['topic']} — {q['question']}"
        with st.expander(label, expanded=not q['correct']):
            st.write(f"**Tu respuesta:** {q['options'][q['selected_index']]}")
            if not q['correct']:
                st.write(f"**Respuesta correcta:** {q['options'][q['correct_index']]}")
            st.write('**Explicación:**', q['explanation'] or 'Consulta los fragmentos originales.')
            st.caption('La clave del quiz fue contrastada previamente con un segundo modelo. Verifica siempre con el documento.')
    if st.button('Cerrar resultados de este intento', key='close_quiz_results'):
        st.session_state.quiz_result = []
        st.rerun()


def render():
    theme.render_header(
        'Evaluación Adaptativa',
        'Responde todas las preguntas y envía el cuestionario una sola vez. Al terminar verás el resultado completo.',
    )
    if not st.session_state.docs_ready:
        theme.render_empty_state('Aún no puedes generar evaluaciones',
                                 'Procesa tus documentos primero en Documentos y configuración.')
        return

    if st.session_state.quiz_notice:
        st.info(st.session_state.quiz_notice)
        st.session_state.quiz_notice = ''
    if st.session_state.get('job_error'):
        st.warning(st.session_state.pop('job_error'))

    _render_results()
    st.divider()

    weak_topics = db.get_weak_topics(limit=st.session_state.max_topics_per_quiz)
    topics_to_quiz = weak_topics or db.get_all_topics()[:st.session_state.max_topics_per_quiz]
    if not topics_to_quiz and jobs.running('topics'):
        st.info('⏳ Los documentos ya están disponibles; NVIDIA está identificando sus temas en segundo plano.')
    left, right = st.columns([2, 1], vertical_alignment='center')
    with left:
        if weak_topics:
            st.markdown('**Temas que necesitan refuerzo según tus evaluaciones**')
            st.markdown(''.join(theme.weak_topic_line_html(t) for t in weak_topics),
                        unsafe_allow_html=True)
        else:
            st.caption('Aún no hay temas con errores registrados. Puedes empezar con una evaluación diagnóstica.')
    with right:
        clicked = st.button('Generar evaluación', type='primary', use_container_width=True,
                            disabled=not topics_to_quiz or jobs.running('quiz'))

    if clicked:
        try:
            specs = [dict(name=t['name'], n=st.session_state.questions_per_topic,
                          mastery=t.get('mastery_score', 0),
                          avoid=db.get_quiz_question_texts(t['name']),
                          mistakes=db.get_wrong_quiz_questions(t['name'], limit=3))
                     for t in topics_to_quiz if not db.has_pending_quiz_for_topic(t['name'])]
            if not specs:
                st.info('Ya tienes preguntas por responder. Completa ese intento primero.')
            else:
                llm = state.get_current_llm()
                verifier = state.get_verifier_llm()
                vs = st.session_state.vector_store
                material = db.current_material_hash()
                if jobs.start('quiz', lambda: _make_quiz_worker(llm, verifier, vs, specs),
                              {'material_hash': material}):
                    st.rerun()
        except Exception as exc:
            st.error(f'No se pudo iniciar la generación ({type(exc).__name__}). Verifica tus APIs.')

    if jobs.running('quiz'):
        st.info('⏳ Preparando la evaluación: Gemini verifica las claves y NVIDIA actúa como respaldo si se agota la cuota. Puedes navegar mientras se ejecuta.')

    pending = db.get_pending_quiz_questions()
    st.divider()
    if not pending:
        if not jobs.running('quiz'):
            st.caption('No hay preguntas pendientes. Genera una evaluación nueva cuando quieras.')
        return

    st.markdown(f'### Evaluación pendiente · {len(pending)} preguntas')
    st.caption('Marca una opción en cada pregunta. No se calificará nada hasta pulsar «Enviar evaluación completa».')
    letters = 'ABCD'
    for i, q in enumerate(pending, 1):
        choices = st.session_state.quiz_draft
        old = choices.get(q['id'])
        with st.container(border=True):
            st.caption(f"Pregunta {i}/{len(pending)} · {q['topic']}")
            st.markdown(f"**{q['question']}**")
            st.radio('Elige una respuesta', options=list(range(4)),
                     format_func=lambda j, opts=q['options']: f'{letters[j]}. {opts[j]}',
                     index=old if old in range(4) else None,
                     key=f"quiz_choice_{q['id']}",
                     on_change=_remember_choice, args=(q['id'],),
                     label_visibility='collapsed')
    filled = sum(q['id'] in st.session_state.quiz_draft for q in pending)
    st.caption(f'Respondidas: {filled} de {len(pending)}')
    submitted = st.button('Enviar evaluación completa', type='primary',
                          disabled=filled != len(pending), use_container_width=True)
    if submitted:
        try:
            selections = {q['id']: st.session_state.quiz_draft[q['id']] for q in pending}
            st.session_state.quiz_result = db.record_quiz_batch(selections)
            for q in pending:
                st.session_state.quiz_draft.pop(q['id'], None)
                st.session_state.pop(f"quiz_choice_{q['id']}", None)
            workspace.save_quiz_draft(st.session_state.student_id, st.session_state.quiz_draft)
            st.rerun()
        except (ValueError, KeyError) as exc:
            st.error(str(exc))
