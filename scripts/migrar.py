"""
migrar.py — Migração dos 476 artigos dos 5 blogs para o SAFIE Blog unificado.

LÊ (read-only) dos 5 repos em ~/CLAUDE/Blogs-SAFIE/Blog-*.
ESCREVE só no worktree ~/CLAUDE/safie-blog-unificado.

Transforma cada artigo antigo (chrome/domínio/paths dos blogs) na página
unificada: domínio safie.blog.br, /temas/→/categorias/, header/footer unificados
(com form), CSS style.css+artigo.css, breadcrumb visível, "Continue lendo"
cross-categoria. Consolida os 5 indice.json em 1 (+nicho). Gera categorias,
nichos, índices, home, sitemap e llms.txt.

Disciplina: HARD-FAIL em qualquer inconsistência (nunca adivinhar). Idempotente
(limpa artigos/capas migrados antes de rodar).

Uso:
  python3 scripts/migrar.py --amostra   # 1 artigo por nicho (5), para validação
  python3 scripts/migrar.py             # os 476
"""

import re
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

WT    = Path(__file__).resolve().parent.parent
BLOGS = Path.home() / "CLAUDE" / "Blogs-SAFIE"
sys.path.insert(0, str(WT / "scripts"))

import publicar as P              # reusa gerar_relacionados_html, atualizar_pagina_*
import gerar_llms_txt as LLMS

NICHO_POR_REPO = {
    "Blog-Cripto": "cripto",
    "Blog-ecommerce": "ecommerce",
    "Blog-fintechs": "fintechs",
    "Blog-ia-for-business": "ia",
    "Blog-reforma-tributaria": "reforma",
}
# subdomínio antigo por nicho (para reescrita de domínio)
SUBDOMINIO = {"cripto": "cripto", "ecommerce": "ecommerce", "fintechs": "fintechs",
              "ia": "ia", "reforma": "reformatributaria"}
# nome antigo do blog (para reescrever <title>/og:site_name → "SAFIE Blog")
NOME_BLOG = {"cripto": "SAFIE Cripto", "ecommerce": "SAFIE E-commerce",
             "fintechs": "SAFIE Fintechs", "ia": "SAFIE IA for Business",
             "reforma": "SAFIE Reforma Tributária"}

BASE_URL       = "https://safie.blog.br"
ARTIGOS_DIR    = WT / "artigos"
CAPAS_DIR      = WT / "assets" / "img" / "artigos"
CATEGORIAS_DIR = WT / "categorias"
INDICE_JSON    = WT / "artigos" / "indice.json"
SITEMAP        = WT / "sitemap.xml"
INDEX_HTML     = WT / "index.html"
CONFIG_SITE    = WT / "config" / "site.json"
CONFIG_CAT     = WT / "config" / "categorias.json"
PART_HEADER    = WT / "templates" / "partials" / "header.html"
PART_FOOTER    = WT / "templates" / "partials" / "footer.html"
T_CATEGORIA    = WT / "templates" / "categoria.html"
T_NICHO        = WT / "templates" / "nicho.html"
T_LISTAGEM     = WT / "templates" / "listagem.html"
T_HOME         = WT / "templates" / "home.html"

ANO = datetime.now().strftime("%Y")


class MigracaoError(Exception):
    pass


def _ler(p, padrao):
    if Path(p).exists():
        try:
            return json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            pass
    return padrao


def _partial(path, ano=""):
    return path.read_text(encoding="utf-8").strip().replace("{{ANO}}", ano)


# ── 1a. Consolidar índices ─────────────────────────────────────────────────────

def consolidar_indice(nichos_filtrar=None):
    consolidado = []
    for repo, nicho in NICHO_POR_REPO.items():
        if nichos_filtrar and nicho not in nichos_filtrar:
            continue
        idx = _ler(BLOGS / repo / "artigos" / "indice.json", [])
        for a in idx:
            a = dict(a)
            a["nicho"] = nicho
            consolidado.append(a)
    return consolidado


# ── 1d/1e/1f. Transformar um HTML de artigo ────────────────────────────────────

