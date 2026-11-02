# Respuesta a las observaciones del docente

## 1. Público objetivo y alcance

**Estudiantes universitarios de pregrado de la Universidad Nacional Federico Villarreal (UNFV)**. El aplicativo se centra en documentación académica propia, definición de conceptos, comparación de teorías, cuestionarios y hábitos de estudio. No se dirige a menores escolares ni ofrece asesoría profesional definitiva.

Implementado en: `agents.py` (`ACADEMIC_RULES`), `views/settings.py`, `auth.py`.

## 2. Restricción de alucinación

- El Orquestador recupera fragmentos numerados `[1]`...`[n]` desde FAISS y la búsqueda léxica.
- El Tutor recibe un bloque único de reglas: acotar fuentes, no inventar bibliografía y considerar el contenido no confiable frente a inyecciones de prompt.
- Gemini audita las respuestas producidas por NVIDIA. Se valida también que al menos una cita exista y que sus IDs estén entre los fragmentos recuperados.
- Si la auditoría falla, se intenta una única corrección; si no supera el nuevo control, no se entrega como verificada.
- Cada pregunta de quiz debe tener cuatro opciones únicas, respuesta y explicación. Un modelo independiente valida las claves; si no valida, se descarta.
- Limitación: dos LLM pueden equivocarse juntos; la puntuación del Verificador no mide por sí sola la verdad. Es necesario revisión humana y evaluación externa.

## 3. API adicional + pruebas

Se emplea NVIDIA Nemotron 3 Ultra (generación), con API gratuita para prototipado sujeta a condiciones, y Gemini 3.8 Flash (verificación y visión) con su propia cuota/posible facturación. El modelo NVIDIA de esta integración es **solo texto**; no se usó incorrectamente para imágenes.

`tests/test_project.py` cubre validación, abstenciones, claves, almacenamiento, material, Word y caché OCR. `evaluacion/casos_30.json` organiza preguntas con evidencia, preguntas fuera del material, fuera del ámbito académico, intentos de inyección y preguntas ambiguas. `tools/evaluate_live.py` produce un CSV de resultados al correrlo con las claves reales. No se incluyen resultados de API simulados como si fueran reales.

## Limitaciones pendientes para una futura versión institucional

- Probar cuantitativamente exactitud factual, recall del índice, falsas abstenciones, latencia y cuota con documentos reales de la UNFV.
- Validar contra datos internos con revisión legal de privacidad y tratamiento de información antes de desplegar.
- Sustituir autenticación demo por identidad institucional (SSO), HTTPS, gestión de sesiones, límites de tasa persistentes, almacenamiento cifrado y pruebas externas de penetración.
- Versionar dependencias en un lockfile del entorno definitivo y crear CI.
- Comprobar manualmente UI y OCR real bajo Windows con ambas API Keys activas.
