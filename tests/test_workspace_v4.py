"""Pruebas V4 de almacenamiento local; no requieren NVIDIA/Gemini ni Streamlit."""
from io import BytesIO
import hashlib
import json
import sqlite3
from types import SimpleNamespace
import pytest
import workspace


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, 'ROOT', tmp_path)
    return tmp_path


class Upload(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name


def test_staging_survives_navigation_and_new_login(isolated):
    a = Upload('caso.pdf', b'%PDF-1.4 contenido educativo')
    assert len(workspace.stage_uploads('alumnoA', [a])) == 1
    # No depende de st.session_state. Un nuevo proceso lee los mismos bytes.
    assert workspace.staged_list('alumnoA')[0]['name'] == 'caso.pdf'
    saved = workspace.staged_as_files('alumnoA')
    assert saved[0].getvalue() == b'%PDF-1.4 contenido educativo'
    assert len(workspace.stage_uploads('alumnoA', [a])) == 1  # sin duplicados
    assert workspace.staged_list('alumnoB') == []
    assert workspace.user_dir('alumnoA') != workspace.user_dir('alumnoB')


def test_staging_rejects_traversal_bad_types_and_size(isolated):
    workspace.stage_uploads('a', [Upload('../carpeta/archivo.PDF', b'PDF')])
    assert workspace.staged_list('a')[0]['name'] == 'archivo.PDF'
    with pytest.raises(ValueError):
        workspace.stage_uploads('a', [Upload('privado.exe', b'x')])
    with pytest.raises(ValueError):
        workspace.stage_uploads('a', [Upload('gigante.pdf', b'0' * (workspace.MAX_FILE_BYTES + 1))])
    assert len(workspace.staged_list('a')) == 1


def test_staging_remove_and_clear(isolated):
    rows = workspace.stage_uploads('a', [Upload('a.pdf', b'A'), Upload('b.pdf', b'B')])
    workspace.discard_staged('a', rows[0]['sha256'])
    assert [x['name'] for x in workspace.staged_list('a')] == ['b.pdf']
    workspace.clear_staged('a')
    assert workspace.staged_list('a') == []


def test_material_chat_plan_quiz_restore_and_clear(isolated):
    pages = [{'source':'caso.pdf','page':1,'text':'Las cuatro fases son...','method':'texto'}]
    h = hashlib.sha256(b'material').hexdigest()
    workspace.save_processed('u', material_hash=h, process_fingerprint='fp', pages=pages,
                             report=[{'archivo':'caso.pdf','paginas':1}], warnings=[],
                             names=['caso.pdf'], ocr_mode='auto', max_ocr_pages=40)
    assert workspace.load_processed('u')['pages'] == pages
    workspace.save_conversation('u', [{'question':'Qué fases','answer':'Son cuatro', 'topic':'Tema'},
                                     {'question':'Procesando','pending':True}])
    assert len(workspace.load_conversation('u')) == 1
    workspace.save_plan('u','Sesión 1', (2, 1, (('Tema', 1, 1),)))
    assert workspace.load_plan('u')['text'] == 'Sesión 1'
    workspace.save_quiz_draft('u', {12: 2, 15: 3})
    assert workspace.load_quiz_draft('u') == {12: 2, 15: 3}
    workspace.clear_processed('u')
    assert workspace.load_processed('u') is None
    assert workspace.load_conversation('u') == []
    assert workspace.load_quiz_draft('u') == {}
    assert workspace.load_plan('u') == {}


def test_invalid_snapshot_and_integrity_rejection(isolated):
    d = workspace.user_dir('a')
    (d/'processed.json').write_text('{mal json', encoding='utf8')
    assert workspace.load_processed('a') is None
    workspace.stage_uploads('a', [Upload('x.pdf', b'original')])
    row = workspace.staged_list('a')[0]
    p = d / 'uploads' / (row['sha256'] + row['ext'])
    p.write_bytes(b'modificado')
    with pytest.raises(ValueError):
        workspace.staged_as_files('a')


def test_ocr_background_cache_same_sqlite(isolated):
    username='alumno'
    token=hashlib.sha256(username.encode('utf8')).hexdigest()
    dbfile=isolated / ('student_' + token + '.db')
    with sqlite3.connect(dbfile) as c:
        c.execute('CREATE TABLE ocr_cache (file_hash TEXT,page INTEGER,text TEXT,'
                  'method TEXT,created_at TEXT,PRIMARY KEY(file_hash,page))')
    c=workspace.StudentOCRCache(username)
    assert c.ocr_cache_get('doc',1) is None
    c.ocr_cache_put('doc',1,'Texto leído','ocr')
    assert c.ocr_cache_get('doc',1) == ('Texto leído','ocr')


def test_navigation_and_background_wiring_exists():
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    settings=(base/'views'/'settings.py').read_text(encoding='utf8')
    jobs=(base/'jobs.py').read_text(encoding='utf8')
    state=(base/'state.py').read_text(encoding='utf8')
    assert 'on_change=_capture_uploads' in settings
    assert 'workspace.staged_as_files' in settings
    assert "jobs.start('ingest'" in settings
    assert "job.kind == 'ingest'" in jobs
    assert 'def restore_workspace' in state
    assert 'workspace.load_index' in state
    assert 'workspace.load_conversation' in state
