#!/usr/bin/env python3
"""Regenera as capas dos artigos publicados com o template SEM título
(templates/imagem-artigo.svg, 02/09/2026) e recoloca a capa na página.

Para cada entrada de artigos/indice.json:
  1. reescreve assets/img/artigos/{slug}.svg pelo template atual (marca + categoria + data);
  2. rasteriza {slug}.jpg (1200x630) via rasterizar_capa (General Sans inline);
  3. insere <img class="artigo-capa" src="/assets/img/artigos/{slug}.jpg"> logo após
     </header> do artigo, se ainda não houver;
  4. confere que og:image, twitter:image, JSON-LD image e o <img> apontam para o
     MESMO arquivo ({slug}.jpg).

Idempotente. --dry-run só conta. --pilot <slug> processa um artigo.
--sem-raster pula o Chromium (só SVG + HTML) para testes rápidos.
Hard-fail se, ao final, alguma página ficar sem <img> ou com divergência de arquivo.
"""
import argparse, json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import publicar as P  # noqa: E402
from rasterizar_capa import rasterizar  # noqa: E402

IMG_RE = re.compile(r'<img class="artigo-capa"[^>]*>')
OG_RE = re.compile(r'<meta property="og:image"\s+content="([^"]+)"')
TW_RE = re.compile(r'<meta name="twitter:image"\s+content="([^"]+)"')

def bloco_img(slug, tema):
    return (f'<img class="artigo-capa" src="/assets/img/artigos/{slug}.jpg" '
            f'alt="Capa do artigo — {tema}" width="1200" height="630" loading="lazy">')

def jsonld_images(html):
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try: d = json.loads(m.group(1))
        except Exception: continue
        for it in (d if isinstance(d, list) else [d]):
            if it.get("@type") == "BlogPosting":
                im = it.get("image")
                if isinstance(im, dict): im = im.get("url")
                if isinstance(im, list): im = im[0] if im else None
                if isinstance(im, dict): im = im.get("url")
                out.append(im)
    return out

def conferir(html, slug):
    alvo = f"/assets/img/artigos/{slug}.jpg"
    refs = {"og": OG_RE.search(html).group(1) if OG_RE.search(html) else None,
            "tw": TW_RE.search(html).group(1) if TW_RE.search(html) else None,
            "ld": (jsonld_images(html) or [None])[0],
            "img": (re.search(r'<img class="artigo-capa" src="([^"]+)"', html) or [None, None])[1]}
    div = {k: v for k, v in refs.items() if not v or not v.endswith(alvo)}
    return div

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--pilot"); ap.add_argument("--sem-raster", action="store_true")
    a = ap.parse_args()
    site = json.loads((BASE / "config" / "site.json").read_text(encoding="utf-8"))
    indice = json.loads((BASE / "artigos" / "indice.json").read_text(encoding="utf-8"))
    if a.pilot: indice = [x for x in indice if x["slug"] == a.pilot]; assert indice, "slug não está no índice"
    n = dict(svg=0, jpg=0, img_inseridos=0, ja_tinham=0, sem_html=0); divergentes = []
    for i, e in enumerate(indice, 1):
        slug, tema = e["slug"], e.get("tema", "")
        html_p = BASE / "artigos" / f"{slug}.html"
        if not html_p.exists(): n["sem_html"] += 1; continue
        art = {"slug": slug, "titulo": e.get("titulo", ""), "tema_nome": tema, "data_iso": e.get("data", "")}
        if not a.dry_run:
            if a.sem_raster:
                P.IMGS_DIR.mkdir(parents=True, exist_ok=True)
                svg = P.preencher_template(P.TEMPLATE_IMG.read_text(encoding="utf-8"), {
                    "CATEGORIA": P.escapar_xml(tema.upper()), "DATA": P.data_capa(art["data_iso"]),
                    "NOME_BLOG": P.escapar_xml(site.get("nome", "SAFIE Blog"))})
                (P.IMGS_DIR / f"{slug}.svg").write_text(svg, encoding="utf-8")
            else:
                P.gerar_imagem_capa(art, site)   # escreve SVG + rasteriza JPG (fail-loud)
                n["jpg"] += 1
        n["svg"] += 1
        html = html_p.read_text(encoding="utf-8")
        if IMG_RE.search(html):
            novo = IMG_RE.sub(bloco_img(slug, tema), html); n["ja_tinham"] += 1
        else:
            # o <header> do site também fecha com </header>: ancorar no cabeçalho do artigo
            m = re.search(r'<header class="artigo-header">.*?</header>', html, re.S)
            assert m, f"{slug}: sem <header class=\"artigo-header\">"
            novo = html[:m.end()] + "\n\n    " + bloco_img(slug, tema) + html[m.end():]; n["img_inseridos"] += 1
        if not a.dry_run and novo != html: html_p.write_text(novo, encoding="utf-8")
        d = conferir(novo, slug)
        if d: divergentes.append((slug, d))
        if i % 25 == 0: print(f"  … {i}/{len(indice)}", flush=True)
    print(" | ".join(f"{k}: {v}" for k, v in n.items()), f"| divergentes: {len(divergentes)}")
    for s, d in divergentes[:10]: print("  divergente:", s, d)
    if not a.dry_run and divergentes: sys.exit(1)

if __name__ == "__main__":
    main()
