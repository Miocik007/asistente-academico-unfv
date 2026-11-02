# V5.1 — Lectura OCR y diagnóstico de fallos

## Fallo que corrige

La V5 mostraba `No terminó la lectura de los documentos (ValueError)` cuando
un PDF escaneado quedaba completamente sin texto. La causa puede ser el
agotamiento de cuota de Gemini (HTTP 429), un motor OCR no disponible o,
separadamente, un fallo al construir embeddings/FAISS.

## Mejora

- Mensaje detallado al usuario sin mostrar claves API.
- El informe de páginas y las advertencias se pueden consultar incluso
  después de un intento fallido.
- Selector de motor OCR: automático, Tesseract local, Gemini API.
- Detección de instalaciones de Tesseract Windows comunes aunque falte PATH.
- No se publican documentos vacíos como si estuvieran procesados.
- Los archivos preparados, el progreso y las conversaciones anteriores
  continúan sin alterarse durante un fallo de lectura.

## Instalar OCR local en Windows sin gastar cuota Gemini

Tesseract es una aplicación adicional (la librería `pytesseract` por sí sola
no instala el motor). Puedes encontrar el instalador para Windows en:
https://github.com/UB-Mannheim/tesseract/wiki

También puedes probar en CMD:

    winget search tesseract
    winget install -e --id UB-Mannheim.TesseractOCR

Durante la instalación incluye el idioma **Spanish (spa)**. Luego reinicia
VS Code/Streamlit y comprueba:

    "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
    "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs

En la app: Documentos y configuración > Opciones de lectura (OCR) >
Motor de OCR > **Tesseract local (gratis, sin cuota)**.
Si el motor no se detecta, puedes crear la variable de entorno
`TESSERACT_CMD` con la ruta completa al ejecutable.

**Importante:** Tesseract funciona mejor para texto impreso legible. Revisa
el texto reconocido por página antes de usarlo como evidencia.

## Prueba

Usa `UNFV_Caso_Campus_Aurora_8_Paginas_Escaneadas_OCR.pdf` (8 páginas, solo
imágenes). Selecciona OCR local y comprueba que se reconozcan las ocho páginas.
Si no se reconoce ninguna, debe mostrarse una explicación, nunca solamente
`ValueError`.

No son pruebas reales de Gemini ni NVIDIA: la integración con sus claves
continúa dependiendo de disponibilidad y cuota de cada proveedor.
