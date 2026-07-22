"""
backfill_ogimage_raster.py — Dá imagem raster (JPG) ao preview social dos
artigos JÁ PUBLICADOS. Preview social (Facebook/LinkedIn/WhatsApp/X) não
renderiza SVG; hoje og:image/twitter:image/JSON-LD image apontam para .svg.

Para cada capa assets/img/artigos/{slug}.svg:
  1. Rasteriza -> assets/img/artigos/{slug}.jpg (1200x630, via rasterizar_capa).
  2. No artigos/{slug}.html, aponta as 3 tags sociais para o .jpg, SEM tocar no
     conteúdo nem no <img> visível (que continua em .svg, vetorial):
       - og:image                (content .svg -> .jpg)
       - twitter:image           (content .svg -> .jpg)
       - JSON-LD BlogPosting.image.url  (.svg -> .jpg, escopado ao campo "url":)

RECONCILIAÇÃO das duas classes encontradas na investigação:
  - 499 artigos: têm og:image + twitter:image + JSON-LD image (todos .svg) -> reescreve os 3.
  - 10 artigos (os mais antigos, 23-25/04): NÃO têm og:image nem twitter:image
    (só twitter:card=summary_large_image, sem imagem — card grande quebrado) e
    JSON-LD image em .svg. Aqui o script INJETA og:image (trio) + twitter:image
    espelhando o template e reescreve o JSON-LD. Reportados como "injetado".

Idempotente: rodar 2x não muda nada na 2ª. NÃO chama API, NÃO regenera conteúdo.
Precedente: scripts/backfill_seo_autor_image.py.

Uso:
  python3 scripts/backfill_ogimage_raster.py --pilot <slug>   # 1 artigo, sem enforce de contagem
  python3 scripts/backfill_ogimage_raster.py --dry-run        # todos, não grava nada
  python3 scripts/backfill_ogimage_raster.py                  # todos, grava, hard-fail se != esperado
  python3 scripts/backfill_ogimage_raster.py --esperado 509 --qualidade 85
  python3 scripts/backfill_ogimage_raster.py --force-jpg      # re-rasteriza mesmo se o .jpg já existe
"""

import argparse
import re
import sys
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
ARTIGOS_DIR = BASE / "artigos"
IMGS_DIR    = BASE / "assets" / "img" / "artigos"
URL_BLOG    = "https://safie.blog.br"

sys.path.insert(0, str(BASE / "scripts"))
from rasterizar_capa import rasterizar, QUALIDADE_JPG_PADRAO


def _regex_troca(slug: str):
    """3 regex escopados que trocam SÓ .svg->.jpg nas tags sociais (nunca no <img> visível)."""
    s = re.escape(slug)
    return {
        "og": re.compile(rf'(<meta property="og:image"\s+content="[^"]*/assets/img/artigos/{s})\.svg(")'),
        "tw": re.compile(rf'(<meta name="twitter:image"\s+content="[^"]*/assets/img/artigos/{s})\.svg(")'),
        "ld": re.compile(rf'("url":\s*"[^"]*/assets/img/artigos/{s})\.svg(")'),
    }


def reescrever_html(html: str, slug: str, jpg_url: str):
    """Retorna (novo_html, classe) onde classe in {'reescrito','injetado','sem-mudanca'}.
    'injetado' = artigo que não tinha og:image/twitter:image e recebeu as tags."""
    rx = _regex_troca(slug)
    original = html
    injetou = False

    # Classe divergente: og:image/twitter:image ausentes -> injetar espelhando o template
    if '<meta property="og:image"' not in html:
        trio = (
            f'  <meta property="og:image"       content="{jpg_url}">\n'
            f'  <meta property="og:image:width" content="1200">\n'
            f'  <meta property="og:image:height" content="630">\n'
        )
        html, n = re.subn(r'(<meta property="og:locale"[^>]*>\n)',
                          lambda m: m.group(1) + trio, html, count=1)
        if n:
            injetou = True
    if '<meta name="twitter:image"' not in html:
        tw = f'  <meta name="twitter:image"       content="{jpg_url}">\n'
        html, n = re.subn(r'(<meta name="twitter:description"[^>]*>\n)',
                          lambda m: m.group(1) + tw, html, count=1)
        if n:
            injetou = True

    # Reescrita .svg -> .jpg nas 3 tags (idempotente: se já é .jpg, não casa)
    html = rx["og"].sub(r"\1.jpg\2", html)
    html = rx["tw"].sub(r"\1.jpg\2", html)
    html = rx["ld"].sub(r"\1.jpg\2", html)

    if html == original:
        return html, "sem-mudanca"
    return html, ("injetado" if injetou else "reescrito")


