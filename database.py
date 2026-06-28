"""Persistência SQLite — bases, colaboradores e chamados."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "bases.db"
UPLOADS_DIR = ROOT / "uploads" / "chamados"
DATA_JSON = ROOT / "data" / "mapa_cipe.json"

TIPOS_PROBLEMA = [
    "Infiltração / Umidade",
    "Fissura / Trinca",
    "Telhado / Cobertura",
    "Esquadrias / Portas / Janelas",
    "Piso / Revestimento",
    "Elétrica / Hidráulica",
    "Limpeza / Higienização",
    "Segurança / Cerca / Muro",
    "Outro",
]

STATUS_CHAMADO = ["Aberto", "Em análise", "Em conserto", "Resolvido", "Cancelado"]


def agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    with conectar() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS setores (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                cor TEXT NOT NULL,
                municipios TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS bases (
                id TEXT PRIMARY KEY,
                titulo TEXT NOT NULL,
                setor_id INTEGER NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                endereco TEXT DEFAULT '',
                telefone TEXT DEFAULT '',
                link_maps TEXT DEFAULT '',
                observacao TEXT DEFAULT '',
                destaque INTEGER DEFAULT 0,
                em_estruturacao INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                ordem INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS colaboradores (
                id TEXT PRIMARY KEY,
                base_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                funcao TEXT DEFAULT '',
                telefone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (base_id) REFERENCES bases(id)
            );
            CREATE TABLE IF NOT EXISTS chamados (
                id TEXT PRIMARY KEY,
                base_id TEXT NOT NULL,
                tipo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                autor_nome TEXT DEFAULT '',
                autor_contato TEXT DEFAULT '',
                foto_path TEXT DEFAULT '',
                status TEXT DEFAULT 'Aberto',
                nota_admin TEXT DEFAULT '',
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                FOREIGN KEY (base_id) REFERENCES bases(id)
            );
            """
        )
        n = conn.execute("SELECT COUNT(*) FROM bases").fetchone()[0]
        if n == 0 and DATA_JSON.exists():
            _seed(conn)
        _migrar_bases(conn)


def _migrar_bases(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(bases)").fetchall()}
    if "link_maps" not in cols:
        conn.execute("ALTER TABLE bases ADD COLUMN link_maps TEXT DEFAULT ''")


def link_maps_base(base: dict) -> str | None:
    """Link do Google Maps — usa o cadastrado na admin ou fallback por coordenadas."""
    custom = (base.get("link_maps") or "").strip()
    if custom:
        return custom
    lat, lng = base.get("lat"), base.get("lng")
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps?q={lat},{lng}"
    return None


def _seed(conn: sqlite3.Connection) -> None:
    with DATA_JSON.open(encoding="utf-8") as f:
        dados = json.load(f)
    for s in dados.get("setores", []):
        conn.execute(
            """
            INSERT OR IGNORE INTO setores (id, nome, cor, municipios)
            VALUES (?, ?, ?, ?)
            """,
            (s["id"], s["nome"], s["cor"], json.dumps(s.get("municipios", []), ensure_ascii=False)),
        )
    for i, p in enumerate(dados.get("pontos", [])):
        if p.get("tipo") != "base":
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO bases (
                id, titulo, setor_id, lat, lng, endereco, telefone, observacao,
                destaque, em_estruturacao, ordem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"],
                p["titulo"],
                p["setor_id"],
                p["lat"],
                p["lng"],
                p.get("endereco") or "",
                p.get("telefone") or "",
                p.get("observacao") or "",
                1 if p.get("destaque") else 0,
                1 if p.get("em_estruturacao") else 0,
                i + 1,
            ),
        )


