"""V5.1: regresión OCR local y errores explícitos, sin usar APIs externas."""
import io
from types import SimpleNamespace

import pytest

import ingest
import processing_diagnostics as diag


class FakeImage(io.BytesIO):
    name = 'apuntes.png'


def test_engine_local_does_not_call_gemini(monkeypatch):
    monkeypatch.setattr(ingest, 'tesseract_available', lambda: True)
    monkeypatch.setattr(ingest, '_ocr_tesseract', lambda data: 'Primera alerta 08:12')
    class Gemini:
        def invoke(self, *args, **kwargs):
            raise AssertionError('En motor local NO se debe consultar Gemini')
    assert ingest._ocr_page(Gemini(), b'imagebytes', engine='local') == (
        'Primera alerta 08:12', ingest.METHOD_OCR_LOCAL)


def test_engine_local_missing_shows_installation_advice(monkeypatch):
    monkeypatch.setattr(ingest, 'tesseract_available', lambda: False)
    with pytest.raises(RuntimeError, match='Instálalo'):
        ingest._ocr_page(None, b'imagebytes', engine='local')


def test_quota_message_not_generic_valueerror():
    result = {
        'pages': [{'text': '', 'method': 'vacía'}] * 8,
        'report': [{'archivo': 'escaneado.pdf', 'paginas': 8, 'errores': 8}],
        'warnings': ['Gemini agotó la cuota de OCR (429)'],
    }
    assert not ingest.pages_to_text(result['pages'])
    user_message = diag.user_ingest_error(
        diag.DocumentProcessingError(diag.describe_empty_extraction(result)))
    assert '8 página(s)' in user_message
    assert 'Gemini agotó' in user_message
    assert 'Tesseract' in user_message
    assert 'preparados' in user_message


def test_if_embeddings_fail_not_misleading_about_gemini():
    exc = diag.DocumentProcessingError('Error en el índice FAISS; Gemini está disponible.')
    assert 'FAISS' in diag.user_ingest_error(exc)
    assert 'instalar tesseract' not in diag.user_ingest_error(exc).lower()


def test_selecting_local_engine_is_wired_through_ui():
    from pathlib import Path
    root = Path(__file__).parents[1]
    ui = (root / 'views' / 'settings.py').read_text(encoding='utf8')
    jobs = (root / 'jobs.py').read_text(encoding='utf8')
    assert "engine=engine" in ui
    assert "'Motor de OCR'" in ui
    assert 'describe_empty_extraction' in ui
    assert 'user_ingest_error(exc)' in jobs


def test_image_input_local_ocr(monkeypatch):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (400, 100), 'white')
    ImageDraw.Draw(img).text((20, 20), 'Primera alerta 08:12', fill='black')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    monkeypatch.setattr(ingest, 'tesseract_available', lambda: True)
    monkeypatch.setattr(ingest, '_ocr_tesseract', lambda _: 'Primera alerta 08:12')
    results = ingest.ingest_files([FakeImage(buf.getvalue())], engine='local', workers=1)
    assert results['report'][0]['ocr_local'] == 1
    assert '08:12' in ingest.pages_to_text(results['pages'])
