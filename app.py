"""
Asistente Académico Inteligente - UNFV

Sistema de estudio adaptativo basado en documentos PDF, RAG e Inteligencia Artificial.
"""

import asyncio

import streamlit as st

import db
import auth
import state
import theme
import jobs

from views import agentes, chat, dashboard, history, quiz, settings


try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


def main():

    st.set_page_config(
        page_title="Asistente Académico Inteligente | UNFV",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state=(
            "expanded" if st.session_state.get("student_id") else "collapsed"
        ),
    )

    # Aplicar diseño institucional
    theme.inject_css()

    # Autenticación antes de abrir información persistente.
    auth.require_login()

    # Inicializar base de datos del estudiante autenticado.
    db.init_db()

    # Inicializar variables de sesión
    state.init_session_state()

    # Recuperación por estudiante tras cerrar sesión / reiniciar Streamlit.
    state.restore_workspace()

    jobs.ensure_session()
    jobs.render_status()

    # Identidad de la aplicación
    theme.render_sidebar_brand()

    # Estado de la sesión
    theme.render_sidebar_status()

    # Navegación principal
    pages = {

        "Asistente Académico": [

            st.Page(
                chat.render,
                title="Asistente",
                icon="💬",
                url_path="asistente",
                default=True,
            ),

            st.Page(
                dashboard.render,
                title="Progreso",
                icon="📊",
                url_path="progreso",
            ),

            st.Page(
                quiz.render,
                title="Evaluación",
                icon="📝",
                url_path="evaluacion",
            ),

            st.Page(
                history.render,
                title="Historial",
                icon="🕘",
                url_path="historial",
            ),
        ],

        "Sistema": [

            st.Page(
                agentes.render,
                title="Sistema multiagente",
                icon="🤖",
                url_path="agentes",
            ),

            st.Page(
                settings.render,
                title="Documentos y configuración",
                icon="⚙️",
                url_path="configuracion",
            ),
        ],
    }

    pg = st.navigation(pages)

    pg.run()


if __name__ == "__main__":
    main()