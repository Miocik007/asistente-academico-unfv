"""
Ingesta de documentos con OCR.

Convierte lo que sube el usuario (PDFs con texto, PDFs escaneados, fotos o
capturas de apuntes) en una lista de páginas de texto, cada una con su
archivo de origen, número de página y método de extracción.

Estrategia por página (modo "auto"):
  1. Se intenta leer el texto nativo del PDF.
  2. Si la página no tiene texto útil (típico de un escaneo) o el texto está
     corrupto, se renderiza como imagen y se transcribe con visión de Gemini
     (el mismo modelo/API key que ya usa la app, sin instalar nada extra).
  3. Si Gemini falla en una página y existe Tesseract en el sistema, se usa
     como respaldo local.

Los resultados del OCR se guardan en caché (SQLite) con el hash del archivo,
así que volver a procesar el mismo documento no vuelve a gastar cuota.

Este módulo no depende de Streamlit ni de LangChain: el LLM es cualquier
objeto con ``.invoke(mensajes)`` (como ChatGoogleGenerativeAI).
"""

import base64
import hashlib
import io
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

MIN_CHARS_PER_PAGE = 40          # menos que esto => se considera página sin texto
RENDER_SCALE = 2.2               # ~160 dpi: buen equilibrio legibilidad/peso
MAX_SIDE_PX = 2000               # lado máximo de la imagen enviada al modelo
JPEG_QUALITY = 85
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_EXTS = IMAGE_EXTS | {'.pdf', '.docx'}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_FILE_COUNT = 10

METHOD_TEXT = "texto"
METHOD_OCR = "ocr"
METHOD_OCR_LOCAL = "ocr-local"
METHOD_EMPTY = "vacía"
METHOD_SKIPPED = "omitida"

