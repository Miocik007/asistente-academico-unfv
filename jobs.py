"""Tareas de IA independientes de las páginas Streamlit.

Se ejecutan en un conjunto acotado de hilos; LOS HILOS NO acceden a
st.session_state ni a la base de datos. Solo la sesión dueña publica resultados.
Esto permite cambiar de sección mientras NVIDIA/Gemini termina una llamada.
No persiste entre reinicios del servidor, cierre de pestaña o sesión nueva.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import RLock
import time
import uuid
import streamlit as st
import workspace


@dataclass
class Job:
    future: object
    kind: str
    metadata: dict
    started: float


class JobRegistry:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="unfv-agent")
        self.lock = RLock()
        self.tasks = {}

    def submit(self, session, kind, func, metadata=None):
        key = (session, kind)
        with self.lock:
            previous = self.tasks.get(key)
            if previous is not None:
                return False
            self.tasks[key] = Job(self.executor.submit(func), kind, metadata or {}, time.time())
            return True

    def active(self, session, kind=None):
        with self.lock:
            return [job for (sid, k), job in self.tasks.items()
                    if sid == session and (kind is None or kind == k)]

    def pop_ready(self, session):
        with self.lock:
            items = []
            for key, job in list(self.tasks.items()):
                if key[0] == session and job.future.done():
                    items.append(job)
                    del self.tasks[key]
            return items

    def discard(self, session):
        with self.lock:
            for key, job in list(self.tasks.items()):
                if key[0] == session:
                    job.future.cancel()
                    del self.tasks[key]


@st.cache_resource(show_spinner=False)
def registry():
    return JobRegistry()


def ensure_session():
    if '_unfv_job_session' not in st.session_state:
        st.session_state['_unfv_job_session'] = uuid.uuid4().hex
    return st.session_state['_unfv_job_session']


def start(kind, func, metadata=None):
    return registry().submit(ensure_session(), kind, func, metadata)


def running(kind=None):
    return bool(registry().active(ensure_session(), kind))


def harvest():
    """Se llama en el hilo principal; todas las escrituras a BD ocurren aquí."""
    import db
    changed = False
    for job in registry().pop_ready(ensure_session()):
        changed = True
        try:
            result = job.future.result()
            if job.kind == 'chat':
                if db.current_material_hash() != job.metadata.get('material_hash'):
                    continue
                msg = result
                for old in st.session_state.chat_messages:
                    if old.get('job_id') == job.metadata['job_id']:
                        old.update(msg)
                        old.pop('pending', None)
                        old.pop('job_id', None)
                        break
                # Guardar cada respuesta TERMINADA de inmediato, no solo al salir.
                workspace.save_conversation(st.session_state.student_id,
                                            st.session_state.chat_messages)
                if msg.get('log'):
                    db.ensure_topics([msg['topic']])
                    db.log_question(msg['question'], msg['answer'], msg['topic'],
                                    ', '.join(st.session_state.pdf_names),
                                    st.session_state.threshold)
                try:
                    db.save_agent_run('chat', msg['question'], msg['topic'],
                                      msg.get('intent'), msg.get('confidence'),
                                      msg.get('revised'), msg.get('total_ms'), msg.get('trace') or [])
                except Exception:
                    pass
            elif job.kind == 'ingest':
                if st.session_state.get('student_id') != job.metadata.get('student_id'):
                    continue
                from views import settings
                import state
                settings._complete_documents_from_result(
                    result,
                    job.metadata['files'],
                    state.get_current_llm(),
                    process_fingerprint=job.metadata['process_fingerprint'],
                    ocr_mode=job.metadata.get('ocr_mode'),
                    max_ocr_pages=job.metadata.get('max_ocr_pages'),
                )
            elif job.kind == 'topics':
                if db.current_material_hash() != job.metadata.get('material_hash'):
                    continue
                if result:
                    db.ensure_topics(result)
                    st.session_state.active_topics = list(result)
                    st.session_state.process_notice = f'Temas identificados: {len(result)}. Ya puedes crear evaluaciones.'
                else:
                    st.session_state.process_notice = 'Documentos listos; no se detectaron temas automáticamente.'
            elif job.kind == 'quiz':
                # No guardar quizzes para material que ya cambió.
                if db.current_material_hash() != job.metadata.get('material_hash'):
                    st.session_state.quiz_notice = 'El material cambió; se descartó el quiz anterior.'
                    continue
                created = dropped = 0
                for topic, questions, trace, summary in result:
                    if questions and not db.has_pending_quiz_for_topic(topic):
                        db.save_quiz_questions(topic, questions)
                        created += len(questions)
                    dropped += summary.get('dropped', 0)
                    try:
                        db.save_agent_run('quiz', f'Quiz: {topic}', topic, 'quiz',
                                          None, False, sum(x.get('ms', 0) for x in trace), trace)
                    except Exception:
                        pass
                st.session_state.quiz_notice = (
                    f'{created} pregunta(s) nuevas preparadas; {dropped} descartadas por la verificación.'
                    if created else 'No se validaron preguntas. Revisa la disponibilidad de Gemini y NVIDIA en «Sistema multiagente». Si agotaste la cuota, vuelve a intentar más tarde; no se publican claves sin verificar.'
                )
        except Exception as exc:
            if job.kind == 'chat':
                import agents
                for msg in st.session_state.chat_messages:
                    if msg.get('job_id') == job.metadata.get('job_id'):
                        msg.update({'answer': agents.NOT_AVAILABLE, 'log': False,
                                    'topic': 'General', 'sources': [], 'trace': [],
                                    'pending': False})
                        msg.pop('job_id', None)
            if job.kind == 'chat':
                workspace.save_conversation(st.session_state.student_id,
                                            st.session_state.chat_messages)
            if job.kind == 'ingest':
                from processing_diagnostics import user_ingest_error
                st.session_state.process_notice = 'No terminó la lectura: ' + user_ingest_error(exc)
                # El diagnóstico completo se conserva solo en la terminal del servidor.
                import logging
                logging.getLogger(__name__).exception(
                    'Error de procesamiento de documentos (%s)', type(exc).__name__, exc_info=exc)
            st.session_state['job_error'] = (
                f'No se completó {job.kind} ({type(exc).__name__}). Revisa conexión y cuota de las APIs.'
            )
    return changed


@st.fragment(run_every='3s')
def _poll_status():
    if harvest():
        st.rerun()
    tasks = registry().active(ensure_session())
    for task in tasks:
        name = {'chat': 'respuesta', 'quiz': 'evaluación', 'topics': 'temas del material', 'ingest': 'lectura y OCR del material'}.get(task.kind, 'tarea')
        st.caption(f'⏳ Generando {name} en segundo plano…')


def render_status():
    """Poll en barra lateral, compatible con Streamlit 1.43+."""
    with st.sidebar:
        _poll_status()
