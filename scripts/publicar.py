"""
publicar.py — Pipeline unificado do SAFIE Blog (safie.blog.br)

Lê dados/artigo_gerado.json, gera o HTML do artigo (template A1 unificado),
a capa em paleta SAFIE, atualiza índice único (com nicho), home JS-driven,
página da categoria e do nicho, sitemap, llms.txt (C4) e commit.

Camadas GEO preservadas:
  C3 — gerar_relacionados_html (cross-categoria, dedup por título)
  C4 — gerar_llms_txt (import + try/except)

Uso:
  python3 scripts/publicar.py
  python3 scripts/publicar.py --sem-git
"""

import json
import re
import subprocess
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import os

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE            = Path(__file__).resolve().parent.parent
CONFIG_SITE     = BASE / "config" / "site.json"
CONFIG_CATEGORIAS = BASE / "config" / "categorias.json"
ARTIGO_PATH     = BASE / "dados" / "artigo_gerado.json"
TEMPLATE_ART    = BASE / "templates" / "artigo.html"
TEMPLATE_CAT    = BASE / "templates" / "categoria.html"
TEMPLATE_NICHO  = BASE / "templates" / "nicho.html"
TEMPLATE_IMG    = BASE / "templates" / "imagem-artigo.svg"
PARTIAL_HEADER  = BASE / "templates" / "partials" / "header.html"
PARTIAL_FOOTER  = BASE / "templates" / "partials" / "footer.html"
ARTIGOS_DIR     = BASE / "artigos"
CATEGORIAS_DIR  = BASE / "categorias"
IMGS_DIR        = BASE / "assets" / "img" / "artigos"
INDICE_JSON     = BASE / "artigos" / "indice.json"
SITEMAP         = BASE / "sitemap.xml"
LOG_DIR         = BASE / "logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
hoje = datetime.now().strftime("%Y-%m-%d")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"publicacao_{hoje}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

load_dotenv(BASE / ".env")

# ── Constantes ────────────────────────────────────────────────────────────────
MESES_ABREV = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]
# Paleta SAFIE (decisão A2.1): capa NOVA sem cor de nicho.
COR_ACENTO_SAFIE = "#154EFA"


# ── Helpers ───────────────────────────────────────────────────────────────────

def ler_json(caminho, padrao):
    p = Path(caminho)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Erro ao ler {caminho}: {e}")
    return padrao


def salvar_json(caminho, dados):
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def preencher_template(template: str, variaveis: dict) -> str:
    for chave, valor in variaveis.items():
        template = template.replace(f"{{{{{chave}}}}}", str(valor) if valor else "")
    return template


