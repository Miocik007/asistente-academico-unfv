"""Página: Sistema multiagente.

Muestra la arquitectura de agentes, qué hace cada uno, y la traza real de las
últimas ejecuciones (guardadas en la base de datos), con métricas de
fiabilidad y latencia.
"""

import pandas as pd
import streamlit as st

import agents
import db
import theme

ARCHITECTURE_DOT = """
digraph G {
  rankdir=LR;
  bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11,
        fillcolor="#FFF3E6", color="#D97706", fontcolor="#28313F", margin="0.14,0.08"];
  edge [color="#667085", fontname="Helvetica", fontsize=9, fontcolor="#667085"];

  user  [label="Estudiante", shape=ellipse, fillcolor="#F1F3F5", color="#667085"];
  docs  [label="PDF, Word / imágenes", shape=folder, fillcolor="#F1F3F5", color="#667085"];
  ocr   [label="👁️ Agente OCR"];
  topics[label="🏷️ Agente de temas"];
  index [label="Índice FAISS\n(archivo + página)", shape=cylinder, fillcolor="#F1F3F5", color="#667085"];
  plan  [label="🧭 Planificador"];
  ret   [label="🔎 Recuperador\nvectores + palabras clave"];
  tutor [label="🎓 Tutor\nNVIDIA"];
  ver   [label="🛡️ Verificador\nGemini → NVIDIA"];
  gen   [label="📝 Generador de quiz"];
  sol   [label="🧪 Solucionador"];
  coach [label="🧑‍🏫 Coach"];
  db    [label="SQLite\nprogreso y trazas", shape=cylinder, fillcolor="#F1F3F5", color="#667085"];

  docs -> ocr [label="páginas sin texto"];
  ocr -> index; docs -> index [label="texto nativo"];
  docs -> topics; topics -> db;

  user -> plan [label="pregunta"];
  plan -> ret [label="sub-consultas"];
  index -> ret;
  ret -> tutor [label="fuentes [n]"];
  tutor -> ver [label="borrador"];
  ver -> tutor [label="si hay dudas:\ncorregir", style=dashed];
  ver -> user [label="respuesta + fiabilidad"];
  plan -> db [label="tema", style=dotted];

  db -> gen [label="puntos débiles"];
  ret -> gen [style=dotted];
  gen -> sol [label="preguntas"];
  sol -> db [label="solo claves\nvalidadas"];
  db -> coach; coach -> user [label="plan de estudio"];
}
"""


def render():
    theme.render_header(
        "Sistema multiagente",
        "Cada agente tiene un rol único; un orquestador los coordina y deja una traza auditable de cada decisión.",
    )

    st.graphviz_chart(ARCHITECTURE_DOT, use_container_width=True)

    st.markdown("##### Agentes y responsabilidades")
    st.dataframe(
        pd.DataFrame(
            [
                {"Agente": f"{icon} {name}", "Rol": role}
                for name, (icon, role) in agents.AGENT_REGISTRY.items()
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    runs = db.get_recent_agent_runs(limit=100)
    if not runs:
        theme.render_empty_state(
            "Aún no hay ejecuciones registradas",
            "Haz una pregunta en el Asistente o genera una evaluación y aquí verás la traza de cada agente.",
        )
        return

    _render_metrics(runs)
    _render_latency(runs)

    st.markdown("##### Últimas ejecuciones")
    for run in runs[:15]:
        kind = {"chat": "💬", "quiz": "📝", "coach": "🧑‍🏫"}.get(run["kind"], "🤖")
        conf = f" · fiabilidad {run['confidence']}/100" if run.get("confidence") is not None else ""
        label = f"{kind} {run['question'][:80]}{conf} · {run['total_ms'] / 1000:.1f} s"
        with st.expander(label):
            st.caption(f"{run['created_at']} · intención: {run.get('intent') or '—'} · tema: {run.get('topic') or '—'}")
            st.markdown(agents.trace_to_markdown(run["trace"]), unsafe_allow_html=True)


def _render_metrics(runs):
    chats = [r for r in runs if r["kind"] == "chat"]
    confs = [r["confidence"] for r in chats if r.get("confidence") is not None]
    revised = sum(1 for r in chats if r.get("revised"))
    avg_ms = sum(r["total_ms"] for r in runs) / len(runs) if runs else 0
    theme.render_stat_row(
        [
            ("Ejecuciones", len(runs), None),
            ("Fiabilidad media", f"{round(sum(confs) / len(confs))}/100" if confs else "—", theme.SUCCESS),
            ("Respuestas corregidas", revised, theme.WARNING),
            ("Tiempo medio", f"{avg_ms / 1000:.1f} s", None),
        ]
    )


def _render_latency(runs):
    totals = {}
    for r in runs:
        for step in r["trace"]:
            key = f"{step.get('icon', '')} {step.get('agent', '?')}"
            totals.setdefault(key, []).append(step.get("ms", 0))
    if not totals:
        return
    st.markdown("##### Tiempo medio por agente (ms)")
    df = pd.DataFrame(
        {"Agente": list(totals.keys()),
         "ms": [round(sum(v) / len(v)) for v in totals.values()]}
    ).set_index("Agente")
    st.bar_chart(df, color=theme.PRIMARY, use_container_width=True)
