#!/usr/bin/env python3
"""Backfill do alinhamento de identidade aos sites (02/09/2026).

Aplica nas páginas ESTÁTICAS já publicadas o que os templates/partials passaram
a gerar, e reconstrói o resumo dos cards no indice.json:

  1. remove a barra arco-íris (<div class="footer-arco-iris">) de todas as páginas;
  2. remove o span com cor ciano no "Blog SAFIE" do rodapé;
  3. remove a <img class="artigo-capa"> do topo dos artigos (título duplicado);
  4. indice.json: resumo cortado em fronteira de palavra (P.resumo_card), lido do
     <aside class="resumo-executivo"> do próprio artigo; se não houver aside,
     recorta o resumo atual na última palavra inteira.

Idempotente. --dry-run mostra contagens sem gravar. Hard-fail se sobrar
qualquer ocorrência após gravar.
"""
import argparse, json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import publicar as P  # noqa: E402

ARCO = re.compile(r'[ \t]*<div class="footer-arco-iris" aria-hidden="true"></div>\n?')
SPAN = ('<span class="logo-marca footer-logo-texto">Blog <span style="color:var(--ciano)">SAFIE</span></span>',
        '<span class="logo-marca footer-logo-texto">Blog SAFIE</span>')
CAPA = re.compile(r'[ \t]*<img class="artigo-capa"[^>]*>\n?')
ASIDE = re.compile(r'<aside class="resumo-executivo"[^>]*>\s*<strong>Resumo executivo</strong>\s*(.*?)</aside>', re.S)
TAGS = re.compile(r"<[^>]+>")

def paginas():
    yield from BASE.glob("artigos/*.html")
    yield from BASE.glob("categorias/*.html")
    for n in ("index.html", "busca.html", "politica-de-cookies/index.html"):
        p = BASE / n
        if p.exists():
            yield p

def resumo_de(html, atual):
    m = ASIDE.search(html)
    if m:
        txt = TAGS.sub(" ", m.group(1))
        return P.resumo_card(txt)
    # sem aside (artigo migrado com outro markup): recorta o atual na última palavra inteira
    atual = (atual or "").strip()
    if not atual or atual.endswith("\u2026") or atual.endswith("."):
        return atual
    corte = atual.rsplit(" ", 1)[0].rstrip(" ,;:.\u2014\u2013-(")
    return corte + "\u2026"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    n_arco = n_span = n_capa = n_files = 0
    for p in paginas():
        s = s0 = p.read_text(encoding="utf-8")
        s, k = ARCO.subn("", s); n_arco += k
        if SPAN[0] in s:
            s = s.replace(SPAN[0], SPAN[1]); n_span += 1
        if p.parent.name == "artigos":
            s, k = CAPA.subn("", s); n_capa += k
        if s != s0:
            n_files += 1
            if not args.dry_run:
                p.write_text(s, encoding="utf-8")
    print(f"páginas alteradas: {n_files} | arco-íris removidos: {n_arco} | spans ciano: {n_span} | capas: {n_capa}")

    idx_path = BASE / "artigos" / "indice.json"
    indice = json.loads(idx_path.read_text(encoding="utf-8"))
    n_res = n_sem_aside = 0
    for a in indice:
        html_p = BASE / "artigos" / f"{a['slug']}.html"
        html = html_p.read_text(encoding="utf-8") if html_p.exists() else ""
        if not ASIDE.search(html):
            n_sem_aside += 1
        novo = resumo_de(html, a.get("resumo", ""))
        if novo != a.get("resumo"):
            a["resumo"] = novo; n_res += 1
    print(f"indice.json: {len(indice)} entradas | resumos reescritos: {n_res} | sem aside (fallback): {n_sem_aside}")
    if not args.dry_run:
        idx_path.write_text(json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        return
    # verificação dura
    rest = [str(p) for p in paginas() if ("footer-arco-iris" in p.read_text(encoding="utf-8")
            or SPAN[0] in p.read_text(encoding="utf-8")
            or (p.parent.name == "artigos" and 'class="artigo-capa"' in p.read_text(encoding="utf-8")))]
    quebrados = [a["slug"] for a in indice if re.search(r"\w$", a.get("resumo", "")) and len(a["resumo"].split()) >= P.RESUMO_MAX_PALAVRAS]
    if rest or quebrados:
        print("FALHA: restos ->", rest[:5], quebrados[:5]); sys.exit(1)
    print("verificação: 0 restos, 0 resumos cortados no meio da palavra")

if __name__ == "__main__":
    main()
