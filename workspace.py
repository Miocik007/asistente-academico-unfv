"""Almacenamiento LOCAL por estudiante para documentos preparados y trabajo finalizado.

- Nunca guarda claves API ni contraseñas.
- No acepta rutas de archivos del usuario: usa IDs SHA-256 y directorios segregados.
- Metadatos JSON con reemplazo atómico; índices FAISS sin pickle.
- Para uso local/prototipo académico. Los archivos no están cifrados en disco.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parent / 'data'
ALLOWED = {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.webp'}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_FILES = 10
MAX_DOCUMENT_TEXT_BYTES = 40 * 1024 * 1024


def user_dir(username: str) -> Path:
    if not username or not isinstance(username, str):
        raise ValueError('Usuario obligatorio para guardar documentos')
    user_hash = hashlib.sha256(username.encode('utf-8')).hexdigest()
    base = ROOT / ('student_' + user_hash)
    base.mkdir(parents=True, exist_ok=True)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    return base


def _atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.unfv_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _json_write(path: Path, value):
    _atomic_write(path, json.dumps(value, ensure_ascii=False, default=str).encode('utf-8'))


def _json_read(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (ValueError, OSError, UnicodeError):
        return default


def _clean_filename(name):
    name = str(name).replace('\\', '/').split('/')[-1].strip()
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    return name[:150] or 'archivo'


def staged_list(username):
    rows = _json_read(user_dir(username) / 'staged.json', [])
    if not isinstance(rows, list):
        return []
    valid = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        token = item.get('sha256', '')
        ext = item.get('ext', '')
        if not re.fullmatch(r'[0-9a-f]{64}', token) or ext not in ALLOWED:
            continue
        path = user_dir(username) / 'uploads' / (token + ext)
        if path.is_file() and 0 < path.stat().st_size <= MAX_FILE_BYTES:
            valid.append(item)
    return valid


def stage_uploads(username, files):
    """Guardar selección en cuanto Streamlit notifica un cambio del uploader.

    Es aditivo. Sacar un archivo del widget NO lo elimina de la lista preparada;
    la UI tiene botones específicos para ello.
    """
    existing = staged_list(username)
    known = {(r['sha256'], r['ext']) for r in existing}
    new_rows = []
    for f in files or []:
        name = _clean_filename(getattr(f, 'name', 'archivo'))
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED:
            raise ValueError(f'Formato no admitido: {ext}')
        value = f.getvalue() if hasattr(f, 'getvalue') else f.read()
        if not value or len(value) > MAX_FILE_BYTES:
            raise ValueError(f'{name}: el archivo debe tener entre 1 byte y 20 MB')
        digest = hashlib.sha256(value).hexdigest()
        if (digest, ext) in known:
            continue
        if len(existing) + len(new_rows) >= MAX_FILES:
            raise ValueError(f'Solo se admiten {MAX_FILES} archivos por lote.')
        new_rows.append(({'name': name, 'sha256': digest, 'ext': ext, 'size': len(value)}, value))
        known.add((digest, ext))
    d = user_dir(username)
    for row, value in new_rows:
        _atomic_write(d / 'uploads' / (row['sha256'] + row['ext']), value)
    existing.extend(row for row, _ in new_rows)
    _json_write(d / 'staged.json', existing)
    return existing


def discard_staged(username, digest):
    rows = staged_list(username)
    keep = [r for r in rows if r['sha256'] != digest]
    _json_write(user_dir(username) / 'staged.json', keep)
    for item in rows:
        if item['sha256'] == digest:
            try:
                (user_dir(username) / 'uploads' / (item['sha256'] + item['ext'])).unlink(missing_ok=True)
            except OSError:
                pass
    return keep


def clear_staged(username):
    for item in staged_list(username):
        discard_staged(username, item['sha256'])
    _json_write(user_dir(username) / 'staged.json', [])


class SavedUpload(io.BytesIO):
    def __init__(self, content, name):
        super().__init__(content)
        self.name = name


def staged_as_files(username):
    files = []
    for item in staged_list(username):
        p = user_dir(username) / 'uploads' / (item['sha256'] + item['ext'])
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('La integridad de un documento preparado no coincide.')
        files.append(SavedUpload(data, item['name']))
    return files


def save_processed(username, *, material_hash, process_fingerprint, pages, report,
                   warnings, names, ocr_mode, max_ocr_pages):
    payload = {
        'version': 1,
        'material_hash': material_hash,
        'process_fingerprint': process_fingerprint,
        'pages': pages,
        'report': report,
        'warnings': warnings,
        'names': names,
        'ocr_mode': ocr_mode,
        'max_ocr_pages': max_ocr_pages,
    }
    data = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
    if len(data) > MAX_DOCUMENT_TEXT_BYTES:
        raise ValueError('El texto extraído supera el máximo de almacenamiento local (40 MB).')
    _atomic_write(user_dir(username) / 'processed.json', data)


def load_processed(username):
    data = _json_read(user_dir(username) / 'processed.json', None)
    if not isinstance(data, dict) or data.get('version') != 1:
        return None
    if not re.fullmatch(r'[0-9a-f]{64}', str(data.get('material_hash', ''))):
        return None
    if not isinstance(data.get('pages'), list) or not isinstance(data.get('names'), list):
        return None
    return data


def save_index(username, material_hash, vector_store):
    """Persistir FAISS SIN deserialización insegura de pickle.

    Guarda un índice binario y los documentos en JSON. Solo se carga desde el
    directorio privado creado por la app, nunca desde archivos subidos.
    """
    import faiss
    d = user_dir(username)
    raw_meta = {
        'material_hash': material_hash,
        'mapping': {str(k): v for k, v in vector_store.index_to_docstore_id.items()},
        'documents': {},
    }
    for uid in vector_store.index_to_docstore_id.values():
        doc = vector_store.docstore.search(uid)
        if not hasattr(doc, 'page_content'):
            raise ValueError('Documento no disponible en el índice.')
        raw_meta['documents'][uid] = {'text': doc.page_content, 'metadata': doc.metadata}
    index_path = d / 'material.faiss'
    temp_index = d / 'material.faiss.tmp'
    faiss.write_index(vector_store.index, str(temp_index))
    os.replace(temp_index, index_path)
    _json_write(d / 'index_meta.json', raw_meta)


def load_index(username, material_hash):
    """Cargar índices FAISS app-managed; no utiliza allow_dangerous_deserialization."""
    import faiss
    from langchain_community.docstore.in_memory import InMemoryDocstore
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from rag_engine import get_embeddings

    d = user_dir(username)
    meta = _json_read(d / 'index_meta.json', None)
    if not isinstance(meta, dict) or meta.get('material_hash') != material_hash:
        return None
    mapping = meta.get('mapping')
    docs = meta.get('documents')
    if not isinstance(mapping, dict) or not isinstance(docs, dict):
        return None
    index_path = d / 'material.faiss'
    if not index_path.exists():
        return None
    faiss_index = faiss.read_index(str(index_path))
    ids = {int(k): str(v) for k, v in mapping.items()}
    if sorted(ids) != list(range(faiss_index.ntotal)) or set(ids.values()) != set(docs):
        raise ValueError('El índice guardado está incompleto.')
    doc_store = InMemoryDocstore({uid: Document(page_content=item['text'],
                                  metadata=item.get('metadata') or {}) for uid, item in docs.items()})
    return FAISS(embedding_function=get_embeddings(), index=faiss_index,
                 docstore=doc_store, index_to_docstore_id=ids)


def clear_processed(username):
    d = user_dir(username)
    for name in ('processed.json', 'material.faiss', 'material.faiss.tmp', 'index_meta.json',
                 'conversation.json', 'study_plan.json', 'quiz_draft.json'):
        (d / name).unlink(missing_ok=True)


def save_conversation(username, messages):
    clean = []
    for msg in messages[-100:]:
        if msg.get('pending'):
            continue  # Una llamada en vuelo no es una respuesta final.
        clean.append({k: msg.get(k) for k in ('question', 'answer', 'topic', 'sources',
                                               'intent', 'confidence', 'revised', 'log')})
    _json_write(user_dir(username) / 'conversation.json', clean)


def load_conversation(username):
    data = _json_read(user_dir(username) / 'conversation.json', [])
    return [m for m in data if isinstance(m, dict) and m.get('question') and m.get('answer')] if isinstance(data, list) else []


def save_plan(username, plan, signature):
    _json_write(user_dir(username) / 'study_plan.json', {'text': str(plan), 'signature': signature})


def load_plan(username):
    data = _json_read(user_dir(username) / 'study_plan.json', {})
    return data if isinstance(data, dict) else {}


def save_quiz_draft(username, answers):
    # Se almacenan solo selecciones y solo localmente; NO respuestas correctas.
    values = {str(k): int(v) for k, v in answers.items() if type(v) is int and 0 <= v < 4}
    _json_write(user_dir(username) / 'quiz_draft.json', values)


def load_quiz_draft(username):
    data = _json_read(user_dir(username) / 'quiz_draft.json', {})
    if not isinstance(data, dict):
        return {}
    return {int(k): int(v) for k, v in data.items() if str(k).isdigit() and type(v) is int and 0 <= v < 4}


def clear_learning_artifacts(username):
    d = user_dir(username)
    for name in ('conversation.json', 'study_plan.json', 'quiz_draft.json'):
        (d / name).unlink(missing_ok=True)


class StudentOCRCache:
    """Caché OCR del SQLite del usuario, accesible desde un hilo sin Streamlit."""
    def __init__(self, username):
        import sqlite3
        digest = hashlib.sha256(username.encode('utf-8')).hexdigest()
        self.path = ROOT / f'student_{digest}.db'
        # La base principal y la tabla son creadas por db.init_db en el hilo UI.

    def ocr_cache_get(self, file_hash, page):
        import sqlite3
        with sqlite3.connect(str(self.path), timeout=30) as conn:
            row = conn.execute('SELECT text,method FROM ocr_cache '
                               'WHERE file_hash=? AND page=?', (file_hash, page)).fetchone()
        return tuple(row) if row else None

    def ocr_cache_put(self, file_hash, page, text, method):
        import sqlite3
        from datetime import datetime
        with sqlite3.connect(str(self.path), timeout=30) as conn:
            conn.execute('INSERT OR REPLACE INTO ocr_cache '
                         '(file_hash,page,text,method,created_at) VALUES (?,?,?,?,?)',
                         (file_hash, page, text, method, datetime.now().isoformat()))
