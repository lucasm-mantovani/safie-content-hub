"""
backfill_seo_autor_image.py — Correção SEO on-page nos artigos JÁ PUBLICADOS.

Alinha, em cada artigos/*.html existente, SEM tocar no conteúdo/texto:
  1. Autor consistente nos 3 lugares. Fonte da verdade = o autor-pessoa que já
     está no JSON-LD (BlogPosting.author.name, resolvido por tema no pipeline).
     Corrige o byline visível ("Por SAFIE" -> "Por <sócio>") e o
     <meta name="author"> ("SAFIE" -> "<sócio>").
  2. Propriedade "image" no BlogPosting (Google exige p/ rich result de artigo).
     URL = a mesma capa já presente no og:image do arquivo.

NÃO chama API, NÃO regenera conteúdo. Idempotente: rodar 2x não muda nada na 2ª.
Precedente de backfill in-place: scripts/backfill_a5.py.

Uso:
  python3 scripts/backfill_seo_autor_image.py --pilot <slug>   # 1 artigo, relatório, sem enforce
  python3 scripts/backfill_seo_autor_image.py --dry-run        # todos, não grava
  python3 scripts/backfill_seo_autor_image.py                  # todos, grava, hard-fail se contagem != esperado
  python3 scripts/backfill_seo_autor_image.py --esperado 509   # ajusta a contagem esperada
"""

import argparse
import json
import re
import sys
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
ARTIGOS_DIR = BASE / "artigos"
URL_BLOG    = "https://safie.blog.br"

RE_LDJSON  = re.compile(r'(<script type="application/ld\+json">\s*)(\[.*?\])(\s*</script>)', re.DOTALL)
RE_OGIMG   = re.compile(r'<meta property="og:image"\s+content="([^"]+)"')
RE_META_AU = re.compile(r'(<meta name="author" content=)"[^"]*"')
RE_BYLINE  = re.compile(r'(Por <strong itemprop="author">)[^<]*(</strong>)')


def processar(path: Path):
    """Retorna (mudou: bool, autor: str|None, tinha_image_antes: bool, erro: str|None)."""
    html = path.read_text(encoding="utf-8")

    m = RE_LDJSON.search(html)
    if not m:
        return False, None, False, "sem bloco ld+json"
    try:
        data = json.loads(m.group(2))
    except json.JSONDecodeError as e:
        return False, None, False, f"ld+json inválido: {e}"

    bp = next((x for x in data if isinstance(x, dict) and x.get("@type") == "BlogPosting"), None)
    if bp is None:
        return False, None, False, "sem BlogPosting"

    autor = ((bp.get("author") or {}).get("name") or "").strip()
    if not autor:
        return False, None, False, "BlogPosting sem author.name"

    tinha_image = "image" in bp
    original = html

    # 1. Injeta image no BlogPosting se ausente (usa a capa do og:image do arquivo)
    if not tinha_image:
        og = RE_OGIMG.search(html)
        img_url = og.group(1) if og else f"{URL_BLOG}/assets/img/artigos/{path.stem}.svg"
        # preserva a ordem canônica do template (image logo após mainEntityOfPage)
        novo_bp = {}
        for k, v in bp.items():
            novo_bp[k] = v
            if k == "mainEntityOfPage":
                novo_bp["image"] = {
                    "@type": "ImageObject", "url": img_url, "width": 1200, "height": 630,
                }
        if "image" not in novo_bp:  # sem mainEntityOfPage: adiciona após description
            novo_bp = {}
            for k, v in bp.items():
                novo_bp[k] = v
                if k == "description":
                    novo_bp["image"] = {
                        "@type": "ImageObject", "url": img_url, "width": 1200, "height": 630,
                    }
        idx = data.index(bp)
        data[idx] = novo_bp
        novo_json = json.dumps(data, ensure_ascii=False, indent=2)
        html = html[:m.start()] + m.group(1) + novo_json + m.group(3) + html[m.end():]

    # 2. Alinha meta author + byline ao autor do JSON-LD
    html = RE_META_AU.sub(rf'\1"{autor}"', html)
    html = RE_BYLINE.sub(rf'\g<1>{autor}\g<2>', html)

    mudou = html != original
    if mudou:
        path.write_text(html, encoding="utf-8")
    return mudou, autor, tinha_image, None


def listar_artigos():
    return sorted(
        p for p in ARTIGOS_DIR.glob("*.html")
        if p.stem != "index" and ".bkp" not in p.name
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=None, help="slug de 1 artigo (sem enforce de contagem)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--esperado", type=int, default=509, help="contagem esperada de artigos (hard-fail se divergir)")
    args = ap.parse_args()

    if args.pilot:
        alvos = [ARTIGOS_DIR / f"{args.pilot}.html"]
        if not alvos[0].exists():
            sys.exit(f"ERRO: {alvos[0]} não existe")
    else:
        alvos = listar_artigos()

    if args.dry_run:
        # dry-run: só relata o que mudaria, sem escrever
        pend_autor = pend_image = 0
        erros = []
        for p in alvos:
            html = p.read_text(encoding="utf-8")
            m = RE_LDJSON.search(html)
            if not m:
                erros.append(f"{p.name}: sem ld+json"); continue
            try:
                data = json.loads(m.group(2))
            except json.JSONDecodeError as e:
                erros.append(f"{p.name}: ld+json inválido ({e})"); continue
            bp = next((x for x in data if isinstance(x, dict) and x.get("@type") == "BlogPosting"), None)
            if not bp:
                erros.append(f"{p.name}: sem BlogPosting"); continue
            if "image" not in bp:
                pend_image += 1
            if 'content="SAFIE"' in html or 'itemprop="author">SAFIE<' in html:
                pend_autor += 1
        print(f"[DRY-RUN] artigos: {len(alvos)} | pendente image: {pend_image} | pendente autor: {pend_autor} | erros: {len(erros)}")
        for e in erros[:20]:
            print("  ERRO:", e)
        if erros:
            sys.exit(1)
        return

    mudados = 0
    ja_ok = 0
    erros = []
    autores = {}
    for p in alvos:
        mudou, autor, tinha_img, erro = processar(p)
        if erro:
            erros.append(f"{p.name}: {erro}")
            continue
        autores[autor] = autores.get(autor, 0) + 1
        if mudou:
            mudados += 1
        else:
            ja_ok += 1

    total = len(alvos) - len(erros)
    print(f"Artigos processados: {len(alvos)} | alterados: {mudados} | já consistentes: {ja_ok} | erros: {len(erros)}")
    print(f"Distribuição de autor: {autores}")
    for e in erros[:20]:
        print("  ERRO:", e)

    if erros:
        sys.exit(f"HARD-FAIL: {len(erros)} arquivo(s) com erro.")

    if not args.pilot and total != args.esperado:
        sys.exit(f"HARD-FAIL: contagem {total} != esperado {args.esperado}.")


if __name__ == "__main__":
    main()