def listar_setores() -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("SELECT * FROM setores ORDER BY id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["municipios"] = json.loads(d["municipios"] or "[]")
        out.append(d)
    return out


def listar_bases(apenas_ativas: bool = True) -> list[dict]:
    q = "SELECT * FROM bases"
    if apenas_ativas:
        q += " WHERE ativo = 1"
    q += " ORDER BY ordem, titulo"
    with conectar() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def obter_base(base_id: str) -> dict | None:
    with conectar() as conn:
        row = conn.execute("SELECT * FROM bases WHERE id = ?", (base_id,)).fetchone()
    return dict(row) if row else None


def salvar_base(dados: dict) -> None:
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO bases (
                id, titulo, setor_id, lat, lng, endereco, telefone, link_maps, observacao,
                destaque, em_estruturacao, ativo, ordem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                titulo=excluded.titulo, setor_id=excluded.setor_id,
                lat=excluded.lat, lng=excluded.lng, endereco=excluded.endereco,
                telefone=excluded.telefone, link_maps=excluded.link_maps,
                observacao=excluded.observacao,
                destaque=excluded.destaque, em_estruturacao=excluded.em_estruturacao,
                ativo=excluded.ativo, ordem=excluded.ordem
            """,
            (
                dados["id"],
                dados["titulo"],
                dados["setor_id"],
                dados["lat"],
                dados["lng"],
                dados.get("endereco") or "",
                dados.get("telefone") or "",
                dados.get("link_maps") or "",
                dados.get("observacao") or "",
                1 if dados.get("destaque") else 0,
                1 if dados.get("em_estruturacao") else 0,
                1 if dados.get("ativo", True) else 0,
                int(dados.get("ordem") or 0),
            ),
        )


def remover_base(base_id: str) -> None:
    """Oculta da consulta pública (soft delete)."""
    with conectar() as conn:
        conn.execute("UPDATE bases SET ativo = 0 WHERE id = ?", (base_id,))


def excluir_base(base_id: str) -> None:
    """Remove permanentemente base, colaboradores e chamados vinculados."""
    with conectar() as conn:
        conn.execute("DELETE FROM chamados WHERE base_id = ?", (base_id,))
        conn.execute("DELETE FROM colaboradores WHERE base_id = ?", (base_id,))
        conn.execute("DELETE FROM bases WHERE id = ?", (base_id,))
def listar_colaboradores(base_id: str | None = None, apenas_ativos: bool = True) -> list[dict]:
    q = "SELECT * FROM colaboradores WHERE 1=1"
    params: list = []
    if base_id:
        q += " AND base_id = ?"
        params.append(base_id)
    if apenas_ativos:
        q += " AND ativo = 1"
    q += " ORDER BY nome"
    with conectar() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def salvar_colaborador(dados: dict) -> None:
    cid = dados.get("id") or f"col_{uuid.uuid4().hex[:10]}"
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO colaboradores (id, base_id, nome, funcao, telefone, email, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                base_id=excluded.base_id, nome=excluded.nome, funcao=excluded.funcao,
                telefone=excluded.telefone, email=excluded.email, ativo=excluded.ativo
            """,
            (
                cid,
                dados["base_id"],
                dados["nome"],
                dados.get("funcao") or "",
                dados.get("telefone") or "",
                dados.get("email") or "",
                1 if dados.get("ativo", True) else 0,
            ),
        )


def remover_colaborador(col_id: str) -> None:
    with conectar() as conn:
        conn.execute("UPDATE colaboradores SET ativo = 0 WHERE id = ?", (col_id,))


def criar_chamado(dados: dict) -> str:
    cid = f"ch_{uuid.uuid4().hex[:10]}"
    ts = agora()
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO chamados (
                id, base_id, tipo, descricao, autor_nome, autor_contato,
                foto_path, status, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Aberto', ?, ?)
            """,
            (
                cid,
                dados["base_id"],
                dados["tipo"],
                dados["descricao"],
                dados.get("autor_nome") or "",
                dados.get("autor_contato") or "",
                dados.get("foto_path") or "",
                ts,
                ts,
            ),
        )
    return cid


def listar_chamados(base_id: str | None = None, status: str | None = None) -> list[dict]:
    q = """
        SELECT c.*, b.titulo AS base_titulo
        FROM chamados c
        JOIN bases b ON b.id = c.base_id
        WHERE 1=1
    """
    params: list = []
    if base_id:
        q += " AND c.base_id = ?"
        params.append(base_id)
    if status:
        q += " AND c.status = ?"
        params.append(status)
    q += " ORDER BY c.criado_em DESC"
    with conectar() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def atualizar_chamado(chamado_id: str, status: str, nota_admin: str = "") -> None:
    with conectar() as conn:
        conn.execute(
            """
            UPDATE chamados SET status = ?, nota_admin = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (status, nota_admin, agora(), chamado_id),
        )


def atualizar_foto_chamado(chamado_id: str, foto_path: str) -> None:
    with conectar() as conn:
        conn.execute(
            "UPDATE chamados SET foto_path = ?, atualizado_em = ? WHERE id = ?",
            (foto_path, agora(), chamado_id),
        )


def contar_chamados_abertos() -> int:
    with conectar() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM chamados WHERE status IN ('Aberto','Em análise','Em conserto')"
        ).fetchone()[0]


def salvar_setor(dados: dict) -> None:
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO setores (id, nome, cor, municipios)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, cor=excluded.cor, municipios=excluded.municipios
            """,
            (
                dados["id"],
                dados["nome"],
                dados["cor"],
                json.dumps(dados.get("municipios") or [], ensure_ascii=False),
            ),
        )
