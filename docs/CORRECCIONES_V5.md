# Correcciones implementadas — V5

## Incidencia original observada

Gemini devolvía `429 RESOURCE_EXHAUSTED` (cuota agotada), por lo que el verificador y el solucionador fallaban tras múltiples reintentos. El Tutor se abstenía sin distinguir si el PDF realmente carecía de respuesta o si había fallado la API de verificación. Los documentos escaneados podían quedar solo parcialmente transcritos y, sin un indicador de cobertura, el usuario no sabía cuántas páginas estaban disponibles para RAG.

## Cambios y alcance

1. `llm_resilience.py`: interruptor temporal de cuota + respaldo NVIDIA para **verificación de texto** (no para OCR).
2. `state.py`: Gemini con reintentos deshabilitados y timeout configurado; verificador NVIDIA 3.5 Lightning como respaldo, luego Nemotron 3 Ultra si fuese necesario.
3. `agents.py`: proveedor de la auditoría registrado en la traza, ampliación léxica de búsqueda, mensaje de API de verificación no disponible separado del mensaje de información ausente.
4. `ingest.py`: fallo rápido ante 429; OCR Tesseract como alternativa **local** si está instalado; no fabrica transcripciones.
5. `views/settings.py`: indicador de páginas reconocidas y visor local del texto por página para diagnóstico.
6. `views/chat.py`: advertencia si el OCR fue parcial y atribución visible del proveedor verificador.
7. `theme.py` y `assets/unfv_wordmark.png`: membrete de universidad en parte superior de la barra lateral.
8. `tests/test_v5_quota_ocr.py`: pruebas simuladas de cuota, respaldo, quizzes y OCR.

## Límites importantes para la exposición

- NVIDIA Ultra no analiza imágenes en esta integración; Gemini o Tesseract se necesitan para convertir el PDF escaneado en texto. Si Gemini agotó la cuota y Tesseract no está instalado, no se pueden recuperar nuevas páginas hasta que el OCR vuelva a funcionar.
- Un segundo modelo NVIDIA reduce el punto único de fallo, pero no es totalmente independiente cuando el tutor también usa NVIDIA. Ninguna auditoría de IA garantiza cero alucinaciones.
- Se comprobó que el código Python compila y se hicieron pruebas de unidad simulando las APIs. **La integración real de NVIDIA y Gemini debe probarse con claves válidas del usuario.**
- El almacenamiento local por usuario sigue siendo apto para prototipos académicos, no para producción institucional.

## Instalación sobre V4 (Windows CMD)

1. Detener Streamlit con `Ctrl+C` y hacer copia de seguridad de la carpeta completa.
2. Extraer el ZIP V5 y copiar sus archivos sobre `C:\Users\admin\Desktop\UNFV_IA_Actualizado`. **No reemplazar** `.streamlit/secrets.toml`, `.venv/` ni `data/`.
3. En CMD: `python -m pip install --default-timeout=180 -r requirements.txt`
4. En CMD: `python -m pytest tests -q`
5. En CMD: `python -m streamlit run app.py`; después `Ctrl+F5` en el navegador.
6. El ejemplo `.streamlit/secrets.toml.example` incluye el nuevo `NVIDIA_VERIFIER_MODEL`. No es obligatorio añadirlo a tu archivo privado: se usa como valor predeterminado.

## Prueba de aceptación mínima

- [ ] La universidad aparece arriba, no debajo de los menús.
- [ ] OCR muestra 8 de 8 páginas para el PDF de prueba; si no, aparece advertencia.
- [ ] Puedo ver en la vista de Documentos el texto extraído de cada página.
- [ ] Chat identifica si la verificación fue de Gemini o de NVIDIA.
- [ ] Al agotar Gemini, el quiz no permanece esperando casi dos minutos solamente en Gemini.
- [ ] Si todos los verificadores fallan, no se publican preguntas ni respuestas no verificadas.
- [ ] No se pierden archivos ni historial de la cuenta al cambiar de vista o volver a iniciar sesión.
