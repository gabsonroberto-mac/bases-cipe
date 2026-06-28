# Consulta de Bases – CIPE Recôncavo

App **Python + Streamlit** — consulta das 9 bases, mapa e municípios por setor.

Sem Flutter, sem Supabase. Dados em `data/mapa_cipe.json` (origem: `consulta_cipe_r`).

## Rodar no PC

```bash
cd streamlit/bases-cipe
pip install -r requirements.txt
streamlit run app.py
```

## Deploy Render.com → bases.applab.cloud

### 1. GitHub

Repositório **`bases-cipe`** (público) com:

- `app.py`
- `requirements.txt`
- `render.yaml`
- `data/mapa_cipe.json`
- `.streamlit/config.toml`

### 2. Render

1. [render.com](https://render.com) → **New +** → **Web Service**
2. Repo **`bases-cipe`**
3. **Create Web Service**
4. URL: `https://bases-cipe.onrender.com`

### 3. Domínio

Render → **Settings** → **Custom Domains** → `bases.applab.cloud` → **Verify**

Hostinger DNS:

| Tipo | Nome | Valor |
|------|------|-------|
| CNAME | `bases` | `bases-cipe.onrender.com` |

### 4. Atualizar dados

Edite `data/mapa_cipe.json` no GitHub → push → Render redeploy automático.

## WhatsApp

```
Consulta de Bases – CIPE Recôncavo
👉 https://bases.applab.cloud
```
