"""Pruebas automatizadas SIN consumir APIs ni descargar modelos."""
import io
import json
import sqlite3
import sys
import types
from types import SimpleNamespace

import pytest

import agents
import db
import ingest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    return db


def test_questions_do_not_mark_weak_without_errors(fresh_db):
    db.ensure_topics(['Álgebra'])
    for _ in range(9):
        db.log_question('¿Cómo?', 'Con evidencia', 'Álgebra', 'doc.pdf', 3)
    assert db.get_topic('Álgebra')['status'] == db.STATUS_NUEVO
    assert db.get_weak_topics() == []


def test_quiz_answer_is_idempotent(fresh_db):
    db.ensure_topics(['Cálculo'])
    db.save_quiz_questions('Cálculo', [{'question':'¿2+2?', 'options':['4','3','5','6'],
                                        'correct_index':0, 'explanation':'Dos más dos son cuatro.'}])
    qid = db.get_pending_quiz_questions()[0]['id']
    assert db.record_quiz_answer(qid, 0) is True
    assert db.record_quiz_answer(qid, 0) is None
    assert db.get_topic('Cálculo')['correct_count'] == 1
    assert db.get_topic('Cálculo')['mastery_score'] == 1


def test_wrong_quiz_marks_weak(fresh_db):
    db.ensure_topics(['Física'])
    db.save_quiz_questions('Física',[{'question':'¿Unidad SI de fuerza?',
      'options':['metro','newton','segundo','litro'], 'correct_index':1,
      'explanation':'La unidad de fuerza es el newton.'}])
    qid = db.get_pending_quiz_questions()[0]['id']
    assert db.record_quiz_answer(qid, 0) is False
    assert db.get_topic('Física')['status'] == db.STATUS_DEBIL


def test_invalid_quiz_is_not_saved(fresh_db):
    db.save_quiz_questions('X', [{'question':'Mal','options':['a','b'], 'correct_index':0},
          {'question':'Repetido','options':['a','a','b','c'], 'correct_index':0}])
    assert db.get_pending_quiz_questions() == []


def test_material_switch_clears_learning_not_ocr(fresh_db):
    assert not db.ensure_material_scope('hash-a')
    db.ensure_topics(['Historia'])
    db.ocr_cache_put('image-hash', 1, 'texto', 'ocr')
    assert not db.ensure_material_scope('hash-a')
    assert db.get_topic('Historia') is not None
    assert db.ensure_material_scope('hash-b')
    assert db.get_all_topics() == []
    assert db.ocr_cache_get('image-hash', 1)[0] == 'texto'


def test_reset_deletes_ocr_and_progress(fresh_db):
    db.ensure_topics(['Tema'])
    db.ocr_cache_put('hash',1,'texto','ocr')
    db.reset_all()
    assert db.ocr_cache_get('hash',1) is None
    assert db.get_all_topics() == []


@pytest.mark.parametrize('wrong', [
    None, {}, [{'question':'q','options':['a','b'], 'correct_index':0}],
    [{'question':'q','options':['a','b','a','d'],'correct_index':0}],
    [{'question':'q','options':['a','b','c','d'],'correct_index':9}],
    [{'question':'q','options':['a','b','c','d'],'correct_index':0,'explanation':''}],
    [{'question':'q','options':['a','b','c','d'],'correct_index':'bad','explanation':'x'}],
])
def test_quiz_validator_rejects_invalid(wrong):
    assert agents._validate_questions(wrong) == []


class FakeLLM:
    def __init__(self, answers):
        self.answers = iter(answers)
    def invoke(self, text):
        return SimpleNamespace(content=next(self.answers))


@pytest.fixture
def patch_retrieval(monkeypatch):
    def fake_retrieve(self, vs, queries, final_k=6, per_query=5):
        return [{'n':1,'source':'intro.pdf','page':2,'text':'El agua hierve a 100 °C a presión atmosférica normal.',
                 'method':'texto'}]
    monkeypatch.setattr(agents.RetrieverAgent,'run',fake_retrieve)


def _plan():
    return json.dumps({'intent':'consulta','standalone_question':'¿A qué temperatura hierve el agua?',
                      'sub_queries':['punto ebullición'], 'topic':'Química'})


def _verdict(score, unsupported=None):
    return json.dumps({'score':score,'unsupported':unsupported or [],'verdict':'Auditoría'})


def test_verified_answer_requires_valid_citation(patch_retrieval):
    llm=FakeLLM([_plan(), 'Hierve a 100 °C [1].'])
    verifier=FakeLLM([_verdict(96)])
    res=agents.Orchestrator(llm,None,['Química'],verifier_llm=verifier).answer('¿Agua?')
    assert res.answer.endswith('[1].')
    assert res.verified and res.confidence==96


def test_fake_citation_abstains_even_high_score(patch_retrieval):
    llm=FakeLLM([_plan(), 'Hierve a 100 °C [99].', 'Hierve a 100 °C [99].'])
    verifier=FakeLLM([_verdict(99),_verdict(99)])
    res=agents.Orchestrator(llm,None,['Química'],verifier_llm=verifier).answer('¿Agua?')
    assert res.answer==agents.NOT_AVAILABLE
    assert not res.verified and not res.log


def test_unverified_answer_fails_closed(patch_retrieval):
    llm=FakeLLM([_plan(), 'Hierve a 100 °C [1].','No sé la respuesta [1].'])
    verifier=FakeLLM([_verdict(30,['fuente insuficiente']),_verdict(10,['sin evidencia'])])
    res=agents.Orchestrator(llm,None,['Química'],verifier_llm=verifier).answer('¿Agua?')
    assert res.answer==agents.NOT_AVAILABLE
    assert not res.verified


