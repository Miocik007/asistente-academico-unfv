"""Evaluación de 30 casos sobre un corpus didáctico controlado, con APIs reales.

NO es un benchmark exhaustivo: el CSV necesita verificación humana de contenido.
Por defecto limita llamadas y permite más solo por opción --limit.
"""
import argparse
import csv
import json
import re
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agents import Orchestrator, NOT_AVAILABLE, _tokens

parser=argparse.ArgumentParser()
parser.add_argument('--limit',type=int,default=5,help='Casos a ejecutar (hasta 30); consumen cuota API')
args=parser.parse_args()
if not 1<=args.limit<=30:
    parser.error('--limit debe estar entre 1 y 30')
conf_path=ROOT/'.streamlit'/'secrets.toml'
if not conf_path.exists():
    sys.exit('Falta .streamlit/secrets.toml')
with conf_path.open('rb') as f:
    cfg=tomllib.load(f)
for k in ('NVIDIA_API_KEY','GOOGLE_API_KEY'):
    if not cfg.get(k) or str(cfg[k]).startswith('PEGA_'):
        sys.exit(f'Configura {k}')

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

nvidia=ChatOpenAI(base_url='https://integrate.api.nvidia.com/v1',
    api_key=cfg['NVIDIA_API_KEY'],model=cfg.get('NVIDIA_MODEL','nvidia/nemotron-3-ultra-550b-a55b'),
    temperature=1.0,max_tokens=2000,timeout=90,max_retries=1,
    extra_body={'chat_template_kwargs':{'enable_thinking':False}})
gemini=ChatGoogleGenerativeAI(model=cfg.get('GEMINI_MODEL','gemini-3.8-flash'),
    google_api_key=cfg['GOOGLE_API_KEY'],temperature=0.1)

raw=(ROOT/'evaluacion'/'material_de_prueba.txt').read_text(encoding='utf-8')
docs=[]
for i,line in enumerate(raw.splitlines()[1:],1):
    docs.append(SimpleNamespace(page_content=line,metadata={'source':'material_de_prueba.txt',
                                                             'page':i,'method':'texto'}))

class DemoStore:
    def __init__(self,docs):
        self.docstore=SimpleNamespace(_dict={i:d for i,d in enumerate(docs)})
    def similarity_search_with_score(self,question,k=5):
        q=set(_tokens(question))
        matched=[]
        for d in self.docstore._dict.values():
            score=len(q & set(_tokens(d.page_content)))
            if score:
                matched.append((d,-score))
        return sorted(matched,key=lambda x:x[1])[:k]

cases=json.loads((ROOT/'evaluacion'/'casos_30.json').read_text(encoding='utf-8'))
output=ROOT/'evaluacion'/'resultados_live.csv'
rows=[]
for idx,item in enumerate(cases[:args.limit],1):
    print(f'Prueba {idx}/{args.limit} — {item["categoria"]}',flush=True)
    try:
        result=Orchestrator(nvidia,DemoStore(docs),['Investigación'],
                            verifier_llm=gemini).answer(item['pregunta'])
        response=result.answer
        row={'id':item['id'],'categoria':item['categoria'],'pregunta':item['pregunta'],
             'esperado':item['expected'],'respuesta':response,'abstencion':int(NOT_AVAILABLE in response),
             'citas':len(re.findall(r'\[\d+\]',response)),
             'auditoria_orientativa':result.confidence or '',
             'duracion_ms':result.total_ms,'error':'','revision_humana':''}
    except Exception as e:
        row={'id':item['id'],'categoria':item['categoria'],'pregunta':item['pregunta'],
             'esperado':item['expected'],'respuesta':'','abstencion':'','citas':'',
             'auditoria_orientativa':'','duracion_ms':'','error':type(e).__name__,
             'revision_humana':''}
    rows.append(row)
    with output.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys())
        writer.writeheader();writer.writerows(rows)
print(f'Archivo generado: {output}')
print('Revisar manualmente exactitud y correspondencia de cada cita; no atribuir precisión automáticamente.')
