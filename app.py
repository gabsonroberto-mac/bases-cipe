"""
Consulta de Bases – CIPE Recôncavo
Chamados com foto · colaboradores · mapa por setor · administração.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

import database as db
from mapa import criar_mapa

UPLOADS = db.UPLOADS_DIR


def admin_pin() -> str:
    try:
        return st.secrets.get("admin_pin", os.environ.get("CIPE_ADMIN_PIN", "cipe2026"))
    except Exception:
        return os.environ.get("CIPE_ADMIN_PIN", "cipe2026")


def admin_logado() -> bool:
    return st.session_state.get("admin_ok") is True


def exigir_admin() -> bool:
    if admin_logado():
        return True
    pin = st.text_input("PIN de administração", type="password", key="pin_admin_tab")
    if pin and pin == admin_pin():
        st.session_state["admin_ok"] = True
        st.rerun()
    if pin:
        st.error("PIN incorreto.")
    st.info("Área restrita à administração.")
    return False


def salvar_foto_chamado(uploaded, chamado_id: str) -> str:
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS / f"{chamado_id}.jpg"
    img = Image.open(uploaded)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > 1600:
        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    img.save(dest, "JPEG", quality=85)
    return str(dest.name)


def url_maps_base(base: dict) -> str | None:
    return db.link_maps_base(base)


def url_maps(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps?q={lat},{lng}"


def fmt_coord(val: float | None) -> str:
    if val is None:
        return ""
    return f"{float(val):.8f}".rstrip("0").rstrip(".")


def parse_coord(texto: str) -> float | None:
    t = (texto or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        return round(float(t), 8)
    except ValueError:
        return None


def extrair_coords_url(url: str) -> tuple[float, float] | None:
    if not url:
        return None
    for pattern in (
        r"@(-?\d+\.?\d*),(-?\d+\.?\d*)",
        r"[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)",
        r"!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)",
    ):
        m = re.search(pattern, url)
        if m:
            return round(float(m.group(1)), 8), round(float(m.group(2)), 8)
    return None


def rotulo_base(b: dict) -> str:
    p = [b["titulo"]]
    if b.get("em_estruturacao"):
        p.append("⚙️ em estruturação")
    elif b.get("destaque"):
        p.append("★ destaque")
    return " — ".join(p)


def form_reportar_problema(base: dict, key: str) -> None:
    st.markdown("#### Reportar problema / chamado")
    with st.form(f"chamado_{key}"):
        tipo = st.selectbox("Tipo do problema", db.TIPOS_PROBLEMA)
        descricao = st.text_area("Descreva o problema *", height=100)
        c1, c2 = st.columns(2)
        with c1:
            autor = st.text_input("Seu nome")
        with c2:
            contato = st.text_input("Telefone / WhatsApp para retorno")
        foto = st.file_uploader("Foto do problema", type=["jpg", "jpeg", "png", "webp"])
        if st.form_submit_button("Enviar chamado", type="primary"):
            if not descricao.strip():
                st.error("Descreva o problema.")
                return
            cid = db.criar_chamado(
                {
                    "base_id": base["id"],
                    "tipo": tipo,
                    "descricao": descricao.strip(),
                    "autor_nome": autor.strip(),
                    "autor_contato": contato.strip(),
                }
            )
            if foto:
                nome = salvar_foto_chamado(foto, cid)
                db.atualizar_foto_chamado(cid, nome)
            st.success(f"Chamado **{cid}** registrado. A equipe responsável foi notificada no painel.")
            st.balloons()


def pagina_consulta() -> None:
    setores = db.listar_setores()
    bases = db.listar_bases()
    busca = st.session_state.get("busca_bases", "")
    filtro_setor = st.session_state.get("filtro_setor", "Todos os setores")

    opcoes = ["Todos os setores"] + [s["nome"] for s in setores]
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        busca = st.text_input("Buscar base", value=busca, placeholder="Ex.: Valença, Laje…")
    with c2:
        filtro_setor = st.selectbox("Setor", opcoes, index=opcoes.index(filtro_setor) if filtro_setor in opcoes else 0)
    with c3:
        abertos = db.contar_chamados_abertos()
        st.metric("Chamados em aberto", abertos)

    st.session_state["busca_bases"] = busca
    st.session_state["filtro_setor"] = filtro_setor

    filtradas = bases
    if filtro_setor != "Todos os setores":
        sid = next(s["id"] for s in setores if s["nome"] == filtro_setor)
        filtradas = [b for b in filtradas if b["setor_id"] == sid]
    if busca.strip():
        q = busca.strip().lower()
        filtradas = [
            b
            for b in filtradas
            if q in b["titulo"].lower()
            or q in (b.get("endereco") or "").lower()
        ]

    aba_mapa, aba_lista, aba_chamados, aba_setores = st.tabs(
        ["Mapa", "Lista de bases", "Chamados recentes", "Municípios"]
    )

    with aba_mapa:
        if not Path(db.ROOT / "data" / "mapa_delimitadores.geojson").exists():
            st.warning(
                "Arquivo `data/mapa_delimitadores.geojson` ausente — mapa mostra só os pinos das bases. "
                "Copie do projeto consulta_cipe_r."
            )
        st.caption("🟢 Setor 1 · 🟠 Setor 2 · 🔵 Setor 3 — áreas coloridas no mapa")
        st_folium(criar_mapa(filtradas, setores), width=None, height=520, returned_objects=[])

    with aba_lista:
        if not filtradas:
            st.info("Nenhuma base encontrada.")
        for b in filtradas:
            setor = next((s for s in setores if s["id"] == b["setor_id"]), None)
            cols = db.listar_colaboradores(b["id"])
            n_ch = len(db.listar_chamados(base_id=b["id"], status="Aberto"))
            titulo = rotulo_base(b)
            if n_ch:
                titulo += f" · 🔧 {n_ch} chamado(s) aberto(s)"
            with st.expander(titulo, expanded=False):
                st.markdown(f"**Setor:** {setor['nome'] if setor else b['setor_id']}")
                st.markdown(f"**Endereço:** {b.get('endereco') or '—'}")
                if b.get("telefone"):
                    st.markdown(f"**Telefone da base:** {b['telefone']}")
                if b.get("observacao"):
                    st.markdown(f"**Observação:** {b['observacao']}")

                st.markdown("**Colaboradores / contatos da guarnição**")
                if cols:
                    for col in cols:
                        linha = f"**{col['nome']}**"
                        if col.get("funcao"):
                            linha += f" — _{col['funcao']}_"
                        st.markdown(linha)
                        ct = []
                        if col.get("telefone"):
                            ct.append(f"📞 {col['telefone']}")
                        if col.get("email"):
                            ct.append(f"✉️ {col['email']}")
                        if ct:
                            st.caption(" · ".join(ct))
                else:
                    st.caption("Nenhum colaborador cadastrado — administração pode incluir.")

                st.link_button("Google Maps", url_maps_base(b) or url_maps(b["lat"], b["lng"]))
                if st.button("Reportar problema nesta base", key=f"btn_ch_{b['id']}"):
                    st.session_state["reportar_base"] = b["id"]
                if st.session_state.get("reportar_base") == b["id"]:
                    form_reportar_problema(b, b["id"])

    with aba_chamados:
        chamados = db.listar_chamados()
        if not chamados:
            st.info("Nenhum chamado registrado ainda.")
        for ch in chamados[:30]:
            with st.expander(f"{ch['base_titulo']} — {ch['tipo']} ({ch['status']})"):
                st.markdown(ch["descricao"])
                st.caption(f"Protocolo: {ch['id']} · {ch['criado_em']}")
                if ch.get("autor_nome") or ch.get("autor_contato"):
                    st.caption(f"Contato: {ch.get('autor_nome') or '—'} · {ch.get('autor_contato') or '—'}")
                if ch.get("foto_path"):
                    fp = UPLOADS / ch["foto_path"]
                    if fp.exists():
                        st.image(str(fp), caption="Foto do problema", use_container_width=True)

    with aba_setores:
        for s in setores:
            with st.expander(f"{s['nome']} — {len(s['municipios'])} municípios"):
                st.markdown(", ".join(sorted(s["municipios"])))


def pagina_admin() -> None:
    if not exigir_admin():
        return

    st.success("Administração liberada.")
    setores = db.listar_setores()

    aba_ch, aba_bases, aba_colab, aba_set = st.tabs(
        ["Chamados", "Bases / pontos no mapa", "Colaboradores", "Setores"]
    )

    with aba_ch:
        st.markdown("### Gerenciar chamados")
        for ch in db.listar_chamados():
            with st.expander(f"{ch['id']} — {ch['base_titulo']} — {ch['status']}"):
                st.markdown(f"**Tipo:** {ch['tipo']}")
                st.markdown(ch["descricao"])
                if ch.get("foto_path"):
                    fp = UPLOADS / ch["foto_path"]
                    if fp.exists():
                        st.image(str(fp), use_container_width=True)
                idx = db.STATUS_CHAMADO.index(ch["status"]) if ch["status"] in db.STATUS_CHAMADO else 0
                novo = st.selectbox("Status", db.STATUS_CHAMADO, index=idx, key=f"st_{ch['id']}")
                nota = st.text_area("Nota interna", value=ch.get("nota_admin") or "", key=f"nt_{ch['id']}")
                if st.button("Salvar chamado", key=f"sv_{ch['id']}"):
                    db.atualizar_chamado(ch["id"], novo, nota.strip())
                    st.success("Atualizado.")
                    st.rerun()

    with aba_bases:
        st.markdown("### Editar ou adicionar base")
        bases = db.listar_bases(apenas_ativas=False)

        with st.expander("Ver todas as bases (ativas e ocultas)", expanded=False):
            if not bases:
                st.caption("Nenhuma base cadastrada.")
            for b in bases:
                status = "ativa" if b.get("ativo") else "oculta"
                st.markdown(f"- **{b['titulo']}** · `{b['id']}` · _{status}_")

        ids = ["— nova base —"] + [b["id"] for b in bases]
        esc = st.selectbox("Base", ids, format_func=lambda x: (
            "— nova base —" if x == "— nova base —"
            else f"{db.obter_base(x)['titulo']} ({x})"
            + (" — oculta" if not db.obter_base(x).get("ativo") else "")
        ))
        atual = db.obter_base(esc) if esc != "— nova base —" else None
        editando = esc != "— nova base —"
        with st.form("form_base"):
            bid = st.text_input(
                "ID (slug)",
                value=esc if editando else "base_nova",
                disabled=editando,
                help="O ID não muda ao editar — evita duplicar base por engano.",
            )
            titulo = st.text_input("Nome", value=atual["titulo"] if atual else "")
            setor_id = st.selectbox(
                "Setor",
                [s["id"] for s in setores],
                index=([s["id"] for s in setores].index(atual["setor_id"]) if atual else 0),
                format_func=lambda x: next(s["nome"] for s in setores if s["id"] == x),
            )
            st.caption(
                "Coordenadas: use **ponto** decimal (ex.: `-12.778912`). "
                "No Google Maps: clique com botão direito no local → copie lat, lng."
            )
            c1, c2 = st.columns(2)
            with c1:
                lat_str = st.text_input(
                    "Latitude",
                    value=fmt_coord(atual["lat"]) if atual else "-13.05",
                    placeholder="-12.778912",
                )
            with c2:
                lng_str = st.text_input(
                    "Longitude",
                    value=fmt_coord(atual["lng"]) if atual else "-39.15",
                    placeholder="-38.919234",
                )
            endereco = st.text_input("Endereço", value=atual.get("endereco") if atual else "")
            telefone = st.text_input("Telefone base", value=atual.get("telefone") if atual else "")
            link_maps = st.text_input(
                "Link Google Maps",
                value=atual.get("link_maps") if atual else "",
                placeholder="https://maps.app.goo.gl/... ou link completo do Google Maps",
                help="Abra o local no Google Maps → Compartilhar → Copiar link. "
                "Se preenchido, substitui o link automático das coordenadas.",
            )
            usar_coords_link = st.checkbox(
                "Preencher lat/lng automaticamente do link (quando o link tiver coordenadas na URL)",
                value=False,
            )
            observacao = st.text_area("Observação", value=atual.get("observacao") if atual else "")
            destaque = st.checkbox("Destaque", value=bool(atual.get("destaque")) if atual else False)
            estrut = st.checkbox("Em estruturação", value=bool(atual.get("em_estruturacao")) if atual else False)
            ativo = st.checkbox("Ativa", value=bool(atual.get("ativo", 1)) if atual else True)
            if st.form_submit_button("Salvar base", type="primary"):
                lat = parse_coord(lat_str)
                lng = parse_coord(lng_str)
                if usar_coords_link and link_maps.strip():
                    coords = extrair_coords_url(link_maps.strip())
                    if coords:
                        lat, lng = coords
                    else:
                        st.warning(
                            "Link curto (maps.app.goo.gl) não traz coordenadas na URL. "
                            "Informe lat/lng manualmente ou use link longo do Google Maps."
                        )
                if lat is None or lng is None:
                    st.error("Latitude e longitude inválidas. Exemplo: -12.778912 e -38.919234")
                elif not (-20 <= lat <= -8) or not (-50 <= lng <= -32):
                    st.warning(
                        f"Coordenadas fora da Bahia ({lat}, {lng}). Confira sinal negativo e se não invertou lat/lng."
                    )
                else:
                    salvar_id = esc if editando else bid.strip()
                    db.salvar_base(
                        {
                            "id": salvar_id,
                            "titulo": titulo.strip(),
                            "setor_id": setor_id,
                            "lat": lat,
                            "lng": lng,
                            "endereco": endereco,
                            "telefone": telefone,
                            "link_maps": link_maps.strip(),
                            "observacao": observacao,
                            "destaque": destaque,
                            "em_estruturacao": estrut,
                            "ativo": ativo,
                        }
                    )
                    st.success(f"Base salva · lat **{fmt_coord(lat)}**, lng **{fmt_coord(lng)}**")
                    st.rerun()
        if editando and atual:
            st.caption(
                f"Coordenadas gravadas: **{fmt_coord(atual['lat'])}**, **{fmt_coord(atual['lng'])}**"
            )

        if esc != "— nova base —" and atual:
            st.divider()
            st.markdown("#### Remover base")
            st.caption(
                f"Selecionada: **{atual['titulo']}** (`{esc}`). "
                "Use **Ocultar** para sumir da consulta ou **Excluir** para apagar duplicata."
            )
            c_ocultar, c_excluir = st.columns(2)
            with c_ocultar:
                if st.button("Ocultar da consulta", type="secondary", use_container_width=True):
                    db.remover_base(esc)
                    st.warning("Base ocultada — não aparece mais na consulta pública.")
                    st.rerun()
            with c_excluir:
                confirmar = st.checkbox(
                    "Confirmo exclusão permanente",
                    key=f"confirm_del_{esc}",
                )
                if st.button(
                    "Excluir base permanentemente",
                    type="primary",
                    disabled=not confirmar,
                    use_container_width=True,
                ):
                    db.excluir_base(esc)
                    st.success("Base excluída do sistema.")
                    st.rerun()

    with aba_colab:
        st.markdown("### Colaboradores por base")
        base_id = st.selectbox(
            "Base",
            [b["id"] for b in db.listar_bases()],
            format_func=lambda x: db.obter_base(x)["titulo"],
            key="colab_base",
        )
        for col in db.listar_colaboradores(base_id, apenas_ativos=False):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{col['nome']}** — {col.get('funcao') or '—'} · {col.get('telefone') or '—'}")
            with c2:
                if col["ativo"] and st.button("Remover", key=f"rm_{col['id']}"):
                    db.remover_colaborador(col["id"])
                    st.rerun()
        st.divider()
        with st.form("novo_colab"):
            nome = st.text_input("Nome *")
            funcao = st.text_input("Função (ex.: Comandante, Auxiliar)")
            tel = st.text_input("Telefone / WhatsApp *")
            email = st.text_input("E-mail")
            if st.form_submit_button("Adicionar colaborador"):
                if not nome.strip() or not tel.strip():
                    st.error("Nome e telefone são obrigatórios.")
                else:
                    db.salvar_colaborador(
                        {"base_id": base_id, "nome": nome.strip(), "funcao": funcao, "telefone": tel, "email": email}
                    )
                    st.success("Colaborador adicionado.")
                    st.rerun()

    with aba_set:
        st.markdown("### Setores (cores no mapa)")
        for s in setores:
            with st.expander(s["nome"]):
                municipios_txt = st.text_area(
                    "Municípios (um por linha)",
                    value="\n".join(s["municipios"]),
                    key=f"mun_{s['id']}",
                )
                cor = st.color_picker("Cor do setor no mapa", s["cor"], key=f"cor_{s['id']}")
                if st.button("Salvar setor", key=f"svs_{s['id']}"):
                    mun = [m.strip() for m in municipios_txt.splitlines() if m.strip()]
                    db.salvar_setor({"id": s["id"], "nome": s["nome"], "cor": cor, "municipios": mun})
                    st.success("Setor atualizado.")
                    st.rerun()

    if st.button("Sair da administração"):
        st.session_state.pop("admin_ok", None)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Bases CIPE Recôncavo", page_icon="🏛️", layout="wide")
    db.init_db()

    st.title("Consulta de Bases – CIPE Recôncavo")
    st.caption("PM Bahia · Mapa · contatos · chamados de manutenção")

    tab_consulta, tab_admin = st.tabs(["Consulta", "Administração"])

    with tab_consulta:
        pagina_consulta()

    with tab_admin:
        pagina_admin()

    st.markdown(
        "<p style='text-align:center;color:#888;font-size:11px;margin-top:2rem'>"
        "Desenvolvido por SD PM CASSEANO</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