def transformar_html(slug, nicho, indice_completo, header_html, footer_html, categorias):
    """Retorna (html_transformado, erros[list]). Não escreve. Não levanta —
    acumula erros para hard-fail centralizado."""
    erros = []
    src = BLOGS / [r for r, n in NICHO_POR_REPO.items() if n == nicho][0] / "artigos" / f"{slug}.html"
    if not src.exists():
        return None, [f"{slug}: HTML de origem não encontrado ({src})"]
    html = src.read_text(encoding="utf-8")

    # asserts de estrutura de entrada (nunca adivinhar)
    if "/assets/css/estilo.css" not in html:
        erros.append(f"{slug}: sem link estilo.css (estrutura inesperada)")
    if html.count('<header class="site-header"') != 1:
        erros.append(f"{slug}: header site-header != 1")
    if html.count('<footer class="site-footer"') != 1:
        erros.append(f"{slug}: footer site-footer != 1")
    if 'rel="canonical"' not in html:
        erros.append(f"{slug}: sem canonical")
    if "application/ld+json" not in html:
        erros.append(f"{slug}: sem JSON-LD")
    if html.count("<main>") != 1:
        erros.append(f"{slug}: <main> != 1")
    # tema_slug do índice (fonte da verdade para breadcrumb)
    entrada = next((a for a in indice_completo if a.get("slug") == slug), None)
    if not entrada:
        erros.append(f"{slug}: ausente no índice consolidado")
    if erros:
        return None, erros

    tema_slug = entrada.get("tema_slug", "")
    tema_nome = entrada.get("tema_nome") or entrada.get("tema", "")
    titulo    = entrada.get("titulo", "")

    # (1) domínio: TODOS os 5 subdomínios → safie.blog.br
    for sub in SUBDOMINIO.values():
        html = html.replace(f"{sub}.safie.blog.br", "safie.blog.br")
    # (2) path /temas/ → /categorias/
    html = html.replace("/temas/", "/categorias/")
    # (3) nome do blog → SAFIE Blog (title, og:site_name, twitter)
    html = html.replace(NOME_BLOG[nicho], "SAFIE Blog")
    # (4) CSS estilo.css → style.css + artigo.css
    html, n_css = re.subn(
        r'<link rel="stylesheet" href="/assets/css/estilo\.css">',
        '<link rel="stylesheet" href="/assets/css/style.css">\n'
        '  <link rel="stylesheet" href="/assets/css/artigo.css">',
        html, count=1)
    if n_css != 1:
        erros.append(f"{slug}: substituição de estilo.css falhou (n={n_css})")
    # (5) header → partial unificado
    html, n_h = re.subn(r'<header class="site-header".*?</header>', lambda m: header_html, html, count=1, flags=re.S)
    if n_h != 1:
        erros.append(f"{slug}: substituição de header falhou (n={n_h})")
    # (6) footer → partial unificado (com form)
    html, n_f = re.subn(r'<footer class="site-footer".*?</footer>', lambda m: footer_html, html, count=1, flags=re.S)
    if n_f != 1:
        erros.append(f"{slug}: substituição de footer falhou (n={n_f})")
    # (7) body: garantir data-nicho (analytics), sem cor inline
    html, _ = re.subn(r"<body[^>]*>", f'<body data-nicho="{nicho}">', html, count=1)
    # (8) tracker de analytics: blog → nicho
    html = re.sub(r"blog:\s*'[^']*'", f"blog: '{nicho}'", html)
    # (9) breadcrumb visível (mesmo formato do template A1 — 3 níveis) após <main>
    bc = (
        '\n<nav class="breadcrumb" aria-label="Trilha de navegação">\n'
        '  <div class="container">\n'
        '    <a href="/">Início</a> <span aria-hidden="true">›</span>\n'
        f'    <a href="/categorias/{tema_slug}">{tema_nome}</a> <span aria-hidden="true">›</span>\n'
        f'    <span aria-current="page">{titulo}</span>\n'
        '  </div>\n</nav>\n'
    )
    html, n_bc = re.subn(r"<main>", "<main>" + bc, html, count=1)
    if n_bc != 1:
        erros.append(f"{slug}: inserção de breadcrumb falhou (n={n_bc})")
    # (10) Continue lendo cross-categoria (C3) — substitui o inner de .relacionados-lista
    art_ctx = {"slug": slug, "tema_slug": tema_slug, "titulo": titulo}
    rel = P.gerar_relacionados_html(art_ctx, indice_completo, cross_categoria=True)
    html, n_rel = re.subn(r'(<div class="relacionados-lista">).*?(</div>)',
                          lambda m: m.group(1) + "\n" + rel + "\n" + m.group(2),
                          html, count=1, flags=re.S)
    if n_rel != 1:
        erros.append(f"{slug}: regeneração de relacionados falhou (n={n_rel})")

    # ── validações de saída (hard-fail) ──
    for sub in SUBDOMINIO.values():
        if f"{sub}.safie.blog.br" in html:
            erros.append(f"{slug}: domínio antigo remanescente ({sub}.safie.blog.br)")
    if "/temas/" in html:
        erros.append(f"{slug}: /temas/ remanescente")
    if 'data-form="rodape"' not in html:
        erros.append(f"{slug}: footer sem form (não substituído)")
    if "/assets/css/style.css" not in html or "/assets/css/artigo.css" not in html:
        erros.append(f"{slug}: CSS unificado ausente")
    if 'class="breadcrumb"' not in html or "/categorias/" not in html:
        erros.append(f"{slug}: breadcrumb/categorias ausente")
    # JSON-LD deve parsear após reescrita
    for bloco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(bloco)
        except Exception as e:
            erros.append(f"{slug}: JSON-LD inválido pós-reescrita ({e})")
            break

    return html, erros


