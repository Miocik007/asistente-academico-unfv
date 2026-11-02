# Asistente Académico Inteligente UNFV · V5.1 · Edición para GitHub y despliegue

**Código académico de demostración multiagente.** Público: estudiantes universitarios de pregrado de la Universidad Nacional Federico Villarreal (UNFV).

**Entrada principal:** `app.py`. **Python:** 3.11. **Stack:** Streamlit, NVIDIA Nemotron, Gemini, FAISS, LangChain, Tesseract OCR, SQLite.

## Guía de publicación (leer antes de subir a GitHub)

Consulta **[`docs/PUBLICACION_GITHUB_STREAMLIT.md`](docs/PUBLICACION_GITHUB_STREAMLIT.md)**.

1. Revisa que NO haya claves, contraseñas ni datos personales en Git.
2. Publica este código desde una carpeta limpia en un nuevo repositorio GitHub.
3. Despliega con Streamlit Community Cloud el archivo `app.py` y Python **3.11**.
4. En **Advanced settings → Secrets** configura `NVIDIA_API_KEY`, `GOOGLE_API_KEY`, modelos y `[users]` con **hashes de contraseñas de prueba**. Nunca publiques el contenido real de `secrets.toml`.
5. Comprueba el acceso mediante HTTPS, OCR, consultas, quiz y la traza de al menos dos agentes. Registra evidencias verdaderas.

> **Limitaciones:** las conversaciones, PDFs e índices se guardan en `data/`/SQLite local; Streamlit Community Cloud no garantiza la persistencia de archivos después de reinicios, y sus recursos pueden ser insuficientes para modelos de embeddings pesados. Esta edición sirve para **probar el despliegue**; no afirma durabilidad, privacidad institucional, alta disponibilidad ni cero alucinaciones. Usa solamente materiales académicos ficticios o autorizados. Las tareas en curso no sobreviven reinicios.

