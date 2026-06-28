# Consulta de Bases – CIPE Recôncavo

Python + Streamlit no Render.com

## Funcionalidades

- **Mapa** com setores coloridos (GeoJSON) + pinos das bases
- **Lista de bases** com colaboradores e telefones
- **Reportar problema** — chamado com foto (manutenção)
- **Administração** (PIN padrão: `cipe2026`) — bases, colaboradores, chamados, setores

## Arquivos importantes

```
app.py
database.py
mapa.py
data/mapa_cipe.json
data/mapa_delimitadores.geojson   ← mapa colorido por setor
```

## Deploy Render

Push no GitHub → Render redeploy automático.

**Nota:** no plano grátis, chamados/fotos/colaboradores ficam no SQLite local do container — podem resetar ao redeploy. Para produção, use disco persistente no Render ou banco externo.

## WhatsApp

```
Consulta de Bases – CIPE Recôncavo
👉 https://bases.applab.cloud
```
