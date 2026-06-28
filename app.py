"""
Consulta de Bases – CIPE Recôncavo
Python + Streamlit | deploy Render.com | dados em JSON (consulta_cipe_r).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "mapa_cipe.json"


@st.cache_data
def carregar_dados() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def setor_por_id(setores: list[dict], setor_id: int) -> dict | None:
    return next((s for s in setores if s["id"] == setor_id), None)


def url_maps(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps?q={lat},{lng}"


def rotulo_base(p: dict) -> str:
    partes = [p["titulo"]]
    if p.get("em_estruturacao"):
        partes.append("⚙️ em estruturação")
    elif p.get("destaque"):
        partes.append("★ destaque")
    return " — ".join(partes)


def pagina_mapa(bases: list[dict]) -> None:
    if not bases:
        st.info("Nenhuma base para exibir no mapa.")
        return
    df = pd.DataFrame(
        [{"lat": b["lat"], "lon": b["lng"], "nome": b["titulo"]} for b in bases]
    )
    st.map(df, latitude="lat", longitude="lon", size=200, zoom=8)


def pagina_lista(bases: list[dict], setores: list[dict]) -> None:
    for p in bases:
        setor = setor_por_id(setores, p["setor_id"])
        setor_nome = setor["nome"] if setor else f"Setor {p['setor_id']}"
        with st.expander(rotulo_base(p), expanded=False):
            st.markdown(f"**Setor:** {setor_nome}")
            st.markdown(f"**Endereço:** {p.get('endereco') or '—'}")
            tel = p.get("telefone")
            if tel:
                st.markdown(f"**Telefone:** {tel}")
            obs = p.get("observacao")
            if obs:
                st.markdown(f"**Observação:** {obs}")
            st.link_button(
                "Abrir no Google Maps",
                url_maps(p["lat"], p["lng"]),
                use_container_width=False,
            )


def pagina_setores(setores: list[dict]) -> None:
    for s in setores:
        with st.expander(f"{s['nome']} — {len(s['municipios'])} municípios"):
            cols = st.columns(3)
            municipios = sorted(s["municipios"])
            chunk = (len(municipios) + 2) // 3
            for i, col in enumerate(cols):
                for m in municipios[i * chunk : (i + 1) * chunk]:
                    col.markdown(f"• {m}")


def main() -> None:
    st.set_page_config(
        page_title="Bases CIPE Recôncavo",
        page_icon="🏛️",
        layout="wide",
    )

    dados = carregar_dados()
    setores = dados["setores"]
    todas_bases = [p for p in dados["pontos"] if p.get("tipo") == "base"]

    st.title("Consulta de Bases – CIPE Recôncavo")
    st.caption("PM Bahia · Companhia Independente de Polícia Especializada Recôncavo")

    opcoes_setor = ["Todos os setores"] + [s["nome"] for s in setores]
    c1, c2 = st.columns([2, 1])
    with c1:
        busca = st.text_input("Buscar base ou município", placeholder="Ex.: Valença, Laje…")
    with c2:
        filtro_setor = st.selectbox("Setor", opcoes_setor)

    bases = todas_bases
    if filtro_setor != "Todos os setores":
        sid = next(s["id"] for s in setores if s["nome"] == filtro_setor)
        bases = [b for b in bases if b["setor_id"] == sid]
    if busca.strip():
        q = busca.strip().lower()
        bases = [
            b
            for b in bases
            if q in b["titulo"].lower()
            or q in (b.get("endereco") or "").lower()
            or q in (b.get("observacao") or "").lower()
        ]

    st.metric("Bases encontradas", len(bases))

    aba_mapa, aba_lista, aba_setores = st.tabs(["Mapa", "Lista de bases", "Municípios por setor"])

    with aba_mapa:
        pagina_mapa(bases)

    with aba_lista:
        pagina_lista(bases, setores)

    with aba_setores:
        pagina_setores(setores)

    st.divider()
    st.caption("Dados importados do painel CIPE · atualize o arquivo data/mapa_cipe.json no GitHub.")


if __name__ == "__main__":
    main()