## Ejecutar localmente

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
python tools/create_password_hash.py
python -m streamlit run app.py
```

Configura tu archivo privado `.streamlit/secrets.toml` antes de ejecutar. Las opciones modelo son ejemplos y requieren que la cuenta tenga acceso. Para Linux, `packages.txt` incluye Tesseract y español.

## Comprobar localmente

```cmd
python -m pytest tests -q
python tools/check_ocr.py
```

El endpoint HTTP nativo de salud de Streamlit es `/_stcore/health` (comprueba la salud del proceso, **no** las respuestas de los agentes).

## Documentación histórica

Las decisiones del producto, los cambios de los agentes y las pruebas locales se describen en la carpeta `docs/`; las evidencias con APIs reales deberán generarse en la URL pública, no simularse.

---
# Actualización 5.1 — Solución al error «No terminó la lectura (ValueError)»

Cuando Gemini no tiene cuota, un PDF escaneado puede quedar sin texto y la
versión previa mostraba un `ValueError` sin diagnóstico. Ahora puedes elegir
**OCR local Tesseract** (sin cuota) desde «Documentos y configuración» y
consultar un informe de lectura fallida. Si la extracción obtuvo texto pero
falló el índice, verás un aviso distinto.

- La instalación de `pytesseract` NO instala el programa Tesseract.
- Comprueba la instalación con `python tools/check_ocr.py`.
- Guía: `docs/CORRECCIONES_V5_1.md`.
- No elimines `.streamlit/secrets.toml`, `.venv` ni `data` al actualizar.

---

# Asistente Académico Inteligente UNFV — Versión 5.0

**Dirigido exclusivamente a estudiantes universitarios de pregrado de la Universidad Nacional Federico Villarreal (UNFV).**

Este proyecto es una mejora del ZIP original `streamlit.unfv-main - copia`. Conserva sus **seis páginas**, diseño, índice FAISS, OCR, historial, cuestionarios y agentes; añade una arquitectura con **NVIDIA Nemotron 3 Ultra como Tutor** y **Gemini como verificador y OCR; si su cuota se agota, el verificador usa un modelo NVIDIA alternativo**. Es un prototipo académico, NO un servicio listo para producción institucional. Ningún modelo garantiza cero alucinaciones.

## Correcciones V5 para las observaciones durante las pruebas

- **Error 429 de Gemini:** ya no se bloquea el chat ni el Solucionador con reintentos largos. Tras detectar agotamiento de cuota, deja de llamar a Gemini durante 10 minutos y pasa al verificador de texto alternativo NVIDIA Nemotron 3.5 Lightning; si esa cuenta no tiene acceso, intenta con Nemotron 3 Ultra. La interfaz y la traza identifican cuál verificó. **NVIDIA como respaldo no es una verificación independiente de proveedor** y tampoco garantiza ausencia de alucinaciones.
- **OCR de escaneados:** no se envían imágenes a NVIDIA Ultra, ya que este modelo es de texto. Si Gemini no permite OCR y Tesseract OCR está instalado, utiliza OCR local. Si ninguno puede leer la página, se muestra cuántas páginas quedaron sin transcribir; **no se inventa contenido**.
- **Diagnóstico de documentos:** en «Documentos y configuración» se ve el número de páginas leídas y se puede desplegar el texto extraído por página para comprobar números, horas y roles sin gastar nuevas llamadas.
- **RAG:** se mejoró la búsqueda de preguntas sobre cronologías, alertas, aislamiento, contención y responsables, y se cambió el modelo predeterminado de embeddings a uno multilingüe para español.
- **Diseño:** el nombre UNFV y «Universidad Nacional Federico Villarreal» se ubican en un membrete compacto en la parte superior de la barra lateral, sin duplicarlo a media altura.
- **Quizzes:** las claves siguen exigiendo validación; si ni Gemini ni NVIDIA están disponibles, no se publican preguntas sin comprobar y se explica la causa.

**Nota de migración:** si ya existía un índice guardado con el modelo de embeddings antiguo, al actualizar conviene volver a procesar los mismos archivos preparados una vez para reconstruirlo con embeddings multilingües. El OCR persistido puede reutilizarse desde su caché. Conserva siempre `data/`.

### OCR local opcional cuando se agota Gemini

Instala el **motor Tesseract OCR para Windows** y, preferentemente, el paquete de idioma español (`spa`). Debe estar disponible el comando `tesseract --version` en una nueva terminal de VS Code. `pytesseract` ya viene en `requirements.txt`; por sí solo no instala el programa Tesseract. Si tu PDF tiene todas las páginas reconocidas en caché, no necesitas volver a ejecutar OCR.

### Pruebas que requieren tus claves reales

1. Haz una consulta cuya respuesta está en el PDF escaneado (por ejemplo, la primera alerta) y abre los fragmentos citados.
2. Ve a **Documentos → Detalle de lectura** y comprueba que se extrajeron las ocho páginas. Si se leyeron menos, **no** puede inferirse que la información ausente no exista en el PDF.
3. Genera un quiz. Si Gemini devuelve 429, comprueba en «Sistema multiagente» que el Solucionador indique NVIDIA alternativo o NVIDIA principal y que no admita claves dudosas.
4. Comprueba que la barra lateral muestre el nombre de la universidad arriba.
5. Cierra sesión y regresa con la misma cuenta para comprobar que se conservan documentos, respuestas terminadas y progreso.

## Instrucciones de instalación en Windows (Visual Studio Code)

Recomendación: **Python 3.11 o 3.12** de 64 bits.

1. Extrae el ZIP completo y abre la carpeta `UNFV_IA_Actualizado` en VS Code.
2. Abre una terminal de PowerShell dentro de esa carpeta.
3. Ejecuta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si no tienes Python 3.11 pero sí 3.12, cambia `-3.11` por `-3.12`. Si PowerShell no permite activar el entorno: `Set-ExecutionPolicy -Scope Process Bypass`, luego vuelve a activar.

4. Crea tu archivo privado (no lo incluyas en entregas):

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

5. Abre `.streamlit/secrets.toml` y reemplaza los valores de ejemplo por las dos claves.

```toml
NVIDIA_API_KEY = "TU_CLAVE_DE_NVIDIA"
GOOGLE_API_KEY = "TU_CLAVE_DE_GEMINI"
NVIDIA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
GEMINI_MODEL = "gemini-3.8-flash"
NVIDIA_VERIFIER_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