def test_verifier_error_fails_closed(patch_retrieval):
    llm=FakeLLM([_plan(), 'La respuesta fue inventada [1].', 'Otra respuesta inventada [1].'])
    verifier=FakeLLM(['NO JSON','TAMPOCO JSON'])
    res=agents.Orchestrator(llm,None,['Química'],verifier_llm=verifier).answer('¿Agua?')
    assert res.answer==agents.NOT_AVAILABLE


def test_quiz_rejected_if_solver_disagrees(patch_retrieval):
    questions=[{'question':'¿Agua?','options':['20','40','100','150'],
                'correct_index':2,'explanation':'Se indica 100 °C.'}]
    generator=FakeLLM([json.dumps(questions)])
    verifier=FakeLLM([json.dumps([{'id':0,'answer_index':0,'supported':True}])])
    q, trace, summary=agents.Orchestrator(generator,None,[],verifier_llm=verifier).make_quiz('Química',1)
    assert not q and summary['dropped']==1


def test_quiz_rejected_if_solver_omits_answer(patch_retrieval):
    questions=[{'question':'¿Agua?','options':['20','40','100','150'],
                'correct_index':2,'explanation':'Se indica 100 °C.'}]
    gen=FakeLLM([json.dumps(questions)])
    verifier=FakeLLM(['[]'])
    q, _, summary=agents.Orchestrator(gen,None,[],verifier_llm=verifier).make_quiz('Química',1)
    assert not q and summary['dropped']==1


def test_quiz_rejected_when_solver_says_string_false(patch_retrieval):
    questions=[{'question':'¿Agua?','options':['20','40','100','150'],
                'correct_index':2,'explanation':'Se indica 100 °C.'}]
    gen=FakeLLM([json.dumps(questions)])
    verifier=FakeLLM([json.dumps([{'id':0,'answer_index':2,'supported':'false'}])])
    q, _, summary=agents.Orchestrator(gen,None,[],verifier_llm=verifier).make_quiz('Química',1)
    assert not q


def test_quiz_accepted_only_with_independent_validation(patch_retrieval):
    questions=[{'question':'¿Agua?','options':['20','40','100','150'],
                'correct_index':2,'explanation':'Se indica 100 °C.'}]
    gen=FakeLLM([json.dumps(questions)])
    verifier=FakeLLM([json.dumps([{'id':0,'answer_index':2,'supported':True}])])
    q, _, summary=agents.Orchestrator(gen,None,[],verifier_llm=verifier).make_quiz('Química',1)
    assert len(q)==1 and summary['dropped']==0
    assert q[0]['options'][q[0]['correct_index']]=='100'


def test_docx_ingestion(tmp_path):
    from docx import Document
    doc=Document(); doc.add_heading('Marco teórico'); doc.add_paragraph('Análisis de sistemas de información')
    bio=io.BytesIO(); doc.save(bio)
    up=SimpleNamespace(name='clase.docx', getvalue=lambda: bio.getvalue())
    result=ingest.ingest_files([up], mode='auto')
    assert len(result['pages'])==1
    assert 'Marco teórico' in result['pages'][0]['text']
    assert result['pages'][0]['page'] is None


def test_image_ocr_uses_cache(fresh_db):
    from PIL import Image
    image=Image.new('RGB',(50,50),'white'); bio=io.BytesIO();image.save(bio,format='PNG')
    up=SimpleNamespace(name='apuntes.png',getvalue=lambda: bio.getvalue())
    called=[]
    orig=ingest._ocr_page
    try:
        ingest._ocr_page=lambda llm,jpeg,allow_local=True: (called.append(1) or 'Texto de clase',ingest.METHOD_OCR)
        ingest.ingest_files([up],llm=object(),cache=db)
        ingest.ingest_files([up],llm=object(),cache=db)
        assert len(called)==1
    finally:
        ingest._ocr_page=orig


def test_file_size_limit():
    up=SimpleNamespace(name='gigante.pdf',getvalue=lambda: b'x'*(20*1024*1024+1))
    with pytest.raises(ValueError, match='supera 20 MB'):
        ingest.ingest_files([up],mode='off')


@pytest.mark.parametrize('rule', [
    'PREGRADO', 'UNFV', 'No inventes', 'DATOS NO FIABLES', 'Cita [n]',
    'ignora instrucciones', 'revelar secretos', 'documentos',
    'información', 'universitarios',
])
def test_prompt_injection_guardrails_are_present(rule):
    # Revisa configuración de las reglas, no resistencia real de un modelo.
    assert rule.casefold() in agents.ACADEMIC_RULES.casefold()


def test_exactly_six_original_pages_preserved():
    from pathlib import Path
    app = (Path(__file__).parents[1] / 'app.py').read_text(encoding='utf-8')
    assert app.count('st.Page(') == 6


def test_provider_is_nvidia_with_required_gemini_verifier():
    from pathlib import Path
    state = (Path(__file__).parents[1] / 'state.py').read_text(encoding='utf-8')
    chat = (Path(__file__).parents[1] / 'views' / 'chat.py').read_text(encoding='utf-8')
    assert 'https://integrate.api.nvidia.com/v1' in state
    assert 'nvidia/nemotron-3-ultra-550b-a55b' in state
    assert 'gemini-3.8-flash' in state
    assert 'verifier = state.get_verifier_llm()' in chat
    assert 'verifier_llm=verifier_llm' in chat
