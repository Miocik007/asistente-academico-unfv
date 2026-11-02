"""Conmutación segura para el verificador de texto (nunca para OCR/visión).

429 de Gemini => enfriamiento temporal compartido por proceso. En el siguiente
intento se prueba el verificador alternativo NVIDIA y, si ese modelo no está
habilitado en la cuenta, NVIDIA principal. La aplicación siempre revela el
proveedor utilizado. No garantiza verdad ni independencia de proveedor.
"""
import threading
import time

_COOLDOWN_SECONDS = 600
_lock = threading.Lock()
_primary_cooldown_until = 0.0


def quota_error(exc):
    message = str(exc).lower()
    return any(term in message for term in (
        'resource_exhausted', 'rate_limit', 'rate limit', 'quota',
        '429', 'too many requests',
    ))


def cooldown_remaining(now=None):
    with _lock:
        return max(0, _primary_cooldown_until - (time.time() if now is None else now))


def mark_quota_exhausted(now=None):
    global _primary_cooldown_until
    with _lock:
        _primary_cooldown_until = max(_primary_cooldown_until,
                                      (time.time() if now is None else now) + _COOLDOWN_SECONDS)


class TextVerifierFailover:
    """Interfaz compatible con .invoke de LangChain; no admite imágenes."""

    def __init__(self, gemini, nvidia_secondary, nvidia_primary=None):
        self.gemini = gemini
        self.nvidia_secondary = nvidia_secondary
        self.nvidia_primary = nvidia_primary
        self.last_provider = None
        self.used_fallback = False

    def invoke(self, prompt, *args, **kwargs):
        self.last_provider = None
        self.used_fallback = False
        if not cooldown_remaining():
            try:
                response = self.gemini.invoke(prompt, *args, **kwargs)
                self.last_provider = 'Gemini'
                return response
            except Exception as exc:
                # Errores de cuota no se reintentan inmediatamente.
                if quota_error(exc):
                    mark_quota_exhausted()
                else:
                    # Credenciales erróneas, bloqueos, etc.: respaldo también,
                    # pero sin suponer que es una cuota de Gemini.
                    pass

        self.used_fallback = True
        last_error = None
        for name, model in (
            ('NVIDIA alternativo', self.nvidia_secondary),
            ('NVIDIA principal', self.nvidia_primary),
        ):
            if model is None:
                continue
            try:
                response = model.invoke(prompt, *args, **kwargs)
                self.last_provider = name
                return response
            except Exception as exc:
                last_error = exc
        raise RuntimeError('No fue posible verificar la evidencia con Gemini ni NVIDIA.') from last_error
