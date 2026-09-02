#!/usr/bin/env python3
"""Backfill de conformidade de copy + remoção do artigo.js (02/09/2026).

Aplica nas páginas ESTÁTICAS já publicadas o que os templates/partials passaram
a gerar:
  1. remove, no formulário do rodapé, o parágrafo "Atendemos founders e gestores
     com acesso direto aos sócios — jurídico e contabilidade sob o mesmo teto.";
  2. troca a tagline do rodapé por "Assessoria jurídica e contabilidade para
     empresas digitais." (junção literal das taglines aprovadas dos sites);
  3. nos artigos, remove o parágrafo da caixa de chamada ("A SAFIE atende
     founders e gestores com acesso direto aos sócios — ... recomendação.");
  4. nos artigos, remove <script src="/assets/js/artigo.js"> (arquivo nunca
     existiu; erro de console em todos os artigos).

Idempotente. --dry-run mostra contagens sem gravar. Hard-fail se sobrar
qualquer ocorrência dos termos vetados após gravar.
"""
import argparse, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FRASE_FORM = re.compile(r'[ \t]*<p>Atendemos founders e gestores com acesso direto aos sócios[^<]*</p>\n?')
FRASE_CTA  = re.compile(r'[ \t]*<p>A SAFIE atende founders e gestores com acesso direto aos sócios[^<]*</p>\n?')
SCRIPT     = re.compile(r'[ \t]*<script src="/assets/js/artigo\.js" defer></script>\n?')
TAG_OLD = '<p>Consultoria jurídico-contábil para negócios digitais, startups e a nova economia.</p>'
TAG_NEW = '<p>Assessoria jurídica e contabilidade para empresas digitais.</p>'
VETADOS = re.compile(r'acesso direto aos s|mesmo teto|mesma casa|nova economia', re.I)

def paginas():
    yield from BASE.glob("artigos/*.html")
    yield from BASE.glob("categorias/*.html")
    for n in ("index.html", "busca.html", "politica-de-cookies/index.html"):
        if (BASE / n).exists():
            yield BASE / n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    n = dict(paginas=0, form=0, tag=0, cta=0, script=0)
    for p in paginas():
        s = s0 = p.read_text(encoding="utf-8")
        s, k = FRASE_FORM.subn("", s); n["form"] += k
        if TAG_OLD in s: s = s.replace(TAG_OLD, TAG_NEW); n["tag"] += 1
        if p.parent.name == "artigos":
            s, k = FRASE_CTA.subn("", s); n["cta"] += k
            s, k = SCRIPT.subn("", s); n["script"] += k
        if s != s0:
            n["paginas"] += 1
            if not a.dry_run: p.write_text(s, encoding="utf-8")
    print(" | ".join(f"{k}: {v}" for k, v in n.items()))
    if a.dry_run: return
    # verificação dura: as FRASES comerciais (rodapé/CTA/tagline) e o artigo.js têm de sumir.
    # Termos soltos no corpo editorial de artigos (ex.: "acesso direto aos seus dados")
    # são texto do artigo, não copy comercial: só reportados, nunca reescritos aqui.
    restos, editoriais = [], []
    for p in paginas():
        h = p.read_text(encoding="utf-8")
        if FRASE_FORM.search(h) or FRASE_CTA.search(h) or TAG_OLD in h or "artigo.js" in h:
            restos.append(str(p.relative_to(BASE)))
        elif VETADOS.search(h):
            editoriais.append(str(p.relative_to(BASE)))
    if restos: print("FALHA: restos ->", restos[:8]); sys.exit(1)
    print("verificação: 0 frases comerciais vetadas, 0 referências a artigo.js nas páginas")
    if editoriais: print(f"aviso: {len(editoriais)} artigo(s) com termo vetado no corpo editorial (não alterados):", editoriais)

if __name__ == "__main__":
    main()
