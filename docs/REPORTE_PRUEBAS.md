# Pruebas ejecutadas y pendientes

## Ejecutado en la preparación del ZIP (48 pruebas locales, V3)

- Compilación sintáctica con `python -m compileall` en todo el código.
- `python -m pytest tests -q`: pruebas automatizadas con LLM/OCR simulados.
- Comprobaciones: no clasificar dificultad por repeticiones, impedir doble respuesta, actualizar dominio con errores, eliminar datos y OCR, evitar mezcla entre materiales, validar cuatro opciones, abstención ante alucinaciones, cita inexistente, verificador fallido, discrepancia del Solucionador, carga DOCX, límite de tamaño y caché de imágenes.

## No ejecutado aquí

- No se ejecutó una llamada en vivo a Nemotron ni Gemini (no se incluyeron credenciales personales).
- No se verificó la instalación íntegra de la interfaz Streamlit en Windows ni se descargó el modelo local de embeddings.
- No se han medido todavía la exactitud real, la tasa de alucinación, el tiempo extremo a extremo, el costo ni las restricciones de cuota de ambas cuentas.

## Protocolo de aceptación sugerido

1. Crear credenciales, ejecutar `python tools/check_models.py` y conservar salida sin datos secretos.
2. Probar PDF textual, PDF escaneado, DOCX y JPG reales.
3. Ejecutar `python tools/evaluate_live.py --limit 5`, después los 30 casos si la cuota lo permite.
4. Revisar manualmente todas las citas y marcar coincidencia real con la fuente.
5. Registrar exactitud, respuestas abstinentes correctas, citas incorrectas, latencia, cuota y errores.
6. Comparar, si se desea, variantes de NVIDIA solo/Gemini solo/doble modelo en un conjunto fijo, manteniendo el mismo documento y preguntas.

**Se considera apto para demostración académica tras pasar el flujo en Windows y las pruebas con API; no para producción institucional.**

## Casos de aceptación V3 (comprobar en Windows)

- [ ] Preguntar en Asistente, navegar a Progreso y regresar: la pregunta debe seguir visible y completarse sin duplicar el registro.
- [ ] Generar un quiz, ir a Historial y volver: la generación debe continuar hasta guardar las preguntas verificadas.
- [ ] Seleccionar varias respuestas de quiz, cambiar a Progreso y regresar: el borrador debe conservar las opciones.
- [ ] Enviar todas las preguntas una sola vez y comprobar los porcentajes en Progreso; fallos visibles con clave y explicación.
- [ ] Generar plan sin evaluaciones: debe indicar «no hay evaluaciones», nunca presentar «0 %» como una precisión observada.
- [ ] Generar plan con 2/8 aciertos: debe indicar 25 % y priorizar temas con fallos registrados.
- [ ] Subir de nuevo el mismo documento: debe evitar OCR e indexación repetidos.
- [ ] Cambiar documento durante una tarea: el resultado viejo no se debe añadir al material nuevo.
- [ ] Ejecutar PDF nativo y escaneado; comparar fuentes y comprobar abstención ante preguntas sin evidencia.


## Verificación específica V4 (sin gastar APIs)

Se añadieron 7 pruebas en `tests/test_workspace_v4.py`:
- persistencia de uploads al cambiar de pantalla/reiniciar sesión;
- aislamiento de documentos entre usuarios;
- validación de extensiones/tamaños, rutas seguras y protección frente a archivos corruptos;
- eliminación de material preparado y resultados;
- persistencia del documento procesado, chat, plan y borrador de quiz;
- caché OCR SQLite accesible desde tareas en segundo plano;
- comprobación de integración de carga, restauración y recolección asíncrona.

Estas 7 pruebas pasan en el entorno de preparación. Se comprobó también la compilación del código de la V4. **No se ha podido volver a ejecutar en este entorno el conjunto completo V3 de 48 pruebas porque no están instaladas aquí Streamlit, LangChain y FAISS**. Deben volver a ejecutarse en la computadora del estudiante con `python -m pytest tests -q`. Tampoco se ha verificado la respuesta real de las APIs.
