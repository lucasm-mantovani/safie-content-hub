#!/usr/bin/env python3
"""Capa do artigo sai do lazy loading (03/09/2026).

O <img class="artigo-capa"> fica logo abaixo do H1 e da autoria — primeira dobra,
candidata a LCP. Com loading="lazy" o carregamento é adiado e a área reservada
(1200x630) fica em branco. Troca, SÓ nesse <img>, loading="lazy" por
loading="eager" fetchpriority="high". width/height são mantidos. Nenhum outro
atributo loading da página é tocado (ferramentas da home, logo etc.).

Idempotente. --dry-run só conta. Hard-fail se sobrar capa lazy ou sem fetchpriority.
"""
import argparse, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CAPA = re.compile(r'<img class="artigo-capa"[^>]*>')

def corrigir(tag: str) -> str:
    novo = re.sub(r'\s+loading="[^"]*"', "", tag)
    novo = re.sub(r'\s+fetchpriority="[^"]*"', "", novo)
    return novo[:-1] + ' loading="eager" fetchpriority="high">'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    tocados = sem_capa = 0
    for p in sorted(BASE.glob("artigos/2*.html")):
        s = p.read_text(encoding="utf-8")
        m = CAPA.search(s)
        if not m: sem_capa += 1; continue
        novo = s.replace(m.group(0), corrigir(m.group(0)), 1)
        if novo != s:
            tocados += 1
            if not a.dry_run: p.write_text(novo, encoding="utf-8")
    print(f"artigos alterados: {tocados} | sem capa: {sem_capa}")
    if a.dry_run: return
    restos = [p.name for p in BASE.glob("artigos/2*.html")
              if (m := CAPA.search(p.read_text(encoding="utf-8"))) and ('loading="eager"' not in m.group(0) or 'fetchpriority="high"' not in m.group(0))]
    if restos: print("FALHA:", restos[:5]); sys.exit(1)
    print("verificação: toda capa com loading=eager e fetchpriority=high")

if __name__ == "__main__":
    main()