# ── 1g. Páginas geradas ────────────────────────────────────────────────────────

def gerar_categorias_index(categorias, site, indice=None):
    """Página /categorias/ (nível superior): cards de categoria agrupados por
    nicho, com contador de artigos por categoria (do índice). Paleta SAFIE
    unificada — sem cor de nicho no chrome (diferenciação por header de grupo)."""
    indice = indice or []
    contagem = {}
    for a in indice:
        ts = a.get("tema_slug", "")
        if ts:
            contagem[ts] = contagem.get(ts, 0) + 1

    def _plural(n):
        return "1 artigo" if n == 1 else f"{n} artigos"

    nichos = site.get("nichos", {})
    linhas = []
    for nicho, bloco in nichos.items():
        cats = [c for c in categorias if c.get("nicho") == nicho]
        if not cats:
            continue
        linhas.append(f'<section class="cat-grupo"><h2>{bloco.get("nome", nicho)}</h2>')
        linhas.append('<div class="categorias-cards-grid" role="list">')
        for c in cats:
            n = contagem.get(c["slug"], 0)
            desc = c.get("descricao", "")
            linhas.append(
                f'  <a class="card-categoria" role="listitem" href="/categorias/{c["slug"]}">'
                f'<h3>{c["nome"]}</h3>'
                f'<p>{desc}</p>'
                f'<span class="card-categoria-count">{_plural(n)}</span></a>'
            )
        linhas.append('</div></section>')
    corpo = "\n".join(linhas)
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Categorias — SAFIE Blog</title>
<meta name="description" content="Todas as categorias do SAFIE Blog, organizadas por área: cripto, e-commerce, fintechs, IA e reforma tributária.">
<link rel="canonical" href="{BASE_URL}/categorias/">
<link rel="stylesheet" href="/assets/css/style.css">
<link rel="icon" href="/favicon.ico" sizes="any">
</head><body>
{_partial(PART_HEADER)}
<main><section class="container">
<div class="secao-header" style="text-align:center;margin-bottom:8px;">
<p class="secao-kicker">Explorar</p><h1>Categorias</h1>
<p class="categorias-intro">Análises jurídicas e contábeis organizadas por área. Escolha um tema para ver os artigos.</p>
</div>
{corpo}
</section></main>
{_partial(PART_FOOTER, ANO)}
</body></html>
"""
    (CATEGORIAS_DIR / "index.html").write_text(html, encoding="utf-8")


def gerar_pagina_de_template(template_path, destino):
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{{HEADER}}", _partial(PART_HEADER)).replace("{{FOOTER}}", _partial(PART_FOOTER, ANO))
    Path(destino).write_text(html, encoding="utf-8")


def gerar_sitemap(indice, categorias, site):
    urls = [f"{BASE_URL}/", f"{BASE_URL}/artigos/", f"{BASE_URL}/categorias/", f"{BASE_URL}/busca"]
    urls += [f"{BASE_URL}/categorias/{n}" for n in site.get("nichos", {})]
    urls += [f"{BASE_URL}/categorias/{c['slug']}" for c in categorias]
    urls += [f"{BASE_URL}/artigos/{a['slug']}" for a in indice]
    hoje = datetime.now().strftime("%Y-%m-%d")
    body = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{hoje}</lastmod>\n  </url>" for u in urls
    )
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n", encoding="utf-8")


# ── Orquestrador ────────────────────────────────────────────────────────────────

def _limpar_saida(slugs):
    """Idempotência: remove artigos/capas migrados (preserva .gitkeep)."""
    for s in slugs:
        (ARTIGOS_DIR / f"{s}.html").unlink(missing_ok=True)
        (CAPAS_DIR / f"{s}.svg").unlink(missing_ok=True)


def main(amostra=False):
    site       = _ler(CONFIG_SITE, {})
    categorias = _ler(CONFIG_CAT, [])

    nichos_filtrar = set(NICHO_POR_REPO.values()) if not amostra else None
    indice_full = consolidar_indice()  # sempre os 476 (contexto de relacionados)

    # 1a asserts
    slugs = [a["slug"] for a in indice_full]
    dup = sorted({s for s in slugs if slugs.count(s) > 1})
    if not amostra and len(indice_full) < 476:
        raise MigracaoError(f"1a: regressão — {len(indice_full)} artigos (< snapshot A3 de 476)")
    if dup:
        raise MigracaoError(f"1a: slugs duplicados entre blogs: {dup}")

    # conflito de path: nicho vs slug de categoria (páginas /categorias/{x})
    conflito = set(NICHO_POR_REPO.values()) & {c["slug"] for c in categorias}
    if conflito:
        raise MigracaoError(f"1g: conflito de path nicho×categoria em /categorias/: {conflito}")

    # amostra: 1 artigo por nicho (preferir com camadas GEO)
    if amostra:
        alvo = []
        for nicho in NICHO_POR_REPO.values():
            cand = [a for a in indice_full if a["nicho"] == nicho]
            escolha = None
            for a in cand:  # tenta achar um com key_takeaways/tabela/citação
                h = (BLOGS / [r for r, n in NICHO_POR_REPO.items() if n == nicho][0]
                     / "artigos" / f"{a['slug']}.html")
                if h.exists() and "key-takeaways" in h.read_text(encoding="utf-8"):
                    escolha = a; break
            alvo.append(escolha or (cand[0] if cand else None))
        alvo = [a for a in alvo if a]
    else:
        alvo = indice_full

    header_html = _partial(PART_HEADER)
    footer_html = _partial(PART_FOOTER, ANO)

    # limpar saída dos alvos (idempotência)
    _limpar_saida([a["slug"] for a in alvo])

    # transformar (acumula erros; hard-fail se qualquer um)
    resultados, erros_todos = {}, []
    for a in alvo:
        html, erros = transformar_html(a["slug"], a["nicho"], indice_full,
                                       header_html, footer_html, categorias)
        if erros:
            erros_todos.extend(erros)
        else:
            resultados[a["slug"]] = html
    if erros_todos:
        raise MigracaoError("TRANSFORM hard-fail (%d erro[s]):\n  - %s" %
                            (len(erros_todos), "\n  - ".join(erros_todos[:40])))

    # escrever HTMLs (1b)
    ARTIGOS_DIR.mkdir(exist_ok=True)
    for slug, html in resultados.items():
        (ARTIGOS_DIR / f"{slug}.html").write_text(html, encoding="utf-8")

    # capas (1c) — hard-fail listando ausentes
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    sem_capa = []
    for a in alvo:
        repo = [r for r, n in NICHO_POR_REPO.items() if n == a["nicho"]][0]
        origem = BLOGS / repo / "assets" / "img" / "artigos" / f"{a['slug']}.svg"
        if origem.exists():
            shutil.copy2(origem, CAPAS_DIR / f"{a['slug']}.svg")
        else:
            sem_capa.append(a["slug"])

    # índice consolidado (só na migração completa; amostra não sobrescreve o final)
    if not amostra:
        idx_norm = [{"slug": a["slug"], "titulo": a.get("titulo", ""),
                     "resumo": (a.get("resumo") or "")[:200],
                     "tema": a.get("tema") or a.get("tema_nome", ""),
                     "tema_slug": a.get("tema_slug", ""), "nicho": a["nicho"],
                     "data": a.get("data", "")} for a in indice_full]
        idx_norm.sort(key=lambda x: x.get("data", ""), reverse=True)
        INDICE_JSON.write_text(json.dumps(idx_norm, ensure_ascii=False, indent=2), encoding="utf-8")

        # páginas (1g)
        for c in categorias:
            P.atualizar_pagina_categoria(c["slug"], categorias, site)
        for nicho in site.get("nichos", {}):
            P.atualizar_pagina_nicho(nicho, categorias, site)
        gerar_categorias_index(categorias, site, idx_norm)
        gerar_pagina_de_template(T_LISTAGEM, ARTIGOS_DIR / "index.html")
        gerar_pagina_de_template(T_HOME, INDEX_HTML)
        gerar_sitemap(idx_norm, categorias, site)
        LLMS.gerar_llms_txt()

        # validações finais de contagem
        n_html = len([p for p in ARTIGOS_DIR.glob("*.html") if p.stem != "index"])
        if n_html != len(indice_full):
            raise MigracaoError(f"FINAL: {n_html} HTMLs em artigos/ (esperado {len(indice_full)} = in)")

    return {"processados": len(resultados), "sem_capa": sem_capa, "amostra": amostra}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Migra os artigos dos 5 blogs para o unificado")
    ap.add_argument("--amostra", action="store_true", help="1 artigo por nicho (5) para validação")
    args = ap.parse_args()
    try:
        r = main(amostra=args.amostra)
    except MigracaoError as e:
        print("HARD-FAIL:", e)
        sys.exit(1)
    print(f"\nOK — processados: {r['processados']}{' [AMOSTRA]' if r['amostra'] else ''}")
    if r["sem_capa"]:
        print(f"SEM CAPA ({len(r['sem_capa'])}): {r['sem_capa']}")
