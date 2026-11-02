"""V5: cuota Gemini, respaldo NVIDIA, seguridad de quizzes y diagnóstico OCR.

Pruebas sin conexiones de red ni claves reales.
"""
import json
from types import SimpleNamespace
from pathlib import Path
import pytest

import agents
import ingest
import llm_resilience as lr


class FakeModel:
    def __init__(self, result=None, error=None):
        self.calls = 0
        self.result = result
        self.error = error

    def invoke(self, prompt, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.result)


@pytest.fixture(autouse=True)
def reset_circuit(monkeypatch):
    monkeypatch.setattr(lr, '_primary_cooldown_until', 0.)


def test_429_immediately_switches_to_nvidia_and_avoids_repeat():
    gemini = FakeModel(error=RuntimeError('429 RESOURCE_EXHAUSTED quota exceeded'))
    nvidia = FakeModel('Texto contrastado')
    v = lr.TextVerifierFailover(gemini, nvidia)
    assert v.invoke('audita').content == 'Texto contrastado'
    assert v.used_fallback and v.last_provider == 'NVIDIA alternativo'
    assert lr.cooldown_remaining() > 0
    v.invoke('audita de nuevo')
    assert gemini.calls == 1
    assert nvidia.calls == 2


def test_gemini_used_when_available():
    gemini = FakeModel('Gemini audita')
    nvidia = FakeModel('NVIDIA audita')
    v = lr.TextVerifierFailover(gemini, nvidia)
    assert v.invoke('consulta').content == 'Gemini audita'
    assert not v.used_fallback
    assert nvidia.calls == 0


def test_second_nvidia_model_fallback_to_ultra():
    lr.mark_quota_exhausted()
    v = lr.TextVerifierFailover(FakeModel(),
                                FakeModel(error=RuntimeError('modelo no habilitado')),
                                FakeModel('NVIDIA principal verifica'))
    assert v.invoke('consulta').content == 'NVIDIA principal verifica'
    assert v.last_provider == 'NVIDIA principal'


def test_all_verifiers_unavailable_fails_closed():
    lr.mark_quota_exhausted()
    v = lr.TextVerifierFailover(FakeModel(),
                                FakeModel(error=RuntimeError('no disponible')))
    with pytest.raises(RuntimeError, match='No fue posible verificar'):
        v.invoke('consulta')


def test_ocr_quota_does_not_repeat_requests(monkeypatch):
    gemini = FakeModel(error=RuntimeError('429 RESOURCE_EXHAUSTED'))
    monkeypatch.setattr(ingest, 'tesseract_available', lambda: False)
    with pytest.raises(RuntimeError, match='cuota'):
        ingest._ocr_page(gemini, b'not-a-jpeg')
    assert gemini.calls == 1
    assert lr.cooldown_remaining() > 0
    with pytest.raises(RuntimeError, match='OCR'):
        ingest._ocr_page(gemini, b'not-a-jpeg')
    assert gemini.calls == 1


def test_ocr_uses_local_fallback_if_gemini_unavailable(monkeypatch):
    lr.mark_quota_exhausted()
    monkeypatch.setattr(ingest, 'tesseract_available', lambda: True)
    monkeypatch.setattr(ingest, '_ocr_tesseract', lambda _: '08:12 primera alerta')
    assert ingest._ocr_page(FakeModel(), b'fake') == ('08:12 primera alerta', 'ocr-local')


def test_chat_verified_using_fallback_reports_provider(monkeypatch):
    question = '¿A qué hora ocurrió la alerta?'
    context = 'La primera alerta fue a las 08:12.'

    def retrieval(self, vs, queries, **kw):
        assert any('cronología' in item for item in queries)
        return [dict(n=1, text=context, source='caso.pdf', page=2, method='ocr')]

    def planner(self, q, hist, topics):
        return {'intent': 'consulta', 'standalone_question': q,
                'sub_queries': [q], 'topic': None}

    monkeypatch.setattr(agents.RetrieverAgent, 'run', retrieval)
    monkeypatch.setattr(agents.PlannerAgent, 'run', planner)
    generator = FakeModel('La primera alerta fue a las 08:12 [1].')
    gemini = FakeModel(error=RuntimeError('429 RESOURCE_EXHAUSTED'))
    verdict = json.dumps({'score': 96, 'unsupported': [], 'verdict': 'Respaldado'})
    checker = lr.TextVerifierFailover(gemini, FakeModel(verdict))
    result = agents.Orchestrator(generator, None, [], verifier_llm=checker).answer(question)
    assert result.answer == 'La primera alerta fue a las 08:12 [1].'
    assert result.verified and result.verification_provider == 'NVIDIA alternativo'
    assert any('NVIDIA alternativo' in step['summary'] for step in result.trace)


def test_quiz_validation_with_nvidia_fallback(monkeypatch):
    def retrieval(self, vs, queries, **kw):
        return [dict(n=1, text='RTO: cuatro horas.', source='caso.pdf',
                     page=6, method='ocr')]

    monkeypatch.setattr(agents.RetrieverAgent, 'run', retrieval)
    question = json.dumps([{'question': '¿Cuál es el RTO indicado?',
                            'options': ['4 horas', '2 horas', '1 día', '1 minuto'],
                            'correct_index': 0, 'explanation': 'RTO es de 4 horas [1].'}])
    solution = json.dumps([{'id': 0, 'answer_index': 0, 'supported': True}])
    verifier = lr.TextVerifierFailover(FakeModel(error=RuntimeError('429 quota')),
                                       FakeModel(solution))
    qs, trace, summary = agents.Orchestrator(
        FakeModel(question), None, ['RTO'], verifier_llm=verifier).make_quiz('RTO', 1)
    assert len(qs) == 1
    assert summary['kept'] == 1
    assert any('NVIDIA alternativo' in str(t.get('detail')) for t in trace)


def test_without_any_verifier_never_publishes_quiz(monkeypatch):
    monkeypatch.setattr(agents.RetrieverAgent, 'run', lambda *a, **k: [
        dict(n=1, text='RTO: cuatro horas.', source='caso.pdf', page=6, method='ocr')])
    question = json.dumps([{'question': '¿Cuál es el RTO indicado?',
                            'options': ['4 horas', '2 horas', '1 día', '1 minuto'],
                            'correct_index': 0, 'explanation': 'RTO es de 4 horas [1].'}])
    checker = lr.TextVerifierFailover(FakeModel(error=RuntimeError('429 quota')),
                    FakeModel(error=RuntimeError('no disponible')))
    qs, trace, summary = agents.Orchestrator(FakeModel(question), None, ['RTO'],
                        verifier_llm=checker).make_quiz('RTO', 1)
    assert not qs and summary['kept'] == 0
    assert any(t['status'] == 'warn' for t in trace)


def test_ocr_review_display_and_top_sidebar_logo():
    root = Path(__file__).parents[1]
    settings = (root / 'views' / 'settings.py').read_text(encoding='utf8')
    theme = (root / 'theme.py').read_text(encoding='utf8')
    assert 'Inspeccionar texto reconocido por página' in settings
    assert 'Lectura incompleta:' in settings
    assert "st.logo('assets/unfv_wordmark.png'" in theme
    assert (root / 'assets' / 'unfv_wordmark.png').exists()
