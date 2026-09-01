#!/usr/bin/env python3
"""
consolidar_clusters.py — Consolidação B1 dos clusters de artigos duplicados.

Lê _archive/plano-consolidacao-clusters-20260818.json e, para cada artigo
não-canônico dos clusters selecionados:
  - adiciona regra 301 em /_redirects (Cloudflare Pages, path -> path);
  - remove o HTML e as capas (SVG + JPG);
  - poda artigos/indice.json e sitemap.xml;
  - reponta links "Continue lendo" que apontem para não-canônicos;
  - regenera llms.txt.

Hard-fail DINÂMICO: as contagens-alvo são (contagem atual − removidos desta
execução), lidas no momento do run — nunca números fixos (o bot publica
diariamente). Qualquer divergência aborta ANTES de escrever qualquer arquivo.

Uso:
  python3 scripts/consolidar_clusters.py --dry-run
  python3 scripts/consolidar_clusters.py --pilot <base-do-cluster>
  python3 scripts/consolidar_clusters.py --rollout
"""

import argparse
import json
import re
import sys
from pathlib import Path

BASE      = Path(__file__).resolve().parent.parent
PLANO     = BASE / "_archive" / "plano-consolidacao-clusters-20260818.json"
INDICE    = BASE / "artigos" / "indice.json"
SITEMAP   = BASE / "sitemap.xml"
REDIRECTS = BASE / "_redirects"
IMGS      = BASE / "assets" / "img" / "artigos"
URL_BLOG  = "https://safie.blog.br"

RE_UL_RELACIONADOS = re.compile(
    r'(<ul class="relacionados-items">)(.*?)(</ul>)', re.S)
RE_LI = re.compile(
    r'<li><a href="/artigos/([^"]+)">([^<]*)</a></li>')


