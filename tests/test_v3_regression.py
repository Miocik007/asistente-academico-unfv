"""Regresión V3: métricas, entrega atómica, navegación y seguridad documental.
No requieren llamadas reales a NVIDIA/Gemini.
"""
import importlib.util
import threading
from pathlib import Path
import sys
import types
from functools import lru_cache

import pytest

import agents
import db


@pytest.fixture
def clean_data(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'one_student.db'))
    db.init_db()
    db.ensure_topics(['Ciclo de incidentes', 'Analista de seguridad'])
    return db


def _questions():
    return [
        dict(question='¿Qué significa RTO?', options=['Recuperación', 'Autenticación', 'Archivo', 'Memoria'],
             correct_index=0, explanation='RTO se refiere al tiempo objetivo de recuperación.'),
        dict(question='¿Qué es contención?', options=['Aislamiento', 'Restauración', 'Inventario', 'Auditoría'],
             correct_index=0, explanation='Contener limita el alcance del incidente.'),
    ]


def test_single_submission_updates_every_answer_once(clean_data):
    db.save_quiz_questions('Ciclo de incidentes', _questions())
    p = db.get_pending_quiz_questions()
    scored = db.record_quiz_batch({p[0]['id']: 0, p[1]['id']: 1})
    assert len(scored) == 2
    assert sum(r['correct'] for r in scored) == 1
    assert db.get_stats_summary()['total_answered'] == 2
    assert db.get_stats_summary()['accuracy'] == 50
    assert db.get_pending_quiz_questions() == []
    assert db.record_quiz_answer(p[0]['id'], 0) is None
    assert db.get_topic('Ciclo de incidentes')['status'] == db.STATUS_DEBIL


def test_invalid_quiz_batch_is_all_or_nothing(clean_data):
    db.save_quiz_questions('Analista de seguridad', _questions())
    qs = db.get_pending_quiz_questions()
    with pytest.raises(ValueError):
        db.record_quiz_batch({qs[0]['id']: 0, qs[1]['id']: 77})
    assert db.get_stats_summary()['total_answered'] == 0
    assert len(db.get_pending_quiz_questions()) == 2
    with pytest.raises(ValueError):
        db.record_quiz_batch({qs[0]['id']: 0, 999999: 0})
    assert db.get_stats_summary()['total_answered'] == 0


def test_plan_without_quiz_never_claims_zero_accuracy(clean_data):
    plan = agents.CoachAgent(None).run(db.get_all_topics(), [], db.get_stats_summary())
    assert 'no hay evaluaciones respondidas' in plan
    assert '0 %' not in plan
    assert '### 1. Diagnóstico' in plan
    assert '### 3. Tres sesiones' in plan
    assert '\\|' not in plan


def test_plan_after_quiz_uses_real_counts(clean_data):
    db.save_quiz_questions('Ciclo de incidentes', _questions())
    qs = db.get_pending_quiz_questions()
    db.record_quiz_batch({qs[0]['id']: 0, qs[1]['id']: 1})
    plan = agents.CoachAgent(None).run(db.get_all_topics(), [], db.get_stats_summary())
    assert '2 preguntas' in plan
    assert '1 acierto' in plan
    assert '50 %' in plan
    assert 'Ciclo de incidentes' in plan
    assert 'no hay evaluaciones respondidas' not in plan


def test_local_planner_only_matches_known_terms():
    assert agents._local_topic_match('Explica el ciclo de incidentes',
                                      ['Ciclo de incidentes', 'Matemáticas']) == 'Ciclo de incidentes'
    assert agents._local_topic_match('¿Cómo preparo un almuerzo?',
                                      ['Ciclo de incidentes']) is None


def test_pending_navigation_job_completion_is_session_scoped(clean_data, monkeypatch):
    # Emula la sesión Streamlit en un entorno sin UI instalada.
    class State(dict):
        def __getattr__(self, key):
            return self[key]
    session = State(chat_messages=[{'question': '¿RTO?', 'pending': True, 'job_id': 'j-1'}],
                    pdf_names=['doc.pdf'], threshold=3, quiz_notice='',
                    active_topics=[], student_id='alumno_de_prueba')
    monkeypatch.setattr('workspace.save_conversation', lambda *a, **k: None)
    fake = types.ModuleType('streamlit')
    fake.session_state = session
    fake.cache_resource = lambda **kwargs: lambda fn: lru_cache(maxsize=1)(fn)
    fake.fragment = lambda **kwargs: lambda fn: fn
    monkeypatch.setitem(sys.modules, 'streamlit', fake)
    path = Path(__file__).parents[1] / 'jobs.py'
    spec = importlib.util.spec_from_file_location('jobs_v3_test', path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, 'jobs_v3_test', mod)
    spec.loader.exec_module(mod)
    db.ensure_material_scope('material-a')
    main_thread = threading.get_ident()
    seen = []
    def worker():
        seen.append(threading.get_ident())
        return {'question':'¿RTO?', 'answer':'Contenido de documento [1].',
                'topic':'Ciclo de incidentes', 'log':True, 'sources':['doc.pdf'],
                'trace':[], 'total_ms':12}
    assert mod.start('chat', worker, {'job_id': 'j-1', 'material_hash': 'material-a'})
    assert not mod.start('chat', worker, {'job_id': 'j-2', 'material_hash': 'material-a'})
    future = mod.registry().active(mod.ensure_session())[0].future
    future.result(timeout=3)
    # Equivale a navegar a otra página y volver; recolectamos DESPUÉS.
    assert session.chat_messages[0]['pending']
    assert mod.harvest()
    assert seen[0] != main_thread
    assert not session.chat_messages[0].get('pending')
    assert db.get_stats_summary()['total_questions'] == 1
    assert db.get_topic('Ciclo de incidentes')['query_count'] == 1
    mod.registry().executor.shutdown(wait=True)


def test_theme_progress_is_real_ratio_not_raw_score():
    theme_file = (Path(__file__).parents[1] / 'theme.py').read_text('utf8')
    assert 'Sin evaluación todavía' in theme_file
    assert "correct / attempts" in theme_file
    assert "width = (count / max_count) * 100 if count else 0" in theme_file


def test_ui_has_one_batch_button_no_recent_answers():
    quiz_file = (Path(__file__).parents[1] / 'views/quiz.py').read_text('utf8')
    assert 'Enviar evaluación completa' in quiz_file
    assert 'record_quiz_batch' in quiz_file
    assert 'Últimas respuestas' not in quiz_file
    assert 'quiz_draft' in quiz_file