def listar_svgs():
    return sorted(IMGS_DIR.glob("*.svg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=None, help="slug de 1 artigo (sem enforce de contagem)")
    ap.add_argument("--dry-run", action="store_true", help="não grava; só relata")
    ap.add_argument("--esperado", type=int, default=509, help="contagem esperada de capas (hard-fail se divergir)")
    ap.add_argument("--qualidade", type=int, default=QUALIDADE_JPG_PADRAO, help="qualidade JPG (padrão 85)")
    ap.add_argument("--force-jpg", action="store_true", help="re-rasteriza mesmo se o .jpg já existir")
    args = ap.parse_args()

    if args.pilot:
        svg = IMGS_DIR / f"{args.pilot}.svg"
        if not svg.exists():
            sys.exit(f"ERRO: {svg} não existe")
        alvos = [svg]
    else:
        alvos = listar_svgs()

    jpg_criados = jpg_existentes = 0
    html_reescritos = html_injetados = html_ja_ok = 0
    erros = []
    injetados_lista = []

    for svg in alvos:
        slug = svg.stem
        html_path = ARTIGOS_DIR / f"{slug}.html"
        jpg_path = IMGS_DIR / f"{slug}.jpg"

        if not html_path.exists():
            erros.append(f"{slug}: SVG sem HTML correspondente")
            continue

        # 1. Rasterizar (idempotente por padrão: pula se já existe)
        precisa_raster = args.force_jpg or not jpg_path.exists()
        if not args.dry_run and precisa_raster:
            try:
                rasterizar(svg, jpg_path, args.qualidade)
            except Exception as e:
                erros.append(f"{slug}: rasterização falhou: {e}")
                continue
        if precisa_raster:
            jpg_criados += 1
        else:
            jpg_existentes += 1

        # 2. Reescrever/injetar tags no HTML
        jpg_url = f"{URL_BLOG}/assets/img/artigos/{slug}.jpg"
        html = html_path.read_text(encoding="utf-8")
        novo, classe = reescrever_html(html, slug, jpg_url)
        if classe == "reescrito":
            html_reescritos += 1
        elif classe == "injetado":
            html_injetados += 1
            injetados_lista.append(slug)
        else:
            html_ja_ok += 1
        if not args.dry_run and novo != html:
            html_path.write_text(novo, encoding="utf-8")

    total = len(alvos) - len(erros)
    tag = "[DRY-RUN] " if args.dry_run else ""
    print(f"{tag}Capas: {len(alvos)} | JPG {'a criar' if args.dry_run else 'criados'}: {jpg_criados} | "
          f"JPG já existiam: {jpg_existentes}")
    print(f"{tag}HTML reescritos: {html_reescritos} | injetados (divergentes): {html_injetados} | "
          f"já OK: {html_ja_ok} | erros: {len(erros)}")
    if injetados_lista:
        print(f"{tag}Divergentes tratados por injeção ({len(injetados_lista)}):")
        for s in injetados_lista:
            print(f"    + {s}")
    for e in erros[:30]:
        print("  ERRO:", e)

    if erros:
        sys.exit(f"HARD-FAIL: {len(erros)} arquivo(s) com erro.")
    if not args.pilot and total != args.esperado:
        sys.exit(f"HARD-FAIL: contagem {total} != esperado {args.esperado}.")


if __name__ == "__main__":
    main()