[users]
# Aquí se agrega la cuenta mediante el paso 6.
```

6. Genera un hash seguro para una cuenta local:

```powershell
python tools/create_password_hash.py
```

Ingresa el usuario y la contraseña en la terminal (la contraseña no se imprime). **Copia solo la línea de hash** que devuelve el comando debajo de `[users]` en `secrets.toml`. Para más estudiantes, repite el procedimiento y añade una línea por persona. No uses un hash de ejemplo; debe ser uno real.

7. Ejecuta las pruebas sin gastar llamadas a APIs:

```powershell
python -m pytest tests -q
```

8. Inicia el sistema:

```powershell
streamlit run app.py
```

Después de iniciar sesión: **Documentos y configuración → Cargar PDF, DOCX o imagen → Procesar documentos → Asistente**. En el primer uso, el modelo de embeddings se descarga; requiere conexión a internet y puede demorar. Las llamadas a NVIDIA y Gemini requieren conexiones válidas y cuotas disponibles.

### Verificación de servicios reales (opcional)

```powershell
python tools/check_models.py
```

Si tus claves están activas, el script comprobará ambos modelos. Su ejecución consume solicitudes a sus respectivas APIs. Puedes configurar otros IDs de modelos en `secrets.toml` si el proveedor cambia los endpoints.

## Distribución de tareas por API

| Componente | Proveedor | Función |
| --- | --- | --- |
| Planificador | Lógica local para preguntas claras; NVIDIA para reformulaciones | Ahorra una llamada a la API en preguntas directas |
| Recuperador | FAISS + coincidencia léxica local | Recupera fragmentos numerados con documento y página |
| Tutor | NVIDIA Nemotron 3 Ultra | Elabora respuesta usando exclusivamente fragmentos |
| Verificador | Gemini; respaldo NVIDIA Lightning o Ultra | Contrasta afirmaciones y citas; señala qué proveedor actuó |
| Solucionador | Gemini; respaldo NVIDIA Lightning o Ultra | Revisa las claves sin ver la respuesta marcada; descarta dudas |
| Agente OCR | Google Gemini 3.8 Flash; Tesseract opcional | Transcribe páginas escaneadas e imágenes |
| Generador de temas y quiz | NVIDIA Nemotron 3 Ultra | Identifica conceptos y prepara preguntas |
| Coach | Reglas deterministas basadas en SQLite | Genera planes sin inventar resultados ni fechas |
| Historial / dominio | SQLite por cuenta | Guarda preguntas, evaluaciones, progreso y trazas |

**Control de incertidumbre:** cuando no se recupera contenido, el verificador falla, no existen citas válidas o la respuesta no supera el umbral orientativo, el Orquestador devuelve una abstención. El puntuador es un LLM, no una prueba matemática de verdad. En las evaluaciones, toda pregunta sin validación secundaria se descarta; durante el respaldo NVIDIA no existe independencia de proveedor.

**Progreso adaptativo:** muchas consultas **no** equivalen a dificultades; un tema se marca débil tras errores reales en quizzes. El primer quiz se puede generar a partir de los temas detectados, aunque aún no existan errores.

## Alcance de archivos

- PDF con texto nativo (página real).
- PDF escaneado (OCR si hace falta).
- Imágenes JPG, PNG, WEBP, BMP, TIFF (OCR Gemini o Tesseract).
- Word `.docx` con párrafos y tablas de texto (sin número real de página; las imágenes incrustadas en Word no reciben OCR). Para Word que contiene escaneos, expórtalo a PDF y activa OCR.
- Límite por carga: hasta 10 archivos, hasta 20 MB por archivo. `streamlit` limita el tamaño de carga por archivo desde `.streamlit/config.toml`.

**Privacidad y persistencia V4:** requiere inicio de sesión local y usa un SQLite y directorio `data/` separados por usuario. Los archivos subidos se copian al área privada de documentos preparados al seleccionarlos (máximo 10 archivos de 20 MB), y sobreviven a la navegación y al reinicio de sesión. Después de procesar el material, se guardan las páginas transcritas y el índice FAISS **sin usar pickle**; se recuperan al volver a entrar. El chat terminado, el plan de estudio y el borrador del quiz se guardan por cuenta. El directorio `data/` contiene material académico en **texto plano, sin cifrado en reposo**, adecuado solo para un prototipo local con documentos de prueba. Al reiniciar progreso se borran documentos, OCR e historial. Cambiar de conjunto de documentos reinicia estadísticas anteriores para evitar contaminación cruzada.

La autenticación local con PBKDF2 y el aislamiento básico no sustituyen un sistema institucional con SSO, TLS, políticas de retención, registros de auditoría y pruebas de seguridad. **No publiques directamente este prototipo ni subas datos personales/confidenciales a las APIs de prototipo.**

## Observaciones del docente, implementadas

1. **Público objetivo:** pregrado universitario UNFV, explícito en pantalla y prompts.
2. **Restricción de alucinación:** normas comunes para agentes, citas numeradas, verificador externo, comprobación local de identificadores y abstención si falla la auditoría. Los documentos se tratan como datos no fiables.
3. **Otra API y más pruebas:** NVIDIA Nemotron como modelo principal, Gemini como auditor; pruebas unitarias `pytest`, evaluación de 30 casos reproducibles y procedimiento opcional de prueba real (`tools/evaluate_live.py`).

## Pruebas y reporte

```powershell
python -m pytest tests -q
python tools/evaluate_live.py --limit 5
# Opcional, con más consumo de API y tiempo:
python tools/evaluate_live.py --limit 30
```

Las pruebas `pytest` no hacen llamadas a NVIDIA ni Gemini; están basadas en dobles de prueba. **No es correcto afirmar que la integración API real ha sido validada sin ejecutar la evaluación en tu propia cuenta.** Consulta `docs/REPORTE_PRUEBAS.md` y `evaluacion/casos_30.json`.

## Archivos importantes

- `app.py`: interfaz y navegación (6 pantallas).
- `auth.py`: acceso de estudiantes con hashes de contraseña.
- `state.py`: inicialización de NVIDIA y Gemini; claves desde secretos.
- `agents.py`: prompts, agentes y Orquestador con verificación obligatoria.
- `rag_engine.py`: índice vectorial, clasificación y extracción de temas.
- `ingest.py`: procesamiento PDF/DOCX/imágenes y OCR.
- `db.py`: base de datos individual por estudiante y caché.
- `views/`: las seis pantallas originales, conservando el diseño de `theme.py`.
- `jobs.py`: tareas asíncronas de NVIDIA/Gemini aisladas por sesión, recolección segura de resultados.
- `.streamlit/secrets.toml.example`: configuración segura de ejemplo, sin claves.
- `tests/`: pruebas unitarias sin credenciales.
- `evaluacion/`: 30 casos para pruebas comparativas con resultados exportables.
- `docs/`: informe técnico de mejoras y resultados.

## Referencias oficiales

- NVIDIA NIM: https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/build
- Google Gemini: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- Streamlit Secrets: https://docs.streamlit.io/develop/concepts/connections/secrets-management

## Corrección visual v2.1

Esta revisión corrige el contraste oscuro que aparecía en los cuadros de usuario/contraseña y botones cuando Streamlit heredaba las preferencias del navegador. El tema es claro explícitamente en `.streamlit/config.toml`, con CSS de respaldo en `theme.py`. El acceso se presenta en una tarjeta centrada, sin menú lateral antes de iniciar sesión; «Ingresar» es naranja oscuro con texto blanco, «Cerrar sesión» mantiene fondo blanco y texto legible. En el asistente sin documentos se muestran tres pasos de inicio.

**Para actualizar una instalación anterior:** extrae este ZIP y usa el código nuevo; conserva tu archivo privado `.streamlit/secrets.toml`, creado por ti, copiándolo a la nueva carpeta. **No copies** `.venv` ni cambies los API Keys. Activa el entorno virtual en la carpeta de este proyecto y ejecuta `python -m streamlit run app.py`. Si conservas la misma carpeta anterior, reemplaza el código y verifica que `.streamlit/config.toml` también se reemplace, sin sobrescribir `secrets.toml`. En el navegador recarga con `Ctrl + F5`.


## Mejoras V3: navegación, evaluaciones y rendimiento

- **Chat:** si haces una pregunta y visitas «Progreso», la llamada a NVIDIA/Gemini continúa en un hilo del servidor. El mensaje pendiente permanece visible al regresar. El resultado se incorpora automáticamente al terminar. Solo se guarda en la BD después de verificar que corresponde al material activo.
- **Quizzes:** se muestra el cuestionario completo y se corrige **una sola vez** al pulsar «Enviar evaluación completa». Debes responder todas las preguntas. Se guarda atómicamente en SQLite; no se repite la calificación. Elige respuestas y cambia de pantalla sin perderlas: se conservan en un borrador de sesión.
- **Corrección:** el resultado completo muestra tu respuesta, la clave correcta cuando fallaste y la explicación. Se quitó «Últimas respuestas» de Evaluación: los intentos anteriores se consultan en Historial.
- **Progreso:** las tarjetas usan **aciertos / preguntas respondidas** y no confunden el contador de avance con un porcentaje. Las barras no muestran actividad artificial en temas con cero consultas. Puedes mostrar/ocultar los temas todavía no evaluados.
- **Coach:** genera de inmediato un plan de 3 sesiones a partir de los aciertos, errores y temas verdaderamente registrados. No inventa materias, porcentajes de dominio, fechas de estudio ni actividades pasadas. El plan queda disponible al cambiar de sección y avisa si cambiaste tus resultados.
- **Documentos:** se mantiene la caché OCR y el análisis de PDF/DOCX. Una carga **idéntica** no se vuelve a procesar. El análisis de temas se ejecuta en segundo plano **después** de que el texto y el índice FAISS están listos; así puedes visitar el Asistente sin esperar la extracción de temas. Si la API falla, puedes reintentarla desde Configuración sin reconstruir el índice.
- **Recuperación:** para preguntas claras sobre un tema conocido se evita una llamada innecesaria al Planificador, sin eliminar la verificación posterior de la respuesta. Las preguntas ambiguas o que hacen referencia a algo anterior siguen usando planificación con IA.

**Límites de estas optimizaciones:** la extracción OCR de páginas realmente escaneadas y la primera descarga/carga del modelo local de embeddings siguen requiriendo tiempo. Una pregunta compleja pasa por NVIDIA y Gemini, o por un segundo pase NVIDIA si Gemini agota su cuota. Las tareas en segundo plano dependen de que el servidor y la sesión de Streamlit sigan activos: **no sobreviven a un reinicio del servidor ni garantizan recuperación tras cerrar/recargar la pestaña**. El historial ya guardado sí permanece en SQLite.

### Actualizar desde la versión 2.1 sin perder nada

1. En la terminal de VS Code, detén la aplicación con `Ctrl + C` y haz una copia de la carpeta anterior por seguridad.
2. Extrae la V3 y **copia su contenido sobre** `C:\Users\admin\Desktop\UNFV_IA_Actualizado`, reemplazando archivos de código.
3. **Conserva sin tocar** `.streamlit/secrets.toml`, `data/` y `.venv/`. No vienen incluidos en el ZIP, por lo que no debes borrarlos.
4. En CMD de esa carpeta, ejecuta ` .venv\Scripts\activate.bat ` y después ` python -m streamlit run app.py `.
5. Si conservaste tu base `data/`, tus temas e intentos previos permanecen. Para activar las métricas V3 no debes reiniciar el progreso.

### Pruebas de la revisión V3

En esta versión se completaron **65 pruebas locales automáticas** (sin llamadas reales a proveedores) y la compilación sintáctica de Python. Incluyen calificación atómica, selección única, protección contra duplicados, datos reales del plan, tareas persistentes al navegar, privacidad por material, verificador y caché OCR. Se debe completar una prueba manual de interfaz con Streamlit en Windows y NVIDIA/Gemini antes de presentar la versión como validada en vivo.


## Novedades V4 — documentos que no desaparecen y recuperación entre sesiones

**Lee primero:** [`docs/GUIA_ENTREGA_V4.md`](docs/GUIA_ENTREGA_V4.md). Incluye comandos CMD, una guía para migrar desde V3 conservando `.venv`, `data` y `secrets.toml`, y pruebas de aceptación antes de exponer.

- **Archivos preparados:** el selector `st.file_uploader` se vacía al navegar, por diseño de Streamlit; V4 lo corrige con un `on_change` que guarda los bytes inmediatamente en el directorio privado de cada estudiante. El listado persistente tiene botones «Quitar» y «Vaciar lista preparada». Puedes elegir archivos hoy y procesarlos después.
- **Lectura de PDF e imágenes en segundo plano:** OCR/lectura se ejecutan sin bloquear el cambio de página de una sesión activa, con caché SQLite de OCR segura para hilos. La creación del índice FAISS se completa al recoger el resultado.
- **Restauración de material:** al entrar, el código restaura las páginas y el índice FAISS local (sin deserializar pickles). Si falta el índice, lo reconstruye con el texto guardado **sin repetir OCR**.
- **Chat, planes y quiz:** respuestas de IA terminadas, plan de estudio y selecciones del quiz pendiente persistentes por estudiante; los resultados previos de evaluaciones continúan en SQLite.
- **No se incluyen datos privados en el ZIP.** Mantén localmente `.streamlit/secrets.toml` y `data/` y haz copias de seguridad antes de actualizar.

**Nota sobre procesos en curso:** cambiar entre las seis pantallas no cancela la tarea OCR o IA; cerrar sesión, reiniciar Streamlit o apagar el servidor puede interrumpir tareas que aún no terminaron. Los archivos preparados y **resultados ya completados** sí sobreviven.

**No afirmar producción certificada:** estas mejoras permiten preparar una demostración final más sólida; hace falta probar en Windows las APIs reales y pasar por una revisión de seguridad antes de una publicación institucional.
