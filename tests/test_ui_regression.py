"""Comprobaciones de configuración visual; no requieren llamadas a APIs."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_uses_light_theme():
    conf = tomllib.loads((ROOT / '.streamlit' / 'config.toml').read_text(encoding='utf-8'))
    assert conf['theme']['base'] == 'light'
    assert conf['theme']['textColor'] == '#202124'
    assert conf['theme']['backgroundColor'] == '#F6F7F9'


def test_login_hides_sidebar_until_authenticated():
    app = (ROOT / 'app.py').read_text(encoding='utf-8')
    auth = (ROOT / 'auth.py').read_text(encoding='utf-8')
    css = (ROOT / 'theme.py').read_text(encoding='utf-8')
    assert 'initial_sidebar_state=(' in app
    assert "auth.require_login()" in app
    assert 'st.navigation(pages)' in app
    assert app.index('auth.require_login()') < app.index('st.navigation(pages)')
    assert 'unfv-login-view' in auth
    assert 'body:has(.unfv-login-view) [data-testid=' in css


def test_login_controls_have_legible_color_overrides():
    css = (ROOT / 'theme.py').read_text(encoding='utf-8')
    auth = (ROOT / 'auth.py').read_text(encoding='utf-8')
    assert 'color: #FFFFFF !important;' in css
    assert 'background: #A64B00 !important;' in css
    assert 'background: #FFFFFF !important;' in css
    assert '-webkit-text-fill-color: #202124 !important;' in css
    assert "st.form_submit_button('Ingresar', type='primary'" in auth


def test_original_six_view_modules_present():
    for module in ('chat', 'dashboard', 'quiz', 'history', 'agentes', 'settings'):
        assert (ROOT / 'views' / f'{module}.py').is_file()
