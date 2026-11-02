"""Errores de procesamiento para mostrar mensajes claros sin revelar claves API."""

class DocumentProcessingError(ValueError):
    """Error de lectura/indexado con explicación segura para el estudiante."""


def describe_empty_extraction(result):
    reports = result.get('report') or []
    warnings = result.get('warnings') or []
    pages = sum(int(x.get('paginas', 0)) for x in reports)
    failed = sum(int(x.get('errores', 0)) for x in reports)
    skipped = sum(int(x.get('omitidas', 0)) for x in reports)
    text = ' '.join(str(x).lower() for x in warnings)
    prefix = (f'No se obtuvo texto de ninguna página ({pages} página(s) detectada(s); '
              f'{failed} error(es) de lectura). ')
    if any(s in text for s in ('cuota', '429', 'resource_exhausted')):
        return (prefix + 'Gemini agotó la cuota de OCR y no hubo un motor local disponible. '
                'Instala Tesseract OCR para Windows y selecciona «Tesseract local», '
                'o reintenta cuando se restablezca la cuota de Gemini. '
                'Los archivos preparados siguen guardados.')
    if skipped or 'desactivado' in text:
        return (prefix + 'El OCR está desactivado o se alcanzó el límite de páginas. '
                'Activa OCR automático/local y aumenta el máximo de páginas.')
    if any(s in text for s in ('no hay motor', 'sin gemini ni tesseract')):
        return (prefix + 'No hay un motor OCR disponible. Configura Gemini '
                'o instala Tesseract OCR local.')
    return (prefix + 'Verifica el detalle de lectura: archivo legible, OCR, '
            'idioma y disponibilidad de la API. Los archivos preparados se conservan.')


def user_ingest_error(exc):
    """Devuelve una explicación pública sin copiar errores arbitrarios del proveedor."""
    if isinstance(exc, DocumentProcessingError):
        return str(exc)
    if isinstance(exc, ValueError):
        return ('Se produjo un error de validación durante la lectura o creación '
                'del índice. Revisa el diagnóstico de lectura e inténtalo otra vez. '
                'Los archivos preparados se conservan.')
    return (f'Falló la operación ({type(exc).__name__}). Revisa la conexión, '
            'los modelos instalados y la disponibilidad del OCR. '
            'Los archivos preparados se conservan.')
