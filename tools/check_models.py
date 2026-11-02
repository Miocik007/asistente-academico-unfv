"""Prueba ambas conexiones con las claves en secrets.toml; no imprime credenciales."""
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / '.streamlit' / 'secrets.toml'
if not path.exists():
    sys.exit('Crea .streamlit/secrets.toml desde el archivo .example.')
with path.open('rb') as f:
    config = tomllib.load(f)

def key(name):
    value = config.get(name, '')
    if not value or 'PEGA_' in str(value):
        sys.exit(f'Falta configurar {name} en secrets.toml.')
    return value

from openai import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

print('Comprobando NVIDIA Nemotron...')
try:
    cli = OpenAI(base_url='https://integrate.api.nvidia.com/v1',
                 api_key=key('NVIDIA_API_KEY'),timeout=45,max_retries=0)
    ans = cli.chat.completions.create(
        model=config.get('NVIDIA_MODEL','nvidia/nemotron-3-ultra-550b-a55b'),
        messages=[{'role':'user','content':'Responde solo: conexión NVIDIA correcta'}],
        temperature=1,max_tokens=90,
        extra_body={'chat_template_kwargs':{'enable_thinking':False}},stream=False)
    print('NVIDIA:', 'OK' if ans.choices and ans.choices[0].message.content else 'Sin texto')
except Exception as exc:
    print('NVIDIA: FALLÓ',type(exc).__name__, 'Revisa clave, cuota y conectividad.')

print('Comprobando Gemini...')
try:
    model=ChatGoogleGenerativeAI(model=config.get('GEMINI_MODEL','gemini-3.8-flash'),
                                 google_api_key=key('GOOGLE_API_KEY'),temperature=0.1,
                                 max_retries=0,timeout=30)
    result=model.invoke('Responde solo: conexión Gemini correcta')
    print('Gemini:', 'OK' if result.content else 'Sin texto')
except Exception as exc:
    print('Gemini: FALLÓ',type(exc).__name__, 'Revisa clave, cuota y modelo.')
