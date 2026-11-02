"""Página: Historial.

A diferencia del historial de chat que se veía en la pestaña de Chat (que se
perdía al recargar la página), esta página lee directamente de la base de
datos: persiste entre sesiones, se puede filtrar por tema, buscar por texto
y exportar a CSV.
"""

import pandas as pd
import streamlit as st

import db
import theme


def render():
    theme.render_header(
    "Historial Académico",
    "Consulta tus preguntas, respuestas y evaluaciones realizadas durante el proceso de aprendizaje.",
)

    tab_chat, tab_quiz = st.tabs(["💬 Preguntas del chat", "🧠 Quiz respondidos"])

    with tab_chat:
        _render_chat_history()

    with tab_quiz:
        _render_quiz_history()


def _topic_options():
    return ["Todos"] + db.get_all_topic_names()


def _download_button(rows, filename, label):
    if not rows:
        return
    df = pd.DataFrame(rows)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=csv, file_name=filename, mime="text/csv")


def _render_chat_history():
    col1, col2 = st.columns([1, 2])
    with col1:
        topic = st.selectbox("Tema", _topic_options(), key="hist_chat_topic")
    with col2:
        search = st.text_input("Buscar en preguntas o respuestas", key="hist_chat_search")

    rows = db.get_recent_questions(
        topic=None if topic == "Todos" else topic,
        search=search or None,
    )

    st.caption(f"{len(rows)} pregunta(s) encontradas.")
    _download_button(rows, "historial_preguntas.csv", "📥 Descargar CSV")

    if not rows:
        st.info("No hay preguntas que coincidan con este filtro.")
        return

    for r in rows:
        preview = r["question"][:70] + ("…" if len(r["question"]) > 70 else "")
        with st.expander(f"🕐 {r['timestamp']} · {r['topic']} · {preview}"):
            st.markdown(f"**Pregunta:** {r['question']}")
            st.markdown(f"**Respuesta:** {r['answer']}")
            st.markdown(theme.tag_badge_html(f"Tema: {r['topic']}"), unsafe_allow_html=True)


def _render_quiz_history():
    col1, col2 = st.columns(2)
    with col1:
        topic = st.selectbox("Tema", _topic_options(), key="hist_quiz_topic")
    with col2:
        correctness_label = st.selectbox(
            "Resultado", ["Todas", "Solo correctas", "Solo incorrectas"], key="hist_quiz_correctness"
        )
    correctness = {
        "Todas": None,
        "Solo correctas": "correct",
        "Solo incorrectas": "incorrect",
    }[correctness_label]

    rows = db.get_answered_quiz_questions(
        topic=None if topic == "Todos" else topic,
        correctness=correctness,
    )

    n_correct = sum(1 for r in rows if r["is_correct"])
    st.caption(f"{len(rows)} pregunta(s) respondidas · {n_correct} correctas.")

    export_rows = [
        {
            "fecha": r["answered_at"],
            "tema": r["topic"],
            "pregunta": r["question"],
            "correcta": bool(r["is_correct"]),
        }
        for r in rows
    ]
    _download_button(export_rows, "historial_quiz.csv", "📥 Descargar CSV")

    if not rows:
        st.info("No hay preguntas de quiz que coincidan con este filtro.")
        return

    letters = ["A", "B", "C", "D", "E", "F"]
    for q in rows:
        icon = "✅" if q["is_correct"] else "❌"
        preview = q["question"][:70] + ("…" if len(q["question"]) > 70 else "")
        with st.expander(f"{icon} {q['answered_at']} · [{q['topic']}] {preview}"):
            selected_idx = q["selected_index"]
            correct_idx = q["correct_index"]
            for i, opt in enumerate(q["options"]):
                tag = ""
                if i == correct_idx:
                    tag = " · correcta"
                elif i == selected_idx:
                    tag = " · tu respuesta"
                st.write(f"{letters[i]}) {opt}{tag}")
            if q["explanation"]:
                st.markdown(
                    theme.feedback_banner_html(bool(q["is_correct"]), q["explanation"]),
                    unsafe_allow_html=True,
                )
