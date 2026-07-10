"""
gerar_llms_txt.py — Camada 4 GEO: gera /llms.txt do hub agregador safie.blog.br.

O hub não tem índice completo: lista as últimas publicações da rede
(data/ultimos_posts.json, regenerado diariamente pelo workflow fetch_posts.yml)
e aponta para os 5 blogs vinculados, cada um com seu próprio llms.txt completo.

Uso:
  python3 scripts/gerar_llms_txt.py
"""

import json
from pathlib import Path

BASE     = Path(__file__).resolve().parent.parent
POSTS    = BASE / "data" / "ultimos_posts.json"
LLMS_TXT = BASE / "llms.txt"

BLOGS = [
    ("SAFIE Reforma Tributária", "https://reformatributaria.safie.blog.br",
     "impactos da reforma tributária (EC 132/2023) para empresas"),
    ("SAFIE Fintechs", "https://fintechs.safie.blog.br",
     "regulação e tributação para fintechs"),
    ("SAFIE E-commerce", "https://ecommerce.safie.blog.br",
     "jurídico e tributário para comércio eletrônico"),
    ("SAFIE Cripto", "https://cripto.safie.blog.br",
     "regulação e tributação de criptoativos"),
    ("SAFIE IA for Business", "https://ia.safie.blog.br",
     "implicações jurídicas do uso de IA em empresas"),
]


def _resumo_curto(resumo: str) -> str:
    resumo = (resumo or "").strip()
    primeira = resumo.split(". ")[0].rstrip(".")
    if len(primeira) < 30:
        return resumo[:200].rstrip()
    return primeira


def gerar_llms_txt() -> Path:
    dados = json.loads(POSTS.read_text(encoding="utf-8"))
    posts = dados.get("posts", []) if isinstance(dados, dict) else dados

    linhas = [
        "# SAFIE — Rede de Blogs",
        "",
        "> Rede de blogs da SAFIE (consultoria jurídico-contábil para negócios digitais)",
        "> cobrindo Reforma Tributária, Fintechs, E-commerce, Criptoativos e IA aplicada",
        "> a negócios. Este é o hub agregador; conteúdo detalhado nos blogs vinculados.",
        "",
        "## Últimas publicações da rede",
        "",
    ]
    for post in posts:
        titulo, url = post.get("titulo", ""), post.get("url", "")
        if not titulo or not url:
            continue
        linhas.append(f"- [{titulo}]({url}): {_resumo_curto(post.get('resumo', ''))}")
    linhas += ["", "## Blogs da rede", ""]
    for nome, url, desc in BLOGS:
        linhas.append(f"- [{nome}]({url}) — [llms.txt]({url}/llms.txt): {desc}")
    linhas += [
        "",
        "## Sobre",
        "",
        "- [Sobre a SAFIE](https://safie.com.br): consultoria jurídico-contábil para negócios digitais",
        "- [Contato](https://safie.com.br/contato)",
        "",
    ]
    LLMS_TXT.write_text("\n".join(linhas), encoding="utf-8")
    return LLMS_TXT


if __name__ == "__main__":
    path = gerar_llms_txt()
    print(f"Gerado: {path} ({path.stat().st_size} bytes, {path.read_text(encoding='utf-8').count(chr(10))} linhas)")
