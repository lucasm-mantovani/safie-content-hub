"""
fetch_posts.py
Busca os artigos mais recentes dos 5 blogs da rede SAFIE e gera data/ultimos_posts.json.
Fonte: /artigos/indice.json de cada blog via Cloudflare Pages (URL pública, sem autenticação).
Roda via GitHub Actions todos os dias às 9h BRT ou manualmente.
"""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BLOGS = [
    {
        "nome": "SAFIE Cripto",
        "slug": "cripto",
        "url": "https://cripto.safie.blog.br",
        "pages_url": "https://safie-blog-cripto.pages.dev",
        "cor": "#4a9eff",
    },
    {
        "nome": "SAFIE E-commerce",
        "slug": "ecommerce",
        "url": "https://ecommerce.safie.blog.br",
        "pages_url": "https://safie-blog-ecommerce.pages.dev",
        "cor": "#ff6b9d",
    },
    {
        "nome": "SAFIE Fintechs",
        "slug": "fintechs",
        "url": "https://fintechs.safie.blog.br",
        "pages_url": "https://safie-blog-fintechs.pages.dev",
        "cor": "#3dd68c",
    },
    {
        "nome": "SAFIE IA for Business",
        "slug": "ia",
        "url": "https://ia.safie.blog.br",
        "pages_url": "https://safie-blog-ia-for-business.pages.dev",
        "cor": "#a78bfa",
    },
    {
        "nome": "SAFIE Reforma Tributária",
        "slug": "reforma-tributaria",
        "url": "https://reformatributaria.safie.blog.br",
        "pages_url": "https://safie-blog-reforma-tributaria.pages.dev",
        "cor": "#d4a857",
    },
]

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]

ARTIGOS_POR_BLOG = 3
TOTAL_MAXIMO = 15


def formatar_data(data_str: str) -> str:
    dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
    return f"{dt.day} {MESES[dt.month - 1]} {dt.year}"


def buscar_indice(blog: dict) -> list:
    url = f"{blog['pages_url']}/artigos/indice.json"
    req = urllib.request.Request(url, headers={"User-Agent": "SAFIE-ContentHub/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


posts = []
for blog in BLOGS:
    try:
        indice = buscar_indice(blog)
        print(f"[OK] {blog['nome']}: {len(indice)} artigos encontrados")
    except Exception as e:
        print(f"[ERRO] {blog['nome']}: {e}")
        continue

    for artigo in indice[:ARTIGOS_POR_BLOG]:
        data_str = artigo["data"]
        data_iso = data_str[:10]
        resumo = artigo["resumo"]
        if len(resumo) > 200:
            resumo = resumo[:200].rstrip() + "…"
        posts.append({
            "blog": blog["nome"],
            "blog_slug": blog["slug"],
            "blog_url": blog["url"],
            "cor": blog["cor"],
            "slug": artigo["slug"],
            "titulo": artigo["titulo"],
            "resumo": resumo,
            "tema": artigo["tema"],
            "data_iso": data_iso,
            "data": formatar_data(data_str),
            "url": f"{blog['url']}/artigos/{artigo['slug']}",
        })

posts.sort(key=lambda p: p["data_iso"], reverse=True)

saida = {
    "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "posts": posts[:TOTAL_MAXIMO],
}

BASE = Path(__file__).parent.parent
destino = BASE / "data" / "ultimos_posts.json"
destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ {len(saida['posts'])} posts gravados em {destino}")
