#!/usr/bin/env python3
"""Remove dos artigos publicados a citação atribuída a sócio com OAB (02/09/2026).

Decisão do Lucas: a assinatura do artigo (byline + JSON-LD author) CONTINUA; sai a
afirmação de que um sócio DISSE aquelas palavras. Dois grupos, por teste mecânico
de primeira pessoa no texto da citação:

  Grupo A (impessoal): o texto vira parágrafo de destaque do artigo, palavra por
    palavra — <p class="destaque-artigo">…</p>. Sai o <cite> inteiro (nome + OAB).
  Grupo B (primeira pessoa: eu/vejo/nosso/…, verbos em -amos/-emos/-imos): o bloco
    inteiro é removido. Nada é reescrito (reescrever seria copy nova).

Idempotente. --dry-run só classifica e lista. Hard-fail se, ao gravar, sobrar
<cite>, "citacao-socio" ou "OAB" em qualquer artigo.
"""
import argparse, json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
BLOCO = re.compile(r'\n?<blockquote class="citacao-socio">\s*<p>(.*?)</p>\s*<cite>(.*?)</cite>\s*</blockquote>\n?', re.S)
FP1 = re.compile(r"\b(eu|me|mim|comigo|meu|minha|meus|minhas|nós|conosco|nosso|nossa|nossos|nossas|a gente|vejo|vemos|tenho|temos|"
                 r"acredito|acreditamos|recomendo|recomendamos|observo|observamos|costumo|costumamos|percebo|percebemos|entendo|entendemos|"
                 r"oriento|orientamos|atendo|atendemos|acompanho|acompanhamos|sugiro|sugerimos|defendo|defendemos|considero|consideramos|"
                 r"avalio|avaliamos|penso|pensamos|insisto|insistimos|aprendi|aprendemos|vi|vimos|aqui na safie|na safie)\b", re.I)
FP2 = re.compile(r"\b(\w{3,}(?:amos|emos|imos))\b", re.I)
NAO_VERBO = {"ramos","termos","extremos","supremos","últimos","ultimos","mínimos","minimos","máximos","maximos","ínfimos","mesmos",
             "legítimos","legitimos","íntimos","intimos","ótimos","otimos","anônimos","anonimos","sinônimos","sinonimos","décimos","decimos"}

def marcadores(txt):
    m = [x.lower() for x in FP1.findall(txt)] + [x.lower() for x in FP2.findall(txt) if x.lower() not in NAO_VERBO]
    return sorted(set(m))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    A, B = [], []
    for p in sorted(BASE.glob("artigos/2*.html")):
        s = p.read_text(encoding="utf-8")
        if "citacao-socio" not in s: continue
        def troca(m):
            texto, cite = m.group(1).strip(), m.group(2).strip()
            mk = marcadores(texto)
            if mk:
                B.append({"slug": p.stem, "cite": cite, "marcadores": mk, "texto": texto}); return "\n"
            A.append({"slug": p.stem, "cite": cite, "texto": texto})
            return '\n<p class="destaque-artigo">' + texto + "</p>\n"
        novo = BLOCO.sub(troca, s)
        novo = re.sub(r"\n{3,}", "\n\n", novo)
        # linha em branco antes do destaque (não colar no parágrafo/lista anterior)
        novo = re.sub(r'\n*<p class="destaque-artigo">', '\n\n<p class="destaque-artigo">', novo)
        if not a.dry_run and novo != s: p.write_text(novo, encoding="utf-8")
    print(f"grupo A (convertidos em destaque): {len(A)} | grupo B (removidos): {len(B)}")
    (BASE / "outputs").mkdir(exist_ok=True)
    rel = BASE / "outputs" / "citacoes-removidas-grupo-B.json"
    if not a.dry_run:
        rel.write_text(json.dumps({"grupo_B_removidos": B, "grupo_A_convertidos": [x["slug"] for x in A]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("relatório:", rel.relative_to(BASE))
    for b in B: print(f"  B {b['slug']} {b['marcadores']}: {b['texto']}")
    if a.dry_run: return
    restos = []
    for p in BASE.glob("artigos/*.html"):
        h = p.read_text(encoding="utf-8")
        if "<cite>" in h or "citacao-socio" in h or re.search(r"OAB[-/ ]?(SP|PR|RJ|MG|\d)", h): restos.append(p.name)
    if restos: print("FALHA: restos ->", restos[:8]); sys.exit(1)
    print("verificação: 0 <cite>, 0 citacao-socio, 0 número/seccional de OAB nos artigos")
    sigla = [p.name for p in BASE.glob("artigos/*.html") if "OAB" in p.read_text(encoding="utf-8")]
    if sigla: print(f"aviso: sigla OAB solta (sem número) em {len(sigla)} artigo(s), em <meta name=keywords> — não alterada")

if __name__ == "__main__":
    main()
