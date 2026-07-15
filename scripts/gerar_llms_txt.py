"""
gerar_llms_txt.py — Camada 4 GEO: gera /llms.txt do SAFIE Blog unificado.

Lê o índice único local (artigos/indice.json) + config/site.json +
config/categorias.json e gera o llms.txt na raiz. Sem agregação remota.

Robusto a índice vazio (gera cabeçalho + categorias mesmo sem artigos).
Importável: from gerar_llms_txt import gerar_llms_txt

Uso:
  python3 scripts/gerar_llms_txt.py
"""

import json
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
INDICE      = BASE / "artigos" / "indice.json"
SITE        = BASE / "config" / "site.json"
CATEGORIAS  = BASE / "config" / "categorias.json"
LLMS_TXT    = BASE / "llms.txt"


def _ler_json(caminho: Path, padrao):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            pass
    return padrao


def _resumo_curto(resumo: str) -> str:
    """Primeira frase do resumo (split '. '); fallback 200 chars."""
    resumo = (resumo or "").strip()
    primeira = resumo.split(". ")[0].rstrip(".")
    if len(primeira) < 30:
        return resumo[:200].rstrip()
    return primeira


def gerar_llms_txt() -> Path:
    site  = _ler_json(SITE, {})
    cats  = _ler_json(CATEGORIAS, [])
    idx   = _ler_json(INDICE, [])

    base_url = site.get("url_completa", "https://safie.blog.br").rstrip("/")
    nome     = site.get("nome", "SAFIE Blog")
    descricao = site.get("descricao", "Direito e contabilidade para negócios digitais")
    nichos   = site.get("nichos", {})

    linhas = [
        f"# {nome}",
        "",
        f"> {descricao}. Consultoria jurídico-contábil para negócios digitais.",
        "> Artigos assinados pelos sócios (Lucas Mantovani e Ítalo Cunha).",
        "",
        "> Nota: conteúdo informativo, não constitui parecer jurídico. Artigos podem ter",
        "> títulos semelhantes por cobrir diferentes ângulos do mesmo tema; considere a",
        "> data e o resumo.",
        "",
        "## Categorias",
        "",
    ]

    # Categorias agrupadas por nicho (ordem do site.json.nichos)
    ordem_nicho = list(nichos.keys()) or sorted({c.get("nicho", "") for c in cats})
    cats_por_nicho = {n: [] for n in ordem_nicho}
    for c in cats:
        cats_por_nicho.setdefault(c.get("nicho", ""), []).append(c)
    for nicho in ordem_nicho:
        for c in cats_por_nicho.get(nicho, []):
            slug = c.get("slug", "")
            desc = (c.get("descricao") or "").strip()
            linha = f"- [{c.get('nome', slug)}]({base_url}/categorias/{slug})"
            linhas.append(f"{linha}: {desc}" if desc else linha)

    # Artigos (mais recente primeiro)
    artigos = sorted(idx, key=lambda a: a.get("data", ""), reverse=True)
    linhas += ["", "## Artigos", ""]
    if artigos:
        for a in artigos:
            titulo, slug = a.get("titulo", ""), a.get("slug", "")
            if not titulo or not slug:
                continue
            resumo = _resumo_curto(a.get("resumo", ""))
            linha = f"- [{titulo}]({base_url}/artigos/{slug})"
            linhas.append(f"{linha}: {resumo}" if resumo else linha)
    else:
        linhas.append("- (nenhum artigo publicado ainda)")

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
    txt = path.read_text(encoding="utf-8")
    print(f"Gerado: {path} ({path.stat().st_size} bytes, {txt.count(chr(10))} linhas)")