def data_amigavel(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        meses = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
        return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"
    except Exception:
        return iso


def data_capa(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{dt.day:02d} {MESES_ABREV[dt.month-1]} {dt.year}"
    except Exception:
        return ""


def escapar_xml(texto: str) -> str:
    return (texto
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def quebrar_titulo(titulo: str) -> tuple:
    """Divide o título em até 3 linhas equilibradas respeitando palavras inteiras."""
    n = len(titulo)
    palavras = titulo.split()

    if n <= 25 or len(palavras) == 1:
        return titulo, "", ""

    if n <= 50:
        melhor = (float("inf"), 1)
        for i in range(1, len(palavras)):
            l1 = " ".join(palavras[:i])
            l2 = " ".join(palavras[i:])
            diff = abs(len(l1) - len(l2))
            if diff < melhor[0]:
                melhor = (diff, i)
        c = melhor[1]
        return " ".join(palavras[:c]), " ".join(palavras[c:]), ""

    alvo = n // 3
    melhor = (float("inf"), 1, 2)
    for i in range(1, len(palavras) - 1):
        for j in range(i + 1, len(palavras)):
            l1 = " ".join(palavras[:i])
            l2 = " ".join(palavras[i:j])
            l3 = " ".join(palavras[j:])
            if not l3:
                continue
            custo = (len(l1) - alvo) ** 2 + (len(l2) - alvo) ** 2 + (len(l3) - alvo) ** 2
            if custo < melhor[0]:
                melhor = (custo, i, j)
    _, i, j = melhor
    return " ".join(palavras[:i]), " ".join(palavras[i:j]), " ".join(palavras[j:])


def _partial(path: Path, ano: str = "") -> str:
    txt = path.read_text(encoding="utf-8") if path.exists() else ""
    return txt.replace("{{ANO}}", ano)


# ── 0. Gerar imagem de capa (paleta SAFIE — sem cor de nicho) ──────────────────

def gerar_imagem_capa(artigo: dict, config_site: dict) -> tuple:
    """Gera o SVG de capa em paleta SAFIE (azul #154EFA + navy).
    Retorna (url_completa, url_relativa)."""
    if not TEMPLATE_IMG.exists():
        log.warning(f"Template de imagem não encontrado: {TEMPLATE_IMG}")
        return "", ""

    IMGS_DIR.mkdir(parents=True, exist_ok=True)

    slug      = artigo["slug"]
    titulo    = artigo["titulo"]
    tema      = artigo.get("tema_nome", "")
    data      = data_capa(artigo.get("data_iso", ""))
    nome_blog = config_site.get("nome", "SAFIE Blog")
    url_blog  = config_site.get("url_completa", "https://safie.blog.br")
    cor_dest  = COR_ACENTO_SAFIE   # fixo — sem cor de nicho (A2.1)
    cor_bco   = "#ffffff"

    l1, l2, l3 = quebrar_titulo(titulo)

    if l3:
        c1, c2, c3 = cor_bco, cor_bco, cor_dest
    elif l2:
        c1, c2, c3 = cor_bco, cor_dest, cor_dest
    else:
        c1, c2, c3 = cor_dest, cor_dest, cor_dest

    variaveis = {
        "TITULO_LINHA_1": escapar_xml(l1),
        "TITULO_LINHA_2": escapar_xml(l2),
        "TITULO_LINHA_3": escapar_xml(l3),
        "COR_LINHA_1":    c1,
        "COR_LINHA_2":    c2,
        "COR_LINHA_3":    c3,
        "CATEGORIA":      escapar_xml(tema.upper()),
        "DATA":           data,
        "NOME_BLOG":      escapar_xml(nome_blog),
    }

    svg = preencher_template(TEMPLATE_IMG.read_text(encoding="utf-8"), variaveis)
    destino = IMGS_DIR / f"{slug}.svg"
    destino.write_text(svg, encoding="utf-8")
    log.info(f"Imagem de capa gerada (paleta SAFIE): {destino}")

    rel = f"/assets/img/artigos/{slug}.svg"
    return f"{url_blog}{rel}", rel


# ── 1. Gerar HTML do artigo (template A1 unificado) ────────────────────────────

def gerar_html_artigo(artigo: dict, config_site: dict, categoria: dict,
                      imagem_url: str = "", imagem_rel: str = "") -> Path:
    template = TEMPLATE_ART.read_text(encoding="utf-8")
    ano      = datetime.now().strftime("%Y")

    bloco_imagem = (
        f'<img class="artigo-capa" src="{imagem_rel}" '
        f'alt="{artigo["titulo"]} — capa ilustrativa do artigo sobre {artigo.get("tema_nome", "")}" '
        f'width="1200" height="630" loading="lazy">'
        if imagem_rel else ""
    )

    variaveis = {
        "HEADER":           _partial(PARTIAL_HEADER),
        "FOOTER":           _partial(PARTIAL_FOOTER, ano),
        "NICHO":            artigo.get("nicho", ""),
        "TITULO":           artigo["titulo"],
        "META_DESCRIPTION": artigo["meta_description"],
        "CANONICAL_URL":    artigo["canonical_url"],
        "DATA_ISO":         artigo["data_iso"],
        "DATA_FORMATADA":   artigo["data_formatada"],
        "TEMPO_LEITURA":    artigo["tempo_leitura"],
        "TEMA":             artigo["tema_nome"],
        "TEMA_SLUG":        artigo["tema_slug"],
        "RESUMO_EXECUTIVO": artigo["resumo_executivo"],
        "CONTEUDO":         artigo["conteudo"],
        "FAQ_HTML":         artigo["faq_html"],
        "REFERENCIAS_HTML": artigo["referencias_html"],
        "RELACIONADOS_HTML":artigo["relacionados_html"],
        "SCHEMA_JSON":      artigo["schema_json"],
        "PALAVRAS_CHAVE":   artigo.get("palavras_chave", ""),
        "ANO":              ano,
        "IMAGEM_CAPA_URL":  imagem_url,
        "IMAGEM_BLOCO":     bloco_imagem,
    }

    html = preencher_template(template, variaveis)

    ARTIGOS_DIR.mkdir(exist_ok=True)
    destino = ARTIGOS_DIR / f"{artigo['slug']}.html"
    destino.write_text(html, encoding="utf-8")
    log.info(f"HTML do artigo gerado: {destino}")
    return destino


# ── 2. Atualizar índice único (com nicho) ──────────────────────────────────────

def atualizar_indice(artigo: dict):
    indice = ler_json(INDICE_JSON, [])
    slug   = artigo["slug"]

    indice = [a for a in indice if a.get("slug") != slug]
    indice.insert(0, {
        "slug":      slug,
        "titulo":    artigo["titulo"],
        "resumo":    artigo["resumo_executivo"][:200],
        "tema":      artigo["tema_nome"],
        "tema_slug": artigo["tema_slug"],
        "nicho":     artigo.get("nicho", ""),
        "data":      artigo["data_iso"],
    })
    salvar_json(INDICE_JSON, indice)
    log.info(f"Índice único atualizado ({len(indice)} artigos)")


# ── Artigos relacionados (Camada 3 GEO — cross-categoria) ──────────────────────

def gerar_relacionados_html(artigo: dict, indice: list, max_itens: int = 3,
                            cross_categoria: bool = True) -> str:
    """C3 GEO: 'Continue lendo' com relacionados reais.
    Mesma categoria (desc por data) → fallback outras categorias (se cross_categoria).
    Exclui o próprio artigo e títulos repetidos (dedup case-insensitive)."""
    slug_atual   = artigo.get("slug", "")
    tema_atual   = artigo.get("tema_slug", "")
    titulo_atual = (artigo.get("titulo") or "").strip().lower()

    def _ordenar(itens):
        return sorted(itens, key=lambda a: a.get("data", ""), reverse=True)

    mesmo_tema = _ordenar([a for a in indice if a.get("tema_slug") == tema_atual])
    outros     = _ordenar([a for a in indice if a.get("tema_slug") != tema_atual]) if cross_categoria else []

    titulos_usados = {titulo_atual}
    escolhidos = []
    for a in mesmo_tema + outros:
        if len(escolhidos) >= max_itens:
            break
        if a.get("slug") == slug_atual:
            continue
        t = (a.get("titulo") or "").strip()
        if not t or t.lower() in titulos_usados:
            continue
        titulos_usados.add(t.lower())
        escolhidos.append(a)

    if not escolhidos:
        return '<p style="color:var(--cinza);font-size:0.9rem;">Mais artigos em breve.</p>'

    itens = "\n".join(f'  <li><a href="/artigos/{a["slug"]}">{a["titulo"]}</a></li>'
                      for a in escolhidos)
    return f'<ul class="relacionados-items">\n{itens}\n</ul>'


# ── 3. Home (JS-driven) ────────────────────────────────────────────────────────

def atualizar_home(indice: list, config_site: dict):
    # Home é JS-driven: lê /artigos/indice.json via main.js. indice.json já atualizado.
    log.info(f"Home JS-driven: indice.json com {len(indice)} artigos (nada a reescrever).")


# ── 4. Página de categoria (gera categorias/{slug}.html do template A1) ────────

def atualizar_pagina_categoria(cat_slug: str, categorias: list, config_site: dict):
    categoria = next((c for c in categorias if c.get("slug") == cat_slug), None)
    if not categoria:
        log.warning(f"[categoria] slug '{cat_slug}' não encontrado em categorias.json")
        return
    nicho = categoria.get("nicho", "")
    nicho_nome = config_site.get("nichos", {}).get(nicho, {}).get("nome", nicho)
    ano = datetime.now().strftime("%Y")

    html = preencher_template(TEMPLATE_CAT.read_text(encoding="utf-8"), {
        "HEADER":              _partial(PARTIAL_HEADER),
        "FOOTER":              _partial(PARTIAL_FOOTER, ano),
        "CATEGORIA_NOME":      categoria.get("nome", cat_slug),
        "CATEGORIA_SLUG":      cat_slug,
        "CATEGORIA_DESCRICAO": categoria.get("descricao", ""),
        "NICHO":               nicho,
        "NICHO_NOME":          nicho_nome,
    })
    CATEGORIAS_DIR.mkdir(exist_ok=True)
    destino = CATEGORIAS_DIR / f"{cat_slug}.html"
    destino.write_text(html, encoding="utf-8")
    log.info(f"Página de categoria gerada: {destino}")


# ── 4b. Página de nicho (agregadora — categorias/{nicho}.html) ─────────────────

def atualizar_pagina_nicho(nicho: str, categorias: list, config_site: dict):
    bloco = config_site.get("nichos", {}).get(nicho, {})
    ano = datetime.now().strftime("%Y")
    html = preencher_template(TEMPLATE_NICHO.read_text(encoding="utf-8"), {
        "HEADER":          _partial(PARTIAL_HEADER),
        "FOOTER":          _partial(PARTIAL_FOOTER, ano),
        "NICHO":           nicho,
        "NICHO_NOME":      bloco.get("nome", nicho),
        "NICHO_DESCRICAO": bloco.get("descricao", ""),
    })
    CATEGORIAS_DIR.mkdir(exist_ok=True)
    destino = CATEGORIAS_DIR / f"{nicho}.html"
    destino.write_text(html, encoding="utf-8")
    log.info(f"Página de nicho gerada: {destino}")


# ── 5. Sitemap ──────────────────────────────────────────────────────────────

def atualizar_sitemap(artigo: dict, config_site: dict):
    url_blog   = config_site.get("url_completa", "https://safie.blog.br")
    url_artigo = f"{url_blog}/artigos/{artigo['slug']}"
    data_hoje  = datetime.now().strftime("%Y-%m-%d")

    novo_url = (
        f"\n  <url>\n"
        f"    <loc>{url_artigo}</loc>\n"
        f"    <lastmod>{data_hoje}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.9</priority>\n"
        f"  </url>"
    )

    if not SITEMAP.exists():
        SITEMAP.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '  <!-- Artigos adicionados automaticamente pelo publicar.py -->\n'
            '</urlset>\n',
            encoding="utf-8",
        )

    conteudo = SITEMAP.read_text(encoding="utf-8")
    if url_artigo in conteudo:
        log.info("Sitemap: URL já existe, pulando.")
        return

    if "<!-- Artigos" in conteudo:
        conteudo = conteudo.replace(
            "<!-- Artigos adicionados automaticamente pelo publicar.py -->",
            f"<!-- Artigos adicionados automaticamente pelo publicar.py -->{novo_url}"
        )
    else:
        conteudo = conteudo.replace("</urlset>", f"{novo_url}\n\n</urlset>")

    SITEMAP.write_text(conteudo, encoding="utf-8")
    log.info("Sitemap atualizado")


# ── 6. Git commit + push (branch atual — nunca hardcode main) ──────────────────

def git_commit_push(artigo: dict):
    data_fmt = datetime.now().strftime("%Y-%m-%d")
    msg = f"post: {data_fmt} — {artigo['titulo'][:60]}"

    def run(cmd):
        result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
        if result.returncode != 0:
            log.warning(f"Git: {' '.join(cmd)} — {result.stderr.strip()}")
        return result.returncode == 0, result.stdout.strip()

    slug = artigo["slug"]
    cat_slug = artigo.get("tema_slug")
    nicho = artigo.get("nicho")
    log.info("[Git] Add cirúrgico (artefatos públicos do pipeline)...")
    arquivos = [
        f"artigos/{slug}.html",
        f"assets/img/artigos/{slug}.svg",
        "artigos/indice.json",
        "sitemap.xml",
        "llms.txt",
    ]
    if cat_slug:
        arquivos.append(f"categorias/{cat_slug}.html")
    if nicho:
        arquivos.append(f"categorias/{nicho}.html")
    for arquivo in arquivos:
        if (BASE / arquivo).exists():
            run(["git", "add", arquivo])
        else:
            log.warning(f"[Git] Artefato ausente, não adicionado: {arquivo}")

    ok, _ = run(["git", "commit", "-m", msg])
    if not ok:
        log.info("[Git] Nada para commitar.")
        return

    ok, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch or "main"
    log.info(f"[Git] Push para origin {branch}...")
    ok, _ = run(["git", "push", "origin", branch])
    if ok:
        log.info("[Git] Push concluído.")
    else:
        log.error("[Git] Falha no push (verifique remote).")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(sem_git: bool = False):
    log.info("=" * 60)
    log.info("PUBLICAR ARTIGO — início")

    artigo      = ler_json(ARTIGO_PATH, {})
    config_site = ler_json(CONFIG_SITE, {})
    categorias  = ler_json(CONFIG_CATEGORIAS, [])

    if not artigo:
        log.error(f"Nenhum artigo encontrado em {ARTIGO_PATH}")
        sys.exit(1)

    categoria = next((c for c in categorias if c.get("slug") == artigo.get("tema_slug")), {})
    log.info(f"Publicando: '{artigo['titulo']}' (categoria {artigo.get('tema_slug')}, nicho {artigo.get('nicho')})")

    # 0. Capa em paleta SAFIE
    imagem_url, imagem_rel = gerar_imagem_capa(artigo, config_site)

    # C3: relacionados reais (índice ainda sem o artigo novo)
    try:
        artigo["relacionados_html"] = gerar_relacionados_html(artigo, ler_json(INDICE_JSON, []))
    except Exception as e:
        log.warning(f"[relacionados] Falha (não bloqueia; fallback = placeholder): {e}")

    gerar_html_artigo(artigo, config_site, categoria, imagem_url, imagem_rel)
    atualizar_indice(artigo)

    # C4: llms.txt (corpo reescrito em A2.3; chamada protegida por try/except)
    try:
        from gerar_llms_txt import gerar_llms_txt
        gerar_llms_txt()
        log.info("llms.txt atualizado (Camada 4 GEO)")
    except Exception as e:
        log.warning(f"[llms.txt] Falha ao gerar (não bloqueia; C4 reescrita em A2.3): {e}")

    indice = ler_json(INDICE_JSON, [])
    atualizar_home(indice, config_site)
    if artigo.get("tema_slug"):
        atualizar_pagina_categoria(artigo["tema_slug"], categorias, config_site)
    if artigo.get("nicho"):
        atualizar_pagina_nicho(artigo["nicho"], categorias, config_site)
    atualizar_sitemap(artigo, config_site)

    if not sem_git:
        git_commit_push(artigo)
    else:
        log.info("[Git] Modo --sem-git: commit e push pulados.")

    log.info("=" * 60)
    log.info(f"PUBLICAÇÃO CONCLUÍDA: {artigo['canonical_url']}")
    log.info("=" * 60)
    return artigo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publica artigo no SAFIE Blog (unificado)")
    parser.add_argument("--sem-git", action="store_true", help="Gera arquivos mas não faz commit/push")
    args = parser.parse_args()
    main(sem_git=args.sem_git)
