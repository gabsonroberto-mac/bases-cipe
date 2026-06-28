"""Mapa Folium com setores coloridos e marcadores das bases."""

from __future__ import annotations

import json
from pathlib import Path

import folium
from folium import GeoJson

from database import link_maps_base

GEOJSON_PATH = Path(__file__).parent / "data" / "mapa_delimitadores.geojson"

CORES_SETOR = {1: "#2E7D32", 2: "#EF6C00", 3: "#1565C0"}


def _cor_setor(setor_id: int, setores: list[dict]) -> str:
    for s in setores:
        if s["id"] == setor_id:
            return s.get("cor") or CORES_SETOR.get(setor_id, "#1a3a5c")
    return CORES_SETOR.get(setor_id, "#1a3a5c")


def criar_mapa(bases: list[dict], setores: list[dict]) -> folium.Map:
    m = folium.Map(location=[-13.05, -39.15], zoom_start=9, tiles="OpenStreetMap")

    if GEOJSON_PATH.exists():
        with GEOJSON_PATH.open(encoding="utf-8") as f:
            geo = json.load(f)
        for feat in geo.get("features", []):
            sid = feat.get("properties", {}).get("setor_id", 0)
            cor = _cor_setor(int(sid), setores)
            GeoJson(
                feat,
                style_function=lambda _x, c=cor: {
                    "fillColor": c,
                    "color": c,
                    "weight": 2,
                    "fillOpacity": 0.25,
                },
            ).add_to(m)

    for b in bases:
        sid = b["setor_id"]
        cor = _cor_setor(sid, setores)
        popup_html = (
            f"<b>{b['titulo']}</b><br>"
            f"{b.get('endereco') or ''}<br>"
            f"{b.get('telefone') or ''}"
        )
        maps_url = link_maps_base(b)
        if maps_url:
            popup_html += f"<br><a href='{maps_url}' target='_blank'>Abrir no Google Maps</a>"
        folium.Marker(
            [b["lat"], b["lng"]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=b["titulo"],
            icon=folium.Icon(color="green" if sid == 1 else "orange" if sid == 2 else "blue", icon="home"),
        ).add_to(m)

    return m
