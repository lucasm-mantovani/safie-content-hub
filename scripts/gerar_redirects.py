"""
gerar_redirects.py — Gera o CSV/JSON de import dos Bulk Redirects (Cloudflare)
para o cutover A6 dos 5 subdomínios → blog unificado safie.blog.br.

FONTE: snapshot unificado (artigos/indice.json = 476 migrados + config/categorias.json
= 37 temas). Usar o unificado (e não os 5 blogs originais, hoje com 485) é proposital:
o destino do redirect precisa EXISTIR no unificado — redirecionar um slug não
migrado apontaria para 404.

Mapa de redirects (301, preserve_query_string, 1:1 exato / subpath_matching off):
  476 artigos  {sub}.safie.blog.br/artigos/{slug} → safie.blog.br/artigos/{slug}
   37 temas    {sub}.safie.blog.br/temas/{slug}   → safie.blog.br/categorias/{slug}
    5 idx tema {sub}.safie.blog.br/temas/          → safie.blog.br/categorias/
    5 listagem {sub}.safie.blog.br/artigos/        → safie.blog.br/artigos/
    5 homes    {sub}.safie.blog.br/                → safie.blog.br/categorias/{nicho}
  = 528

Uso: python3 scripts/gerar_redirects.py [OUTDIR]
"""

import csv
import json
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else WT / "_redirects_out"
BASE_NEW = "https://safie.blog.br"

# nicho (chave unificada) → subdomínio antigo
SUBDOMINIO = {
    "cripto": "cripto", "ecommerce": "ecommerce", "fintechs": "fintechs",
    "ia": "ia", "reforma": "reformatributaria",
}
NICHOS = list(SUBDOMINIO.keys())


def main():
    indice = json.loads((WT / "artigos" / "indice.json").read_text(encoding="utf-8"))
    cats = json.loads((WT / "config" / "categorias.json").read_text(encoding="utf-8"))

    rows = []  # (source, target, tipo)

    for a in indice:  # 476 artigos
        sub = SUBDOMINIO[a["nicho"]]
        rows.append((f"https://{sub}.safie.blog.br/artigos/{a['slug']}",
                     f"{BASE_NEW}/artigos/{a['slug']}", "artigo"))

    for c in cats:  # 37 temas
        sub = SUBDOMINIO[c["nicho"]]
        rows.append((f"https://{sub}.safie.blog.br/temas/{c['slug']}",
                     f"{BASE_NEW}/categorias/{c['slug']}", "tema"))

    for n in NICHOS:  # 5 índices de tema
        rows.append((f"https://{SUBDOMINIO[n]}.safie.blog.br/temas/",
                     f"{BASE_NEW}/categorias/", "idx_tema"))

    for n in NICHOS:  # 5 listagens
        rows.append((f"https://{SUBDOMINIO[n]}.safie.blog.br/artigos/",
                     f"{BASE_NEW}/artigos/", "listagem"))

    for n in NICHOS:  # 5 homes de nicho
        rows.append((f"https://{SUBDOMINIO[n]}.safie.blog.br/",
                     f"{BASE_NEW}/categorias/{n}", "home_nicho"))

    # ── Validações (hard-fail) ──
    esperado = len(indice) + len(cats) + 5 + 5 + 5
    assert len(rows) == esperado, f"total {len(rows)} != esperado {esperado}"
    assert len(indice) == 476, f"indice tem {len(indice)} (esperado 476)"
    assert len(cats) == 37, f"categorias tem {len(cats)} (esperado 37)"

    sources = [s for s, _, _ in rows]
    dups = sorted({s for s in sources if sources.count(s) > 1})
    assert not dups, f"sources duplicados: {dups[:10]}"

    for s, t, _ in rows:
        assert t.startswith("https://safie.blog.br/"), f"target inválido: {t}"
        assert s.startswith("https://") and ".safie.blog.br/" in s, f"source inválido: {s}"
        assert " " not in s and " " not in t, f"espaço em URL: {s} {t}"

    # ── Escrever CSV (template Cloudflare Bulk Redirects) ──
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "redirects.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_url", "target_url", "status_code", "preserve_query_string",
                    "include_subdomains", "subpath_matching", "preserve_path_suffix"])
        for s, t, _ in rows:
            w.writerow([s, t, 301, "true", "false", "false", "false"])

    # ── Escrever JSON (itens de API para import na Parte 2) ──
    json_path = OUT / "redirects.json"
    items = [{"redirect": {
        "source_url": s, "target_url": t, "status_code": 301,
        "preserve_query_string": True, "include_subdomains": False,
        "subpath_matching": False, "preserve_path_suffix": False,
    }} for s, t, _ in rows]
    json_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Relatório ──
    from collections import Counter
    tipos = Counter(tp for _, _, tp in rows)
    print(f"OK — {len(rows)} redirects | 0 source duplicado | targets safie.blog.br válidos")
    print(f"por tipo: {dict(tipos)}")
    print(f"CSV : {csv_path}")
    print(f"JSON: {json_path}")
    print("\nAMOSTRA (1 por nicho — artigo):")
    vistos = set()
    for s, t, tp in rows:
        if tp != "artigo":
            continue
        sub = s.split("//")[1].split(".")[0]
        if sub in vistos:
            continue
        vistos.add(sub)
        print(f"  {s}\n    -> {t}")
        if len(vistos) == 5:
            break


if __name__ == "__main__":
    main()
