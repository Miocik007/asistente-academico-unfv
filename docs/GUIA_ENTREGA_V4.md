# Guía de presentación y pruebas — Asistente UNFV 4.0

## Entrega

La carpeta es un **proyecto completo**, no un parche. Contiene la interfaz Streamlit, agentes, RAG, OCR, verificador, evaluaciones, bases de datos aisladas y almacenamiento local por estudiante.

**Público:** estudiantes universitarios de pregrado de la Universidad Nacional Federico Villarreal.

**Modelos:** NVIDIA Nemotron 3 Ultra (Tutor) y Gemini (Verificador y OCR). Los IDs exactos pueden configurarse mediante `.streamlit/secrets.toml` según el acceso de cada cuenta.

**Seguridad de las respuestas:** RAG con fuentes, reglas contra alucinaciones, control de citas, verificación cruzada y posibilidad de responder «información insuficiente». **No garantiza cero alucinaciones**.

## Cómo actualizar desde V3 en Windows (CMD)

1. Detén la aplicación (`Ctrl+C`).
2. **Haz una copia de seguridad de tu carpeta actual** `C:\Users\admin\Desktop\UNFV_IA_Actualizado`.
3. Descomprime V4. Copia el contenido nuevo **encima del código anterior**, sin reemplazar ni eliminar:
   - `.streamlit/secrets.toml` (tus claves y usuarios)
   - `.venv/` (tu entorno Python)
   - `data/` (progreso, OCR y documentos ya persistidos)
4. Desde la carpeta del proyecto ejecuta:

```cmd
.venv\Scripts\activate.bat
python -m pip install --default-timeout=180 --retries=10 -r requirements.txt
python -m pytest tests -q
python -m streamlit run app.py
```

5. En navegador: `Ctrl+F5` para recargar el diseño.

**Si vienes de V3:** el historial y los resultados previos que ya estén en `data/` se mantienen. Pero **los PDF y la conversación que V3 guardaba solo en memoria no se pueden recuperar retroactivamente**. Debes subir esos archivos UNA VEZ en V4. A partir de entonces se conservarán localmente, y el OCR no se repetirá al reingresar mientras mantengas `data/`.

## Pruebas de aceptación sugeridas (realizar en Windows)

Marca cada prueba cuando la completes y anota evidencia/captura:

- [ ] **Preparar PDF sin procesar.** Subir 2 PDF en Documentos; aparecerán en «Archivos preparados».
- [ ] **Navegación.** Ir a Progreso y volver a Documentos; la lista preparada sigue disponible aunque el control original de Streamlit se vacíe.
- [ ] **Cerrar sesión antes de procesar.** Salir e ingresar con la misma cuenta; el listado preparado sigue.
- [ ] **Separación por usuario.** Una segunda cuenta no ve los documentos de la primera.
- [ ] **OCR asíncrono.** Pulsar Procesar en el PDF de ocho páginas escaneadas, cambiar de apartado y regresar: la tarea continúa mientras el servidor y la sesión permanezcan activos.
- [ ] **Recuperación del material.** Cuando acabe OCR, cerrar sesión y entrar: los documentos aparecen procesados sin volver a enviar las páginas al OCR.
- [ ] **Preguntas.** Hacer 2 preguntas con evidencia y 1 sin evidencia; comparar las respuestas con el PDF.
- [ ] **Conservar chat.** Cerrar sesión y volver a entrar: las respuestas ya terminadas se muestran en Asistente.
- [ ] **Evaluación.** Generar quiz, marcar 2 opciones, salir y volver: el borrador marcado se conserva. Completar y pulsar un solo botón de envío.
- [ ] **Plan de estudio.** Generar plan en Progreso, salir y volver: el mismo texto se recupera. Tras completar otro quiz debe avisar que el plan requiere actualización.
- [ ] **Borrar material.** Retirar documentos procesados de la cuenta y verificar que ya no aparecen; el historial de progreso se mantiene.
- [ ] **Borrar todo.** Reiniciar progreso con confirmación y comprobar que se eliminan PDFs, archivos preparados, respuestas y caché del usuario.
- [ ] **Seguridad mínima.** Asegurarse de que no se comparte `secrets.toml` ni el directorio `data/`.
- [ ] **Comprobación APIs.** Ejecutar `python tools/check_models.py` con cuenta activa y verificar los dos servicios.

## Límites que debes explicar al docente

- Las llamadas a NVIDIA y Gemini dependen de conectividad, credenciales, cuota y modelos disponibles.
- El OCR de ocho páginas exige tiempo; ahora sigue en segundo plano mientras navegas por la **misma sesión**, pero **se cancela al cerrar sesión**, y no sobrevive al cierre del servidor o reinicio de la computadora.
- Las respuestas de IA no son infalibles. El verificador minimiza, pero no elimina, afirmaciones incorrectas; se requieren pruebas con respuestas de referencia.
- Los PDF y respuestas se guardan **localmente y sin cifrado en disco** dentro de `data/` por cuenta. Solo recomendado para demostración académica con documentos de prueba, no para despliegue público ni material confidencial.
- La versión requiere controles adicionales antes de desplegarla como plataforma institucional: HTTPS, SSO, protección de datos, cifrado en reposo, auditoría y pruebas de penetración.

## Ubicación de archivos relevantes

- `workspace.py`: lista de archivos preparados y persistencia local segura de rutas.
- `state.py`: recuperación del espacio de trabajo por estudiante.
- `views/settings.py`: uploader con guardado inmediato, OCR en segundo plano y gestión de documentos.
- `jobs.py`: administración de tareas, sincronización de resultados desde hilo principal.
- `views/chat.py`, `views/dashboard.py`, `views/quiz.py`: persistencia del chat, plan y borrador.
- `tests/test_workspace_v4.py`: pruebas unitarias de recuperación y aislamiento.
