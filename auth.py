"""Inicio de sesión local con contraseñas PBKDF2; ninguna credencial en el código."""
import hashlib
import html
import hmac
import secrets
import streamlit as st

ROUNDS = 350_000


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                bytes.fromhex(salt), ROUNDS).hex()
    return f'pbkdf2_sha256${ROUNDS}${salt}${digest}'


def verify_password(password, stored):
    try:
        method, count, salt, expected = stored.split('$')
        if method != 'pbkdf2_sha256' or not 100_000 <= int(count) <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                    bytes.fromhex(salt), int(count)).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def require_login():
    """Control de acceso local para el prototipo universitario."""
    try:
        users = dict(st.secrets.get('users', {}))
    except Exception:
        users = {}

    # El menú se muestra únicamente después de iniciar sesión.
    if st.session_state.get('student_id') in users:
        with st.sidebar:
            st.markdown(
                '<div class="unfv-session-label">'
                '<span class="unfv-session-dot"></span>'
                f' Sesión: <strong>{html.escape(st.session_state["student_id"])}</strong>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button('Cerrar sesión', key='logout', use_container_width=True):
                # Las tareas no terminadas NO deben quedar vinculadas a otra sesión.
                import jobs
                jobs.registry().discard(jobs.ensure_session())
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        return st.session_state['student_id']

    # Este marcador permite aplicar estilos SOLO al login. Se oculta el
    # menú persistente que podría quedar visible tras una sesión anterior.
    st.markdown('<div class="unfv-login-view"></div>', unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.8, 1], gap='large')
    with center:
        st.markdown(
            '<div class="unfv-login-heading">'
            '<div class="unfv-login-icon">🎓</div>'
            '<h1>Asistente Académico UNFV</h1>'
            '<p>Acceso para estudiantes universitarios de pregrado</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        if not users:
            st.error('No hay estudiantes configurados. Agrega [users] a .streamlit/secrets.toml.')
            st.code('python tools/create_password_hash.py', language='powershell')
            st.stop()
        with st.form('login', clear_on_submit=False):
            st.markdown('**Iniciar sesión**')
            username = st.text_input('Usuario', placeholder='Tu usuario').strip()
            password = st.text_input('Contraseña', type='password', placeholder='Tu contraseña')
            submitted = st.form_submit_button('Ingresar', type='primary', use_container_width=True)
        st.markdown(
            '<p class="unfv-login-hint">'
            'Para acceder utiliza las credenciales configuradas por el administrador del proyecto.'
            '</p>', unsafe_allow_html=True,
        )
        if submitted:
            attempts = st.session_state.get('login_attempts', 0)
            if attempts >= 8:
                st.error('Demasiados intentos en esta sesión. Cierra y vuelve a abrir el navegador.')
            elif username in users and verify_password(password, users[username]):
                st.session_state['student_id'] = username
                st.session_state['login_attempts'] = 0
                st.rerun()
            else:
                st.session_state['login_attempts'] = attempts + 1
                st.error('Credenciales incorrectas.')
    st.stop()
