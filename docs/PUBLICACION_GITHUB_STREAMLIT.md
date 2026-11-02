# Publicación segura · UNFV V5.1 en GitHub y Streamlit Community Cloud

## A. Antes de GitHub

- Esta carpeta está limpia: no contiene `secrets.toml` con valores, bases de datos de usuarios, índices FAISS generados ni material de estudiantes. Se incluyen **solamente archivos de código y ejemplos**.
- No publiques el contenido de tu `data/` original, ni `.venv/`, PDFs, documentos o capturas con información privada.
- `gitignore` es preventivo: no elimina claves ya confirmadas en commits. Antes de confirmar, ejecuta `git status --short` y `git diff --cached --name-only`; si un secreto ya llegó a GitHub, revócalo y límpialo del historial.
- Usa una contraseña de **prueba** distinta de tus contraseñas personales. Guarda solo el hash PBKDF2 en el gestor de Secrets de Streamlit y comparte la contraseña con el docente por un canal privado, no en el cuestionario ni en el repositorio.

## B. Subir al repositorio nuevo (CMD o terminal de VS Code)

1. Crea en GitHub un repositorio nuevo vacío, por ejemplo `asistente-academico-unfv`, con visibilidad **Public** para que lo vea tu profesor. Sin crear README o `.gitignore` remoto porque ya están aquí.
2. Abre una terminal en la carpeta que contiene `app.py`, no en una carpeta superior.
3. Comprueba Git con `git --version`.
4. Ejecuta:

```cmd
git init
git branch -M main
git add .
git status --short
git diff --cached --name-only
git commit -m "Version academica multiagente UNFV V5.1"
git remote add origin https://github.com/TU_USUARIO/asistente-academico-unfv.git
git push -u origin main
```

Sustituye `TU_USUARIO`. Si Git solicita una identidad, configura con `git config --global user.name` y `git config --global user.email` según tu cuenta. **No pegues una contraseña ni token en el comando `git remote add`.**

## C. Desplegar

1. Abre `https://share.streamlit.io/` e inicia sesión con GitHub.
2. Selecciona **Create app → Yup, I have an app**.
3. Selecciona repo `asistente-academico-unfv`, rama `main`, archivo principal `app.py`.
4. En **Advanced settings**, selecciona Python **3.11**, importante para las librerías del proyecto.
5. En **Secrets** pega el TOML **real** desde tu copia privada (o copia solo los valores necesarios), incluyendo variables de modelo y `[users]` con hashes para usuarios de prueba. **No publiques ni compartas capturas de este panel.**
6. Pulsa **Deploy**. Streamlit instala Python de `requirements.txt` y Tesseract + idiomas de `packages.txt` automáticamente. Puede haber fallos de memoria por `sentence-transformers`, `torch` y FAISS; confirma en los logs.
7. Obtén la URL `https://...streamlit.app`. Comprueba `/_stcore/health` y ejecuta una consulta real desde el navegador del docente. La ruta salud solo significa que el servidor responde.

## D. Seguridad y limitaciones (NO ocultar al docente)

- **Persistencia:** este proyecto todavía guarda datos en SQLite y archivos locales. Streamlit Community Cloud no garantiza que el material permanezca tras reinicio, hibernación o redeploy. Para entregar persistencia duradera, migrar a una base administrada y almacenamiento de objetos con acceso por usuario.
- **Privacidad:** el proveedor aloja la aplicación fuera de la computadora local; no subas documentos personales reales ni material institucional confidencial. Los documentos de prueba deberán ser ficticios y autorizados.
- **Acceso:** la autenticación PBKDF2 con usuarios configurados en Secrets es aceptable para una demostración con cuentas controladas, pero no sustituye una solución de identidad institucional, límites globales de intentos, cuotas por usuario ni auditoría externa.
- **Recursos:** Comunidad gratuita tiene recursos limitados. El modelo local de embeddings puede tardar y consumir memoria, incluso si el LLM se ejecuta vía API en NVIDIA. No prometas rendimiento sin medirlo en el despliegue.
- **Alucinaciones:** RAG y verificación mitigan errores; no garantizan precisión total. El respaldo NVIDIA tampoco es una segunda verificación independiente del proveedor NVIDIA.

## E. Evidencia que solicita el profesor

- A5: URL HTTPS pública y captura donde el docente inicia sesión.
- A6: URL GitHub pública, con archivos de código y documentación.
- A7: video real de 3–5 minutos.
- E9: consulta desde la URL y **traza**: usuario → planificador → recuperador (FAISS) → tutor NVIDIA → verificador Gemini o respaldo → respuesta. Guardar tiempos y herramientas, sin claves.
- G5: `https://TU_URL.streamlit.app/_stcore/health` (estado `ok`, si está disponible). Esta comprobación no verifica la IA.
- I1: ≥6 pruebas con entradas, esperado, real, agente y resultado.
- I2/G7: medir tiempos y fallos, y cuántos usuarios simultáneos probaron realmente.
- K: confirmar únicamente afirmaciones verificadas.

Referencias oficiales:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