OCR_PROMPT = (
    "Eres un motor de OCR. Transcribe fielmente TODO el texto visible en esta "
    "imagen de una página de documento académico, en el idioma original "
    "(normalmente español).\n"
    "Reglas:\n"
    "- Respeta el orden de lectura, los párrafos, títulos y listas.\n"
    "- Si hay tablas, devuélvelas como tablas markdown.\n"
    "- Fórmulas: escríbelas en texto plano o LaTeX simple.\n"
    "- No resumas, no traduzcas, no corrijas, no agregues comentarios.\n"
    "- Si una palabra es ilegible escribe [ilegible]; no inventes texto.\n"
    "- Ignora números de página sueltos y marcas de agua.\n"
    "- Si la imagen no contiene texto, responde exactamente: [SIN TEXTO]\n"
    "Devuelve ÚNICAMENTE la transcripción."
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _file_name(f):
    return getattr(f, "name", None) or "documento"


def _file_bytes(f):
    if hasattr(f, "getvalue"):
        return f.getvalue()
    data = f.read()
    try:
        f.seek(0)
    except Exception:
        pass
    return data


def _clean(text):
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _has_useful_text(text):
    """True si el texto nativo parece texto real (no vacío ni corrupto)."""
    t = _clean(text)
    if len(re.findall(r"\w", t)) < MIN_CHARS_PER_PAGE:
        return False
    # Texto corrupto típico de PDFs mal codificados: muchos "�" o símbolos raros
    bad = t.count("�") + len(re.findall(r"[^\w\s\.,;:¿?¡!\-–—()\[\]\"'%/+=*<>°$€@#&_]", t))
    return bad / max(len(t), 1) < 0.25


def _response_text(response):
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _strip_fences(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _to_jpeg_bytes(pil_image):
    img = pil_image.convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > MAX_SIDE_PX:
        ratio = MAX_SIDE_PX / longest
        img = img.resize((int(w * ratio), int(h * ratio)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Motores de OCR
# ---------------------------------------------------------------------------

def _tesseract_path():
    """Detecta Tesseract, incluso si su instalación Windows no agregó PATH."""
    locations = [os.environ.get('TESSERACT_CMD'), shutil.which('tesseract')]
    for base in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')):
        if base:
            locations.append(os.path.join(base, 'Tesseract-OCR', 'tesseract.exe'))
    for path in locations:
        if path and os.path.isfile(path):
            return path
    return None


def tesseract_available():
    executable = _tesseract_path()
    if executable is None:
        return False
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = executable
        return True
    except Exception:
        return False


def _ocr_tesseract(jpeg_bytes):
    import pytesseract
    from PIL import Image

    lang = "eng"
    try:
        langs = set(pytesseract.get_languages(config=""))
        if "spa" in langs and "eng" in langs:
            lang = "spa+eng"
        elif "spa" in langs:
            lang = "spa"
    except Exception:
        pass
    img = Image.open(io.BytesIO(jpeg_bytes))
    return _clean(pytesseract.image_to_string(img, lang=lang))


def _ocr_llm(llm, jpeg_bytes, retries=1):
    """Transcribe una imagen con un LLM multimodal (Gemini). Reintenta con
    espera creciente ante límites de cuota o errores transitorios."""
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    message = [{
        "role": "user",
        "content": [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ],
    }]
    last_exc = None
    for attempt in range(retries + 1):
        try:
            text = _strip_fences(_response_text(llm.invoke(message)))
            if text.strip().upper().startswith("[SIN TEXTO]"):
                return ""
            return _clean(text)
        except Exception as exc:  # cuota, red, contenido bloqueado...
            last_exc = exc
            from llm_resilience import quota_error, mark_quota_exhausted
            if quota_error(exc):
                mark_quota_exhausted()
                break  # no insistir cuando el proveedor indica cuota agotada
            if attempt < retries:
                time.sleep(1.5 * (2 ** attempt))
    raise last_exc


def _ocr_page(llm, jpeg_bytes, allow_local=True, engine="auto"):
    """Gemini para visión; si hay cuota agotada, Tesseract local como respaldo.

    Nemotron 3 Ultra es SOLO texto: nunca se le envía la imagen del usuario.
    """
    from llm_resilience import cooldown_remaining
    if engine not in ('auto', 'local', 'gemini'):
        raise ValueError('Motor OCR inválido.')
    local_ok = allow_local and tesseract_available()
    if engine == 'local':
        if local_ok:
            return _ocr_tesseract(jpeg_bytes), METHOD_OCR_LOCAL
        raise RuntimeError('Tesseract OCR local no está instalado o no se detecta. '
                           'Instálalo y reinicia la aplicación, o elige OCR automático.')
    if engine == 'gemini':
        if llm is None:
            raise RuntimeError('Gemini no está configurado para OCR.')
        return _ocr_llm(llm, jpeg_bytes), METHOD_OCR
    if cooldown_remaining():
        if local_ok:
            return _ocr_tesseract(jpeg_bytes), METHOD_OCR_LOCAL
        raise RuntimeError('Gemini agotó la cuota de OCR. Las páginas sin texto no pudieron leerse. '
                           'Reintenta tras renovar la cuota o instala Tesseract OCR.')
    if llm is not None:
        try:
            return _ocr_llm(llm, jpeg_bytes), METHOD_OCR
        except Exception as exc:
            if not local_ok:
                from llm_resilience import quota_error
                if quota_error(exc):
                    raise RuntimeError('Gemini agotó la cuota de OCR (429). '
                                       'Reintenta más tarde o instala Tesseract OCR.') from exc
                raise RuntimeError(f'OCR con Gemini falló ({type(exc).__name__}).') from exc
    if local_ok:
        return _ocr_tesseract(jpeg_bytes), METHOD_OCR_LOCAL
    raise RuntimeError('No hay motor de OCR disponible (sin Gemini ni Tesseract).')


# ---------------------------------------------------------------------------
# Lectura de PDFs
# ---------------------------------------------------------------------------

def _native_texts(data):
    """Texto nativo de cada página. Devuelve lista de str (puede haber '')."""
    texts = None
    reader_cls = None
    try:
        from PyPDF2 import PdfReader as reader_cls  # dependencia original
    except Exception:
        try:
            from pypdf import PdfReader as reader_cls
        except Exception:
            reader_cls = None

    if reader_cls is not None:
        try:
            reader = reader_cls(io.BytesIO(data))
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            texts = []
            for page in reader.pages:
                try:
                    texts.append(page.extract_text() or "")
                except Exception:
                    texts.append("")
        except Exception:
            texts = None

    # Respaldo / complemento con pdfium para páginas vacías
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        n = len(pdf)
        if texts is None or len(texts) != n:
            texts = [""] * n
        for i in range(n):
            if not _has_useful_text(texts[i]):
                try:
                    tp = pdf[i].get_textpage()
                    alt = tp.get_text_range() or ""
                    if len(alt.strip()) > len(texts[i].strip()):
                        texts[i] = alt
                except Exception:
                    pass
        pdf.close()
    except Exception:
        if texts is None:
            raise
    return texts


def _render_pdf_page(pdf, index):
    page = pdf[index]
    bitmap = page.render(scale=RENDER_SCALE)
    return _to_jpeg_bytes(bitmap.to_pil())


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def ingest_files(files, llm=None, mode="auto", max_ocr_pages=60,
                 progress=None, cache=None, workers=2, engine="auto"):
    """Extrae el texto de PDFs e imágenes, aplicando OCR donde haga falta.

    files:         objetos tipo UploadedFile (name + getvalue()/read()).
    llm:           modelo multimodal para el OCR (opcional).
    mode:          "auto" (OCR solo en páginas sin texto), "force" (OCR en
                   todas las páginas) u "off" (nunca).
    max_ocr_pages: tope de páginas a transcribir en total (control de cuota).
    progress:      callback progress(hechas, total, mensaje).
    cache:         objeto con ocr_cache_get(hash, page) / ocr_cache_put(hash,
                   page, text, method) para no repetir OCR.
    engine:        "auto" (Gemini con respaldo Tesseract), "local" (solo
                   Tesseract), "gemini" (solo Gemini).

    Devuelve dict: {"pages": [...], "report": [...], "warnings": [...]}
      pages  -> [{"source","page","text","method"}]
      report -> un dict por archivo con conteos por método.
    """
    pages_out = []
    report = []
    warnings = []
    ocr_budget = max(0, int(max_ocr_pages))
    ocr_tasks = []   # (slot_en_pages_out, jpeg_bytes, file_hash, page_no)

    def note(done, total, msg):
        if progress:
            try:
                progress(done, total, msg)
            except Exception:
                pass

    total_files = len(files)
    if total_files > MAX_FILE_COUNT:
        raise ValueError(f'Máximo {MAX_FILE_COUNT} archivos por lote.')
    for fi, f in enumerate(files):
        name = _file_name(f)
        ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
        if ext not in ALLOWED_EXTS:
            raise ValueError(f'Formato no admitido: {ext}.')
        data = _file_bytes(f)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(f'El archivo {name} supera 20 MB.')
        fhash = hashlib.sha256(data).hexdigest()[:32]
        rep = {"archivo": name, "paginas": 0, "texto": 0, "ocr": 0,
               "ocr_local": 0, "vacias": 0, "omitidas": 0, "errores": 0,
               "caracteres": 0}
        note(fi, total_files, f"Leyendo {name}…")

        # --------------------------- Word DOCX --------------------------
        if ext == '.docx':
            try:
                from docx import Document
                doc = Document(io.BytesIO(data))
                parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                for table in doc.tables:
                    for row in table.rows:
                        parts.append(' | '.join(cell.text.strip() for cell in row.cells))
                doc_text = _clean('\n'.join(parts))
                rep['paginas'] = 1  # DOCX no posee paginación estable sin renderizar
                pages_out.append({'source': name, 'page': None, 'text': doc_text,
                                  'method': METHOD_TEXT if doc_text else METHOD_EMPTY})
                if not doc_text:
                    warnings.append(f'{name}: Word sin texto legible; revisa si contiene imágenes.')
            except Exception:
                rep['errores'] += 1
                warnings.append(f'{name}: no se pudo extraer texto de Word; verifica el archivo.')
            report.append(rep)
            continue

        # ------------------------- imagen suelta -------------------------
        if ext in IMAGE_EXTS:
            rep["paginas"] = 1
            if mode == "off":
                rep["omitidas"] += 1
                warnings.append(f"{name}: es una imagen y el OCR está desactivado.")
                pages_out.append({"source": name, "page": 1, "text": "", "method": METHOD_SKIPPED})
            else:
                if cache is not None:
                    hit = cache.ocr_cache_get(fhash, 1)
                    if hit is not None:
                        txt, method = hit
                        pages_out.append({'source': name, 'page': 1, 'text': txt, 'method': method})
                        report.append(rep)
                        continue
                try:
                    from PIL import Image
                    jpeg = _to_jpeg_bytes(Image.open(io.BytesIO(data)))
                except Exception as exc:
                    rep["errores"] += 1
                    warnings.append(f"{name}: no se pudo abrir la imagen ({exc}).")
                    pages_out.append({"source": name, "page": 1, "text": "", "method": METHOD_EMPTY})
                    report.append(rep)
                    continue
                slot = len(pages_out)
                pages_out.append({"source": name, "page": 1, "text": "", "method": METHOD_EMPTY})
                if ocr_budget > 0:
                    ocr_budget -= 1
                    ocr_tasks.append((slot, jpeg, fhash, 1))
                else:
                    rep["omitidas"] += 1
                    pages_out[slot]["method"] = METHOD_SKIPPED
                    warnings.append(f"{name}: se alcanzó el máximo de páginas con OCR.")
            report.append(rep)
            continue

        # ------------------------------ PDF ------------------------------
        try:
            native = _native_texts(data)
        except Exception as exc:
            rep["errores"] += 1
            warnings.append(f"{name}: no se pudo leer el PDF ({exc}).")
            report.append(rep)
            continue

        rep["paginas"] = len(native)
        pdf_doc = None
        for pno, raw in enumerate(native, start=1):
            has_text = _has_useful_text(raw)
            needs_ocr = (mode == "force") or (mode == "auto" and not has_text)

            if not needs_ocr:
                if has_text:
                    pages_out.append({"source": name, "page": pno, "text": _clean(raw), "method": METHOD_TEXT})
                else:
                    pages_out.append({"source": name, "page": pno, "text": "", "method": METHOD_EMPTY})
                continue

            # ¿ya está en caché?
            if cache is not None:
                hit = cache.ocr_cache_get(fhash, pno)
                if hit is not None:
                    text, method = hit
                    pages_out.append({"source": name, "page": pno, "text": text, "method": method})
                    continue

            if ocr_budget <= 0:
                rep["omitidas"] += 1
                pages_out.append({"source": name, "page": pno,
                                  "text": _clean(raw) if has_text else "",
                                  "method": METHOD_TEXT if has_text else METHOD_SKIPPED})
                continue

            try:
                if pdf_doc is None:
                    import pypdfium2 as pdfium
                    pdf_doc = pdfium.PdfDocument(data)
                jpeg = _render_pdf_page(pdf_doc, pno - 1)
            except Exception as exc:
                rep["errores"] += 1
                warnings.append(f"{name} p.{pno}: no se pudo convertir a imagen ({exc}).")
                pages_out.append({"source": name, "page": pno,
                                  "text": _clean(raw) if has_text else "",
                                  "method": METHOD_TEXT if has_text else METHOD_EMPTY})
                continue

            ocr_budget -= 1
            slot = len(pages_out)
            pages_out.append({"source": name, "page": pno, "text": _clean(raw) if has_text else "",
                              "method": METHOD_TEXT if has_text else METHOD_EMPTY})
            ocr_tasks.append((slot, jpeg, fhash, pno))

        if pdf_doc is not None:
            try:
                pdf_doc.close()
            except Exception:
                pass
        report.append(rep)

    # ---------------------- ejecutar el OCR pendiente ----------------------
    if ocr_tasks:
        total = len(ocr_tasks)
        done = 0
        note(0, total, f"Aplicando OCR a {total} página(s)…")
        rep_by_name = {r["archivo"]: r for r in report}

        def work(task):
            slot, jpeg, fhash, pno = task
            text, method = _ocr_page(llm, jpeg, engine=engine)
            return slot, fhash, pno, text, method

        with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
            futures = {pool.submit(work, t): t for t in ocr_tasks}
            for fut in as_completed(futures):
                slot, jpeg, fhash, pno = futures[fut]
                entry = pages_out[slot]
                try:
                    _slot, _h, _p, text, method = fut.result()
                    if text.strip():
                        entry["text"] = text
                        entry["method"] = method
                        if cache is not None:
                            try:
                                cache.ocr_cache_put(fhash, pno, text, method)
                            except Exception:
                                pass
                    elif entry["method"] != METHOD_TEXT:
                        entry["method"] = METHOD_EMPTY
                except Exception as exc:
                    r = rep_by_name.get(entry["source"])
                    if r is not None:
                        r["errores"] += 1
                    warnings.append(f"{entry['source']} p.{entry['page']}: {exc}")
                done += 1
                note(done, total, f"OCR {done}/{total}")

    # ------------------------------ conteos ------------------------------
    rep_by_name = {r["archivo"]: r for r in report}
    for p in pages_out:
        r = rep_by_name.get(p["source"])
        if r is None:
            continue
        m = p["method"]
        if m == METHOD_TEXT:
            r["texto"] += 1
        elif m == METHOD_OCR:
            r["ocr"] += 1
        elif m == METHOD_OCR_LOCAL:
            r["ocr_local"] += 1
        elif m == METHOD_EMPTY:
            r["vacias"] += 1
        r["caracteres"] += len(p["text"])
    for r in report:
        if r["omitidas"] and mode != "off":
            warnings.append(
                f"{r['archivo']}: {r['omitidas']} página(s) sin OCR por el límite "
                f"de páginas; sube el máximo en Configuración para incluirlas."
            )

    return {"pages": pages_out, "report": report, "warnings": warnings}


def pages_to_text(pages):
    """Une el texto de todas las páginas (para muestreo de temas, etc.)."""
    return "\n".join(p["text"] for p in pages if p.get("text"))
