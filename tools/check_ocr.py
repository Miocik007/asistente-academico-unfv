"""Diagnóstico local seguro de OCR. Uso: python tools/check_ocr.py"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest

if __name__ == '__main__':
    path = ingest._tesseract_path()
    if not ingest.tesseract_available():
        print('OCR LOCAL: NO DISPONIBLE')
        print('Instala Tesseract OCR para Windows con el idioma español (spa).')
        print('Manual: https://github.com/UB-Mannheim/tesseract/wiki')
        raise SystemExit(1)
    import pytesseract
    print('OCR LOCAL: DISPONIBLE')
    print('Ejecutable:', path)
    print('Idiomas:', ', '.join(pytesseract.get_languages(config='')))
    if 'spa' not in pytesseract.get_languages(config=''):
        print('Aviso: faltan datos en español (spa). El OCR de español puede perder precisión.')