def fail(msg: str):
    print(f"HARD-FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def carregar_selecao(args):
    """Retorna (clusters selecionados, mapa nc->canonico do plano inteiro)."""
    plano = json.loads(PLANO.read_text(encoding="utf-8"))
    clusters = plano["clusters"]
    mapa_total = {}
    for c in clusters:
        for m in c["membros"]:
            if m != c["canonico"]:
                mapa_total[m] = c["canonico"]
    if len(mapa_total) != plano["total_redirects"]:
        fail(f"plano inconsistente: {len(mapa_total)} nao-canonicos != "
             f"total_redirects {plano['total_redirects']}")

    if args.pilot:
        sel = [c for c in clusters if c["base"] == args.pilot]
        if len(sel) != 1:
            fail(f"--pilot '{args.pilot}' não identifica exatamente 1 cluster "
                 f"(achou {len(sel)}); use o campo 'base' do plano")
    else:
        sel = clusters
    return sel, mapa_total


def main():
    ap = argparse.ArgumentParser(description="Consolidação B1 de clusters")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true",
                      help="simula tudo, não escreve nada")
    modo.add_argument("--pilot", metavar="CLUSTER_BASE",
                      help="aplica somente o cluster com este 'base'")
    modo.add_argument("--rollout", action="store_true",
                      help="aplica todos os clusters pendentes do plano")
    args = ap.parse_args()
    aplicar = not args.dry_run

    sel, mapa_total = carregar_selecao(args)

    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    slugs_indice = {a["slug"] for a in indice}
    sitemap = SITEMAP.read_text(encoding="utf-8")
    n_urls_antes = sitemap.count("<url>")

    # ── seleção desta execução: nc -> canonico ──
    # No rollout, clusters já aplicados (ex.: piloto) são pulados; um cluster
    # parcialmente aplicado (nc sem HTML mas ainda no índice) é inconsistência.
    mapa = {}
    for c in sel:
        ncs = [m for m in c["membros"] if m != c["canonico"]]
        presentes = [s for s in ncs if (BASE / "artigos" / f"{s}.html").exists()]
        if not presentes:
            continue  # cluster já consolidado
        if len(presentes) != len(ncs) and not args.rollout:
            fail(f"cluster '{c['base']}' parcialmente aplicado: "
                 f"{len(presentes)}/{len(ncs)} HTMLs presentes")
        for s in presentes:
            mapa[s] = c["canonico"]

    if not mapa:
        fail("nada a fazer: nenhum não-canônico pendente na seleção")
    n = len(mapa)

    # ── pré-validações (tudo ANTES de escrever qualquer coisa) ──
    for nc, canon in mapa.items():
        if not (BASE / "artigos" / f"{canon}.html").exists():
            fail(f"canônico sem HTML: {canon}")
        if canon not in slugs_indice:
            fail(f"canônico fora do indice.json: {canon}")
        if nc not in slugs_indice:
            fail(f"não-canônico fora do indice.json: {nc}")
        if f"<loc>{URL_BLOG}/artigos/{nc}</loc>" not in sitemap:
            fail(f"não-canônico fora do sitemap.xml: {nc}")
        for ext in ("svg", "jpg"):
            if not (IMGS / f"{nc}.{ext}").exists():
                fail(f"capa ausente: {nc}.{ext}")

    # ── alvos dinâmicos ──
    alvo_indice = len(indice) - n
    alvo_sitemap = n_urls_antes - n

    # ── indice.json podado ──
    indice_novo = [a for a in indice if a["slug"] not in mapa]
    if len(indice_novo) != alvo_indice:
        fail(f"indice: {len(indice_novo)} != alvo {alvo_indice} "
             f"({len(indice)} − {n})")

    # ── sitemap podado (blocos <url> no formato do publicar.py) ──
    sitemap_novo = sitemap
    for nc in mapa:
        bloco = re.compile(
            r"\n  <url>\s*<loc>" + re.escape(f"{URL_BLOG}/artigos/{nc}")
            + r"</loc>.*?</url>", re.S)
        sitemap_novo, k = bloco.subn("", sitemap_novo)
        if k != 1:
            fail(f"sitemap: bloco de {nc} casou {k}x (esperado 1)")
    if sitemap_novo.count("<url>") != alvo_sitemap:
        fail(f"sitemap: {sitemap_novo.count('<url>')} != alvo {alvo_sitemap} "
             f"({n_urls_antes} − {n})")

    # ── _redirects (mantém linhas existentes; nunca duplica) ──
    linhas_existentes = []
    if REDIRECTS.exists():
        linhas_existentes = REDIRECTS.read_text(encoding="utf-8").splitlines()
    ja_tem = {ln.split()[0] for ln in linhas_existentes if ln.strip()}
    novas = [f"/artigos/{nc} /artigos/{canon} 301"
             for nc, canon in sorted(mapa.items())
             if f"/artigos/{nc}" not in ja_tem]
    redirects_novo = "\n".join(linhas_existentes + novas) + "\n"

    # ── repontar "Continue lendo" nos HTMLs que permanecem ──
    # Escopo = seleção desta execução (piloto edita só o próprio cluster;
    # o rollout, com o restante do plano, cobre os demais).
    titulos = {a["slug"]: a["titulo"] for a in indice}
    edicoes = {}   # path -> novo conteúdo
    repontados = []
    restantes = [p for p in (BASE / "artigos").glob("*.html")
                 if p.stem not in mapa and p.stem != "index"]
    for path in restantes:
        html = path.read_text(encoding="utf-8")
        m = RE_UL_RELACIONADOS.search(html)
        if not m:
            continue
        itens = RE_LI.findall(m.group(2))
        mudou = False
        vistos, novos_itens = set(), []
        for slug, texto in itens:
            slug_limpo = slug.strip("/")
            if slug_limpo in mapa:
                canon = mapa[slug_limpo]
                repontados.append((path.stem, slug_limpo, canon))
                slug_limpo = canon
                texto = titulos.get(canon, texto)
                mudou = True
            if slug_limpo == path.stem or slug_limpo in vistos:
                mudou = True  # remove self-link / duplicata pós-reponte
                continue
            vistos.add(slug_limpo)
            novos_itens.append(
                f'  <li><a href="/artigos/{slug_limpo}">{texto}</a></li>')
        if mudou:
            ul = m.group(1) + "\n" + "\n".join(novos_itens) + "\n" + m.group(3)
            edicoes[path] = html[:m.start()] + ul + html[m.end():]

    # ── relatório ──
    print(f"modo: {'DRY-RUN' if args.dry_run else ('PILOT ' + args.pilot if args.pilot else 'ROLLOUT')}")
    print(f"clusters na seleção com pendência: "
          f"{len({c for c in mapa.values()})} | não-canônicos a remover: {n}")
    print(f"redirects: {len(linhas_existentes)} existentes + {len(novas)} novas "
          f"= {len(linhas_existentes) + len(novas)} linhas")
    print(f"indice.json : {len(indice)} -> {len(indice_novo)} (alvo {alvo_indice})")
    print(f"sitemap.xml : {n_urls_antes} -> {sitemap_novo.count('<url>')} (alvo {alvo_sitemap})")
    print(f"arquivos a remover: {n} HTML + {n} SVG + {n} JPG")
    print(f"links 'Continue lendo' repontados: {len(repontados)} "
          f"em {len(edicoes)} páginas")
    for pagina, de, para in repontados:
        print(f"  {pagina}: {de} -> {para}")

    if args.dry_run:
        print("\nDRY-RUN: nada foi escrito.")
        return

    # ── aplicar (validações todas OK) ──
    REDIRECTS.write_text(redirects_novo, encoding="utf-8")
    INDICE.write_text(json.dumps(indice_novo, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    SITEMAP.write_text(sitemap_novo, encoding="utf-8")
    for path, conteudo in edicoes.items():
        path.write_text(conteudo, encoding="utf-8")
    for nc in mapa:
        (BASE / "artigos" / f"{nc}.html").unlink()
        (IMGS / f"{nc}.svg").unlink()
        (IMGS / f"{nc}.jpg").unlink()

    sys.path.insert(0, str(BASE / "scripts"))
    from gerar_llms_txt import gerar_llms_txt
    gerar_llms_txt()

    # ── pós-validação (hard-fail dinâmico de novo, agora no disco) ──
    ind_final = json.loads(INDICE.read_text(encoding="utf-8"))
    if len(ind_final) != alvo_indice:
        fail(f"pós: indice {len(ind_final)} != {alvo_indice}")
    if SITEMAP.read_text(encoding="utf-8").count("<url>") != alvo_sitemap:
        fail("pós: sitemap diverge do alvo")
    sobras = [nc for nc in mapa if (BASE / "artigos" / f"{nc}.html").exists()]
    if sobras:
        fail(f"pós: HTMLs não removidos: {sobras}")
    print("\nAPLICADO e validado no disco.")


if __name__ == "__main__":
    main()
