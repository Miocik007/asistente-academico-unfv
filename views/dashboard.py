"""Página: Dashboard de progreso."""

import pandas as pd
import streamlit as st

import agents
import db
import state
import theme
import workspace

STATUS_FILTER_OPTIONS = {
    "Todos los estados": None,
    "🆕 Nuevo": db.STATUS_NUEVO,
    "⚠️ Punto débil": db.STATUS_DEBIL,
    "🔄 En refuerzo": db.STATUS_REFORZADO,
    "✅ Dominado": db.STATUS_DOMINADO,
}

SORT_OPTIONS = {
    "Más consultado primero": ("query_count", True),
    "Menor avance registrado primero": ("mastery_score", False),
    "Nombre (A-Z)": ("name", False),
}


def render():
    theme.render_header(
    "Progreso Académico",
    "Consulta tu rendimiento real en evaluaciones y los temas que necesitan repaso.",
)

    topics = db.get_all_topics()
    if not topics:
        theme.render_empty_state(
            "📊 Todavía no hay datos de progreso",
            "Haz algunas preguntas en el 💬 Chat para que empiecen a aparecer "
            "temas y estadísticas aquí.",
        )
        return

    _render_stats(topics)
    st.caption("La precisión es el porcentaje de respuestas correctas en quizzes; las consultas y el puntaje interno de avance no son porcentajes de dominio.")
    _render_trend_chart()

    st.markdown("##### Frecuencia de consultas por tema")
    consulted = [t for t in topics if t['query_count'] > 0]
    if consulted:
        theme.render_frequency_bars(consulted)
    else:
        st.caption('Aún no hay consultas registradas; las evaluaciones se contabilizan por separado.')

    st.write("")
    st.markdown("##### Detalle por tema")
    _render_topic_grid(topics)

    st.divider()
    _render_study_plan(topics)


def _render_stats(topics):
    stats = db.get_stats_summary()
    n_debil = sum(1 for t in topics if t["status"] == db.STATUS_DEBIL)
    n_reforzado = sum(1 for t in topics if t["status"] == db.STATUS_REFORZADO)
    n_dominado = sum(1 for t in topics if t["status"] == db.STATUS_DOMINADO)

    theme.render_stat_row(
        [
            ("Temas totales", len(topics), None),
            ("Puntos débiles activos", n_debil, theme.COLORS[db.STATUS_DEBIL]["ink"]),
            ("En refuerzo", n_reforzado, theme.COLORS[db.STATUS_REFORZADO]["ink"]),
            ("Dominados", n_dominado, theme.COLORS[db.STATUS_DOMINADO]["ink"]),
            (
                "Precisión en quizzes",
                f"{stats['accuracy']}%" if stats["total_answered"] else "—",
                None,
            ),
        ]
    )


def _render_trend_chart():
    daily = db.get_daily_query_counts(days=14)
    if len(daily) < 2:
        return
    st.markdown("##### Preguntas por día (últimos días con actividad)")
    df = pd.DataFrame(daily, columns=["Día", "Preguntas"]).set_index("Día")
    st.bar_chart(df, color=theme.PRIMARY, use_container_width=True)
    st.write("")


def _render_topic_grid(topics):
    filt_col, sort_col = st.columns(2)
    with filt_col:
        status_label = st.selectbox("Filtrar por estado", list(STATUS_FILTER_OPTIONS.keys()))
    with sort_col:
        sort_label = st.selectbox("Ordenar por", list(SORT_OPTIONS.keys()))

    status_value = STATUS_FILTER_OPTIONS[status_label]
    show_all = st.checkbox('Mostrar también temas sin evaluación', value=False,
                           help='Oculta los temas nuevos cuando existen temas ya evaluados.')
    evaluated = any(t['correct_count'] + t['incorrect_count'] > 0 for t in topics)
    filtered = [t for t in topics
                if (status_value is None or t['status'] == status_value)
                and (show_all or not evaluated or t['correct_count'] + t['incorrect_count'] > 0
                     or status_value == db.STATUS_NUEVO)]
    hidden = sum(1 for t in topics if t not in filtered)
    if hidden and not show_all:
        st.caption(f'{hidden} tema(s) nuevos u ocultos. Marca la casilla para mostrarlos.')

    sort_key, reverse = SORT_OPTIONS[sort_label]
    filtered = sorted(filtered, key=lambda t: t[sort_key], reverse=reverse)

    if not filtered:
        st.caption("Ningún tema coincide con este filtro.")
        return
    theme.render_topic_grid(filtered)


def _render_study_plan(topics):
    """Plan instantáneo, reproducible y persistente durante la sesión."""
    st.markdown('##### 🧑‍🏫 Plan de estudio personalizado')
    st.caption('Se elabora usando únicamente tus aciertos, errores y temas registrados. No presupone actividades realizadas.')
    stats = db.get_stats_summary()
    signature = (stats['total_answered'], stats['total_correct'],
                 tuple(sorted((t['name'], t['correct_count'], t['incorrect_count']) for t in topics)))
    if st.button('Generar / actualizar plan de estudio', type='secondary'):
        orch = agents.Orchestrator(None, None, [])
        plan, trace = orch.study_plan(topics, db.get_wrong_quiz_questions(limit=6), stats)
        st.session_state.study_plan = plan
        st.session_state.plan_signature = signature
        workspace.save_plan(st.session_state.student_id, plan, signature)
        try:
            db.save_agent_run('coach', 'Plan de estudio', None, 'plan', None, False,
                              sum(x.get('ms', 0) for x in trace), trace)
        except Exception:
            pass
    if st.session_state.study_plan:
        if st.session_state.get('plan_signature') != signature:
            st.warning('Este plan se creó antes de tus últimas evaluaciones. Actualízalo para utilizar los resultados nuevos.')
        st.markdown(st.session_state.study_plan)
